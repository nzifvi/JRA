import numpy
import pygenn

class WPSNN:
    # model parameters are static. they cannot be modified during runtime as they are basically constant variables in GPU memory.
    # - work-around: create a custom model which copies LIF and adds a Iinh dynamic variable to apply currents to
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

    def __init__(self, radius = 1, neuronSpacing = 0.1, thetaBinWidth = 0.01, phiBinWidth = 0.01, currentDecayConstant = 1000, currentClamp = 300, duration = 500):
        # CONSTRUCTOR PARAMETERS' UNITS:
        # - radius               : metres
        # - neuronSpacing        : metres  (radial bin width)
        # - thetaBinWidth        : radians (azimuth bin width)
        # - phiBinWidth          : radians (elevation bin width)
        # - currentDecayConstant : ms
        # - currentClamp         : nA
        # - duration             : ms
        self.radius               = radius
        self.neuronSpacing        = neuronSpacing
        self.thetaBinWidth        = thetaBinWidth
        self.phiBinWidth          = phiBinWidth
        self.currentDecayConstant = currentDecayConstant
        self.currentClamp         = currentClamp
        self.duration             = duration

        self.model    = pygenn.GeNNModel("float", "WPSNN")
        self.model.dt = 1.0

        self.sphericalCoordinateLattice = self._initSphericalCoordinateLattice()
        self.indexTable                 = self._initIndexTable()
        self.ringTable                  = self._initRingTable()
        self.connList                   = self._buildConnections()
        self.neighbourTable             = self._initNeighbourTable()
        self.lifParameters = {
            "C"         : 1.0,
            "TauM"      : 20.0,
            "Vrest"     : -65.0,
            "Vreset"    : -65.0,
            "Vthresh"   : -50.0,
            "TauRefrac" : 50.0,
            "TauInh"    : float(self.currentDecayConstant),
            "Ioffset": 0.0
        }
        self.lifInit = {
            "V"          : -65.0,
            "RefracTime" : 0.0,
            "Iinh"       : 0.0
        }
        self.neurons = self.model.add_neuron_population(
            "Neurons",
            len(self.sphericalCoordinateLattice),
            WPSNN._NEURON,
            self.lifParameters,
            self.lifInit
        )
        """
        self.neurons = self.model.add_neuron_population(
            "Neurons",
            len(self.sphericalCoordinateLattice),
            "LIF",
            params = self.lifParameters,
            vars = self.lifInit,
        )
        """
        self.neurons.spike_recording_enabled = True

        preIndices, postIndices, weights, delays = zip(*self.connList)

        self.synapses = self.model.add_synapse_population(
            "Synapses",
            "SPARSE",
            self.neurons,
            self.neurons,
            pygenn.init_weight_update(
                "StaticPulseDendriticDelay",
                {},
                {
                    "g": list(weights),
                    "d": list(delays)}
            ),
            pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        self.synapses.set_sparse_connections(list(preIndices), list(postIndices))
        self.synapses.max_dendritic_delay_timesteps = 8


        self.stim = self.model.add_neuron_population(
            "Stim", 1,
            "SpikeSourceArray", {},
            {"startSpike": 0, "endSpike": 1}
        )
        self.stim.extra_global_params["spikeTimes"].set_init_values([2.0])
        self.stimSynapses = self.model.add_synapse_population(
            "StimSynapses",
            "SPARSE",
            self.stim,
            self.neurons,
            pygenn.init_weight_update(
                "StaticPulseConstantWeight",
                {
                    "g": 300.0
                }
            ),
            pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau" : 5.0}
            )
        )
        self.stimSynapses.set_sparse_connections([0], [0])

        self.model.build()
        self.model.load(num_recording_timesteps=self.duration)


    def _initSphericalCoordinateLattice(self):
        lattice = [(0.0, 0.0)]
        r = self.neuronSpacing
        while r <= self.radius + 1e-9:
            r         = round(r, 10)
            noNeurons = int(2 * numpy.pi * r / self.neuronSpacing)
            thetaStep = (2 * numpy.pi) / noNeurons
            for i in range(noNeurons):
                lattice.append((r, round(i * thetaStep, 10)))
            r += self.neuronSpacing
        return lattice

    def _initIndexTable(self):
        return {coord: idx for idx, coord in enumerate(self.sphericalCoordinateLattice)}

    def _initRingTable(self):
        ringTable = {}
        for idx, (r, theta) in enumerate(self.sphericalCoordinateLattice):
            if r not in ringTable:
                ringTable[r] = []
            ringTable[r].append((theta, idx))
        return ringTable

    def _initNeighbourTable(self):
        neighbourTable = {}
        for pre, post, _, _ in self.connList:
            if pre not in neighbourTable:
                neighbourTable[pre] = []
            neighbourTable[pre].append(post)
        return neighbourTable

    def _buildConnections(self, weight=300.0, delay=1.0):
        rings       = []
        currentR    = None
        currentRing = []
        for idx, (r, theta) in enumerate(self.sphericalCoordinateLattice):
            if r != currentR:
                if currentRing:
                    rings.append(currentRing)
                currentR    = r
                currentRing = []
            currentRing.append(idx)
        if currentRing:
            rings.append(currentRing)

        connList = []
        for i, ring in enumerate(rings):

            if i == 0:
                for j in rings[1]:
                    connList.append((ring[0], j,       weight, delay))
                    connList.append((j,       ring[0], weight, delay))
                continue

            for j, k in enumerate(ring):
                prevIdx = ring[(j - 1) % len(ring)]
                nextIdx = ring[(j + 1) % len(ring)]
                connList.append((k, prevIdx, weight, delay))
                connList.append((k, nextIdx, weight, delay))

                innerRing = rings[i - 1]
                connList.append((k, innerRing[j % len(innerRing)], weight, delay))

                if i < len(rings) - 1:
                    outerRing = rings[i + 1]
                    connList.append((k, outerRing[j % len(outerRing)], weight, delay))

        return connList

    def _bin(self, r, theta, phi=None):
        rBinned     = round(round(r     / self.neuronSpacing) * self.neuronSpacing, 10)
        thetaBinned = round(round(theta / self.thetaBinWidth) * self.thetaBinWidth, 10)
        thetaBinned = round(thetaBinned % (2 * numpy.pi), 10)

        if phi is None:
            return rBinned, thetaBinned, None

        phiBinned = round(round(phi / self.phiBinWidth) * self.phiBinWidth, 10)
        phiBinned = round(phiBinned % (2 * numpy.pi), 10)
        return rBinned, thetaBinned, phiBinned

    def inject(self, r, theta, phi=None):
        pass

    def step(self):
        self.model.step_time()

    def propagateWave(self):
        currentTime = self.model.t
        self.stim.extra_global_params["spikeTimes"].view[0] = currentTime + 2.0
        self.stim.extra_global_params["spikeTimes"].push_to_device()
        self.stim.vars["startSpike"].view[0] = 0
        self.stim.vars["endSpike"].view[0] = 1
        self.stim.vars["startSpike"].push_to_device()
        self.stim.vars["endSpike"].push_to_device()

    def backpropagateWave(self, targetR, targetTheta, targetPhi=None):
        pass

    def reset(self):
        pass