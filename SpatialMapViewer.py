import socket
import struct
import time
import numpy


class SpatialMapViewer:
    MAGIC      = b"HMAP"
    PATH_MAGIC = b"HPTH"
    # magic, nx, ny, robotX, robotY, xExtent, yExtent, clamp
    HEADER = "<4sHHfffff"

    def __init__(self, spatialMap, host="10.0.0.24", port=9870, sendInterval=0.1):
        self._map          = spatialMap
        self._interval     = sendInterval
        self._target       = (host, port)
        self._lastSendTime = 0.0
        self._xExtent      = float(spatialMap._xExtent)
        self._yExtent      = float(spatialMap._yExtent)
        self._clamp        = float(spatialMap._currentClamp)
        self._socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

    def update(self, robotX, robotY, force=False):
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
            payload = numpy.ascontiguousarray(grid, dtype=numpy.float32).tobytes()
            self._socket.sendto(header + payload, self._target)
        except Exception as e:
            print("[VIEWER] send failed. continuing: {}".format(e))

    def sendPath(self, path):
        """Transmit a planned path polyline to the laptop receiver.

        path: array-like of shape (N, 2) in world metres (x, y), robot->target
              order, exactly as returned by TrigSpatialMap.pathCoordinates().
              None or empty -> sends a zero-length path (clears the line).
        """
        if path is None:
            points = numpy.empty((0, 2), dtype=numpy.float32)
        else:
            points = numpy.asarray(path, dtype=numpy.float32).reshape(-1, 2)

        count = points.shape[0]
        # UDP payload: 4 + 2 + count*8 bytes. A 51x51 lattice path is at most a
        # few hundred points => a few KB, well under the datagram limit. Guard anyway.
        MAX_POINTS = 8000
        if count > MAX_POINTS:
            # decimate uniformly rather than truncate, so the shape is preserved
            idx = numpy.linspace(0, count - 1, MAX_POINTS).astype(numpy.int64)
            points = points[idx]
            count = points.shape[0]

        header = struct.pack("<4sH", SpatialMapViewer.PATH_MAGIC, count)
        payload = header + numpy.ascontiguousarray(points, dtype=numpy.float32).tobytes()
        try:
            self._socket.sendto(payload, self._target)
        except OSError as e:
            print("[SpatialMapViewer] sendPath failed: {}".format(e))

    def close(self):
        try:
            self._socket.close()
        except Exception:
            pass