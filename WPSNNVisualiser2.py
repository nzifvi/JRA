import numpy
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button

from LIDARSimulator import LIDARSimulator
from WPSNN import WPSNN

import time

UPDATE_INTERVAL_MS = 5


class CombinedVisualiser:
    def __init__(self, lidar: LIDARSimulator, network: WPSNN):
        self.lidar        = lidar
        self.network      = network
        self.scanning     = False
        self.running      = False
        self.currentAngle = 0.0
        self.timestep     = 0
        self._waveDone    = True
        self._lastFrameTime = time.perf_counter()
        self.rayTrail = []
        self.trailLength = 2
        self.robotHeading = 0.0  # radians
        self.robotSpeed = 0.0  # m/s
        self.linearSpeed = 0.5  # m/s when moving
        self.turnSpeed = 1.0  # rad/s when turning
        self.keysHeld = set()

        # precompute neuron coordinate arrays
        coords  = numpy.array(network.lattice)
        self.xs = coords[:, 0]
        self.ys = coords[:, 1]

        # ── figure layout ────────────────────────────────────────────────
        self.fig = plt.figure(figsize=(16, 8))
        self.fig.canvas.mpl_connect("key_press_event", self._onKeyPress)
        self.fig.canvas.mpl_connect("key_release_event", self._onKeyRelease)

        # left axis: lidar
        self.axLidar = self.fig.add_axes([0.03, 0.10, 0.42, 0.85])
        #self.axLidar.set_facecolor("#0f0f1a")
        self.axLidar.set_title("LiDAR Scanner", color="white", pad=10)
        self.axLidar.tick_params(colors="grey")
        self.axLidar.set_aspect("equal")
        self.axLidar.set_xlim(-lidar.maxRange * 1.1, lidar.maxRange * 1.1)
        self.axLidar.set_ylim(-lidar.maxRange * 1.1, lidar.maxRange * 1.1)

        # right axis: wpsnn
        self.axNet = self.fig.add_axes([0.48, 0.10, 0.42, 0.85])
        self.axNet.set_facecolor("#0f0f1a")
        self.axNet.set_title("WPSNN", color="white", pad=10)
        self.axNet.tick_params(colors="grey")
        self.axNet.set_aspect("equal")

        # ── lidar layers ─────────────────────────────────────────────────
        for (x1, y1), (x2, y2) in self.lidar.walls:
            self.axLidar.plot([x1, x2], [y1, y2], color="#4a4a8a", linewidth=1.5, zorder=1)

        self.sensorMarker = self.axLidar.scatter(
            [lidar.sensorX], [lidar.sensorY],
            c="red", s=60, zorder=5
        )
        self.scatterHits = self.axLidar.scatter(
            [], [], c="green", s=4, alpha=0.8, zorder=3
        )
        self.rayLine, = self.axLidar.plot(
            [], [], color="green", linewidth=0.8, alpha=0.6, zorder=2
        )
        self.hitXs = []
        self.hitYs = []

        # ── wpsnn layers ─────────────────────────────────────────────────
        self.scatterIinh = self.axNet.scatter(
            self.xs, self.ys,
            c=numpy.zeros(len(self.xs)),
            cmap="hot", vmin=0.0, vmax=float(network.currentClamp),
            s=20, alpha=0.6, zorder=1
        )
        self.scatterSpikes = self.axNet.scatter(
            [], [], c="cyan", s=35, zorder=2
        )
        self.scatterTarget = self.axNet.scatter(
            [], [], c="red", s=80, marker="*", zorder=3,
            edgecolors="white", linewidths=0.5
        )
        self.pathLine, = self.axNet.plot(
            [], [], color="white", linewidth=1.5, alpha=0.85, zorder=4
        )

        self.scatterIinh.set_picker(8)
        self.fig.canvas.mpl_connect("pick_event", self._onPick)

        self.targetX = None
        self.targetY = None
        self.mode    = "inject"

        # ── info panel ───────────────────────────────────────────────────
        infoAx = self.fig.add_axes([0.92, 0.50, 0.07, 0.45])
        infoAx.set_facecolor("#0f0f1a")
        infoAx.axis("off")

        self.modeText     = infoAx.text(0.05, 0.95, "Mode: INJECT",  color="cyan",  transform=infoAx.transAxes, fontsize=8)
        self.timestepText = infoAx.text(0.05, 0.82, "Step: 0",       color="white", transform=infoAx.transAxes, fontsize=8)
        self.angleText    = infoAx.text(0.05, 0.69, "Angle: 0.00",   color="white", transform=infoAx.transAxes, fontsize=8)
        self.hitsText     = infoAx.text(0.05, 0.56, "Hits: 0",       color="white", transform=infoAx.transAxes, fontsize=8)
        self.targetText   = infoAx.text(0.05, 0.43, "Target: None",  color="white", transform=infoAx.transAxes, fontsize=8)

        # ── buttons ──────────────────────────────────────────────────────
        btnColor = "#2a2a4a"
        btnHover = "#3a3a6a"

        axScan      = self.fig.add_axes([0.92, 0.42, 0.07, 0.05])
        axClearScan = self.fig.add_axes([0.92, 0.30, 0.07, 0.05])
        axMode      = self.fig.add_axes([0.92, 0.24, 0.07, 0.05])
        axWave      = self.fig.add_axes([0.92, 0.18, 0.07, 0.05])
        axPath      = self.fig.add_axes([0.92, 0.12, 0.07, 0.05])
        axRunEnd    = self.fig.add_axes([0.92, 0.06, 0.07, 0.05])
        axRun       = self.fig.add_axes([0.92, 0.00, 0.07, 0.05])

        self.btnScan      = Button(axScan,     "Scan",        color=btnColor, hovercolor=btnHover)

        self.btnClearScan = Button(axClearScan,"Clear Scan",  color=btnColor, hovercolor=btnHover)
        self.btnMode      = Button(axMode,     "Mode:INJECT", color=btnColor, hovercolor=btnHover)
        self.btnWave      = Button(axWave,     "Trigger Wave",color=btnColor, hovercolor=btnHover)
        self.btnPath      = Button(axPath,     "Compute Path",color=btnColor, hovercolor=btnHover)
        self.btnRunEnd    = Button(axRunEnd,   "Run to End",  color=btnColor, hovercolor=btnHover)
        self.btnRun       = Button(axRun,      "Run",         color=btnColor, hovercolor=btnHover)

        for btn in (self.btnScan, self.btnClearScan, self.btnMode,
                    self.btnWave, self.btnPath, self.btnRunEnd, self.btnRun):
            btn.label.set_color("white")

        self.btnScan.on_clicked(self._onToggleScan)
        self.btnClearScan.on_clicked(self._onClearScan)
        self.btnMode.on_clicked(self._onToggleMode)
        self.btnWave.on_clicked(self._onTriggerWave)
        self.btnPath.on_clicked(self._onComputePath)
        self.btnRunEnd.on_clicked(self._onRunToEnd)
        self.btnRun.on_clicked(self._onToggleRun)

    # ── lidar callbacks ──────────────────────────────────────────────────

    def _onToggleScan(self, event):
        self.scanning = not self.scanning
        self.btnScan.label.set_text("Pause Scan" if self.scanning else "Scan")
        self.fig.canvas.draw_idle()


    def _onClearScan(self, event):
        self.hitXs        = []
        self.hitYs        = []
        self.currentAngle = 0.0
        self.scanning     = False
        self.btnScan.label.set_text("Scan")
        self.scatterHits.set_offsets(numpy.empty((0, 2)))
        self.rayLine.set_data([], [])
        self.hitsText.set_text("Hits: 0")
        self.angleText.set_text("Angle: 0.00")
        self.fig.canvas.draw_idle()

    def _refreshHits(self):
        if len(self.hitXs) > 0:
            self.scatterHits.set_offsets(
                numpy.column_stack([self.hitXs, self.hitYs])
            )
        else:
            self.scatterHits.set_offsets(numpy.empty((0, 2)))

    # ── wpsnn callbacks ──────────────────────────────────────────────────

    def _onPick(self, event):
        if event.artist is not self.scatterIinh:
            return
        idx = event.ind[0]
        x   = self.xs[idx]
        y   = self.ys[idx]

        if self.mode == "inject":
            try:
                self.network.inject(x, y)
                self.network.neurons.vars["Iinh"].pull_from_device()
                self.scatterIinh.set_array(numpy.array(self.network.neurons.vars["Iinh"].view))
            except ValueError:
                pass

        elif self.mode == "target":
            self.targetX = x
            self.targetY = y
            self.targetText.set_text(f"Target:\nx={x:.2f} y={y:.2f}")
            self.scatterTarget.set_offsets([[x, y]])

        self.fig.canvas.draw_idle()

    def _onToggleMode(self, event):
        if self.mode == "inject":
            self.mode = "target"
            self.modeText.set_text("Mode: TARGET")
            self.modeText.set_color("red")
            self.btnMode.label.set_text("Mode:TARGET")
        else:
            self.mode = "inject"
            self.modeText.set_text("Mode: INJECT")
            self.modeText.set_color("cyan")
            self.btnMode.label.set_text("Mode:INJECT")
        self.fig.canvas.draw_idle()

    def _onTriggerWave(self, event):
        self._waveDone = False
        self.network.propagateWave()

    def _onComputePath(self, event):
        if self.targetX is None or self.targetY is None:
            print("No target set — switch to TARGET mode and click a neuron")
            return
        if self.network.model.timestep < self.network.duration:
            remaining = self.network.duration - self.network.model.timestep
            print(f"Simulation not complete — {remaining} timesteps remaining")
            return

        wasRunning   = self.running
        self.running = False

        try:
            self.network.backpropagateWave(self.targetX, self.targetY)
            path = self.network.calculatePath()

            if len(path) < 2:
                print("Path too short to display")
                return

            coords = numpy.array([self.network.lattice[i] for i in path])
            self.pathLine.set_data(coords[:, 0], coords[:, 1])
            print(f"Path computed: {len(path)} neurons")

        except RuntimeError as e:
            print(f"Path computation failed: {e}")

        finally:
            self.running = wasRunning

        self.fig.canvas.draw_idle()

    def _onRunToEnd(self, event):
        self.running  = False
        remaining     = self.network.duration - self.network.model.timestep
        for _ in range(remaining):
            self.network.step()
            self.timestep += 1
        self.timestepText.set_text(f"Step: {self.timestep}")
        print("Simulation complete — ready to compute path")
        self.fig.canvas.draw_idle()

    def _onToggleRun(self, event):
        self.running = not self.running
        self.btnRun.label.set_text("Pause" if self.running else "Run")
        self.fig.canvas.draw_idle()

    def _onKeyPress(self, event):
        self.keysHeld.add(event.key)

    def _onKeyRelease(self, event):
        self.keysHeld.discard(event.key)

    def _driveRobot(self, elapsed: float):
        oldX = self.lidar.sensorX
        oldY = self.lidar.sensorY
        oldHeading = self.robotHeading

        if 'a' in self.keysHeld:
            self.robotHeading += self.turnSpeed * elapsed
        if 'd' in self.keysHeld:
            self.robotHeading -= self.turnSpeed * elapsed

        if 'w' in self.keysHeld:
            self.lidar.sensorX += numpy.cos(self.robotHeading) * self.linearSpeed * elapsed
            self.lidar.sensorY += numpy.sin(self.robotHeading) * self.linearSpeed * elapsed
        if 's' in self.keysHeld:
            self.lidar.sensorX -= numpy.cos(self.robotHeading) * self.linearSpeed * elapsed
            self.lidar.sensorY -= numpy.sin(self.robotHeading) * self.linearSpeed * elapsed

        self.sensorMarker.set_offsets([[self.lidar.sensorX, self.lidar.sensorY]])

    # ── animation loop ───────────────────────────────────────────────────

    def _update(self, frame):
        artists = (self.scatterHits, self.rayLine, self.sensorMarker,
                   self.scatterIinh, self.scatterSpikes, self.scatterTarget, self.pathLine)

        # ── lidar step ───────────────────────────────────────────────────
        now = time.perf_counter()
        elapsed = now - self._lastFrameTime
        self._lastFrameTime = now

        self._driveRobot(elapsed)

        minAngVelocity = None
        maxAngVelocity = None

        stepsPerFrame = int(elapsed * self.lidar.rangeFrequency)

        for _ in range(stepsPerFrame):
            self.currentAngle, hitX, hitY, closestT, modulatedAngularVelocity = self.lidar.step(self.currentAngle)

            if maxAngVelocity is None or modulatedAngularVelocity > maxAngVelocity:
                maxAngVelocity = modulatedAngularVelocity

            if minAngVelocity is None or modulatedAngularVelocity < minAngVelocity:
                minAngVelocity = modulatedAngularVelocity

            if hitX is not None:
                self.hitXs.append(hitX)
                self.hitYs.append(hitY)

                dx = hitX - self.lidar.sensorX
                dy = hitY - self.lidar.sensorY
                cosH = numpy.cos(self.robotHeading)
                sinH = numpy.sin(self.robotHeading)
                localX = cosH * dx + sinH * dy
                localY = -sinH * dx + cosH * dy

                try:
                    self.network.injectGaussian(localX, localY)
                except ValueError:
                    pass

            if self.currentAngle >= 2 * numpy.pi:
                self.currentAngle = 0.0
                self.lidar.resetRevolution()
                print(f"Scan period completed. {len(self.hitXs)} hits injected")
                print(f"    - min angular velocity observed: {minAngVelocity}")
                print(f"    - max angular velocity observed: {maxAngVelocity}")
                break

        rayDirX = numpy.cos(self.currentAngle)
        rayDirY = numpy.sin(self.currentAngle)
        endX = self.lidar.sensorX + closestT * rayDirX
        endY = self.lidar.sensorY + closestT * rayDirY

        self.rayTrail.append((endX, endY))
        if len(self.rayTrail) > self.trailLength:
            self.rayTrail.pop(0)

        if len(self.rayTrail) > 1:
            trailCoords = numpy.array(self.rayTrail)
            self.rayLine.set_data(
                [self.lidar.sensorX] + list(trailCoords[:, 0]),
                [self.lidar.sensorY] + list(trailCoords[:, 1])
            )


        self.angleText.set_text(f"Angle: {self.currentAngle:.2f}")
        self.hitsText.set_text(f"Hits: {len(self.hitXs)}")

        # ── wpsnn step ───────────────────────────────────────────────────
        if self.running:
            for _ in range(UPDATE_INTERVAL_MS):
                self.network.step()
                self.timestep += 1

            self.network.neurons.vars["V"].pull_from_device()
            self.network.neurons.vars["Iinh"].pull_from_device()

            vValues = numpy.array(self.network.neurons.vars["V"].view)
            iinhValues = numpy.array(self.network.neurons.vars["Iinh"].view)

            self.scatterIinh.set_array(iinhValues)

            activeIndices = numpy.where(vValues >= self.network.lifParameters["Vthresh"])[0]
            if len(activeIndices) > 0:
                self.scatterSpikes.set_offsets(
                    numpy.column_stack([self.xs[activeIndices], self.ys[activeIndices]])
                )
            else:
                self.scatterSpikes.set_offsets(numpy.empty((0, 2)))
                if not self._waveDone:
                    print(f"Wave finished at timestep {self.timestep}")
                    self._waveDone = True

            self.timestepText.set_text(f"Step: {self.timestep}")

        return artists

    def run(self):
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update,
            frames=None,
            interval=50,
            blit=True,
            repeat=True,
            cache_frame_data=False
        )
        plt.show()


if __name__ == "__main__":
    lidar = LIDARSimulator() # manually overridden rangeFrequency so the radii is actually visible
    lidar.addRectangle(-11.9, -11.9, 24, 24)  # outer boundary

    # internal walls forming a maze-like structure
    lidar.addWall(-3.6, 3.2, 5.0, 5.2)  # top left horizontal
    lidar.addWall(
        -1.0,
        -1.0,
        10.0,
        -1.0
    )
    lidar.addWall(
        10.0,
        -1.0,
        10.0,
        8.0
    )

    network    = WPSNN(radius = 12, neuronSpacing = 0.3) # (1, 0.05) -> increase by factor of 12 (12, 0.6)
    visualiser = CombinedVisualiser(lidar, network)
    visualiser.run()