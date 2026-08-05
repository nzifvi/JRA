import serial
import struct
import time
import glob
from enum import Enum
import traceback
import numpy

import threading


class LIDARInterface:
    SENSOR_RANGE = 12.0

    def __init__(self, connectionRetryAmount, stopEvent):
        self.serial            = None
        self.retryAmount       = connectionRetryAmount
        self.lidarBaud         = 230400
        self.packetLength      = 47
        self.measurementLength = 12
        self.msgFormat = "<xBHH" + "HB" * self.measurementLength + "HHB"

        self.stopEvent   = stopEvent
        self._cachedData = None

        self._minConfidence = 20.0

        self._cacheLock = threading.Lock()

    def _findLidarPort(self):
        for port in glob.glob("/dev/ttyUSB*"):
            try:
                s = serial.Serial(port, self.lidarBaud, timeout=1)
                s.close()
                return port
            except Exception as e:
                print("[LIDAR] found {} but was unable to open it: {}".format(port, e))
                continue
        return None

    def _connectLIDAR(self):
        for _ in range(self.retryAmount):
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
        raise RuntimeError(
            "! ERROR: could not connect to LiDAR after {} attempts".format(self.retryAmount))

    def _parsePacket(self, dataPacket):
        length, speed, startAngle, *posData, stopAngle, timeStamp, crc = \
        struct.unpack(self.msgFormat, dataPacket)

        arrivalTime = time.monotonic()

        startAngle = float(startAngle) / 100.0
        stopAngle  = float(stopAngle) / 100.0
        if stopAngle < startAngle:
            stopAngle += 360.0

        angleSpan = stopAngle - startAngle
        stepSize = angleSpan / (self.measurementLength - 1)
        dtPacket = angleSpan / speed if speed > 0 else 0.0

        points = []
        for i in range(self.measurementLength):
            az = (startAngle + stepSize * i) % 360.0
            dist = posData[2 * i] / 1000.0
            conf = posData[2 * i + 1]

            captureTime = arrivalTime - dtPacket * (1.0 - i / (self.measurementLength - 1))

            if conf >= self._minConfidence and 0.0 < dist <= self.SENSOR_RANGE:
                points.append(
                    (captureTime, az, dist)
                )

        return arrivalTime, points

    def run(self):
        try:
            self.serial = self._connectLIDAR()
        except Exception as e:
            print("[LIDAR] failed to connect: {}".format(e))
            self.stopEvent.set()
            return

        LIDARStates = Enum("State", ["SYNC_0", "SYNC_1", "SYNC_2", "LOCKED"])
        state = LIDARStates.SYNC_0
        data = b''

        while not self.stopEvent.is_set():
            try:
                if state == LIDARStates.SYNC_0:
                    data = b''
                    if self.serial.read() == b'\x54':
                        data = b'\x54'
                        state = LIDARStates.SYNC_1

                elif state == LIDARStates.SYNC_1:
                    if self.serial.read() == b'\x2C':
                        data += b'\x2C'
                        state = LIDARStates.SYNC_2
                    else:
                        state = LIDARStates.SYNC_0

                elif state == LIDARStates.SYNC_2:
                    data += self.serial.read(self.packetLength - 2)
                    if len(data) != self.packetLength:
                        state = LIDARStates.SYNC_0
                        continue
                    _, points = self._parsePacket(data)
                    self._updateCache(points)
                    state = LIDARStates.LOCKED

                elif state == LIDARStates.LOCKED:
                    data = self.serial.read(self.packetLength)
                    if (len(data) != self.packetLength
                            or data[0] != 0x54
                            or data[1] != 0x2C):
                        print("[LIDAR] warning: serial sync lost. resyncing")
                        state = LIDARStates.SYNC_0
                        continue
                    _, points = self._parsePacket(data)
                    self._updateCache(points)

            except Exception as e:
                print("[LIDAR] error: {}".format(e))
                traceback.print_exc()
                self.stopEvent.set()
                return

    def close(self):
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass

    def _updateCache(self, data):
        self._cacheLock.acquire()
        self._cachedData = data
        self._cacheLock.release()

    def readCache(self):
        self._cacheLock.acquire()
        temp = self._cachedData
        self._cacheLock.release()

        azimuths     = []
        distances    = []

        for _, az, dist in temp:
            azimuths.append(az)
            distances.append(dist)

        return numpy.array(azimuths), numpy.array(distances)
