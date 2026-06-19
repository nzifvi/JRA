import numpy
from HESCC import WPSNN
from enum import Enum, auto

class RobotState(Enum):
    ROTATE         = auto()
    DRIVE          = auto()
    INIT           = auto()
    PATH_BLOCKED   = auto()
    FINISHED       = auto()

class MISHController:
    def __init__(self):
        self.allocentricPose = numpy.zeros(3)
        self.HESCC = WPSNN()
        self.robotState = RobotState.INIT

    def _updateAllocentricPose(self):
        allocentricPosEstimate     = self.HESCC.decodePosition()
        allocentricHeadingEstimate = self.HESCC.decodeHeading()

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
        self.HESCC.step()
        self._updateAllocentricPose()

        if self.HESCC.checkPath(self.pathIndex):
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



