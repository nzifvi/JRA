import numpy
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from SpatialMap import TrigSpatialMap

LATCH_MS      = 60
ERASE_START   = 400
RELATCH_START = 1200
TOTAL         = 1800

INJECT_ON  = 30.0
INJECT_OFF = -30.0
TAU_INH    = 100.0

smap = TrigSpatialMap(xSize=0.5, ySize=0.5, neuronSpacing=0.1, duration=TOTAL)
smap._memoryMapPop.spike_recording_enabled = True   # must be set pre-build

cells = {
    "A (static)"  : smap._indexTable[( 0.0,  0.0)],
    "B (dynamic)" : smap._indexTable[( 0.1,  0.0)],   # adjacent to A
}
idxA, idxB = cells["A (static)"], cells["B (dynamic)"]

mag     = smap._injectionSource.vars["mag"]
mapIinh = smap._spatialMapPop.vars["Iinh"]

def setMag(**assignments):
    mag.view[:] = 0.0
    for index, value in assignments.items():
        mag.view[int(index)] = value
    mag.push_to_device()

times = []
traces = {name: [] for name in cells}

for step in range(TOTAL):
    if step == 0:
        setMag(**{str(idxA): INJECT_ON, str(idxB): INJECT_ON})
    elif step == LATCH_MS:
        setMag()                                    # all zero: hold phase
    elif step == ERASE_START:
        setMag(**{str(idxB): INJECT_OFF})           # B only
    elif step == RELATCH_START:
        setMag(**{str(idxB): INJECT_ON})            # B re-observed

    smap.step()
    mapIinh.pull_from_device()
    times.append(smap.model.t)
    for name, index in cells.items():
        traces[name].append(float(mapIinh.view[index]))

smap.model.pull_recording_buffers_from_device()
spikeTimes, spikeIds = smap._memoryMapPop.spike_recording_data[0]

times  = numpy.array(times)
traces = {name: numpy.array(values) for name, values in traces.items()}

def peakIn(trace, lo, hi):
    window = (times >= lo) & (times < hi)
    return trace[window].max() if window.any() else float("nan")

aPre    = peakIn(traces["A (static)"], ERASE_START - 200, ERASE_START)
aDuring = peakIn(traces["A (static)"], ERASE_START + 100, RELATCH_START)
bPre    = peakIn(traces["B (dynamic)"], ERASE_START - 200, ERASE_START)
bPost   = peakIn(traces["B (dynamic)"], TOTAL - 200, TOTAL)

bSpikes = numpy.sort(spikeTimes[spikeIds == idxB])
released = bSpikes[bSpikes > ERASE_START]
lastB    = released[-1] if len(released) else ERASE_START

eraseWindow = (times > ERASE_START) & (times < RELATCH_START)
below1pct   = times[eraseWindow][traces["B (dynamic)"][eraseWindow] < 0.01 * bPre]
fadeTime    = below1pct[0] - ERASE_START if len(below1pct) else float("nan")

print(f"A peak before erase   : {aPre:7.1f}")
print(f"A peak during erase   : {aDuring:7.1f}   perturbation {100*(aDuring-aPre)/aPre:+.2f} %")
print(f"B peak before erase   : {bPre:7.1f}")
print(f"B peak after re-latch : {bPost:7.1f}   recovery {100*bPost/bPre:.1f} %")
print(f"B last spike post-erase: {lastB - ERASE_START:5.0f} ms")
print(f"B fade to 1%          : {fadeTime:5.0f} ms   (5*TauInh = {5*TAU_INH:.0f})")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True,
                               gridspec_kw={"height_ratios": [2, 1], "hspace": 0.1})

colours = {"A (static)": "#1f77b4", "B (dynamic)": "#d62728"}
for name, trace in traces.items():
    ax1.plot(times, trace, lw=1.3, color=colours[name], label=name, zorder=3)
ax1.set_ylabel(r"SpatialMap $I_{inh}$  (nA)")
ax1.legend(loc="upper left", framealpha=0.95)

for row, (name, index) in enumerate(cells.items()):
    cellSpikes = spikeTimes[spikeIds == index]
    ax2.plot(cellSpikes, numpy.full(len(cellSpikes), row), "|",
             ms=7, mew=1.2, color=colours[name])
ax2.set_yticks(range(len(cells)))
ax2.set_yticklabels(list(cells))
ax2.set_ylim(-0.5, len(cells) - 0.5)
ax2.set_ylabel("MemoryMap spikes")
ax2.set_xlabel("time (ms)")

for ax in (ax1, ax2):
    ax.axvspan(0, LATCH_MS, color="#2ca02c", alpha=0.10, zorder=0)
    ax.axvspan(ERASE_START, RELATCH_START, color="#d62728", alpha=0.10, zorder=0)
    ax.axvspan(RELATCH_START, TOTAL, color="#2ca02c", alpha=0.10, zorder=0)
    ax.grid(alpha=0.25, lw=0.6)
    ax.set_xlim(0, TOTAL)

plt.tight_layout()
plt.savefig("selective_suppression.png", dpi=300, bbox_inches="tight")
plt.show()