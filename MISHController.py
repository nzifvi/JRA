import re
import time
import threading
import serial
import glob
import numpy
from enum import Enum, auto
import queue

from Joystick import Joystick
from LIDARInterface import LIDARInterface
from Odometer import Odometer
from SpatialMap import TrigSpatialMap

from SpatialMapViewer import SpatialMapViewer

class SpatialMapThreadStates(Enum):
    INJECTING       = auto()
    PROPAGATE       = auto()
    PROPAGATING     = auto()
    BACKPROPAGATING = auto()
    PATH_COMPLETE   = auto()

class RobotStates(Enum):
    IDLE       = auto()
    NAV        = auto()
    CORRECTION = auto()

class NavigationStates(Enum):
    IDLE      = auto()
    ROTATE    = auto()
    TRANSLATE = auto()

# Standalone planner-client sub-FSM, independent of drive mode.
class PlanStates(Enum):
    IDLE          = auto()
    AWAITING_PLAN = auto()

class MISHController:
    MANUAL_CODE               = 304
    AUTONOMOUS_CODE           = 307
    PLAN_TRIGGER_CODE         = 306
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

    ROT_TOLERANCE = numpy.deg2rad(3.0)
    DIST_TOLERANCE = 0.10 # m
    ROT_TIME_OUT = 5.0 #s
    TRANSLATE_TIME_OUT = 8.0 #s
    ROT_KP = 10.0
    ROT_KI = 10.0
    ROT_KD = 0.10
    DIST_KP = 0.0
    DIST_KI = 0.0
    DIST_KD = 0.0
    ROT_INTEGRAL_CLAMP = numpy.deg2rad(90.0)
    DIST_INTEGRAL_CLAMP = 0.5
    CMD_CLAMP = 1.0

    HARDCODED_TARGET  = (0.8, -0.3)  # world metres (x, y); a reachable open cell



    TELEMETRY_PATTERN = re.compile(
        r'DATA:HDG:([+-]?\d+(?:\.\d+)?):ENC_FR_DELTA:([+-]?\d+):'
        r'ENC_FL_DELTA:([+-]?\d+):ENC_RR_DELTA:([+-]?\d+):'
        r'ENC_RL_DELTA:([+-]?\d+)'
    )

    def __init__(self):
        self.joystick = Joystick(maxRetryAttempts=MISHController.CONNECTION_RETRY_ATTEMPTS)

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
            wheelRadius        = MISHController.WHEEL_RADIUS,
            halfWidth          = MISHController.HALF_WIDTH,
            halfLength         = MISHController.HALF_LENGTH,
            ticksPerRevolution = MISHController.TICKS_PER_REVOLUTION,
        )
        self._poseLock    = threading.Lock()

        self.lidar = LIDARInterface(
            connectionRetryAmount = MISHController.CONNECTION_RETRY_ATTEMPTS,
            stopEvent             = self.stopEvent,
        )
        self.spatialMap = TrigSpatialMap()

        self._planReqQueue = queue.Queue(maxsize = 1)
        self._pathQueue    = queue.Queue()

        self._lastDt        = None
        self._rotIntegral   = 0.0
        self._prevRotError  = None
        self._distIntegral  = 0.0
        self._prevDistError = None

    def _findArduinoPort(self):
        for port in glob.glob("/dev/ttyACM*"):
            try:
                s = serial.Serial(port, MISHController.BAUD_RATE, timeout=2)
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
                ser = serial.Serial(port, MISHController.BAUD_RATE, timeout=2)
                print("    - Connected to Arduino on {} at {} baud".format(
                    port, MISHController.BAUD_RATE))
                time.sleep(2)
                ser.timeout = MISHController.SERIAL_READ_TIMEOUT
                ser.reset_input_buffer()
                return ser
            except Exception as e:
                print("Failed to open Arduino on {}: {}".format(port, e))
                time.sleep(2)
        raise RuntimeError(
            "! ERROR: could not connect to Arduino after {} attempts".format(
                self.CONNECTION_RETRY_ATTEMPTS))

    def _handleTelemetryLine(self, line):
        m = MISHController.TELEMETRY_PATTERN.match(line)
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

        fr = fr * MISHController.ENCODER_SIGN
        fl = fl * MISHController.ENCODER_SIGN

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

                if len(self._rxBuffer) > MISHController.MAX_RX_BUFFER:
                    self._rxBuffer = b""

                while b"\n" in self._rxBuffer:
                    raw, self._rxBuffer = self._rxBuffer.split(b"\n", 1)
                    line = raw.decode(errors="replace").strip()
                    if line:
                        self._handleTelemetryLine(line)

                time.sleep(MISHController.SERIAL_POLL_PERIOD)

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

        state = SpatialMapThreadStates.INJECTING
        isWavePropagationInitiated = False
        wavePropagationSteps       = 0

        robotX  = None
        robotY  = None
        targetX = None
        targetY = None

        while not self.stopEvent.is_set():
            if state == SpatialMapThreadStates.INJECTING:
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
                                azimuthVec=azimuthVec,
                                distanceVec=distanceVec,
                                heading=heading,
                                robotX=x,
                                robotY=y,
                                sigma=0.05
                            )
                            lastInject = now

                            targetSteps = int((now - startTime) * 1000.0
                                              * self.TIME_SCALE / self.MODEL_DT_MS)
                            budget = min(targetSteps - self._modelSteps,
                                         self.MAX_CATCHUP_STEPS)

                            if budget > 0:
                                for _ in range(budget):
                                    self.spatialMap.step()
                                self._modelSteps += budget

                        # Plan requests arrive from run() via _planReqQueue,
                        # triggered by the B button. The injection loop only plans
                        # on demand. Polled every tick, independent of step budget.
                        try:
                            targetX, targetY = self._planReqQueue.get_nowait()
                            state = SpatialMapThreadStates.PROPAGATING
                        except queue.Empty:
                            pass
                except Exception as e:
                    self.stopAll("_injectionLoop failed: {}".format(e))

            elif state == SpatialMapThreadStates.PROPAGATING:
                if not isWavePropagationInitiated:
                    with self._poseLock:
                        robotX, robotY, _ = self.odometer.getPose()

                    if robotX is None or robotY is None:
                        # cannot propagate without a valid source pose; abandon
                        # this plan and let run() time out / re-request.
                        print("! [_injectionLoop] no pose for wave source; "
                              "aborting plan")
                        self._pathQueue.put(None)
                        targetX = targetY = None
                        state = SpatialMapThreadStates.INJECTING
                        continue

                    self.spatialMap.resetWaveProp()
                    self.spatialMap.propagateWave(
                        robotX = robotX,
                        robotY = robotY,
                    )
                    isWavePropagationInitiated = True
                    wavePropagationSteps = 0

                # Step the model so the wavefront actually propagates through the
                # SpatialMap population. Stepping exactly _duration times fills the
                # recording ring (num_recording_timesteps=duration) without overwrite.
                self.spatialMap.step()
                wavePropagationSteps += 1

                if wavePropagationSteps >= self.spatialMap._duration:
                    isWavePropagationInitiated = False
                    wavePropagationSteps = 0
                    state = SpatialMapThreadStates.BACKPROPAGATING

            elif state == SpatialMapThreadStates.BACKPROPAGATING:
                if targetX is None or targetY is None:
                    print("! targetX or targetY are unassigned. Returning to INJECTING state")
                    self._pathQueue.put(None)
                    state = SpatialMapThreadStates.INJECTING
                else:
                    try:
                        hasBackpropReachedTargetNeuron = self.spatialMap.backpropagateWave(
                            robotX = robotX,
                            robotY = robotY,
                            targetX = targetX,
                            targetY = targetY
                        )
                    except ValueError as e:
                        # target binned outside the lattice, etc.
                        print("! [_injectionLoop] backprop rejected target: {}".format(e))
                        self._pathQueue.put(None)
                        targetX = targetY = None
                        state = SpatialMapThreadStates.INJECTING
                        continue

                    if hasBackpropReachedTargetNeuron:
                        state = SpatialMapThreadStates.PATH_COMPLETE
                    else:
                        print("! Wavepropagation did not reach target neuron. Returning to INJECTING state")
                        self._pathQueue.put(None)
                        targetX = targetY = None
                        state = SpatialMapThreadStates.INJECTING

            elif state == SpatialMapThreadStates.PATH_COMPLETE:
                self._pathQueue.put(self.spatialMap.pathCoordinates())
                targetX = None
                targetY = None
                state = SpatialMapThreadStates.INJECTING

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

    def _sendPathToViewer(self, viewer, path):
        # Forward the planned path polyline to the laptop-side receiver for
        # display. viewer.sendPath is a visualiser-side method you still need to
        # implement; guarded so a missing method degrades gracefully rather than
        # killing the run loop.
        if path is None:
            return
        sender = getattr(viewer, "sendPath", None)
        if sender is None:
            print("[MISHController] viewer has no sendPath(); path not displayed")
            return
        try:
            sender(path)
        except Exception as e:
            print("[MISHController] sendPath failed: {}".format(e))

    def run(self):
        print("[SUPERVISOR] mode = idle")
        lastControllerConnectionTest = time.time()
        isJoystickConnected = True

        viewer = SpatialMapViewer(
            spatialMap = self.spatialMap,
            host       = "10.0.0.1"
        )

        # --- standalone planner client (independent of drive mode) ---
        planState     = PlanStates.IDLE
        targetX       = None
        targetY       = None
        path          = None          # most recent successfully planned path
        pendingReplan = False         # set by NAV when a fresh plan is needed

        # --- drive FSM ---
        robotState    = RobotStates.IDLE
        navState      = NavigationStates.IDLE
        waypointIndex = 0
        missionActive = False         # true once autonomous has armed on a path

        navigationTargetHeading  = None
        navigationTargetWaypoint = None
        waypointStartTime        = 0.0

        while not self.stopEvent.is_set():
            try:
                # --- joystick liveness ---
                if time.time() - lastControllerConnectionTest > 1.0:
                    isJoystickConnected = self.joystick.isConnected()
                    lastControllerConnectionTest = time.time()

                # --- mode selection (autonomous is GATED on a held path) ---
                if isJoystickConnected:
                    for code in self.joystick.pollButtonPresses():
                        if code == self.MANUAL_CODE:
                            self.currentMode = "manual"
                            missionActive = False
                            print("[MISHController] mode set to manual")
                        elif code == self.AUTONOMOUS_CODE:
                            if path is not None and len(path) > 0:
                                self.currentMode = "autonomous"
                                robotState    = RobotStates.NAV
                                navState      = NavigationStates.IDLE
                                waypointIndex = 0
                                missionActive = True
                                print("[MISHController] mode set to autonomous; "
                                      "driving planned path")
                            else:
                                print("[MISHController] autonomous refused: "
                                      "no path planned. Press B to plan first.")
                        elif code == self.PLAN_TRIGGER_CODE:
                            # B button: plan a wavepath to the hardcoded target
                            # from the current pose. Does not change drive mode.
                            targetX, targetY = self.HARDCODED_TARGET
                            pendingReplan = True
                            print("[MISHController] B pressed: planning to "
                                  "hardcoded target ({:.2f}, {:.2f})".format(
                                      targetX, targetY))
                        else:
                            self.currentMode = "idle"
                            missionActive = False

                # --- standalone planner sub-FSM (runs every loop, any mode) ---
                if planState == PlanStates.IDLE:
                    # A plan is requested only via pendingReplan: set by the B
                    # button (fresh plan to the hardcoded target) or by NAV
                    # (re-plan from the current pose during a mission).
                    if pendingReplan and targetX is not None:
                        try:
                            self._planReqQueue.put_nowait((targetX, targetY))
                            planState     = PlanStates.AWAITING_PLAN
                            pendingReplan = False
                        except queue.Full:
                            pass  # a plan is already in flight
                elif planState == PlanStates.AWAITING_PLAN:
                    try:
                        newPath = self._pathQueue.get_nowait()
                        planState = PlanStates.IDLE
                        if newPath is None or len(newPath) == 0:
                            print("[MISHController] planning failed: no path to target")
                            path = None
                            if missionActive:
                                # mission can't continue without a path
                                missionActive = False
                                robotState = RobotStates.IDLE
                                self.currentMode = "idle"
                        else:
                            path = newPath
                            waypointIndex = 0
                            self._sendPathToViewer(viewer, path)
                            print("[MISHController] path planned ({} waypoints)".format(
                                len(path)))
                    except queue.Empty:
                        pass

                # --- viewer (guard against pre-telemetry None pose) ---
                with self._poseLock:
                    x, y, heading = self.odometer.getPose()
                if x is not None and y is not None and heading is not None:
                    viewer.update(x, y, heading)

                # --- MANUAL ---
                if self.currentMode == "manual":
                    leftX  = self.joystick.getAxis(0)
                    leftY  = -self.joystick.getAxis(1)
                    rightX = self.joystick.getAxis(2)
                    rightY = -self.joystick.getAxis(5)
                    self._writeCommand((leftY + rightY) / 127,
                                       -leftX / 127,
                                       rightX / 127)

                # --- AUTONOMOUS (drive the already-planned path) ---
                elif self.currentMode == "autonomous":

                    if robotState == RobotStates.NAV:
                        if navState == NavigationStates.IDLE:
                            if path is None or waypointIndex >= len(path):
                                robotState = RobotStates.CORRECTION
                                navState   = NavigationStates.IDLE
                            else:
                                waypoint = path[waypointIndex]
                                navigationTargetWaypoint = (float(waypoint[0]),
                                                            float(waypoint[1]))
                                with self._poseLock:
                                    xPos, yPos, _ = self.odometer.getPose()
                                navigationTargetHeading = numpy.arctan2(
                                    waypoint[1] - yPos,
                                    waypoint[0] - xPos
                                )
                                self._rotIntegral  = 0.0
                                self._prevRotError = None
                                self._lastDt       = None
                                waypointStartTime  = time.time()
                                navState = NavigationStates.ROTATE

                        elif navState == NavigationStates.ROTATE:
                            if time.time() - waypointStartTime > self.ROT_TIME_OUT:
                                print("[NAV] rotate timeout on waypoint {}".format(
                                    waypointIndex))
                                self._writeCommand(0.0, 0.0, 0.0)
                                navState = NavigationStates.TRANSLATE
                                self._distIntegral  = 0.0
                                self._prevDistError = None
                                self._lastDt        = None
                                waypointStartTime   = time.time()
                            elif self._rotateStep(navigationTargetHeading):
                                navState = NavigationStates.TRANSLATE
                                self._distIntegral  = 0.0
                                self._prevDistError = None
                                self._lastDt        = None
                                waypointStartTime   = time.time()

                        elif navState == NavigationStates.TRANSLATE:
                            if time.time() - waypointStartTime > self.TRANSLATE_TIME_OUT:
                                print("[NAV] translate timeout on waypoint {}".format(
                                    waypointIndex))
                                self._writeCommand(0.0, 0.0, 0.0)
                                navState = NavigationStates.IDLE
                                # re-plan: ask the planner sub-FSM for a fresh path
                                # from the current pose. path is left intact so the
                                # autonomous gate / missionActive is preserved.
                                pendingReplan = True
                            elif self._translateStep(navigationTargetWaypoint):
                                self._writeCommand(0.0, 0.0, 0.0)
                                navState = NavigationStates.IDLE
                                # goal-reached test against the TRUE target, not
                                # the intermediate waypoint.
                                if targetX is None or targetY is None:
                                    robotState = RobotStates.CORRECTION
                                else:
                                    with self._poseLock:
                                        xPos, yPos, _ = self.odometer.getPose()
                                    goalDist = float(numpy.hypot(targetX - xPos,
                                                                 targetY - yPos))
                                    if goalDist <= self.DIST_TOLERANCE:
                                        robotState = RobotStates.CORRECTION
                                    else:
                                        # re-plan afresh toward the same goal
                                        pendingReplan = True

                    elif robotState == RobotStates.CORRECTION:
                        self._writeCommand(0.0, 0.0, 0.0)
                        print("[MISHController] target reached; goal cleared")
                        targetX = targetY = None
                        path = None
                        missionActive = False
                        robotState = RobotStates.IDLE
                        navState   = NavigationStates.IDLE
                        self.currentMode = "idle"

                    else:
                        # RobotStates.IDLE inside autonomous: nothing to drive
                        self._writeCommand(0.0, 0.0, 0.0)

                # --- IDLE mode: hold still ---
                else:
                    self._writeCommand(0.0, 0.0, 0.0)

                time.sleep(self.CONTROL_PERIOD)

            except Exception as e:
                self.stopAll("run loop failed: {}".format(e))

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

    def _getDt(self) -> float:
        now = time.time()
        dt = self.CONTROL_PERIOD if self._lastDt is None else now - self._lastDt
        self._lastDt = now
        return dt

    def _rotateStep(self, targetHeading):
        current = self.latestHeading
        if current is None:
            return False

        error = numpy.arctan2(
            numpy.sin(targetHeading - current),
            numpy.cos(targetHeading - current)
        )
        if abs(error) <= self.ROT_TOLERANCE:
            self._writeCommand(0.0, 0.0, 0.0)
            self._rotIntegral = 0.0
            self._prevRotError = None
            return True

        dt = self._getDt()
        self._rotIntegral += error * dt
        dError = 0.0 if self._prevRotError is None else (error - self._prevRotError) / dt
        self._prevRotError = error

        command = self.ROT_KP * error + self.ROT_KI * self._rotIntegral + self.ROT_KD * dError
        self._writeCommand(
            lin = 0.0,
            strafe = 0.0,
            rot = int(numpy.clip(command, -127, 127)) / 127
        )
        return False

    def _translateStep(self, target):
        with self._poseLock:
            x, y, heading = self.odometer.getPose()
        if x is None:
            return False

        dx = target[0] - x
        dy = target[1] - y
        error = float(numpy.hypot(dx, dy))

        if error <= self.DIST_TOLERANCE:
            self._writeCommand(0.0, 0.0, 0.0)
            self._distIntegral = 0.0
            self._prevDistError = None
            return True

        dt = self._getDt()
        self._distIntegral += error * dt
        dError = 0.0 if self._prevDistError is None else (error - self._prevDistError) / dt
        self._prevDistError = error

        command = self.DIST_KP * error + self.DIST_KI * self._distIntegral + self.DIST_KD * dError
        self._writeCommand(
            lin = int(numpy.clip(command, -127, 127)) / 127,
            strafe = 0.0,
            rot = 0.0
        )
        return False

if __name__ == "__main__":
    supervisor = MISHController()
    supervisor.start()