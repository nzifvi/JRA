class PID:
    def __init__(self, getCurrentTime, Kp, Ki, Kd):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd

        self.historicalError = []
        self.getCurrentTime = getCurrentTime
        self.lastTime = self.getCurrentTime()

    def reset(self):
        self.historicalError = []
        self.lastTime = self.getCurrentTime()

    def run(self, target, actual):
        currentError = target - actual
        deltaT = self._calcDeltaTime()
        correction = self.Kp*currentError + (self.Ki*self._sumHistoricalError() * deltaT) + (self.Kd*((currentError - self._getLastError()) / deltaT))
        self._updateHistoricalErrors(currentError)
        self.lastTime = self.getCurrentTime()
        return correction

    def _sumHistoricalError(self):
        if len(self.historicalError) == 0:
            return 0
        else:
            return sum(self.historicalError)

    def _updateHistoricalErrors(self, currentError):
        self.historicalError.append(currentError)

    def _calcDeltaTime(self):
        return self.getCurrentTime() - self.lastTime

    def _getLastError(self):
        if len(self.historicalError) == 0:
            return 0
        else:
            return self.historicalError[-1]
