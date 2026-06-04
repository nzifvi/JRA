from WPSNN import WPSNN
import numpy
import matplotlib.pyplot as plt

network = WPSNN()



print("WPSNN Model Params: ")
print(f"lifParameters: {network.lifParameters}")
print(f"Lateral weight: {network.connList[0][2]}")
print(f"Lateral delay:  {network.connList[0][3]}")
print(f"Stim weight:    300.0 (StaticPulseConstantWeight, compiled)")
print(f"ExpCurr tau:    5.0")
print(f"model.dt:       {network.model.dt}")

firstSpikeTime = numpy.full(len(network.sphericalCoordinateLattice), numpy.inf)
refracCounts   = []
cumulativeFired = []

STEPS = 50
for t in range(STEPS):
    network.step()
    network.neurons.vars["RefracTime"].pull_from_device()
    refracTimes = numpy.array(network.neurons.vars["RefracTime"].view)

    justFired = numpy.where(refracTimes > 0.0)[0]
    for i in justFired:
        if firstSpikeTime[i] == numpy.inf:
            firstSpikeTime[i] = t

    refracCounts.append(int(numpy.sum(refracTimes > 0.0)))
    cumulativeFired.append(int(numpy.sum(firstSpikeTime != numpy.inf)))

rings = sorted(network.ringTable.keys())
ringFirstSpike = []
for r in rings:
    indices = [i for (theta, i) in network.ringTable[r]]
    times   = [firstSpikeTime[i] for i in indices]
    ringFirstSpike.append((r, min(times)))

t_axis = list(range(STEPS))

fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].set_title("Neurons in refractory period")
axes[0].plot(t_axis, refracCounts)
axes[0].set_xlabel("timestep")
axes[0].set_ylabel("count")

axes[1].set_title("Cumulative neurons fired")
axes[1].plot(t_axis, cumulativeFired)
axes[1].axhline(
    len(network.sphericalCoordinateLattice),
    color="red",
    linestyle="--",
    label="total neurons"
)
axes[1].set_xlabel("timestep")
axes[1].set_ylabel("count")
axes[1].legend()

axes[2].set_title("First spike time per ring")
axes[2].plot(
    [r for r, t in ringFirstSpike],
    [t for r, t in ringFirstSpike],
    marker="o"
)
axes[2].set_xlabel("ring radius (m)")
axes[2].set_ylabel("first spike timestep")

plt.tight_layout()
plt.show()