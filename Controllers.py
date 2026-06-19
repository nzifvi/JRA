import pigpio

class Device:
    def __init__(self, pins:tuple):
        self.pins = pins

    def status(self) -> bool:
        # function is called to ensure that Device has been initialised correctly, without fault.
        # - returns True to indicate ready.
        # - returns False to indicate failure.
        pass

    def getPin(self) -> tuple:
        return self.pins

class LIDARController(Device):
    def __init__(self, pin):
        super().__init__(pin)

class MotorController(Device):
    def __init__(self, pin):
        super().__init__(pin)

class Encoder(Device):
    def __init__(self, pin):
        super().__init__(pin)
