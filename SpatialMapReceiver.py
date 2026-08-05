import socket
import struct
import sys
import numpy
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

MAGIC = b"HMAP"
HEADER      = "<4sHHfffff"
HEADER_SIZE = struct.calcsize(HEADER)
PORT        = 9870

def parseFrame(data):
    if len(data) < HEADER_SIZE:
        return None
    magic, nx, ny, robotX, robotY, xExt, yExt, clamp = struct.unpack(HEADER, data[:HEADER_SIZE])
    if magic != MAGIC:
        return None

    gridBytes = nx * ny * 4
    if len(data) < HEADER_SIZE + gridBytes:
        return None

    grid = numpy.frombuffer(
        data,
        dtype = numpy.float32,
        count = nx * ny,
        offset = HEADER_SIZE
    ).reshape(nx, ny)

    return grid, robotX, robotY, xExt, yExt, clamp

def drain(skt):
    latest = None
    while True:
        try:
            latest = skt.recv(131072)
        except BlockingIOError:
            return latest
        except socket.error:
            return latest

def main():
    skt = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )
    skt.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_RCVBUF,
        1 << 20
    )
    skt.bind(("0.0.0.0", PORT))
    skt.setblocking(False)

    fig = ax = img = robot = None

    plt.ion()
    while True:
        data = drain(skt)
        if data is not None:
            frame = parseFrame(data)
            if frame is not None:
                grid, rx, ry, xExt, yExt, clamp = frame

                if img is None:
                    fig, ax = plt.subplots()
                    img = ax.imshow(
                        grid.T,
                        origin = "lower",
                        extent = (-xExt, xExt, -yExt, yExt),
                        vmin = 0.0,
                        vmax = clamp,
                        cmap = "inferno",
                        interpolation = "nearest"
                    )
                    fig.colorbar(
                        img,
                        ax = ax,
                        label = "Iinh"
                    )
                    (robot, ) = ax.plot(
                        [],
                        [],
                        "co",
                        markersize = 8,
                        label = "robot"
                    )
                img.set_data(grid.T)
                robot.set_data([rx], [ry])
        if fig is not None:
            if not plt.fignum_exists(fig.number):
                break
            fig.canvas.draw_idle()
            fig.canvas.flush_events()

        plt.pause(0.003)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)