import numpy
import time
import threading
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from GFTC import (HESCC, DISTANCE_BINS, EGOCENTRIC_BEARING_BINS,
                  ALLOCENTRIC_BEARING_BINS, HDC_COUNT, LIDAR_RANGE)

STEPS_PER_FRAME = 20                   # HESCC steps per animation frame (sim runs faster than redraw)
MOVE_SPEED      = 0.25                 # metres per key press (W/S)
TURN_SPEED      = numpy.radians(8.0)   # radians per key press (A/D)
WORLD_HALF      = 7.0                  # half-extent of the displayed world (m)

CAMERA_FOV_H   = numpy.radians(87.0)    # D435 horizontal depth FOV
CAMERA_COLUMNS = 64                     # simulated depth columns (downsampled)
CAMERA_MIN_Z   = 0.105                  # D435 minimum depth distance (m)
CAMERA_MAX_Z   = LIDAR_RANGE            # cap at the PWb/PWo distance grid range
CAMERA_FPS     = 30                     # D435 depth stream frame rate
CAMERA_MAX_AGE = 0.5                    # seconds before a frame is considered stale


class World:
    def __init__(self):
        self.segments = []   # list of (x1, y1, x2, y2, kind)
        w = 6.0
        self._addBox(-w, -w, w, w, kind="boundary")          # outer room walls
        self._addBox(2.0, 2.0, 3.5, 3.5, kind="object")      # free-standing boxes
        self._addBox(-4.0, 1.0, -3.0, 2.0, kind="object")
        self._addBox(0.5, -4.0, 2.0, -2.5, kind="object")

    def _addBox(self, x1, y1, x2, y2, kind):
        self.segments.append((x1, y1, x2, y1, kind))
        self.segments.append((x2, y1, x2, y2, kind))
        self.segments.append((x2, y2, x1, y2, kind))
        self.segments.append((x1, y2, x1, y1, kind))

    def cast(self, ox, oy, angle, maxRange):
        dx, dy = numpy.cos(angle), numpy.sin(angle)
        best_t, best_kind = None, None
        for (x1, y1, x2, y2, kind) in self.segments:
            ex, ey = x2 - x1, y2 - y1
            denom = dx * ey - dy * ex
            if abs(denom) < 1e-12:
                continue
            t = ((x1 - ox) * ey - (y1 - oy) * ex) / denom
            u = ((x1 - ox) * dy - (y1 - oy) * dx) / denom
            if t >= 0.0 and 0.0 <= u <= 1.0 and t <= maxRange:
                if best_t is None or t < best_t:
                    best_t, best_kind = t, kind
        return best_t, best_kind


class Robot:
    def __init__(self, x=0.0, y=0.0, heading=0.0):
        self.x = x
        self.y = y
        self.heading = heading   # radians, allocentric

    def forward(self, dist):
        self.x += dist * numpy.cos(self.heading)
        self.y += dist * numpy.sin(self.heading)

    def rotate(self, dAngle):
        self.heading = (self.heading + dAngle) % (2 * numpy.pi)


class SimulatedDepthCamera:
    def __init__(self, world, robot):
        self.world = world
        self.robot = robot
        self._columnOffsets = numpy.linspace(
            -CAMERA_FOV_H / 2.0, CAMERA_FOV_H / 2.0, CAMERA_COLUMNS
        )
        self._frame = []
        self._frameTimestamp = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        print(f"[SimulatedDepthCamera] started @ {CAMERA_FPS} fps")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("[SimulatedDepthCamera] stopped")

    def latest_frame(self, maxAge=CAMERA_MAX_AGE):
        with self._lock:
            if time.time() - self._frameTimestamp > maxAge:
                return []
            return list(self._frame)

    def _reader(self):
        period = 1.0 / CAMERA_FPS
        while self._running:
            frame = self._renderFrame()
            with self._lock:
                self._frame = frame
                self._frameTimestamp = time.time()
            time.sleep(period)   # emulate the depth-stream frame interval

    def _renderFrame(self):
        rx, ry, rh = self.robot.x, self.robot.y, self.robot.heading
        hits = []
        for offset in self._columnOffsets:
            worldAngle = rh + offset
            dist, kind = self.world.cast(rx, ry, worldAngle, CAMERA_MAX_Z)
            if dist is None or dist < CAMERA_MIN_Z:
                continue
            egoBearing = offset % (2.0 * numpy.pi)   # bearing relative to nose
            hits.append((dist, egoBearing, kind))
        return hits


class RobotSimVisualiser:
    VREST = -65.0
    VMAX  = 15.0    # Vthresh - Vrest

    def __init__(self, network: HESCC, camera: SimulatedDepthCamera):
        self.network = network
        self.camera  = camera
        self.world   = camera.world
        self.robot   = camera.robot
        self.running = True
        self.timestep = 0

        # ── figure layout ─────────────────────────────────────────────────
        self.fig = plt.figure(figsize=(20, 10))
        self.fig.patch.set_facecolor("#0d0d1a")
        self.fig.suptitle("HESCC Robot Simulator  —  W/S move · A/D rotate · space pause",
                          color="white", fontsize=13, y=0.99)

        self.axWorld = self._makeAx([0.04, 0.08, 0.42, 0.84], "Simulated World (top-down)")
        self.axWorld.set_aspect("equal")
        self.axWorld.set_xlim(-WORLD_HALF, WORLD_HALF)
        self.axWorld.set_ylim(-WORLD_HALF, WORLD_HALF)

        self.axPWb, self.meshPWb = self._makePolar([0.52, 0.55, 0.20, 0.37],
                                                   "PWb (egocentric boundaries)",
                                                   EGOCENTRIC_BEARING_BINS, "viridis")
        self.axPWo, self.meshPWo = self._makePolar([0.76, 0.55, 0.20, 0.37],
                                                   "PWo (egocentric objects)",
                                                   EGOCENTRIC_BEARING_BINS, "viridis")
        self.axBVC, self.meshBVC = self._makePolar([0.52, 0.05, 0.20, 0.37],
                                                   "BVC (allocentric boundaries)",
                                                   ALLOCENTRIC_BEARING_BINS, "plasma")
        self.axOVC, self.meshOVC = self._makePolar([0.76, 0.05, 0.20, 0.37],
                                                   "OVC (allocentric objects)",
                                                   ALLOCENTRIC_BEARING_BINS, "plasma")

        self.axHDC = self._makeAx([0.52, 0.46, 0.44, 0.05], "HDC (heading bump)")
        self.lineHDC, = self.axHDC.plot(
            numpy.arange(HDC_COUNT), numpy.zeros(HDC_COUNT),
            color="#ff9900", lw=1.2
        )
        self.axHDC.set_ylim(0, self.VMAX)
        self.axHDC.set_xlim(0, HDC_COUNT - 1)

        for (x1, y1, x2, y2, kind) in self.world.segments:
            colour = "#8888aa" if kind == "boundary" else "#ff6644"
            self.axWorld.plot([x1, x2], [y1, y2], color=colour, lw=2, zorder=1)

        self.rayLines = [
            self.axWorld.plot([], [], color="#44ff88", lw=0.5, alpha=0.5, zorder=2)[0]
            for _ in range(CAMERA_COLUMNS)
        ]
        self.robotMarker, = self.axWorld.plot([], [], "o", color="cyan",
                                              ms=10, zorder=4, markeredgecolor="white")
        self.headingArrow = self.axWorld.annotate(
            "", xy=(0, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", color="cyan", lw=2), zorder=5
        )

        self.txtStatus = self.axWorld.text(
            0.02, 0.98, "", color="white", fontsize=8,
            transform=self.axWorld.transAxes, va="top",
            bbox=dict(facecolor="#1a1a2e", alpha=0.8, edgecolor="none")
        )

        self.fig.canvas.mpl_connect("key_press_event", self._onKey)

    # ── helpers ────────────────────────────────────────────────────────────

    def _makeAx(self, rect, title):
        ax = self.fig.add_axes(rect)
        ax.set_facecolor("#12122a")
        ax.set_title(title, color="white", fontsize=9, pad=4)
        ax.tick_params(colors="grey", labelsize=6)
        for sp in ax.spines.values():
            sp.set_edgecolor("#3a3a6a")
        return ax

    def _makePolar(self, rect, title, bearingBins, cmap):
        ax = self.fig.add_axes(rect, projection="polar")
        ax.set_facecolor("#12122a")
        ax.set_title(title, color="white", fontsize=9, pad=8)
        ax.tick_params(colors="grey", labelsize=6)
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(1)
        ax.set_yticklabels([])
        ax.grid(color="#3a3a6a", lw=0.3)
        thetaEdges = numpy.linspace(0, 2 * numpy.pi, bearingBins + 1)
        rEdges     = numpy.linspace(0, LIDAR_RANGE, DISTANCE_BINS + 1)
        T, R = numpy.meshgrid(thetaEdges, rEdges)
        zeros = numpy.zeros((DISTANCE_BINS, bearingBins))
        mesh = ax.pcolormesh(T, R, zeros, cmap=cmap, vmin=0, vmax=self.VMAX, shading="flat")
        return ax, mesh

    def _pullV(self, pop):
        pop.vars["V"].pull_from_device()
        return numpy.maximum(
            numpy.array(pop.vars["V"].view, dtype=numpy.float32) - self.VREST, 0.0
        )

    def _setPolar(self, mesh, vVec, bearingBins):
        grid = vVec.reshape(DISTANCE_BINS, bearingBins)
        mesh.set_array(grid.ravel())

    # ── keyboard handler ─────────────────────────────────────────────────────

    def _onKey(self, event):
        if event.key == "w":
            self.robot.forward(MOVE_SPEED)
        elif event.key == "s":
            self.robot.forward(-MOVE_SPEED)
        elif event.key == "a":
            self.robot.rotate(TURN_SPEED)
        elif event.key == "d":
            self.robot.rotate(-TURN_SPEED)
        elif event.key == " ":
            self.running = not self.running

    # ── injection: re-assert the latest depth frame + heading EVERY step ──────

    def _injectStep(self, frame):
        # CLEAR egocentric input first — the camera gives a fresh frame, not an addition
        self.network.PWbPop.vars["Iext"].view[:] = 0.0
        self.network.PWbPop.vars["Iext"].push_to_device()
        self.network.PWoPop.vars["Iext"].view[:] = 0.0
        self.network.PWoPop.vars["Iext"].push_to_device()

        self.network.setHDInput(self.robot.heading)  # setHDInput already overwrites (=), good
        for dist, egoBearing, kind in frame:
            if kind == "boundary":
                self.network.injectIntoPWb(dist, egoBearing)
            else:
                self.network.injectIntoPWo(dist, egoBearing)

    # ── animation update ─────────────────────────────────────────────────────

    def _update(self, frameIdx):
        if self.running:
            for _ in range(STEPS_PER_FRAME):
                frame = self.camera.latest_frame()   # grab latest (may repeat between cam frames)
                self._injectStep(frame)              # re-assert EVERY step -> persistent drive
                self.network.step()
                self.timestep += 1
            self._lastFrame = self.camera.latest_frame()
        else:
            self._lastFrame = self.camera.latest_frame()

        # ── world overlay ─────────────────────────────────────────────────
        self.robotMarker.set_data([self.robot.x], [self.robot.y])
        self.headingArrow.set_position((self.robot.x, self.robot.y))
        self.headingArrow.xy = (
            self.robot.x + 1.0 * numpy.cos(self.robot.heading),
            self.robot.y + 1.0 * numpy.sin(self.robot.heading)
        )
        for idx, line in enumerate(self.rayLines):
            if idx < len(self._lastFrame):
                dist, egoBearing, _ = self._lastFrame[idx]
                worldAngle = self.robot.heading + egoBearing
                ex = self.robot.x + dist * numpy.cos(worldAngle)
                ey = self.robot.y + dist * numpy.sin(worldAngle)
                line.set_data([self.robot.x, ex], [self.robot.y, ey])
            else:
                line.set_data([], [])

        # ── population readouts (polar) ───────────────────────────────────
        self._setPolar(self.meshPWb, self._pullV(self.network.PWbPop), EGOCENTRIC_BEARING_BINS)
        self._setPolar(self.meshPWo, self._pullV(self.network.PWoPop), EGOCENTRIC_BEARING_BINS)
        self._setPolar(self.meshBVC, self._pullV(self.network.BVCPop), ALLOCENTRIC_BEARING_BINS)
        self._setPolar(self.meshOVC, self._pullV(self.network.OVCPop), ALLOCENTRIC_BEARING_BINS)
        self.lineHDC.set_ydata(self._pullV(self.network.HDCPop))

        self.txtStatus.set_text(
            f"t={self.timestep}\n"
            f"pos=({self.robot.x:.1f}, {self.robot.y:.1f})\n"
            f"heading={numpy.degrees(self.robot.heading):.0f}deg\n"
            f"{'RUNNING' if self.running else 'PAUSED (space)'}"
        )

        return (self.robotMarker, self.txtStatus, self.meshPWb, self.meshPWo,
                self.meshBVC, self.meshOVC, self.lineHDC, *self.rayLines)

    def run(self):
        self.ani = animation.FuncAnimation(
            self.fig, self._update, frames=None,
            interval=50, blit=False, cache_frame_data=False
        )
        plt.show()


if __name__ == "__main__":
    print("! Initialising HESCC model")
    network = HESCC()

    world  = World()
    robot  = Robot(0.0, 0.0, 0.0)
    camera = SimulatedDepthCamera(world, robot)
    camera.start()

    print("! Launching simulator  (click the window, then use W/A/S/D)")
    vis = RobotSimVisualiser(network, camera)
    try:
        vis.run()
    finally:
        camera.stop()