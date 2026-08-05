import numpy

class Odometer:
    def __init__(self, wheelRadius, halfWidth, halfLength, ticksPerRevolution, x = 0.0, y = 0.0):
        self._wheelRadius = wheelRadius
        self._halfWidth = halfWidth
        self._halfLength = halfLength
        self._ticksPerRevolution = ticksPerRevolution
        self._metresPerTick = (2.0 * numpy.pi * wheelRadius) / ticksPerRevolution

        self.x = x
        self.y = y

        self._lastHeading = None

    def _wrap(self, angle) -> numpy.ndarray:
        return numpy.arctan2(
            numpy.sin(angle),
            numpy.cos(angle)
        )

    def reset(self, x = 0.0, y = 0.0, heading = None) -> None:
        self.x = x
        self.y = y

        if heading is not None:
            self._lastHeading = heading
        else:
            self._lastHeading = None

    def update(self, deltaFL, deltaFR, heading) -> None:
        if self._lastHeading is None:
            self._lastHeading = heading


        sFL = deltaFL * self._metresPerTick
        sFR = deltaFR * self._metresPerTick

        dx = 0.25 * (sFL + sFR)
        dy = 0.25 * (-sFL + sFR)

        thetaDelta = self._wrap(heading - self._lastHeading)
        headingMidPoint = self._lastHeading + 0.5 * thetaDelta

        self.x += numpy.cos(headingMidPoint) * dx - numpy.sin(headingMidPoint) * dy
        self.y += numpy.sin(headingMidPoint) * dx + numpy.cos(headingMidPoint) * dy
        self._lastHeading = heading

    def getPose(self) -> tuple:
        if self._lastHeading is None:
            return self.x, self.y, 0.0
        else:
            return self.x, self.y, self._lastHeading