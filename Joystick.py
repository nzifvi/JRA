import time
import evdev
import select
import threading
from SignalSystem import BiDirectionalChannel

class Joystick:
    def __init__(self, channel:BiDirectionalChannel, maxRetryAttempts, targetName = "Logitech"):
        self.targetName = targetName
        self.device     = None
        self.maxRetryAttempts = maxRetryAttempts
        self.channel = channel

    def connect(self):
        print(f"! Searching for {self.targetName} device")
        for _ in range(self.maxRetryAttempts):
            for p in evdev.list_devices():
                possibleDevice = evdev.InputDevice(p)
                if self.targetName in possibleDevice.name:
                    self.device = possibleDevice
                    print(f"    - Connected to {self.targetName} device on {self.device.path}")
                    return self.device
                possibleDevice.close()
            print(f"    - Cannot find {self.targetName} device. Retrying")
            time.sleep(2)
        raise RuntimeError(f"! ERROR: could not connect to {self.targetName} device after {self.maxRetryAttempts}")

    def isConnected(self) -> bool:
        if self.device is not None and self.device.path in evdev.list_devices():
            return True
        print(f"! FAULT: cannot locate{self.targetName} device")
        return False

    def getAxis(self, axis):
        try:
            return self.device.absinfo(axis).value - 127
        except Exception:
            return 0

    def pollButtonPresses(self):
        pressed = []
        r, _, _ = select.select(
            [self.device.fd],
            [],
            [],
            0
        )
        if r:
            for e in self.device.read():
                if e.type == evdev.ecodes.EV_KEY and e.value == 1:
                    pressed.append(e.code)
        return pressed