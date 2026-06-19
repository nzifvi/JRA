import numpy
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import FancyArrowPatch
from matplotlib.widgets import Button

from LIDARSimulator import LIDARSimulator
from HESCC import HESCC, ENV_SIZE, NEURON_SPACING, PLACE_SIDE, CURRENT_CLAMP, DURATION

import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPDATE_INTERVAL_MS  = 5       # WPSNN steps per animation frame
WINDOW_HALF         = 15.0    # half-width of sliding window (metres) → 30m x 30m
PERSISTENCE_TAU     = 5       # scan cycles before a hit is promoted to boundary
PERSISTENCE_DECAY   = 1       # counter decrement per cycle without observation


# ---------------------------------------------------------------------------
# CombinedVisualiser
# ---------------------------------------------------------------------------

class CombinedVisualiser:
    """
    Allocentric visualiser for the MISHA WPSNN system.

    Left axis  — LiDAR scanner in world-frame coordinates.
    Right axis — WPSNN SpatialMap sliding window centred on the decoded
                 robot position. Shows Iinh (obstacle map), active spikes,
                 decoded position, and planned path.

    Robot is driven via keyboard (WASD). All injection is allocentric —
    LiDAR hits are transformed to world-frame coordinates before injection
    into SpatialMap, BVCells, and OVCells.

    Persistence filter classifies hits as boundary (BVC) or object (OVC):
        - Each world-frame bin maintains a persistence counter
        - Counter increments when a hit lands in the bin each scan cycle
        - Counter decrements each cycle when no hit is observed
        - Bins above PERSISTENCE_TAU are classified as boundary (BVC)
        - Bins below are classified as object (OVC)
    """

    def __init__(self, lidar: LIDARSimulator, network: WPSNN):
        self.lidar   = lidar
        self.network = network

        # ── simulation state ─────────────────────────────────────────────
        self.scanning       = False
        self.running        = False
        self.currentAngle   = 0.0
        self.timestep       = 0
        self._waveDone      = True
        self._lastFrameTime = time.perf_counter()
        self.path           = None
        self.targetX        = None
        self.targetY        = None

        # ── robot state ──────────────────────────────────────────────────
        self.robotX       = float(lidar.sensorX)   # world-frame position
        self.robotY       = float(lidar.sensorY)
        self.robotHeading = 0.0             # radians, allocentric
        self.linearSpeed  = 0.5             # m/s
        self.turnSpeed    = 1.0             # rad/s
        self.keysHeld     = set()

        # ── ray trail ────────────────────────────────────────────────────
        self.rayTrail    = []
        self.trailLength = 2

        # ── persistence filter state ─────────────────────────────────────
        # Counter grid — one cell per WPSNN spatial bin
        # Shape: (PLACE_SIDE, PLACE_SIDE)
        self._persistenceGrid  = numpy.zeros(
            (PLACE_SIDE, PLACE_SIDE), dtype=numpy.int32
        )
        # Bins observed in the current scan cycle — reset each revolution
        self._observedThisCycle = numpy.zeros(
            (PLACE_SIDE, PLACE_SIDE), dtype=bool
        )

        # ── precompute neuron coordinates for rendering ──────────────────
        coords       = numpy.array(network._lattice)
        self._allXs  = coords[:, 0]
        self._allYs  = coords[:, 1]

        # ── figure layout ────────────────────────────────────────────────
        self.fig = plt.figure(figsize=(16, 8))
        self.fig.patch.set_facecolor("#0f0f1a")
        self.fig.canvas.mpl_connect("key_press_event",   self._onKeyPress)
        self.fig.canvas.mpl_connect("key_release_event", self._onKeyRelease)

        # Left axis — LiDAR world-frame view
        self.axLidar = self.fig.add_axes([0.03, 0.10, 0.42, 0.85])
        self.axLidar.set_facecolor("#0f0f1a")
        self.axLidar.set_title("LiDAR — world frame", color="white", pad=10)
        self.axLidar.tick_params(colors="grey")
        self.axLidar.set_aspect("equal")
        self.axLidar.set_xlim(-lidar.maxRange * 1.1, lidar.maxRange * 1.1)
        self.axLidar.set_ylim(-lidar.maxRange * 1.1, lidar.maxRange * 1.1)

        # Right axis — WPSNN sliding window
        self.axNet = self.fig.add_axes([0.48, 0.10, 0.42, 0.85])
        self.axNet.set_facecolor("#0f0f1a")
        self.axNet.set_title("SpatialMap — allocentric sliding window", color="white", pad=10)
        self.axNet.tick_params(colors="grey")
        self.axNet.set_aspect("equal")

        # ── LiDAR layers ─────────────────────────────────────────────────
        for (x1, y1), (x2, y2) in self.lidar.walls:
            self.axLidar.plot(
                [x1, x2], [y1, y2],
                color="#4a4a8a", linewidth=1.5, zorder=1
            )

        self.sensorMarker = self.axLidar.scatter(
            [self.robotX], [self.robotY],
            c="red", s=60, zorder=5, label="robot"
        )
        # Heading arrow on LiDAR axis
        self.headingArrow = self.axLidar.annotate(
            "", xy=(self.robotX, self.robotY),
            xytext=(self.robotX, self.robotY),
            arrowprops=dict(arrowstyle="->", color="red", lw=1.5)
        )
        self.scatterHits = self.axLidar.scatter(
            [], [], c="green", s=4, alpha=0.8, zorder=3
        )
        self.rayLine, = self.axLidar.plot(
            [], [], color="green", linewidth=0.8, alpha=0.6, zorder=2
        )
        self.hitXs = []
        self.hitYs = []

        # ── WPSNN layers — initially empty, updated each frame ───────────
        # Iinh heatmap — only neurons in sliding window are rendered
        self.scatterIinh = self.axNet.scatter(
            [], [], c=[], cmap="hot",
            vmin=0.0, vmax=float(CURRENT_CLAMP),
            s=6, alpha=0.8, zorder=1
        )
        # Active spikes
        self.scatterSpikes = self.axNet.scatter(
            [], [], c="cyan", s=20, zorder=2
        )
        # Decoded position marker
        self.decodedMarker = self.axNet.scatter(
            [], [], c="red", s=80, marker="o", zorder=4,
            edgecolors="white", linewidths=0.8, label="decoded pos"
        )
        # Target marker
        self.scatterTarget = self.axNet.scatter(
            [], [], c="yellow", s=80, marker="*", zorder=5,
            edgecolors="white", linewidths=0.5, label="target"
        )
        # Path line
        self.pathLine, = self.axNet.plot(
            [], [], color="white", linewidth=1.5, alpha=0.85, zorder=6
        )
        # Decoded heading arrow on WPSNN axis
        self.decodedArrow = self.axNet.annotate(
            "", xy=(0, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", color="red", lw=1.5)
        )

        # Target selection via click on WPSNN axis
        self.fig.canvas.mpl_connect("button_press_event", self._onNetClick)

        # ── info panel ───────────────────────────────────────────────────
        infoAx = self.fig.add_axes([0.92, 0.50, 0.07, 0.45])
        infoAx.set_facecolor("#0f0f1a")
        infoAx.axis("off")

        self.timestepText  = infoAx.text(0.05, 0.95, "Step: 0",          color="white", transform=infoAx.transAxes, fontsize=8)
        self.angleText     = infoAx.text(0.05, 0.84, "Angle: 0.00",      color="white", transform=infoAx.transAxes, fontsize=8)
        self.hitsText      = infoAx.text(0.05, 0.73, "Hits: 0",          color="white", transform=infoAx.transAxes, fontsize=8)
        self.targetText    = infoAx.text(0.05, 0.62, "Target: None",      color="white", transform=infoAx.transAxes, fontsize=8)
        self.posText       = infoAx.text(0.05, 0.51, "Pos: (0.00, 0.00)", color="cyan",  transform=infoAx.transAxes, fontsize=8)
        self.hdText        = infoAx.text(0.05, 0.40, "HD: 0.00 rad",      color="cyan",  transform=infoAx.transAxes, fontsize=8)
        self.trueposText   = infoAx.text(0.05, 0.29, "True: (0.00,0.00)", color="green", transform=infoAx.transAxes, fontsize=8)
        self.bvcText       = infoAx.text(0.05, 0.18, "BVC inj: 0",        color="white", transform=infoAx.transAxes, fontsize=8)
        self.ovcText       = infoAx.text(0.05, 0.07, "OVC inj: 0",        color="white", transform=infoAx.transAxes, fontsize=8)

        # ── buttons ──────────────────────────────────────────────────────
        btnColor = "#2a2a4a"
        btnHover = "#3a3a6a"

        axScan      = self.fig.add_axes([0.92, 0.42, 0.07, 0.05])
        axClearScan = self.fig.add_axes([0.92, 0.36, 0.07, 0.05])
        axWave      = self.fig.add_axes([0.92, 0.30, 0.07, 0.05])
        axPath      = self.fig.add_axes([0.92, 0.24, 0.07, 0.05])
        axRunEnd    = self.fig.add_axes([0.92, 0.18, 0.07, 0.05])
        axRun       = self.fig.add_axes([0.92, 0.12, 0.07, 0.05])
        axReset     = self.fig.add_axes([0.92, 0.06, 0.07, 0.05])

        self.btnScan      = Button(axScan,      "Scan",         color=btnColor, hovercolor=btnHover)
        self.btnClearScan = Button(axClearScan, "Clear Scan",   color=btnColor, hovercolor=btnHover)
        self.btnWave      = Button(axWave,      "Trigger Wave", color=btnColor, hovercolor=btnHover)
        self.btnPath      = Button(axPath,      "Compute Path", color=btnColor, hovercolor=btnHover)
        self.btnRunEnd    = Button(axRunEnd,    "Run to End",   color=btnColor, hovercolor=btnHover)
        self.btnRun       = Button(axRun,       "Run",          color=btnColor, hovercolor=btnHover)
        self.btnReset     = Button(axReset,     "Reset Wave",   color=btnColor, hovercolor=btnHover)

        for btn in (self.btnScan, self.btnClearScan, self.btnWave,
                    self.btnPath, self.btnRunEnd, self.btnRun, self.btnReset):
            btn.label.set_color("white")

        self.btnScan.on_clicked(self._onToggleScan)
        self.btnClearScan.on_clicked(self._onClearScan)
        self.btnWave.on_clicked(self._onTriggerWave)
        self.btnPath.on_clicked(self._onComputePath)
        self.btnRunEnd.on_clicked(self._onRunToEnd)
        self.btnRun.on_clicked(self._onToggleRun)
        self.btnReset.on_clicked(self._onResetWave)

        # initial window bounds
        self._updateWindowBounds(0.0, 0.0)


    # -----------------------------------------------------------------------
    # Sliding window helpers
    # -----------------------------------------------------------------------

    def _updateWindowBounds(self, cx: float, cy: float):
        """
        Set the WPSNN axis limits to a WINDOW_HALF*2 square centred on (cx, cy).
        Clamps to arena bounds.
        """
        half     = ENV_SIZE / 2.0
        xMin     = numpy.clip(cx - WINDOW_HALF, -half, half - WINDOW_HALF * 2)
        xMax     = xMin + WINDOW_HALF * 2
        yMin     = numpy.clip(cy - WINDOW_HALF, -half, half - WINDOW_HALF * 2)
        yMax     = yMin + WINDOW_HALF * 2
        self.axNet.set_xlim(xMin, xMax)
        self.axNet.set_ylim(yMin, yMax)
        self._windowXMin = xMin
        self._windowXMax = xMax
        self._windowYMin = yMin
        self._windowYMax = yMax

    def _windowMask(self) -> numpy.ndarray:
        """
        Boolean mask over all lattice neurons — True if inside the current
        sliding window.

        Returns
        -------
        numpy.ndarray, shape (N_SPATIAL_MAP,), dtype bool
        """
        return (
            (self._allXs >= self._windowXMin) &
            (self._allXs <= self._windowXMax) &
            (self._allYs >= self._windowYMin) &
            (self._allYs <= self._windowYMax)
        )


    # -----------------------------------------------------------------------
    # Persistence filter
    # -----------------------------------------------------------------------

    def _worldBin(self, wx: float, wy: float):
        """
        Convert a world-frame coordinate to a persistence grid (row, col).

        Returns
        -------
        (int, int) or None if outside arena bounds.
        """
        half = ENV_SIZE / 2.0
        if not (-half <= wx < half and -half <= wy < half):
            return None
        col = int((wx + half) / NEURON_SPACING)
        row = int((wy + half) / NEURON_SPACING)
        col = min(col, PLACE_SIDE - 1)
        row = min(row, PLACE_SIDE - 1)
        return row, col

    def _persistenceUpdate(self, wx: float, wy: float):
        """
        Record a hit at world-frame position (wx, wy) in the current
        scan cycle's observation grid.

        Parameters
        ----------
        wx, wy : float — world-frame hit coordinates
        """
        cell = self._worldBin(wx, wy)
        if cell is not None:
            self._observedThisCycle[cell] = True

    def _persistenceCycleEnd(self):
        """
        Called at the end of each scan revolution.

        Increments counters for observed bins, decrements for unobserved.
        Resets the per-cycle observation grid.
        """
        self._persistenceGrid[self._observedThisCycle]  += 1
        self._persistenceGrid[~self._observedThisCycle] -= PERSISTENCE_DECAY
        numpy.clip(self._persistenceGrid, 0, PERSISTENCE_TAU * 2,
                   out=self._persistenceGrid)
        self._observedThisCycle[:] = False

    def _classifyHit(self, wx: float, wy: float) -> str:
        """
        Classify a world-frame hit as 'boundary' or 'object' based on
        the persistence counter at that bin.

        Returns
        -------
        'boundary' if counter >= PERSISTENCE_TAU, else 'object'
        """
        cell = self._worldBin(wx, wy)
        if cell is None:
            return "object"
        return "boundary" if self._persistenceGrid[cell] >= PERSISTENCE_TAU \
               else "object"


    # -----------------------------------------------------------------------
    # LiDAR callbacks
    # -----------------------------------------------------------------------

    def _onToggleScan(self, event):
        self.scanning = not self.scanning
        self.btnScan.label.set_text("Pause Scan" if self.scanning else "Scan")
        self.fig.canvas.draw_idle()

    def _onClearScan(self, event):
        self.hitXs              = []
        self.hitYs              = []
        self.currentAngle       = 0.0
        self.scanning           = False
        self._persistenceGrid[:] = 0
        self._observedThisCycle[:] = False
        self.btnScan.label.set_text("Scan")
        self.scatterHits.set_offsets(numpy.empty((0, 2)))
        self.rayLine.set_data([], [])
        self.hitsText.set_text("Hits: 0")
        self.angleText.set_text("Angle: 0.00")
        self.fig.canvas.draw_idle()


    # -----------------------------------------------------------------------
    # WPSNN callbacks
    # -----------------------------------------------------------------------

    def _onNetClick(self, event):
        """
        Click on the WPSNN axis to set a target in world-frame coordinates.
        """
        if event.inaxes is not self.axNet:
            return
        self.targetX = event.xdata
        self.targetY = event.ydata
        self.targetText.set_text(
            f"Target:\nx={self.targetX:.1f} y={self.targetY:.1f}"
        )
        self.scatterTarget.set_offsets([[self.targetX, self.targetY]])
        self.fig.canvas.draw_idle()

    def _onTriggerWave(self, event):
        """
        Initiate wavefront from decoded robot position.
        """
        decodedPos = self.network.decodePosition()
        try:
            self.network.propagateWave(
                float(decodedPos[0]),
                float(decodedPos[1])
            )
            self._waveDone = False
            print(f"Wave triggered from decoded position "
                  f"({decodedPos[0]:.2f}, {decodedPos[1]:.2f})")
        except ValueError as e:
            print(f"Wave trigger failed: {e}")
            print("Position decode may be unreliable — "
                  "ensure SpatialMap has received sufficient input.")

    def _onComputePath(self, event):
        if self.targetX is None or self.targetY is None:
            print("No target set — click on the SpatialMap axis to set one.")
            return
        if self.network.model.timestep < DURATION:
            remaining = DURATION - self.network.model.timestep
            print(f"Simulation not complete — {remaining} timesteps remaining.")
            return

        wasRunning   = self.running
        self.running = False

        decodedPos = self.network.decodePosition()

        try:
            self.network.backpropagateWave(
                self.targetX, self.targetY,
                float(decodedPos[0]), float(decodedPos[1])
            )
            path = self.network.calculatePath()

            if len(path) < 2:
                print("Path too short to display.")
                return

            coords = numpy.array([self.network._lattice[i] for i in path])
            self.pathLine.set_data(coords[:, 0], coords[:, 1])
            print(f"Path computed: {len(path)} neurons.")

        except (RuntimeError, ValueError) as e:
            print(f"Path computation failed: {e}")

        finally:
            self.running = wasRunning

        self.fig.canvas.draw_idle()

    def _onRunToEnd(self, event):
        self.running  = False
        remaining     = DURATION - self.network.model.timestep
        for _ in range(remaining):
            self.network.step()
            self.timestep += 1
        self.timestepText.set_text(f"Step: {self.timestep}")
        print("Simulation complete — ready to compute path.")
        self.fig.canvas.draw_idle()

    def _onToggleRun(self, event):
        self.running = not self.running
        self.btnRun.label.set_text("Pause" if self.running else "Run")
        self.fig.canvas.draw_idle()

    def _onResetWave(self, event):
        self.network.resetWaveProp()
        self.pathLine.set_data([], [])
        self.timestep     = 0
        self._waveDone    = True
        self.timestepText.set_text("Step: 0")
        print("Wave reset.")
        self.fig.canvas.draw_idle()


    # -----------------------------------------------------------------------
    # Robot driving
    # -----------------------------------------------------------------------

    def _onKeyPress(self, event):
        self.keysHeld.add(event.key)

    def _onKeyRelease(self, event):
        self.keysHeld.discard(event.key)

    def _driveRobot(self, elapsed: float):
        """
        Update robot world-frame position and heading from held keys.
        Propagates position to lidar sensor.

        W/S — forward/backward
        A/D — turn left/right
        """
        if "a" in self.keysHeld:
            self.robotHeading += self.turnSpeed * elapsed
        if "d" in self.keysHeld:
            self.robotHeading -= self.turnSpeed * elapsed

        if "w" in self.keysHeld:
            self.robotX += numpy.cos(self.robotHeading) * self.linearSpeed * elapsed
            self.robotY += numpy.sin(self.robotHeading) * self.linearSpeed * elapsed
        if "s" in self.keysHeld:
            self.robotX -= numpy.cos(self.robotHeading) * self.linearSpeed * elapsed
            self.robotY -= numpy.sin(self.robotHeading) * self.linearSpeed * elapsed

        # keep robot within arena
        half            = ENV_SIZE / 2.0
        self.robotX     = float(numpy.clip(self.robotX, -half, half))
        self.robotY     = float(numpy.clip(self.robotY, -half, half))
        self.robotHeading = self.robotHeading % (2 * numpy.pi)

        # sync lidar sensor position
        self.lidar.sensorX = self.robotX
        self.lidar.sensorY = self.robotY

        # update sensor marker and heading arrow on lidar axis
        self.sensorMarker.set_offsets([[self.robotX, self.robotY]])
        arrowLen = self.lidar.maxRange * 0.1
        self.headingArrow.set_position((self.robotX, self.robotY))
        self.headingArrow.xy = (
            self.robotX + arrowLen * numpy.cos(self.robotHeading),
            self.robotY + arrowLen * numpy.sin(self.robotHeading)
        )

        # update speed and heading input populations
        speed = self.linearSpeed if ("w" in self.keysHeld or
                                      "s" in self.keysHeld) else 0.0
        self.network.setSpeedInput(speed)
        self.network.setHDInput(self.robotHeading)


    # -----------------------------------------------------------------------
    # Animation loop
    # -----------------------------------------------------------------------

    def _update(self, frame):
        artists = (
            self.scatterHits, self.rayLine, self.sensorMarker,
            self.scatterIinh, self.scatterSpikes,
            self.scatterTarget, self.pathLine,
            self.decodedMarker
        )

        # ── timing ───────────────────────────────────────────────────────
        now     = time.perf_counter()
        elapsed = now - self._lastFrameTime
        self._lastFrameTime = now

        # ── robot driving ─────────────────────────────────────────────────
        self._driveRobot(elapsed)

        # ── LiDAR step ───────────────────────────────────────────────────
        closestT         = self.lidar.maxRange
        bvcInjCount      = 0
        ovcInjCount      = 0
        minAngVelocity   = None
        maxAngVelocity   = None
        stepsPerFrame    = max(1, int(elapsed * self.lidar.rangeFrequency))

        for _ in range(stepsPerFrame):
            self.currentAngle, hitX, hitY, closestT, modulatedAngularVelocity = \
                self.lidar.step(self.currentAngle)

            if maxAngVelocity is None or modulatedAngularVelocity > maxAngVelocity:
                maxAngVelocity = modulatedAngularVelocity
            if minAngVelocity is None or modulatedAngularVelocity < minAngVelocity:
                minAngVelocity = modulatedAngularVelocity

            if hitX is not None:
                # ── allocentric transform ─────────────────────────────
                # LiDAR returns egocentric (hitX, hitY) relative to sensor.
                # Transform to world-frame by adding robot position.
                worldHitX = hitX + self.robotX
                worldHitY = hitY + self.robotY

                self.hitXs.append(worldHitX)
                self.hitYs.append(worldHitY)

                # record in persistence filter
                self._persistenceUpdate(worldHitX, worldHitY)

                # ── allocentric (d, phi) ──────────────────────────────
                dx  = worldHitX - self.robotX
                dy  = worldHitY - self.robotY
                d   = numpy.sqrt(dx**2 + dy**2)
                phi = numpy.arctan2(dy, dx) % (2 * numpy.pi)

                # ── classify and inject ───────────────────────────────
                classification = self._classifyHit(worldHitX, worldHitY)

                if classification == "boundary":
                    self.network.injectIntoBVCPopulation(d, phi)
                    bvcInjCount += 1
                else:
                    self.network.injectIntoOVCPopulation(d, phi)
                    ovcInjCount += 1

                # ── inject into spatial map ───────────────────────────
                #self.network.injectGaussian(worldHitX, worldHitY)

            if self.currentAngle >= 2 * numpy.pi:
                self.currentAngle = 0.0
                self.lidar.resetRevolution()
                self._persistenceCycleEnd()
                print(
                    f"Scan cycle complete — {len(self.hitXs)} total hits | "
                    f"BVC: {bvcInjCount} OVC: {ovcInjCount} | "
                    f"ω min: {minAngVelocity:.3f} max: {maxAngVelocity:.3f}"
                )
                self.hitXs = []
                self.hitYs = []
                break

        # ── update LiDAR scatter ─────────────────────────────────────────
        if len(self.hitXs) > 0:
            self.scatterHits.set_offsets(
                numpy.column_stack([self.hitXs, self.hitYs])
            )
        else:
            self.scatterHits.set_offsets(numpy.empty((0, 2)))

        # ray trail
        rayDirX = numpy.cos(self.currentAngle)
        rayDirY = numpy.sin(self.currentAngle)
        endX    = self.lidar.sensorX + closestT * rayDirX
        endY    = self.lidar.sensorY + closestT * rayDirY
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
        self.bvcText.set_text(f"BVC inj: {bvcInjCount}")
        self.ovcText.set_text(f"OVC inj: {ovcInjCount}")
        self.trueposText.set_text(
            f"True: ({self.robotX:.1f}, {self.robotY:.1f})"
        )

        # ── WPSNN step ───────────────────────────────────────────────────
        if self.running:
            for _ in range(UPDATE_INTERVAL_MS):
                self.network.step()
                self.timestep += 1

            # pull state from device
            self.network.spatialMap.vars["V"].pull_from_device()
            self.network.spatialMap.vars["Iinh"].pull_from_device()

            vValues    = numpy.array(self.network.spatialMap.vars["V"].view)
            iinhValues = numpy.array(self.network.spatialMap.vars["Iinh"].view)

            # ── decode position and heading ───────────────────────────
            decodedPos = self.network.decodePosition()
            decodedHD  = self.network.decodeHeading()

            dx  = float(decodedPos[0])
            dy  = float(decodedPos[1])

            # update sliding window centred on decoded position
            self._updateWindowBounds(dx, dy)

            # ── update WPSNN scatter (window only) ────────────────────
            mask         = self._windowMask()
            windowXs     = self._allXs[mask]
            windowYs     = self._allYs[mask]
            windowIinh   = iinhValues[mask]
            windowV      = vValues[mask]

            if len(windowXs) > 0:
                self.scatterIinh.set_offsets(
                    numpy.column_stack([windowXs, windowYs])
                )
                self.scatterIinh.set_array(windowIinh)
            else:
                self.scatterIinh.set_offsets(numpy.empty((0, 2)))
                self.scatterIinh.set_array(numpy.array([]))

            # active spikes within window
            spikeThresh   = -50.0
            activeLocal   = numpy.where(windowV >= spikeThresh)[0]
            if len(activeLocal) > 0:
                self.scatterSpikes.set_offsets(
                    numpy.column_stack([
                        windowXs[activeLocal],
                        windowYs[activeLocal]
                    ])
                )
            else:
                self.scatterSpikes.set_offsets(numpy.empty((0, 2)))
                if not self._waveDone:
                    print(f"Wave finished at timestep {self.timestep}")
                    self._waveDone = True

            # decoded position marker
            self.decodedMarker.set_offsets([[dx, dy]])

            # decoded heading arrow
            arrowLen = WINDOW_HALF * 0.12
            self.decodedArrow.set_position((dx, dy))
            self.decodedArrow.xy = (
                dx + arrowLen * numpy.cos(decodedHD),
                dy + arrowLen * numpy.sin(decodedHD)
            )

            # info panel
            self.posText.set_text(f"Pos: ({dx:.1f}, {dy:.1f})")
            self.hdText.set_text(f"HD: {numpy.degrees(decodedHD):.1f}°")
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    lidar = LIDARSimulator()
    lidar.addRectangle(-11.9, -11.9, 24, 24)

    lidar.addWall(-3.6,  3.2,  5.0,  5.2)
    lidar.addWall(-1.0, -1.0, 10.0, -1.0)
    lidar.addWall(10.0, -1.0, 10.0,  8.0)

    network    = WPSNN()
    visualiser = CombinedVisualiser(lidar, network)
    visualiser.run()