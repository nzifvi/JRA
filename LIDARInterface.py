import serial
import struct
import time
import glob
from enum import Enum

class LIDARInterface:
    def __init__(self, connectionRetryAmount, stopEvent):
        self.serial      = None
        self.retryAmount = connectionRetryAmount
        self.lidarBaud   = 230400
        self.packetLength = 47
        self.measurementLength = 12
        self.msgFormat = "<xBHH" + "HB" * self.measurementLength + "HHB"

        self.stopEvent = stopEvent

    def _findLidarPort(self):
        ports = glob.glob("/dev/ttyUSB*")
        for port in ports:
            try:
                s = serial.Serial(port, self.lidarBaud, timeout = 1)
                s.close()
                return port
            except Exception as e:
                print("[LIDAR] found {} but was unable to open serial connection due to {]".format(port, e))
                return None

    def _connectLIDAR(self):
        for i in range(self.retryAmount):
            port = self._findLidarPort()
            if not port:
                print("    - Cannot find LiDAR. Retrying")
                time.sleep(2)
                continue
            try:
                ser = serial.Serial(port, self.lidarBaud, timeout=1)
                print("    - Connected to LiDAR on {}".format(port))
                return ser
            except Exception as e:
                print("Failed to open LiDAR on {}: {}".format(port, e))
                time.sleep(2)
        raise RuntimeError(f"! ERROR: could not connect to LiDAR after {self.retryAmount} attempts")

    def _parsePacket(self, dataPacket):
        length, speed, startAngle, *posData, stopAngle, timeStamp, crc = struct.unpack(self.msgFormat, dataPacket)

        startAngle = float(startAngle) / 100.0
        stopAngle  = float(stopAngle) / 100.0

        if stopAngle < startAngle:
            stopAngle += 360.0

        stepSize = (stopAngle - startAngle) / (self.measurementLength - 1)

        angle      = [startAngle + stepSize * i for i in range(0, self.measurementLength - 1)]
        distance   = posData[0::2]
        confidence = posData[1::2]

        return list(zip(angle, distance, confidence))

    def run(self):
        LIDARStates = Enum(
            "State",
            ["SYNC_0", "SYNC_1", "SYNC_2", "LOCKED"],
        )
        state = LIDARStates.SYNC_0

        while not self.stopEvent:

