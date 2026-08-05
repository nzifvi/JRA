import socket
import struct
import time
import numpy

class SpatialMapViewer:
    MAGIC = b"HMAP"
    HEADER = "<4sHHfffffH"

    def __init__(self, spatialMap, host = "10.0.0.24", port = 9870, sendInterval = 0.1):
        self._map = spatialMap
        self._interval = sendInterval
        self._target = (host, port)
        self._lastSendTime = 0.0

        self._xExtent = float(spatialMap._xExtent)
        self._yExtent = float(spatialMap._yExtent)
        self._clamp   = float(spatialMap.clamp)

        self._socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

    def update(self, robotX, robotY, force = False):
        now = time.time()
        if not force and now - self._lastSendTime < self._interval:
            return
        self._lastSendTime = now

        try:
            grid = self._map.snapshot()
            header = struct.pack(
                SpatialMapViewer.HEADER,
                SpatialMapViewer.MAGIC,
                grid.shape[0],
                grid.shape[1],
                float(robotX),
                float(robotY),
                self._xExtent,
                self._yExtent,
                self._clamp,
            )
            payload = grid.astype(numpy.float32).tobytes()

            self._socket.sendto(
                header + payload,
                self._target
            )
        except Exception as e:
            print("[VIEWER] send failed. continuing: {}".format(e))

    def close(self):
        try:
            self._socket.close()
        except Exception as e:
            pass