import numpy

class LIDARSimulator:
    def __init__(self, maxRange=12, minRange = 0.3, angularResolution=0.01257,
                 sensorX=0.0, sensorY=0.0, angularVelocity = 62.83, rangeFrequency = 5000):
        # CONSTRUCTOR PARAMETERS' UNITS:
        # - maxRange           : metres
        # - angularResolution  : radians
        # - angularVelocity    : radians / s
        # - rangeFrequency     : Hz
        # - sensorX, sensorY   : metres
        self.maxRange          = maxRange
        self.minRange          = minRange
        self.angularResolution = angularResolution
        self.angularVelocity   = angularVelocity
        self.rangeFrequency    = rangeFrequency
        self.sensorX           = sensorX
        self.sensorY           = sensorY
        self.walls             = []  # list of ((x1, y1), (x2, y2))

        self._neuronsInjectedDuringCurrentRevolution = set()

    def addWall(self, x1, y1, x2, y2):
        self.walls.append(((x1, y1), (x2, y2)))

    def addRectangle(self, x, y, width, height):
        # adds 4 walls forming a rectangle with bottom-left corner at (x, y)
        self.addWall(x,         y,          x + width, y         )  # bottom
        self.addWall(x + width, y,          x + width, y + height)  # right
        self.addWall(x + width, y + height, x,         y + height)  # top
        self.addWall(x,         y + height, x,         y         )  # left

    def scan(self) -> list:
        hits = []
        theta = 0.0
        time = 0.0

        while theta < 2 * numpy.pi:
            theta, hitX, hitY, _ = self.step(theta)
            time += 1.0 / self.rangeFrequency

            if hitX is not None:
                hits.append((hitX, hitY, time))

        return hits

    def _raySegmentIntersection(self, rayOriginX, rayOriginY, rayDirX, rayDirY, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1

        denom = rayDirX * dy - rayDirY * dx

        if abs(denom) < 1e-10:
            return None  # parallel

        t = ((x1 - rayOriginX) * dy - (y1 - rayOriginY) * dx) / denom
        u = ((x1 - rayOriginX) * rayDirY - (y1 - rayOriginY) * rayDirX) / denom

        if t >= 0.0 and 0.0 <= u <= 1.0:
            return t
        return None

    def _modulateAngularVelocity(self, lastRange) -> float:
        modulatedAngularVelocity = (self.angularVelocity * self.minRange) / lastRange
        return float(
            numpy.clip(
                modulatedAngularVelocity,
                1e-4,
                self.angularVelocity
            )
        )

    def step(self, currentAngle: float) -> tuple:
        # cast ray at current angle
        rayDirectionX = numpy.cos(currentAngle)
        rayDirectionY = numpy.sin(currentAngle)
        closestT = self.maxRange

        for (x1, y1), (x2, y2) in self.walls:
            t = self._raySegmentIntersection(
                self.sensorX, self.sensorY,
                rayDirectionX, rayDirectionY,
                x1, y1, x2, y2
            )
            if t is not None and t < closestT:
                closestT = t

        # compute hit
        if closestT < self.maxRange:
            lastRange = closestT
            key = (
                round(round((self.sensorX + closestT * rayDirectionX) / self.minRange) * self.minRange, 10),
                round(round((self.sensorY + closestT * rayDirectionY) / self.minRange) * self.minRange, 10)
            )
            if key not in self._neuronsInjectedDuringCurrentRevolution:
                self._neuronsInjectedDuringCurrentRevolution.add(key)
                hitX = self.sensorX + closestT * rayDirectionX
                hitY = self.sensorY + closestT * rayDirectionY
            else:
                hitX = None
                hitY = None
        else:
            hitX = None
            hitY = None
            lastRange = self.maxRange

        # CLV: modulate ω then integrate θ
        modulatedAngularVelocity = self._modulateAngularVelocity(lastRange)
        nextAngle = currentAngle + modulatedAngularVelocity * (1.0 / self.rangeFrequency)

        return nextAngle, hitX, hitY, closestT, modulatedAngularVelocity

    def resetRevolution(self):
        self._neuronsInjectedDuringCurrentRevolution.clear()