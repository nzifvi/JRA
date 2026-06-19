import serial
import numpy
import struct
import threading
import collections
from typing import Optional
import time

# ── LD06 protocol constants ───────────────────────────────────────────────────
_HEADER          = 0x54
_PACKET_LEN      = 47
_POINTS_PER_PKT  = 12
_MIN_DISTANCE_M  = 0.15   # LD06 minimum reliable range (metres)
_MAX_DISTANCE_M  = 6.0   # LD06 maximum range (metres)

_CRC_TABLE = bytes([
    0x00,0x4d,0x9a,0xd7,0x79,0x34,0xe3,0xae,0xf2,0xbf,0x68,0x25,0x8b,0xc6,0x11,0x5c,
    0xa9,0xe4,0x33,0x7e,0xd0,0x9d,0x4a,0x07,0x5b,0x16,0xc1,0x8c,0x22,0x6f,0xb8,0xf5,
    0x1f,0x52,0x85,0xc8,0x66,0x2b,0xfc,0xb1,0xed,0xa0,0x77,0x3a,0x94,0xd9,0x0e,0x43,
    0xb6,0xfb,0x2c,0x61,0xcf,0x82,0x55,0x18,0x44,0x09,0xde,0x93,0x3d,0x70,0xa7,0xea,
    0x3e,0x73,0xa4,0xe9,0x47,0x0a,0xdd,0x90,0xcc,0x81,0x56,0x1b,0xb5,0xf8,0x2f,0x62,
    0x97,0xda,0x0d,0x40,0xee,0xa3,0x74,0x39,0x65,0x28,0xff,0xb2,0x1c,0x51,0x86,0xcb,
    0x21,0x6c,0xbb,0xf6,0x58,0x15,0xc2,0x8f,0xd3,0x9e,0x49,0x04,0xaa,0xe7,0x30,0x7d,
    0x88,0xc5,0x12,0x5f,0xf1,0xbc,0x6b,0x26,0x7a,0x37,0xe0,0xad,0x03,0x4e,0x99,0xd4,
    0x7c,0x31,0xe6,0xab,0x05,0x48,0x9f,0xd2,0x8e,0xc3,0x14,0x59,0xf7,0xba,0x6d,0x20,
    0xd5,0x98,0x4f,0x02,0xac,0xe1,0x36,0x7b,0x27,0x6a,0xbd,0xf0,0x5e,0x13,0xc4,0x89,
    0x63,0x2e,0xf9,0xb4,0x1a,0x57,0x80,0xcd,0x91,0xdc,0x0b,0x46,0xe8,0xa5,0x72,0x3f,
    0xca,0x87,0x50,0x1d,0xb3,0xfe,0x29,0x64,0x38,0x75,0xa2,0xef,0x41,0x0c,0xdb,0x96,
    0x42,0x0f,0xd8,0x95,0x3b,0x76,0xa1,0xec,0xb0,0xfd,0x2a,0x67,0xc9,0x84,0x53,0x1e,
    0xeb,0xa6,0x71,0x3c,0x92,0xdf,0x08,0x45,0x19,0x54,0x83,0xce,0x60,0x2d,0xfa,0xb7,
    0x5d,0x10,0xc7,0x8a,0x24,0x69,0xbe,0xf3,0xaf,0xe2,0x35,0x78,0xd6,0x9b,0x4c,0x01,
    0xf4,0xb9,0x6e,0x23,0x8d,0xc0,0x17,0x5a,0x06,0x4b,0x9c,0xd1,0x7f,0x32,0xe5,0xa8,
])


def _crc8(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = _CRC_TABLE[crc ^ b]
    return crc


def _parse_packet(buf: bytes) -> Optional[list]:
    """
    Parse a 47-byte LD06 packet.

    Returns a list of (distance_m, phi_rad) tuples for valid points,
    along with the start and end angles for revolution detection.
    Returns None on CRC failure.

    Packet layout:
        [0]        header  = 0x54
        [1]        ver_len = 0x2C
        [2:4]      speed   (deg/s * 100, uint16 LE)
        [4:6]      start_angle (deg * 100, uint16 LE)
        [6:42]     12 x 3-byte points: dist_mm (uint16 LE), intensity (uint8)
        [42:44]    end_angle (deg * 100, uint16 LE)
        [44:46]    timestamp (ms, uint16 LE)
        [46]       CRC-8
    """
    if _crc8(buf[:46]) != buf[46]:
        return None

    start_angle = struct.unpack_from('<H', buf, 4)[0] / 100.0   # degrees
    end_angle   = struct.unpack_from('<H', buf, 42)[0] / 100.0  # degrees

    span = end_angle - start_angle
    if span < 0:
        span += 360.0
    step = span / (_POINTS_PER_PKT - 1)

    points = []
    for i in range(_POINTS_PER_PKT):
        base = 6 + i * 3
        dist_mm   = struct.unpack_from('<H', buf, base)[0]
        angle_deg = start_angle + step * i
        if angle_deg >= 360.0:
            angle_deg -= 360.0

        d = dist_mm / 1000.0
        if not (_MIN_DISTANCE_M <= d <= _MAX_DISTANCE_M):
            continue

        phi = numpy.deg2rad(angle_deg)
        points.append((d, phi))

    return {
        "points":      points,
        "start_angle": start_angle,
        "end_angle":   end_angle,
    }


class LiDARInterface:
    """
    Reads LD06 packets from the ESP32 over serial and injects
    boundary vector / object vector inputs into a HESCC instance.

    Revolution detection
    --------------------
    The LD06 streams packets continuously with monotonically increasing
    start_angle values that wrap 359 -> 0 at each full revolution.
    A wrap is detected when start_angle < previous start_angle, which
    marks the boundary between revolutions. Injection into the HESCC
    populations is flushed once per revolution to avoid double-counting
    the same sweep.

    Usage
    -----
        lidar = LiDARInterface(port="COM3")
        lidar.start()
        ...
        # in your main simulation loop:
        lidar.inject(hescc_instance)
        hescc_instance.step()
        ...
        lidar.stop()
    """

    def __init__(self, port: str, baud: int = 115200):
        """
        Parameters
        ----------
        port : str
            Serial port the ESP32 is on, e.g. "COM3" or "/dev/ttyUSB0".
        baud : int
            Baud rate for the ESP32 -> PC link (NOT the LiDAR baud rate,
            which is handled internally on the ESP32). Default 115200.
        """
        self._port   = port
        self._baud   = baud
        self._serial: Optional[serial.Serial] = None

        # Double-buffered revolution store:
        # _pending  — being filled by the reader thread (current revolution)
        # _ready    — last complete revolution, consumed by inject()
        self._pending: list  = []
        self._ready:   list  = []
        self._readyTimeStamp = 0.0
        self._lock = threading.Lock()

        self._prev_start_angle: Optional[float] = None
        self._running = False
        self._thread:  Optional[threading.Thread] = None

        # Diagnostics
        self.packets_received = 0
        self.packets_dropped  = 0
        self.revolutions      = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Open the serial port and begin background reading."""
        self._serial  = serial.Serial(self._port, self._baud, timeout=1.0)
        self._running = True
        self._thread  = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        print(f"[LiDARInterface] started on {self._port} @ {self._baud} baud")

    def stop(self):
        """Stop the background reader and close the serial port."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._serial and self._serial.is_open:
            self._serial.close()
        print("[LiDARInterface] stopped")

    def inject(self, hescc, maxAge:float = 0.5) -> int:
        with self._lock:
            if time.time() - self._readyTimeStamp > maxAge:
                return 0
            if not self._ready:
                return 0
            points = list(self._ready)
            self._ready = []

        for d, phi in points:
            hescc.injectIntoBVCPopulation(d, phi)
            hescc.injectIntoOVCPopulation(d, phi)

        return len(points)

    def latest_scan(self, maxAge = 0.5) -> list:
        """
        Return the most recent complete revolution as a list of
        (distance_m, phi_rad) tuples without injecting into the model.
        Useful for visualisation or logging.
        """
        with self._lock:
            if time.time() - self._readyTimeStamp > maxAge:
                return []
            else:
                return list(self._ready)

    # ── Background serial reader ──────────────────────────────────────────────

    def _reader(self):
        """
        Background thread: reads raw bytes from serial, frames packets,
        parses them, and accumulates points into _pending.
        On revolution wrap, atomically swaps _pending -> _ready.
        """
        buf    = bytearray()
        in_pkt = False
        idx    = 0

        while self._running:
            try:
                raw = self._serial.read(self._serial.in_waiting or 1)
            except serial.SerialException:
                break

            for byte in raw:
                if not in_pkt:
                    if byte == _HEADER:
                        buf    = bytearray([byte])
                        idx    = 1
                        in_pkt = True
                else:
                    buf.append(byte)
                    idx += 1
                    if idx == _PACKET_LEN:
                        in_pkt = False
                        self._process_packet(bytes(buf))
                        idx = 0

    def _process_packet(self, raw: bytes):
        result = _parse_packet(raw)
        if result is None:
            self.packets_dropped += 1
            return

        self.packets_received += 1
        start = result["start_angle"]

        # Detect revolution wrap: start_angle resets below previous value
        if self._prev_start_angle is not None and start < self._prev_start_angle:
            # Complete revolution — promote pending to ready
            with self._lock:
                self._ready   = self._pending
                self._pending = []
                self._readyTimeStamp = time.time()
            self.revolutions += 1

        self._prev_start_angle = start
        self._pending.extend(result["points"])


if __name__ == "__main__":
    # ── Minimal smoke test (no HESCC required) ────────────────────────────────
    import time

    PORT = "COM3"

    lidar = LiDARInterface(port=PORT)
    lidar.start()

    print("Reading for 5 seconds...")
    time.sleep(5)

    scan = lidar.latest_scan()
    print(f"Revolutions    : {lidar.revolutions}")
    print(f"Packets rx     : {lidar.packets_received}")
    print(f"Packets dropped: {lidar.packets_dropped}")
    print(f"Points in last scan: {len(scan)}")
    if scan:
        print("First 5 points (d_m, phi_rad):")
        for d, phi in scan[:5]:
            print(f"  d={d:.3f} m  phi={numpy.rad2deg(phi):.1f} deg")

    lidar.stop()