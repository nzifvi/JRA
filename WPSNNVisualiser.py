import numpy
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button

from WPSNN import WPSNN

UPDATE_INTERVAL_MS = 5  # simulation steps per animation frame


class WPSNNVisualiser:
    def __init__(self, network: WPSNN):
        self.network  = network
        self.timestep = 0
        self.running  = False
        self.mode     = "inject"   # "inject" | "target"
        self.targetX  = None
        self.targetY  = None
        self._waveDone = True

        # precompute coordinate arrays for all neurons
        coords  = numpy.array(network.lattice)
        self.xs = coords[:, 0]
        self.ys = coords[:, 1]

        # ── figure layout ────────────────────────────────────────────────
        self.fig = plt.figure(figsize=(10, 8))
        self.fig.patch.set_facecolor("#1a1a2e")

        # cartesian axis for the network
        self.ax = self.fig.add_axes([0.05, 0.15, 0.65, 0.80])
        self.ax.set_facecolor("#0f0f1a")
        self.ax.set_title("WPSNN Visualiser", color="white", pad=12)
        self.ax.tick_params(colors="grey")
        self.ax.set_aspect("equal")

        # ── scatter layers ───────────────────────────────────────────────
        # layer 1: Iinh heatmap (obstacle model)
        self.scatterIinh = self.ax.scatter(
            self.xs, self.ys,
            c=numpy.zeros(len(self.xs)),
            cmap="hot", vmin=0.0, vmax=float(network.currentClamp),
            s=20, alpha=0.6, zorder=1
        )

        # layer 2: spiking neurons (wave propagation)
        self.scatterSpikes = self.ax.scatter(
            [], [],
            c="cyan", s=35, zorder=2, label="Spiking"
        )

        # layer 3: target neuron marker
        self.scatterTarget = self.ax.scatter(
            [], [],
            c="red", s=80, marker="*", zorder=3,
            edgecolors="white", linewidths=0.5, label="Target"
        )

        # layer 4: computed path line
        self.pathLine, = self.ax.plot(
            [], [], color="white", linewidth=1.5,
            alpha=0.85, zorder=4
        )

        # make neurons pickable
        self.scatterIinh.set_picker(8)
        self.fig.canvas.mpl_connect("pick_event", self._onPick)

        # ── info panel ───────────────────────────────────────────────────
        infoAx = self.fig.add_axes([0.72, 0.50, 0.26, 0.45])
        infoAx.set_facecolor("#0f0f1a")
        infoAx.axis("off")

        self.modeText     = infoAx.text(0.05, 0.90, "Mode: INJECT",  color="cyan",  transform=infoAx.transAxes, fontsize=9)
        self.timestepText = infoAx.text(0.05, 0.75, "Timestep: 0",   color="white", transform=infoAx.transAxes, fontsize=9)
        self.targetText   = infoAx.text(0.05, 0.60, "Target: None",  color="white", transform=infoAx.transAxes, fontsize=9)
        infoAx.text(0.05, 0.40, "Click lattice to inject\nobstacle / set target",
                    color="grey", transform=infoAx.transAxes, fontsize=8)

        # ── buttons ──────────────────────────────────────────────────────
        btnColor = "#2a2a4a"
        btnHover = "#3a3a6a"

        axMode   = self.fig.add_axes([0.72, 0.42, 0.26, 0.06])
        axWave   = self.fig.add_axes([0.72, 0.34, 0.26, 0.06])
        axPath   = self.fig.add_axes([0.72, 0.26, 0.26, 0.06])
        axPause  = self.fig.add_axes([0.72, 0.18, 0.26, 0.06])
        axReset  = self.fig.add_axes([0.72, 0.10, 0.26, 0.06])
        axRunEnd = self.fig.add_axes([0.72, 0.02, 0.26, 0.06])

        self.btnMode   = Button(axMode,   "Mode: INJECT", color=btnColor, hovercolor=btnHover)
        self.btnWave   = Button(axWave,   "Trigger Wave", color=btnColor, hovercolor=btnHover)
        self.btnPath   = Button(axPath,   "Compute Path", color=btnColor, hovercolor=btnHover)
        self.btnPause  = Button(axPause,  "Run",          color=btnColor, hovercolor=btnHover)
        self.btnReset  = Button(axReset,  "Reset",        color=btnColor, hovercolor=btnHover)
        self.btnRunEnd = Button(axRunEnd, "Run to End",   color=btnColor, hovercolor=btnHover)

        for btn in (self.btnMode, self.btnWave, self.btnPath, self.btnPause, self.btnReset, self.btnRunEnd):
            btn.label.set_color("white")

        self.btnMode.on_clicked(self._onToggleMode)
        self.btnWave.on_clicked(self._onTriggerWave)
        self.btnPath.on_clicked(self._onComputePath)
        self.btnPause.on_clicked(self._onTogglePause)
        self.btnReset.on_clicked(self._onReset)
        self.btnRunEnd.on_clicked(self._onRunToEnd)

    # ── interaction callbacks ────────────────────────────────────────────

    def _onPick(self, event):
        if event.artist is not self.scatterIinh:
            return
        idx = event.ind[0]
        x   = self.xs[idx]
        y   = self.ys[idx]

        if self.mode == "inject":
            self.network.neurons.vars["Iinh"].pull_from_device()
            self.network.neurons.vars["Iinh"].view[idx] += float(self.network.currentClamp)
            self.network.neurons.vars["Iinh"].push_to_device()

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
            self.btnMode.label.set_text("Mode: TARGET")
        else:
            self.mode = "inject"
            self.modeText.set_text("Mode: INJECT")
            self.modeText.set_color("cyan")
            self.btnMode.label.set_text("Mode: INJECT")
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
            print(f"Simulation not complete — {remaining} timesteps remaining. Run to completion first.")
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

    def _onTogglePause(self, event):
        self.running = not self.running
        self.btnPause.label.set_text("Pause" if self.running else "Run")
        self.fig.canvas.draw_idle()

    def _onReset(self, event):
        self._waveDone = False
        self.network.resetWaveProp()
        self.timestep = 0
        self.running  = False
        self.targetX  = None
        self.targetY  = None
        self.btnPause.label.set_text("Run")
        self.targetText.set_text("Target: None")
        self.timestepText.set_text("Timestep: 0")
        self.scatterTarget.set_offsets(numpy.empty((0, 2)))
        self.pathLine.set_data([], [])
        self.fig.canvas.draw_idle()

    def _onRunToEnd(self, event):
        self.running  = False
        remaining     = self.network.duration - self.network.model.timestep
        for _ in range(remaining):
            self.network.step()
            self.timestep += 1
        self.timestepText.set_text(f"Timestep: {self.timestep}")
        print("Simulation complete — ready to compute path")
        self.fig.canvas.draw_idle()

    # ── animation loop ───────────────────────────────────────────────────

    def _update(self, frame):
        if not self.running:
            return (self.scatterIinh, self.scatterSpikes,
                    self.scatterTarget, self.pathLine)

        for _ in range(UPDATE_INTERVAL_MS):
            self.network.step()
            self.timestep += 1

        # pull state from GPU
        self.network.neurons.vars["V"].pull_from_device()
        self.network.neurons.vars["Iinh"].pull_from_device()

        vValues = numpy.array(self.network.neurons.vars["V"].view)
        iinhValues = numpy.array(self.network.neurons.vars["Iinh"].view)

        # update Iinh heatmap
        self.scatterIinh.set_array(iinhValues)

        # update spiking neuron overlay
        activeIndices = numpy.where(vValues >= self.network.lifParameters["Vthresh"])[0]
        if len(activeIndices) > 0:
            self.scatterSpikes.set_offsets(
                numpy.column_stack([self.xs[activeIndices], self.ys[activeIndices]])
            )
            self._waveDone = False
        else:
            self.scatterSpikes.set_offsets(numpy.empty((0, 2)))
            if not self._waveDone:
                print(f"Wave finished at timestep {self.timestep}")
                self._waveDone = True

        self.timestepText.set_text(f"Timestep: {self.timestep}")

        return (self.scatterIinh, self.scatterSpikes,
                self.scatterTarget, self.pathLine)

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
    network = WPSNN()
    print(f"Lattice size:  {len(network.lattice)}")
    print(f"Connections:   {len(network.connList)}")
    print(f"Origin index:  {network.indexTable[(0.0, 0.0)]}")
    visualiser = WPSNNVisualiser(network)
    visualiser.run()