import numpy
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from LIDARInterface import LiDARInterface

SERIAL_PORT = "COM5"
SERIAL_BAUD = 115200
LIDAR_RANGE = 6


class LiDARDebugVisualiser:
    def __init__(self, lidar: LiDARInterface):
        self.lidar = lidar

        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.fig.patch.set_facecolor("#0d0d1a")
        self.ax.set_facecolor("#0d0d1a")
        self.ax.set_title("LiDAR Live Point Cloud", color="white", fontsize=12)
        self.ax.tick_params(colors="grey")
        self.ax.set_xlim(-LIDAR_RANGE, LIDAR_RANGE)
        self.ax.set_ylim(-LIDAR_RANGE, LIDAR_RANGE)
        self.ax.set_aspect("equal")
        self.ax.set_xlabel("x (m)", color="grey")
        self.ax.set_ylabel("y (m)", color="grey")
        for sp in self.ax.spines.values():
            sp.set_edgecolor("#3a3a6a")

        # range rings
        for r, style in [(3, ":"), (6, ":"), (9, ":"), (LIDAR_RANGE, "--")]:
            self.ax.add_patch(plt.Circle(
                (0, 0), r, fill=False,
                color="#3a3a6a", linestyle=style, lw=0.8
            ))
            self.ax.text(
                0, r + 0.2, f"{r:.0f}m",
                color="#3a3a6a", fontsize=7, ha="center"
            )

        # robot origin
        self.ax.scatter([0], [0], c="red", s=60, zorder=5, marker="^")

        # point cloud
        self.scatter = self.ax.scatter(
            [], [], s=3, c=[], cmap="plasma",
            vmin=0, vmax=LIDAR_RANGE, alpha=0.9, zorder=3
        )
        self.fig.colorbar(
            self.scatter, ax=self.ax, label="distance (m)"
        ).ax.tick_params(colors="grey")

        # stats overlay
        self.txtStats = self.ax.text(
            0.02, 0.98, "", color="white", fontsize=9,
            transform=self.ax.transAxes, va="top",
            bbox=dict(facecolor="#1a1a2e", alpha=0.7, edgecolor="none")
        )

    def _update(self, frame):
        points = self.lidar.latest_scan()

        if points:
            ds   = numpy.array([d   for d,   _ in points])
            phis = numpy.array([phi for _, phi in points])
            xs   = ds * numpy.cos(phis)
            ys   = ds * numpy.sin(phis)
            self.scatter.set_offsets(numpy.column_stack([xs, ys]))
            self.scatter.set_array(ds)
        else:
            self.scatter.set_offsets(numpy.empty((0, 2)))
            self.scatter.set_array(numpy.array([]))

        self.txtStats.set_text(
            f"Points:  {len(points) if points else 0}\n"
            f"Revs:    {self.lidar.revolutions}\n"
            f"Pkts rx: {self.lidar.packets_received}\n"
            f"Dropped: {self.lidar.packets_dropped}"
        )

        return self.scatter, self.txtStats

    def run(self):
        self.ani = animation.FuncAnimation(
            self.fig, self._update,
            frames=None, interval=50,
            blit=False, cache_frame_data=False
        )
        plt.show()


if __name__ == "__main__":
    lidar = LiDARInterface(port=SERIAL_PORT, baud=SERIAL_BAUD)
    lidar.start()

    vis = LiDARDebugVisualiser(lidar)

    try:
        vis.run()
    finally:
        lidar.stop()