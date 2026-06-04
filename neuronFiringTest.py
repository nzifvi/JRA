import pygenn
import numpy
import matplotlib.pyplot as plt

def plotRefactoryTimes(customRefractoryPeriods, pygennRefractoryPeriods) -> None:
    customLIFRefrac0, customLIFRefrac1 = customRefractoryPeriods
    pygennLIFRefrac0, pygennLIFRefrac1 = pygennRefractoryPeriods

    t_axis = list(range(STEPS))
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("Custom LIF (top) vs Pygenn LIF (bottom)")

    axes[0][0].set_title("Custom LIF Neuron 0 (pre)")
    axes[0][0].axhline(-50.0, color="red", linestyle="--", label="Vthresh")
    axes[0][0].axhline(-65.0, color="gray", linestyle="--", label="Vrest")
    axes[0][0].plot(t_axis, customLIFRefrac0, label="RefracTime", color="orange")
    axes[0][0].set_xlabel("timestep")
    axes[0][0].legend()

    axes[0][1].set_title("Custom LIF Neuron 1 (post)")
    axes[0][1].axhline(-50.0, color="red", linestyle="--", label="Vthresh")
    axes[0][1].axhline(-65.0, color="gray", linestyle="--", label="Vrest")
    axes[0][1].plot(t_axis, customLIFRefrac1, label="RefracTime", color="orange")
    axes[0][1].set_xlabel("timestep")
    axes[0][1].legend()

    axes[1][0].set_title("Pygenn LIF Neuron 0 (pre)")
    axes[1][0].axhline(-50.0, color="red", linestyle="--", label="Vthresh")
    axes[1][0].axhline(-65.0, color="gray", linestyle="--", label="Vrest")
    axes[1][0].plot(t_axis, pygennLIFRefrac0, label="RefracTime", color="orange")
    axes[1][0].set_xlabel("timestep")
    axes[1][0].legend()

    axes[1][1].set_title("Pygenn LIF Neuron 1 (post)")
    axes[1][1].axhline(-50.0, color="red", linestyle="--", label="Vthresh")
    axes[1][1].axhline(-65.0, color="gray", linestyle="--", label="Vrest")
    axes[1][1].plot(t_axis, pygennLIFRefrac1, label="RefracTime", color="orange")
    axes[1][1].set_xlabel("timestep")
    axes[1][1].legend()

    plt.tight_layout()
    plt.show()

_NEURON = pygenn.create_neuron_model(
        "LifWithInhibition",
        params = ["C", "TauM", "Vrest", "Vreset", "Vthresh", "TauRefrac", "TauInh", "Ioffset"],
        vars   = [("V", "scalar"), ("RefracTime", "scalar"), ("Iinh", "scalar")],
        sim_code = """
            if (RefracTime > 0.0) {
                RefracTime -= dt;
            } else {
                scalar dV = (-(V - Vrest) + Isyn + Ioffset - Iinh) / TauM;
                V += dV * dt;
                Iinh -= (Iinh / TauInh) * dt;
            }
            """,
        threshold_condition_code = "RefracTime <= 0.0 && V >= Vthresh",
        reset_code = """
            V = Vreset;
            RefracTime = TauRefrac;
        """
    )

PARAMS = {
    "C": 1.0, "TauM": 20.0, "Vrest": -65.0, "Vreset": -65.0,
    "Vthresh": -50.0, "TauRefrac": 50.0, "TauInh": 1000.0, "Ioffset": 0.0
}
INIT = {"V": -65.0, "RefracTime": 0.0, "Iinh": 0.0}
STEPS = 20

m1    = pygenn.GeNNModel("float", "test_custom")
m1.dt = 1.0
n1    = m1.add_neuron_population("Neurons", 2, _NEURON, PARAMS, INIT)
s1    = m1.add_synapse_population(
    "Synapses", "SPARSE", n1, n1,
    pygenn.init_weight_update("StaticPulseConstantWeight", {"g": 300.0}),
    pygenn.init_postsynaptic("ExpCurr", {"tau": 5.0})
)
s1.set_sparse_connections([0], [1])
m1.build()
m1.load()

n1.vars["V"].pull_from_device()
n1.vars["V"].view[0] = -49.0
n1.vars["V"].push_to_device()

customLIFV0      = []
customLIFV1      = []
customLIFRefrac0 = []
customLIFRefrac1 = []

for t in range(STEPS):
    m1.step_time()
    n1.vars["V"].pull_from_device()
    n1.vars["RefracTime"].pull_from_device()
    customLIFV0.append(float(n1.vars["V"].view[0]))
    customLIFV1.append(float(n1.vars["V"].view[1]))
    customLIFRefrac0.append(float(n1.vars["RefracTime"].view[0]))
    customLIFRefrac1.append(float(n1.vars["RefracTime"].view[1]))

m2    = pygenn.GeNNModel("float", "test_lif")
m2.dt = 1.0
n2    = m2.add_neuron_population("Neurons", 2, "LIF",
    {"C": 1.0, "TauM": 20.0, "Vrest": -65.0, "Vreset": -65.0,
     "Vthresh": -50.0, "TauRefrac": 50.0, "Ioffset": 0.0},
    {"V": -65.0, "RefracTime": 0.0}
)
s2    = m2.add_synapse_population(
    "Synapses", "SPARSE", n2, n2,
    pygenn.init_weight_update("StaticPulseConstantWeight", {"g": 300.0}),
    pygenn.init_postsynaptic("ExpCurr", {"tau": 5.0})
)
s2.set_sparse_connections([0], [1])
m2.build()
m2.load()

n2.vars["V"].pull_from_device()
n2.vars["V"].view[0] = -49.0
n2.vars["V"].push_to_device()

pygennLIFV0      = []
pygennLIFV1      = []
pygennLIFRefrac0 = []
pygennLIFRefrac1 = []

for t in range(STEPS):
    m2.step_time()
    n2.vars["V"].pull_from_device()
    n2.vars["RefracTime"].pull_from_device()
    pygennLIFV0.append(float(n2.vars["V"].view[0]))
    pygennLIFV1.append(float(n2.vars["V"].view[1]))
    pygennLIFRefrac0.append(float(n2.vars["RefracTime"].view[0]))
    pygennLIFRefrac1.append(float(n2.vars["RefracTime"].view[1]))

plotRefactoryTimes(
    (customLIFRefrac0, customLIFRefrac1),
    (pygennLIFRefrac0, pygennLIFRefrac1)
)

lif = pygenn.neuron_models.LIF()
print("=== sim_code ===")
print(lif.get_sim_code())
print("=== threshold_condition_code ===")
print(lif.get_threshold_condition_code())
print("=== reset_code ===")
print(lif.get_reset_code())