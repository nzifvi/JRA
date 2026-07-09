import glob
import re
import time
import threading
import evdev
import serial
import numpy

from Joystick import Joystick
from LIDARInterface import Camera


from GFTC import GFTC
from SignalSystem import BiDirectionalChannel, RobotState

class PIDController:
    def __init__(self, kp, ki, kd, dt, queueCapacity):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt

        self.errorQueue = []
        self.queueCapacity = queueCapacity


    def _calculateDiscretisedIntegral(self, error):
        if len(self.errorQueue) > self.queueCapacity:
            self.errorQueue.pop(0)
        self.errorQueue.append(error)

        return self.dt * (sum(self.errorQueue))

    def _calculateDiscretisedDerivative(self, error):
        if len(self.errorQueue) >= 2:
            return (error - self.errorQueue[-2]) / self.dt
        else:
            return 0

    def calculateDesiredTarget(self, error):
        return (self.kp * error) + (self.ki * self._calculateDiscretisedIntegral(error)) + (self.kd * ())

class BayesOptimalIntegrator:
    # Take measurements, from rotary encoders on the same side, and produce a reliability estimate
    # using Bayes-optimal Integration
    def __init__(self, queueCapacity):
        self.sensor1Readings = []
        self.sensor2Readings = []
        self.queueCapcity = queueCapacity

    def _loadReading(self, queue, reading):
        if len(queue) >= self.queueCapcity:
            queue.pop(0)
        queue.append(reading)

    def _calculateMean(self, queue):
        return sum(queue) / len(queue)

    def _calculateVariance(self, queue):
        mean = self._calculateMean(queue)
        return sum((x - mean) ** 2 for x in queue) / len(queue)

    def _calculatePrecision(self, queue):
        return 1 / self._calculateVariance(queue)

    def _calculatePosteriorPrecision(self) -> tuple:
        sensor1Precision = self._calculatePrecision(self.sensor1Readings)
        sensor2Precision = self._calculatePrecision(self.sensor2Readings)
        return sensor1Precision + sensor2Precision, sensor1Precision, sensor2Precision

    def _calculatePosteriorMean(self):
        posteriorPrecision, sensor1Precision, sensor2Precision = self._calculatePosteriorPrecision()
        sensor1Mean = self._calculateMean(self.sensor1Readings)
        sensor2Mean = self._calculateMean(self.sensor2Readings)

        posteriorMean = sensor1Mean * (sensor1Precision/posteriorPrecision) + sensor2Mean * (sensor2Precision/posteriorPrecision)
        return posteriorMean

class MISHController:
    def __init__(self):
        self.allocentricPose = numpy.zeros(3)
        self.GFTC = GFTC()
        self.robotState = RobotState.INIT

    def _updateAllocentricPose(self):
        allocentricPosEstimate     = self.GFTC.decodePosition()
        allocentricHeadingEstimate = self.GFTC.decodeHeading()

        self.allocentricPose[:2] = [allocentricPosEstimate[0], allocentricPosEstimate[1]]
        self.allocentricPose[2] = allocentricHeadingEstimate

    def _calculateTargetBearingAndDistance(self, targetPosition):
        deltaPos = targetPosition - self.allocentricPose[:2]
        return numpy.arctan2(deltaPos[1], deltaPos[0]), numpy.linalg.norm(deltaPos)

    def _calculateAppliedAngularVelocities(self, deltaTheta, appliedVelocity = 0.0):
        correctedAngularVelocity = self.angularVelocityKP * deltaTheta

        leftWheelAngularVelocity = (appliedVelocity + self.wheelToCentreDist * correctedAngularVelocity) / self.wheelRadius
        rightWheelAngularVelocity = (appliedVelocity - self.wheelToCentreDist * correctedAngularVelocity) / self.wheelRadius

        return leftWheelAngularVelocity, rightWheelAngularVelocity

    def _rotate(self, targetPosition) -> bool:
        targetBearing, _ = self._calculateTargetBearingAndDistance(targetPosition)

        deltaTheta = targetBearing - self.allocentricPose[2]
        deltaTheta = numpy.arctan2(numpy.sin(deltaTheta), numpy.cos(deltaTheta))

        if abs(deltaTheta) < self.angleTolerance:
            return True # rotation finished. current bearing aligned to target bearing
        else:
            leftWheelAngularVelocity, rightWheelAngularVelocity = self._calculateAppliedAngularVelocities(deltaTheta)
            # drive wheels
            return False

    def _drive(self, targetPosition) -> bool:
        targetBearing, targetDistance = self._calculateTargetBearingAndDistance(targetPosition)

        if targetDistance < self.distanceTolerance:
            return True
        else:
            velocityApplied = numpy.clip(
                self.linearVelocityKP * targetDistance,
                0.0,
                self.maxLinearVelocity
            )

            deltaTheta = targetBearing - self.allocentricPose[2]
            deltaTheta = numpy.arctan2(numpy.sin(deltaTheta), numpy.cos(deltaTheta))

            leftWheelAngularVelocity, rightWheelAngularVelocity = self._calculateAppliedAngularVelocities(
                deltaTheta = deltaTheta if abs(deltaTheta) > self.angleTolerance else 0.0,
                appliedVelocity = velocityApplied
            )
            return False

    def step(self):
        self.GFTC.step()
        self._updateAllocentricPose()

        if self.GFTC.checkPath(self.pathIndex):
            self.robotState = RobotState.PATH_BLOCKED

        if self.robotState == RobotState.INIT:
            pass
        elif self.robotState == RobotState.ROTATE:
            isHeadingAligned = self._rotate(self.currentTargetPosition)
            if isHeadingAligned:
                self.robotState = RobotState.DRIVE
        elif self.robotState == RobotState.DRIVE:
            isAtCurrentTargetPosition = self._drive(self.currentTargetPosition)
            if isAtCurrentTargetPosition:
                if len(self.path) == 0:
                    self.robotState = RobotState.FINISHED
                else:
                    self._currentTargetPosition = self.path.dequeue()
                    self.robotState = RobotState.ROTATE
        elif self.robotState == RobotState.PATH_BLOCKED:
            leftWheelAngularVelocity  = 0.0
            rightWheelAngularVelocity = 0.0

            # EMERGENCY STOP: set angular velocities, of all motors, to 0.

            self.pathQueue.clear()
            self.navigateTo(self.finalTargetPosition)
            self.robotState = RobotState.ROTATE

class Supervisor:
    MANUAL_MODE_CODE          = 304
    AUTONOMOUS_MODE_CODE      = 307
    CONNECTION_RETRY_ATTEMPTS = 5

    TELEMETRY_PATTERN = re.compile(
        r'DATA:HDG:([\d\.]+):ENC_FR_DELTA:([-\d]+):ENC_FL_DELTA:([-\d]+):'
        r'ENC_RR_DELTA:([-\d]+):ENC_RL_DELTA:([-\d]+)'
    )

    def __init__(self):
        self.joystick = Joystick(maxRetryAttempts = Supervisor.CONNECTION_RETRY_ATTEMPTS)
        self.camera   = Camera()

        self.currentMode     = "idle"
        self.lastCommandTime = 0.0
        self.lastCommandSent = ""

        self.ser               = None
        self.latestAzimuth     = None
        self.latestEncoderFlow = None

        self._serialReaderThread = None

        self.mish = MISHController()

        self.stopEvent = threading.Event()


    def _findArduinoPort(self):
        ports = glob.glob("/dev/ttyACM*")
        if not ports:
            return None
        for port in ports:
            try:
                s = serial.Serial(port, 9600, timeout=2)
                s.close()
                return port
            except Exception as e:
                print("[ARDUINO] Found {} but couldn't open it: {}".format(port, e))
                continue
        return None

    def _connectArduino(self):
        print("! Searching for Arduino on serial port /dev/ttyACM*...")
        for i in range(self.CONNECTION_RETRY_ATTEMPTS):
            port = self._findArduinoPort()
            if not port:
                print("    - Cannot find Arduino. Retrying")
                time.sleep(2)
                continue
            try:
                ser = serial.Serial(port, 9600, timeout=2)
                print("    - Connected to Arduino on {}".format(port))
                time.sleep(2)
                return ser
            except Exception as e:
                print("Failed to open Arduino on {}: {}".format(port, e))
                time.sleep(2)
        raise RuntimeError(f"! ERROR: could not connect to Ardunio after {self.CONNECTION_RETRY_ATTEMPTS} attempts")

    def _readSerial(self):
        while not self.stopEvent.is_set():
            try:
                if self.ser and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode().strip()
                    m = Supervisor.TELEMETRY_PATTERN.match(line)
                    if m:
                        self.latestAzimuth = float(m.group(1))
                        fr, fl, rr, rl = (int(m.group(i)) for i in (2, 3, 4, 5))
                        self.latestEncoderFlow = (fr + fl + rr + rl) / 4.0
                        print("[TELEMETRY] AZI {:.2f}  FR {}  FL {}  RR {}  RL {}".format(self.latestAzimuth, fr, fl, rr,
                                                                                          rl))
            except Exception as e:
                self.stopAll(f"_readSerial failed: {e}")
            time.sleep(0.05)

    def _writeCommand(self, lin, strafe, rot):
        now = time.time()
        if now - self.lastCommandTime >= 0.05 and self.ser:
            cmd = "CMD:MOVE:{:.2f}:{:.2f}:{:.2f}".format(lin, strafe, rot)
            self.ser.write((cmd + "\n").encode())
            self.lastCommandSent = cmd
            self.lastCommandTime = now

    def start(self):
        try:
            self.ser = self._connectArduino()
        except Exception as e:
            self.stopAll(f"Arduino connection failed: {e}")
            raise
        try:
            self.joystick.connect()
        except Exception as e:
            self.stopAll(f"Joystick connection failed: {e}")
            raise
        try:
            self.camera.start()
        except Exception as e:
            self.stopAll(f"Camera connection failed: {e}")
            raise

        self._serialReaderThread = threading.Thread(target=self._readSerial, daemon = True)
        self._serialReaderThread.start()

        try:
            self.run()
        finally:
            self.stopAll("Robot operation terminated")

    def run(self):
        print("[SUPERVISOR] mode = idle")
        lastControllerConnectionTest = time.time()
        isJoystickConnected = True
        lastAutonomousWarning = 0.0

        while not self.stopEvent.is_set():
            deltaT = time.time() - lastControllerConnectionTest
            try:
                iterationTime = time.time()

                if deltaT > 1.0:
                    isJoystickConnected = self.joystick.isConnected()
                    lastControllerConnectionTest = time.time()

                if isJoystickConnected:
                    for code in self.joystick.pollButtonPresses():
                        if code == self.MANUAL_MODE_CODE:
                            print("[SUPERVISOR] mode = manual")
                            self.currentMode = "manual"
                        elif code == self.AUTONOMOUS_MODE_CODE:
                            print("[SUPERVISOR] mode = autonomous")
                            self.currentMode = "autonomous"
                else:
                    self.currentMode = "idle"

                leftX = self.joystick.getAxis(0)
                leftY = -self.joystick.getAxis(1)
                rightX = self.joystick.getAxis(2)
                rightY = -self.joystick.getAxis(5)

                forward = leftY + rightY

                if self.currentMode == "manual":
                    lin = forward / 127
                    strafe = -leftX / 127
                    rot = rightX / 127
                elif self.currentMode == "autonomous":
                    lin, strafe, rot = 0.0, 0.0, 0.0
                    if self.mish is not None:
                        try:
                            distanceFrame = self.camera.getLatestDistanceFrame() if self.camera else None

                            self.mish.GFTC.setHDInput(
                                heading_rad = self.latestAzimuth * (numpy.pi / 180.0)
                            )
                            # FIGURE OUT HOW TO DIFFERENTIATE OBJECTS AND BOUNDARIES
                            # - PWo must receive a varient of the distanceFrame which focuses on objects.
                            # - PWb must receive a varient of the distanceFrame which focus on boundaries

                            self.mish.step()
                        except Exception as e:
                            if iterationTime - lastAutonomousWarning >= 1.0:
                                print("[AUTONOMOUS] mish.step() raised:", e)
                                lastAutonomousWarning = iterationTime
                else:
                    lin = 0.0
                    strafe = 0.0
                    rot = 0.0

                self._writeCommand(lin, strafe, rot)

            except Exception as e:
                self.stopAll(f"Supervisor.run() failed: {e}")

    def stopAll(self, reason):
        if self.stopEvent.is_set():
            return
        print(f"! FATAL ERROR ENCOUNTERED: {reason}")
        self.stopEvent.set()

        if self.camera:
            self.camera.stop()

        if self._serialReaderThread and self._serialReaderThread is not threading.current_thread():
            self._serialReaderThread.join(timeout=1.0)

        if self.ser:
            self.ser.close()

if __name__ == "__main__":
    supervisor = Supervisor()
    supervisor.start()
