import re
import time
import threading

import serial
import glob
import numpy

import os

from Joystick import Joystick
from LIDARInterface import LIDARInterface
from Odometer import Odometer
from SpatialMap import TrigSpatialMap

from SpatialMapViewer import SpatialMapViewer


class Supervisor:
    MANUAL_MODE_CODE          = 304
    SAVE_DATA_CODE            = 307
    CONNECTION_RETRY_ATTEMPTS = 5
    CONTROL_PERIOD            = 0.05 # 20 Hz
    INJECTION_PERIOD          = 0.02 # 50 Hz
    SNAPSHOT_PERIOD           = 1.0 # 1 Hz
    BAUD_RATE           = 9600
    SERIAL_READ_TIMEOUT = 0.05
    SERIAL_POLL_PERIOD  = 0.005
    MAX_RX_BUFFER       = 8192

    # encoder polarity is inverted (god knows why)
    ENCODER_SIGN = -1

    MODEL_DT_MS        = 1.0
    TIME_SCALE         = 1.0
    MAX_CATCHUP_STEPS  = 50

    WHEEL_RADIUS         = 0.045 # m
    HALF_WIDTH           = 0.1225  # m  (l_x)
    HALF_LENGTH          = 0.1275  # m  (l_y)
    TICKS_PER_REVOLUTION = 660  # output shaft: CPR x gearing x quadrature (calibrated by manually minimising pose error against a known distance)

    TELEMETRY_PATTERN = re.compile(
        r'DATA:HDG:([+-]?\d+(?:\.\d+)?):ENC_FR_DELTA:([+-]?\d+):'
        r'ENC_FL_DELTA:([+-]?\d+):ENC_RR_DELTA:([+-]?\d+):'
        r'ENC_RL_DELTA:([+-]?\d+)'
    )

    def __init__(self):
        self.joystick = Joystick(maxRetryAttempts=Supervisor.CONNECTION_RETRY_ATTEMPTS)

        self.currentMode     = "idle"
        self.lastCommandTime = 0.0
        self.lastCommandSent = ""

        self.ser           = None
        self.latestHeading = None       # radians

        self._serialReaderThread          = None
        self._lidarThread                 = None
        self._spatialMapInjectionThread   = None

        self._rxBuffer   = b""
        self._modelSteps = 0
        self._telemetryAccepted = 0
        self._telemetryRejected = 0
        self._lastRejectWarning = 0.0

        self.stopEvent = threading.Event()

        self.odometer  = Odometer(
            wheelRadius        = Supervisor.WHEEL_RADIUS,
            halfWidth          = Supervisor.HALF_WIDTH,
            halfLength         = Supervisor.HALF_LENGTH,
            ticksPerRevolution = Supervisor.TICKS_PER_REVOLUTION,
        )
        self._poseLock    = threading.Lock()

        self.lidar = LIDARInterface(
            connectionRetryAmount = Supervisor.CONNECTION_RETRY_ATTEMPTS,
            stopEvent             = self.stopEvent,
        )
        self.spatialMap = TrigSpatialMap()

    def _findArduinoPort(self):
        for port in glob.glob("/dev/ttyACM*"):
            try:
                s = serial.Serial(port, Supervisor.BAUD_RATE, timeout=2)
                s.close()
                return port
            except Exception as e:
                print("[ARDUINO] Found {} but couldn't open it: {}".format(port, e))
                continue
        return None

    def _connectArduino(self):
        print("! Searching for Arduino on serial port /dev/ttyACM*...")
        for _ in range(self.CONNECTION_RETRY_ATTEMPTS):
            port = self._findArduinoPort()
            if not port:
                print("    - Cannot find Arduino. Retrying")
                time.sleep(2)
                continue
            try:
                ser = serial.Serial(port, Supervisor.BAUD_RATE, timeout=2)
                print("    - Connected to Arduino on {} at {} baud".format(
                    port, Supervisor.BAUD_RATE))
                time.sleep(2)
                ser.timeout = Supervisor.SERIAL_READ_TIMEOUT
                ser.reset_input_buffer()
                return ser
            except Exception as e:
                print("Failed to open Arduino on {}: {}".format(port, e))
                time.sleep(2)
        raise RuntimeError(
            "! ERROR: could not connect to Arduino after {} attempts".format(
                self.CONNECTION_RETRY_ATTEMPTS))

    def _handleTelemetryLine(self, line):
        m = Supervisor.TELEMETRY_PATTERN.match(line)
        if m is None:
            self._telemetryRejected += 1
            now = time.time()
            if now - self._lastRejectWarning > 5.0:
                total = self._telemetryAccepted + self._telemetryRejected
                print("[TELEMETRY] {} / {} lines rejected ({:.1f}%). "
                      "Last: {!r}".format(self._telemetryRejected, total,
                                          100.0 * self._telemetryRejected / max(1, total),
                                          line[:80]))
                self._lastRejectWarning = now
            return

        try:
            heading = numpy.radians(float(m.group(1)))
            # NOTE: rear wheel encoders are disregarded due to them being disconnected
            fr, fl, _, _ = (int(m.group(i)) for i in (2, 3, 4, 5))
        except ValueError:
            self._telemetryRejected += 1
            return

        s = Supervisor.ENCODER_SIGN
        fr = fr * -1
        fl = fl * -1

        self._telemetryAccepted += 1
        with self._poseLock:
            self.odometer.update(fl, fr, heading)
            self.latestHeading = heading

    def _readSerial(self):
        while not self.stopEvent.is_set():
            try:
                if self.ser is None:
                    time.sleep(0.05)
                    continue

                waiting = self.ser.in_waiting
                chunk = self.ser.read(waiting if waiting > 0 else 1)
                if chunk:
                    self._rxBuffer += chunk

                if len(self._rxBuffer) > Supervisor.MAX_RX_BUFFER:
                    self._rxBuffer = b""

                while b"\n" in self._rxBuffer:
                    raw, self._rxBuffer = self._rxBuffer.split(b"\n", 1)
                    line = raw.decode(errors="replace").strip()
                    if line:
                        self._handleTelemetryLine(line)

                time.sleep(Supervisor.SERIAL_POLL_PERIOD)

            except (serial.SerialException, OSError) as e:
                self.stopAll("_readSerial serial failure: {}".format(e))
            except Exception as e:
                print("[SERIAL] non-fatal error: {}".format(e))
                time.sleep(0.05)

    def _writeCommand(self, lin, strafe, rot):
        now = time.time()
        if now - self.lastCommandTime >= 0.05 and self.ser:
            cmd = "CMD:MOVE:{:.2f}:{:.2f}:{:.2f}".format(lin, strafe, rot)
            self.ser.write((cmd + "\n").encode())
            self.lastCommandSent = cmd
            self.lastCommandTime = now

    def _injectionLoop(self):
        lastInject = 0.0
        startTime = time.time()
        self._modelSteps = 0
        lastLagWarning = 0.0

        while not self.stopEvent.is_set():
            try:
                now = time.time()

                if now - lastInject >= self.INJECTION_PERIOD:
                    azimuthVec, distanceVec = self.lidar.readCache()
                    with self._poseLock:
                        x, y, heading = self.odometer.getPose()

                    if (x is None or y is None or heading is None
                            or azimuthVec is None or distanceVec is None):
                        pass
                    else:
                        self.spatialMap.gaussianInject(
                            azimuthVec=azimuthVec, distanceVec=distanceVec,
                            heading=heading, robotX=x, robotY=y, sigma=0.05)
                    lastInject = now

                targetSteps = int((now - startTime) * 1000.0
                                  * self.TIME_SCALE / self.MODEL_DT_MS)
                budget = min(targetSteps - self._modelSteps,
                             self.MAX_CATCHUP_STEPS)

                if budget <= 0:
                    time.sleep(0.0005)
                    continue

                for _ in range(budget):
                    self.spatialMap.step()
                self._modelSteps += budget

                if (targetSteps - self._modelSteps > 500
                        and now - lastLagWarning > 5.0):
                    print("[TIMING] model time is {} steps behind wall clock; "
                          "reduce TIME_SCALE or the map dynamics will run "
                          "slow".format(targetSteps - self._modelSteps))
                    lastLagWarning = now

            except Exception as e:
                self.stopAll("_injectionLoop failed: {}".format(e))

    def start(self):
        try:
            self.ser = self._connectArduino()
        except Exception as e:
            self.stopAll("Arduino connection failed: {}".format(e))
            raise
        try:
            self.joystick.connect()
        except Exception as e:
            self.stopAll("Joystick connection failed: {}".format(e))
            raise

        self._serialReaderThread = threading.Thread(
            target=self._readSerial,
            daemon=True
        )
        self._lidarThread = threading.Thread(
            target=self.lidar.run,
            daemon=True
        )
        self._spatialMapInjectionThread = threading.Thread(
            target = self._injectionLoop,
            daemon = True
        )
        self._serialReaderThread.start()
        self._lidarThread.start()
        self._spatialMapInjectionThread.start()

        try:
            self.run()
        finally:
            self.stopAll("Robot operation terminated")

    def run(self):
        print("[SUPERVISOR] mode = idle")
        lastControllerConnectionTest = time.time()
        isJoystickConnected = True

        viewer = SpatialMapViewer(
            spatialMap = self.spatialMap,
            host       = "10.0.0.1"
        )

        while not self.stopEvent.is_set():
            deltaT = time.time() - lastControllerConnectionTest
            try:
                if deltaT > 1.0:
                    isJoystickConnected = self.joystick.isConnected()
                    lastControllerConnectionTest = time.time()

                if isJoystickConnected:
                    for code in self.joystick.pollButtonPresses():
                        if code == self.MANUAL_MODE_CODE:
                            print("[SUPERVISOR] mode = manual")
                            self.currentMode = "manual"
                else:
                    self.currentMode = "idle"

                with self._poseLock:
                    x, y, _ = self.odometer.getPose()
                viewer.update(robotX=x, robotY=y)

                leftX  = self.joystick.getAxis(0)
                leftY  = -self.joystick.getAxis(1)
                rightX = self.joystick.getAxis(2)
                rightY = -self.joystick.getAxis(5)

                forward = leftY + rightY

                if self.currentMode == "manual":
                    lin    = forward / 127
                    strafe = -leftX / 127
                    rot    = rightX / 127
                elif self.currentMode == "save":
                    print("[SUPERVISOR] saving complete. returning to manual mode")
                    self.currentMode = "manual"
                    lin = strafe = rot = 0.0
                else:
                    lin = strafe = rot = 0.0

                # NOTE: due to modelling robot as having differential drive, strafe is disabled
                self._writeCommand(lin, strafe, rot)

            except Exception as e:
                self.stopAll("Supervisor.run() failed: {}".format(e))

            time.sleep(self.CONTROL_PERIOD)

    def stopAll(self, reason):
        if self.stopEvent.is_set():
            return
        print("! FATAL ERROR ENCOUNTERED: {}".format(reason))

        total = self._telemetryAccepted + self._telemetryRejected
        if total:
            print("  telemetry: {} accepted, {} rejected ({:.1f}% loss)".format(
                self._telemetryAccepted, self._telemetryRejected,
                100.0 * self._telemetryRejected / total))

        self.stopEvent.set()

        if self._serialReaderThread and self._serialReaderThread is not threading.current_thread():
            self._serialReaderThread.join(timeout=1.0)

        if self._lidarThread and self._lidarThread is not threading.current_thread():
            self._lidarThread.join(timeout=1.0)

        if self._spatialMapInjectionThread and self._spatialMapInjectionThread is not threading.current_thread():
            self._spatialMapInjectionThread.join(timeout=1.0)

        if self.ser:
            self.ser.close()
        self.lidar.close()


if __name__ == "__main__":
    supervisor = Supervisor()
    supervisor.start()