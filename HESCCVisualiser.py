import numpy
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import FancyArrowPatch
import time

from HESCC import (HESCC, ENV_SIZE, NEURON_SPACING, PLACE_SIDE, CURRENT_CLAMP,
                   BVC_AMOUNT, OVC_AMOUNT, HD_CELL_AMOUNT, GRID_CELL_AMOUNT,
                   GRID_SIDE, SPEED_CELL_AMOUNT, PHI_BIN_AMOUNT, DISTANCE_BIN_AMOUNT)
from LIDARInterface import LiDARInterface

# ── Pipeline constants ────────────────────────────────────────────────────────
UPDATE_INTERVAL_MS = 5
PERSISTENCE_TAU    = 5
PERSISTENCE_DECAY  = 1
SERIAL_PORT        = "COM5"
SERIAL_BAUD        = 115200
CLV_SCALE          = 50.0
CLV_MIN_DUTY       = 60
CLV_MAX_DUTY       = 200


class HESCCPipelineVisualiser:
    """
    Live pipeline visualiser for HESCC + LD06 LiDAR.

    Layout
    ------
    Left panel — each neuron population displayed as a live activity plot,
    arranged to mirror the actual network connectivity.  Arrows between
    populations follow the synaptic pathways defined in HESCC.__init__.

    Right panel — full Spatial Map imshow (PLACE_SIDE × PLACE_SIDE) with
    decoded position and heading overlaid.

    Population displays
    -------------------
    Speed Input / Speed Cells  — line plot of firingRate / V−Vrest
    HD Input    / HD Cells     — line plot over preferred angle (0–2π)
    Grid Cells                 — imshow  (GRID_CELL_AMOUNT//GRID_SIDE) × GRID_SIDE
    BVC                        — imshow  PHI_BIN_AMOUNT × DISTANCE_BIN_AMOUNT
    OVC                        — imshow  PHI_BIN_AMOUNT × DISTANCE_BIN_AMOUNT
    Spatial Map                — imshow  PLACE_SIDE × PLACE_SIDE

    Arrows
    ------
    Drawn once in figure-fraction coordinates after the first canvas render
    so that axes positions are finalised.  Colours match the pathway type:
      cyan   — speed pathway
      amber  — head-direction pathway
      purple — path integration (grid → place)
      green  — BVC → SpatialMap  (Oja, boundary cues)
      coral  — OVC → SpatialMap  (Oja, object cues)

    LiDAR pipeline
    --------------
    Unchanged from the original HESCCVisualiser: each animation frame drains
    the latest complete revolution, classifies hits via the persistence filter,
    and injects into BVC or OVC populations.  CLV duty is computed and sent
    back to the ESP32 over serial.
    """

    VREST = -65.0
    VMAX  = 15.0      # Vthresh − Vrest = −50 − (−65) = 15 mV

    # ── colour palette for pathways ──────────────────────────────────────────
    C_SPEED = "#00ccff"
    C_HD    = "#ff9900"
    C_GRID  = "#aa88ff"
    C_BVC   = "#44ff88"
    C_OVC   = "#ff6644"

    def __init__(self, network: HESCC, lidar: LiDARInterface):
        self.network  = network
        self.lidar    = lidar
        self.running  = True
        self.timestep = 0

        # ── persistence filter state ─────────────────────────────────────
        self._persistenceGrid   = numpy.zeros(
            (PLACE_SIDE, PLACE_SIDE), dtype=numpy.int32
        )
        self._observedThisCycle = numpy.zeros(
            (PLACE_SIDE, PLACE_SIDE), dtype=bool
        )

        # ── figure ────────────────────────────────────────────────────────
        self.fig = plt.figure(figsize=(22, 11))
        self.fig.patch.set_facecolor("#0d0d1a")
        self.fig.suptitle(
            "HESCC — Live Pipeline Monitor",
            color="white", fontsize=13, y=0.99
        )

        # ── population axes (left panel) ──────────────────────────────────
        #   [left, bottom, width, height]  in figure-fraction coordinates
        self.axSpeedIn = self._makeAx([0.02, 0.84, 0.08, 0.11], "Speed Input")
        self.axSpeed   = self._makeAx([0.13, 0.84, 0.08, 0.11], "Speed Cells")
        self.axHDIn    = self._makeAx([0.02, 0.58, 0.08, 0.20], "HD Input")
        self.axHD      = self._makeAx([0.13, 0.58, 0.08, 0.20], "HD Cells")
        self.axGrid    = self._makeAx([0.24, 0.56, 0.12, 0.34], "Grid Cells")
        self.axBVC     = self._makeAx([0.02, 0.28, 0.17, 0.24], "BVC")
        self.axOVC     = self._makeAx([0.02, 0.02, 0.17, 0.24], "OVC")

        # ── spatial map axis (right panel) ────────────────────────────────
        self.axSMap = self._makeAx([0.42, 0.03, 0.54, 0.93], "Spatial Map")

        # ── Speed Input: firingRate line ──────────────────────────────────
        self.lineSpeedIn, = self.axSpeedIn.plot(
            numpy.arange(SPEED_CELL_AMOUNT),
            numpy.zeros(SPEED_CELL_AMOUNT),
            color=self.C_SPEED, lw=0.8
        )
        self.axSpeedIn.set_ylim(0, 110)
        self.axSpeedIn.set_xlim(0, SPEED_CELL_AMOUNT - 1)
        self.axSpeedIn.set_ylabel("Hz", color="grey", fontsize=6)

        # ── Speed Cells: V−Vrest line ────────────────────────────────────
        self.lineSpeed, = self.axSpeed.plot(
            numpy.arange(SPEED_CELL_AMOUNT),
            numpy.zeros(SPEED_CELL_AMOUNT),
            color=self.C_SPEED, lw=0.8
        )
        self.axSpeed.set_ylim(0, self.VMAX)
        self.axSpeed.set_xlim(0, SPEED_CELL_AMOUNT - 1)
        self.axSpeed.set_ylabel("mV", color="grey", fontsize=6)

        # ── HD Input: firingRate over preferred angle ─────────────────────
        hdAngles = network._hdCoords
        self.lineHDIn, = self.axHDIn.plot(
            hdAngles, numpy.zeros(HD_CELL_AMOUNT),
            color=self.C_HD, lw=0.8
        )
        self.axHDIn.set_ylim(0, 110)
        self.axHDIn.set_xlim(0, 2 * numpy.pi)
        self.axHDIn.set_xticks([0, numpy.pi, 2 * numpy.pi])
        self.axHDIn.set_xticklabels(["0", "π", "2π"], color="grey", fontsize=6)
        self.axHDIn.set_ylabel("Hz", color="grey", fontsize=6)

        # ── HD Cells: V−Vrest over preferred angle ────────────────────────
        self.lineHD, = self.axHD.plot(
            hdAngles, numpy.zeros(HD_CELL_AMOUNT),
            color=self.C_HD, lw=0.8
        )
        self.axHD.set_ylim(0, self.VMAX)
        self.axHD.set_xlim(0, 2 * numpy.pi)
        self.axHD.set_xticks([0, numpy.pi, 2 * numpy.pi])
        self.axHD.set_xticklabels(["0", "π", "2π"], color="grey", fontsize=6)
        self.axHD.set_ylabel("mV", color="grey", fontsize=6)

        # ── Grid Cells: imshow (GRID_CELL_AMOUNT//GRID_SIDE) × GRID_SIDE ──
        _gridRows = GRID_CELL_AMOUNT // GRID_SIDE
        self.imGrid = self.axGrid.imshow(
            numpy.zeros((_gridRows, GRID_SIDE)),
            aspect="auto", cmap="plasma",
            vmin=0, vmax=self.VMAX, origin="lower"
        )
        self.fig.colorbar(
            self.imGrid, ax=self.axGrid, fraction=0.046, pad=0.04
        ).ax.tick_params(labelsize=6, colors="grey")

        # ── BVC: imshow PHI_BIN_AMOUNT × DISTANCE_BIN_AMOUNT ─────────────
        self.imBVC = self.axBVC.imshow(
            numpy.zeros((PHI_BIN_AMOUNT, DISTANCE_BIN_AMOUNT)),
            aspect="auto", cmap="viridis",
            vmin=0, vmax=self.VMAX, origin="lower"
        )
        self.axBVC.set_xlabel("distance bin", color="grey", fontsize=6)
        self.axBVC.set_ylabel("φ bin",         color="grey", fontsize=6)
        self.fig.colorbar(
            self.imBVC, ax=self.axBVC, fraction=0.046, pad=0.04
        ).ax.tick_params(labelsize=6, colors="grey")

        # ── OVC: imshow PHI_BIN_AMOUNT × DISTANCE_BIN_AMOUNT ─────────────
        self.imOVC = self.axOVC.imshow(
            numpy.zeros((PHI_BIN_AMOUNT, DISTANCE_BIN_AMOUNT)),
            aspect="auto", cmap="viridis",
            vmin=0, vmax=self.VMAX, origin="lower"
        )
        self.axOVC.set_xlabel("distance bin", color="grey", fontsize=6)
        self.axOVC.set_ylabel("φ bin",         color="grey", fontsize=6)
        self.fig.colorbar(
            self.imOVC, ax=self.axOVC, fraction=0.046, pad=0.04
        ).ax.tick_params(labelsize=6, colors="grey")

        # ── Spatial Map: imshow PLACE_SIDE × PLACE_SIDE ───────────────────
        _half = ENV_SIZE / 2.0
        self.imSMap = self.axSMap.imshow(
            numpy.zeros((PLACE_SIDE, PLACE_SIDE)),
            aspect="equal", cmap="hot",
            vmin=0, vmax=self.VMAX, origin="lower",
            extent=[-_half, _half, -_half, _half]
        )
        self.fig.colorbar(
            self.imSMap, ax=self.axSMap,
            fraction=0.03, pad=0.02, label="V − Vrest (mV)"
        ).ax.tick_params(labelsize=7, colors="grey")

        # decoded position marker + heading arrow overlaid on Spatial Map
        self.posMarker, = self.axSMap.plot(
            [], [], "o", color="red", ms=8, zorder=5,
            markeredgecolor="white", markeredgewidth=0.8
        )
        self.hdArrow = self.axSMap.annotate(
            "", xy=(0, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", color="red", lw=2.0), zorder=6
        )
        self.axSMap.set_xlim(-_half, _half)
        self.axSMap.set_ylim(-_half, _half)
        self.axSMap.set_xlabel("x (m)", color="grey", fontsize=8)
        self.axSMap.set_ylabel("y (m)", color="grey", fontsize=8)

        # status text overlay
        self.txtStatus = self.axSMap.text(
            0.02, 0.98, "", color="white", fontsize=7,
            transform=self.axSMap.transAxes, va="top",
            bbox=dict(facecolor="#1a1a2e", alpha=0.75, edgecolor="none")
        )

        # ── Run / Pause button ────────────────────────────────────────────
        from matplotlib.widgets import Button
        axBtn = self.fig.add_axes([0.02, 0.965, 0.07, 0.025])
        self.btnRun = Button(
            axBtn, "Pause", color="#2a2a4a", hovercolor="#3a3a6a"
        )
        self.btnRun.label.set_color("white")
        self.btnRun.on_clicked(self._toggleRun)

    # ── axis factory ──────────────────────────────────────────────────────────

    def _makeAx(self, rect, title):
        ax = self.fig.add_axes(rect)
        ax.set_facecolor("#12122a")
        ax.set_title(title, color="white", fontsize=8, pad=3)
        ax.tick_params(colors="grey", labelsize=6)
        for sp in ax.spines.values():
            sp.set_edgecolor("#3a3a6a")
        return ax

    # ── connectivity arrows ───────────────────────────────────────────────────

    def _drawArrows(self):
        """
        Draw FancyArrowPatch connections between population axes in
        figure-fraction coordinates.  Must be called after canvas.draw()
        so that axes positions are finalised.
        """
        def _pos(ax):
            """Return (x0, x1, y0, y1, xc, yc) for an axis."""
            p = ax.get_position()
            return p.x0, p.x1, p.y0, p.y1, \
                   (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2

        def _arrow(x1, y1, x2, y2, color, label="", rad=0.0):
            patch = FancyArrowPatch(
                (x1, y1), (x2, y2),
                transform=self.fig.transFigure,
                arrowstyle="->", color=color, lw=1.3,
                mutation_scale=12,
                connectionstyle=f"arc3,rad={rad}",
                zorder=9
            )
            self.fig.add_artist(patch)
            if label:
                self.fig.text(
                    (x1 + x2) / 2,
                    max(y1, y2) + 0.016,
                    label,
                    color=color, fontsize=6, ha="center",
                    transform=self.fig.transFigure
                )

        si = _pos(self.axSpeedIn)
        sc = _pos(self.axSpeed)
        hi = _pos(self.axHDIn)
        hc = _pos(self.axHD)
        gc = _pos(self.axGrid)
        bv = _pos(self.axBVC)
        ov = _pos(self.axOVC)
        sm = _pos(self.axSMap)

        # Speed Input → Speed Cells  (straight horizontal)
        _arrow(si[1], si[5], sc[0], sc[5], self.C_SPEED)

        # Speed Cells → Grid Cells  (arc down — Speed sits above Grid)
        _arrow(sc[1], sc[5], gc[0], gc[5],
               self.C_SPEED, label="speed", rad=-0.25)

        # HD Input → HD Cells  (straight horizontal)
        _arrow(hi[1], hi[5], hc[0], hc[5], self.C_HD)

        # HD Cells → Grid Cells  (slight arc)
        _arrow(hc[1], hc[5], gc[0], gc[5],
               self.C_HD, label="HD", rad=0.1)

        # Grid Cells → Spatial Map  (path integration)
        _arrow(gc[1], gc[5], sm[0], sm[5],
               self.C_GRID, label="path integration")

        # BVC → Spatial Map  (Oja, boundary cues — arc below centre)
        _arrow(bv[1], bv[5], sm[0], sm[5] + 0.08,
               self.C_BVC, label="Oja (boundaries)", rad=-0.12)

        # OVC → Spatial Map  (Oja, object cues — arc above centre)
        _arrow(ov[1], ov[5], sm[0], sm[5] - 0.08,
               self.C_OVC, label="Oja (objects)", rad=0.12)

    # ── persistence filter (unchanged from original) ──────────────────────────

    def _worldBin(self, d: float, phi: float):
        pos  = self.network.decodePosition()
        wx   = float(pos[0]) + d * numpy.cos(phi)
        wy   = float(pos[1]) + d * numpy.sin(phi)
        half = ENV_SIZE / 2.0
        if not (-half <= wx < half and -half <= wy < half):
            return None
        col = min(int((wx + half) / NEURON_SPACING), PLACE_SIDE - 1)
        row = min(int((wy + half) / NEURON_SPACING), PLACE_SIDE - 1)
        return row, col

    def _persistenceUpdate(self, d: float, phi: float):
        cell = self._worldBin(d, phi)
        if cell is not None:
            self._observedThisCycle[cell] = True

    def _persistenceCycleEnd(self):
        self._persistenceGrid[ self._observedThisCycle] += 1
        self._persistenceGrid[~self._observedThisCycle] -= PERSISTENCE_DECAY
        numpy.clip(self._persistenceGrid, 0, PERSISTENCE_TAU * 2,
                   out=self._persistenceGrid)
        self._observedThisCycle[:] = False

    def _classifyHit(self, d: float, phi: float) -> str:
        cell = self._worldBin(d, phi)
        if cell is None:
            return "object"
        return "boundary" if self._persistenceGrid[cell] >= PERSISTENCE_TAU \
               else "object"

    # ── CLV ───────────────────────────────────────────────────────────────────

    def _clvDuty(self, points: list):
        if not points:
            return CLV_MIN_DUTY, 0.0
        d_min = min(d for d, _ in points)
        duty  = int(numpy.clip(CLV_SCALE / d_min, CLV_MIN_DUTY, CLV_MAX_DUTY))
        return duty, d_min

    # ── helpers ───────────────────────────────────────────────────────────────

    def _pullV(self, pop) -> numpy.ndarray:
        """Pull membrane voltage and return V − Vrest, clipped to [0, ∞)."""
        pop.vars["V"].pull_from_device()
        return numpy.maximum(
            numpy.array(pop.vars["V"].view, dtype=numpy.float32) - self.VREST,
            0.0
        )

    def _pullRate(self, pop) -> numpy.ndarray:
        """Pull Poisson firing rate from an input population."""
        pop.vars["firingRate"].pull_from_device()
        return numpy.array(pop.vars["firingRate"].view, dtype=numpy.float32)

    def _toggleRun(self, event):
        self.running = not self.running
        self.btnRun.label.set_text("Pause" if self.running else "Run")
        self.fig.canvas.draw_idle()

    # ── animation update ──────────────────────────────────────────────────────

    def _update(self, frame):
        # ── drain latest LiDAR revolution ─────────────────────────────────
        points   = self.lidar.latest_scan()
        bvcCount = 0
        ovcCount = 0
        duty     = CLV_MIN_DUTY
        d_min    = 0.0

        if points:
            self.network.setHDInput(0.0)
            self.network.setSpeedInput(0.1)

            for d, phi in points:
                self._persistenceUpdate(d, phi)
            self._persistenceCycleEnd()

            for d, phi in points:
                if self._classifyHit(d, phi) == "boundary":
                    self.network.injectIntoBVCPopulation(d, phi)
                    bvcCount += 1
                else:
                    self.network.injectIntoOVCPopulation(d, phi)
                    ovcCount += 1

            duty, d_min = self._clvDuty(points)
            try:
                self.lidar._serial.write(b"D" + bytes([duty]))
            except Exception:
                pass

        # ── HESCC steps ───────────────────────────────────────────────────
        if self.running:
            for _ in range(UPDATE_INTERVAL_MS):
                self.network.step()
                self.timestep += 1

        # ── pull activity from every population ───────────────────────────
        speedInRate = self._pullRate(self.network.speedInputPop)
        hdInRate    = self._pullRate(self.network.hdInputPop)
        speedV      = self._pullV(self.network.speedCellPop)
        hdV         = self._pullV(self.network.hdCellPop)
        gridV       = self._pullV(self.network.gridCellPop)
        bvcV        = self._pullV(self.network.BVCPop)
        ovcV        = self._pullV(self.network.OVCPop)
        smapV       = self._pullV(self.network.spatialMap)

        if self.timestep % 100 == 0:
            print(f"t={self.timestep}  SpatialMap V-Vrest: "
                  f"min={smapV.min():.3f}  max={smapV.max():.3f}  "
                  f"mean={smapV.mean():.4f}  (threshold gap = {self.VMAX})")
            print(f"t={self.timestep}  GridCells V-Vrest: "
                  f"max={gridV.max():.3f}  (threshold gap = {self.VMAX})")

        # ── update line plots ─────────────────────────────────────────────
        self.lineSpeedIn.set_ydata(speedInRate)
        self.lineSpeed.set_ydata(speedV)
        self.lineHDIn.set_ydata(hdInRate)
        self.lineHD.set_ydata(hdV)

        # ── update imshows ────────────────────────────────────────────────
        _gridRows = GRID_CELL_AMOUNT // GRID_SIDE
        self.imGrid.set_data(gridV.reshape(_gridRows, GRID_SIDE))
        self.imBVC.set_data(bvcV.reshape(PHI_BIN_AMOUNT, DISTANCE_BIN_AMOUNT))
        self.imOVC.set_data(ovcV.reshape(PHI_BIN_AMOUNT, DISTANCE_BIN_AMOUNT))
        self.imSMap.set_data(smapV.reshape(PLACE_SIDE, PLACE_SIDE))

        # ── decoded position and heading overlay ──────────────────────────
        decodedPos = self.network.decodePosition()
        decodedHD  = self.network.decodeHeading()
        dx, dy     = float(decodedPos[0]), float(decodedPos[1])

        self.posMarker.set_data([dx], [dy])
        arrowLen = 2.0
        self.hdArrow.set_position((dx, dy))
        self.hdArrow.xy = (
            dx + arrowLen * numpy.cos(decodedHD),
            dy + arrowLen * numpy.sin(decodedHD)
        )

        # ── status text ───────────────────────────────────────────────────
        self.txtStatus.set_text(
            f"t={self.timestep}  "
            f"pos=({dx:.1f},{dy:.1f})  "
            f"HD={numpy.degrees(decodedHD):.0f}°\n"
            f"BVC={bvcCount}  OVC={ovcCount}  "
            f"PWM={duty}  d_min={d_min:.2f}m\n"
            f"revs={self.lidar.revolutions}  "
            f"pkts={self.lidar.packets_received}  "
            f"drop={self.lidar.packets_dropped}"
        )

        return (
            self.lineSpeedIn, self.lineSpeed,
            self.lineHDIn,    self.lineHD,
            self.imGrid, self.imBVC, self.imOVC, self.imSMap,
            self.posMarker,   self.txtStatus,
        )

    # ── entry point ───────────────────────────────────────────────────────────

    def run(self):
        # Force a full render first so all axes positions are finalised,
        # then draw the static connectivity arrows before the animation loop.
        self.fig.canvas.draw()
        self._drawArrows()

        self.ani = animation.FuncAnimation(
            self.fig, self._update,
            frames=None, interval=50,
            blit=False, cache_frame_data=False
        )
        plt.show()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("! Initialising HESCC model")
    network = HESCC()

    print("! Starting LiDAR interface")
    lidar = LiDARInterface(port=SERIAL_PORT, baud=SERIAL_BAUD)
    lidar._last_duty = 102
    lidar.start()

    print("! Launching visualiser")
    vis = HESCCPipelineVisualiser(network, lidar)

    try:
        vis.run()
    finally:
        lidar.stop()