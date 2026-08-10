import socket
import struct
import sys
import numpy
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

MAGIC       = b"HMAP"
PATH_MAGIC  = b"HPTH"
HEADER      = "<4sHHfffff"
HEADER_SIZE = struct.calcsize(HEADER)
PATH_HEADER = "<4sH"
PATH_HEADER_SIZE = struct.calcsize(PATH_HEADER)

PORT = 9870          # map + path inbound (from Jetson)


def parseFrame(data):
    if len(data) < HEADER_SIZE:
        return None
    magic, nx, ny, robotX, robotY, xExt, yExt, clamp = struct.unpack(
        HEADER, data[:HEADER_SIZE])
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


def parsePath(data):
    # HPTH frame: magic, uint16 count, count*(float32 x, float32 y)
    if len(data) < PATH_HEADER_SIZE:
        return None
    magic, count = struct.unpack(PATH_HEADER, data[:PATH_HEADER_SIZE])
    if magic != PATH_MAGIC:
        return None
    needed = PATH_HEADER_SIZE + count * 2 * 4
    if len(data) < needed:
        return None
    if count == 0:
        return numpy.empty((0, 2), dtype=numpy.float32)
    pts = numpy.frombuffer(
        data,
        dtype = numpy.float32,
        count = count * 2,
        offset = PATH_HEADER_SIZE
    ).reshape(count, 2)
    return pts


def drain(skt):
    # Return the most recent MAP frame and the most recent PATH frame seen in
    # this drain pass. Splitting by magic means a rare path packet is never
    # dropped in favour of a newer, more frequent map packet.
    latestMap  = None
    latestPath = None
    while True:
        try:
            packet = skt.recv(131072)
        except BlockingIOError:
            break
        except socket.error:
            break
        if packet[:4] == PATH_MAGIC:
            latestPath = packet
        else:
            latestMap = packet
    return latestMap, latestPath


def main():
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    skt.bind(("0.0.0.0", PORT))
    skt.setblocking(False)

    fig = ax = img = robot = None
    pathLine = None      # Line2D for the planned path polyline

    plt.ion()
    while True:
        mapData, pathData = drain(skt)

        if mapData is not None:
            frame = parseFrame(mapData)
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
                    fig.colorbar(img, ax=ax, label="Iinh")
                    (robot, ) = ax.plot([], [], "co", markersize=8, label="robot")
                    (pathLine, ) = ax.plot([], [], "-", color="lime",
                                           linewidth=2.0, label="planned path")
                    ax.legend(loc="upper right", fontsize=8)
                img.set_data(grid.T)
                robot.set_data([rx], [ry])

        if pathData is not None and pathLine is not None:
            pts = parsePath(pathData)
            if pts is not None:
                if len(pts) == 0:
                    pathLine.set_data([], [])
                    print("[receiver] empty path received")
                else:
                    pathLine.set_data(pts[:, 0], pts[:, 1])
                    print("[receiver] path drawn ({} points)".format(len(pts)))

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