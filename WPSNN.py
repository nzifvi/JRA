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

        self.path                       = None
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
            "Stim",
            len(self.sphericalCoordinateLattice),
            "SpikeSourceArray",
            {},
            {
                "startSpike" : numpy.zeros(len(self.sphericalCoordinateLattice), dtype = numpy.uint32),
                "endSpike"   : numpy.zeros(len(self.sphericalCoordinateLattice), dtype = numpy.uint32)
            }
        )
        self.stim.extra_global_params["spikeTimes"].set_init_values(
            numpy.full(
                len(self.sphericalCoordinateLattice),
                numpy.finfo(numpy.float32).max,
                dtype = numpy.float32
            )
        )
        self.stimSynapses = self.model.add_synapse_population(
            "StimSynapses",
            "SPARSE",
            self.stim,
            self.neurons,
            pygenn.init_weight_update(
                "StaticPulseConstantWeight",
                {"g" : float(self.currentClamp)}
            ),
            pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau" : 5.0}
            )
        )
        self.stimSynapses.set_sparse_connections(
            list(range(len(self.sphericalCoordinateLattice))),
            list(range(len(self.sphericalCoordinateLattice))),
        )

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
        rBinned, thetaBinned, _ = self._bin(r, theta, phi)
        if (rBinned, thetaBinned) not in self.indexTable:
            raise ValueError(
                f"Access attempt for non-existent neuron at binned coordinate (r={rBinned}, theta={thetaBinned})"
            )

        i = self.indexTable[(rBinned, thetaBinned)]

        self.stim.extra_global_params["spikeTimes"].pull_from_device()
        self.stim.extra_global_params["spikeTimes"].view[i] = self.model.t + 2.0
        self.stim.extra_global_params["spikeTimes"].push_to_device()

        self.stim.vars["startSpike"].pull_from_device()
        self.stim.vars["endSpike"].pull_from_device()
        self.stim.vars["startSpike"].view[i] = i
        self.stim.vars["endSpike"].view[i] = i + 1
        self.stim.vars["startSpike"].push_to_device()
        self.stim.vars["endSpike"].push_to_device()

    def step(self):
        self.model.step_time()

    def propagateWave(self): # EGOCENTRIC IMPLEMENTATION (always initiates from origin)
        self.inject(0.0, 0.0)

    def backpropagateWave(self, targetR, targetTheta, targetPhi=None):
        self.model.pull_recording_buffers_from_device()
        times, indices = self.neurons.spike_recording_data[0]

        firstSpike = {}
        for t, i in zip(times, indices):
            i = int(i)
            if i not in firstSpike or t < firstSpike[i]:
                firstSpike[i] = t

        rBinned, thetaBinned, _ = self._bin(targetR, targetTheta, targetPhi)
        targetNeuronKey = (rBinned, thetaBinned)
        targetIndex = self.indexTable[targetNeuronKey]

        if targetIndex not in firstSpike:
            raise RuntimeError(
                f"Wavefront did not reach target neuron at binned coordinate (r={rBinned}, theta = {thetaBinned})"
            )

        self.path = []
        currentIndex = targetIndex
        originIndex = self.indexTable[(0.0, 0.0)]
        maxTime = self.duration

        while currentIndex != originIndex:
            self.path.append(currentIndex)

            neighbours = self.neighbourTable.get(currentIndex, [])
            best, bestTime = None, maxTime
            for neighbour in neighbours:
                if neighbour in firstSpike and firstSpike[neighbour] < bestTime:
                    bestTime = firstSpike[neighbour]
                    best     = neighbour

            if best is None:
                break

            maxTime      = bestTime
            currentIndex = best

        self.path.append(originIndex)

    def calculatePath(self):
        if self.path is None:
            raise RuntimeError(
                "Path has not been calculated via a call to WPSNN.backpropagateWave() function member"
            )

        return list(
            reversed(
                self.path
            )
        )

    def resetWaveProp(self):
        n = len(self.sphericalCoordinateLattice)
        self.stim.vars["startSpike"].view[:] = numpy.zeros(n, dtype=numpy.uint32)
        self.stim.vars["endSpike"].view[:] = numpy.zeros(n, dtype=numpy.uint32)
        self.stim.vars["startSpike"].push_to_device()
        self.stim.vars["endSpike"].push_to_device()

        self.stim.extra_global_params["spikeTimes"].view[:] = numpy.full(n, numpy.finfo(numpy.float32).max,
                                                                         dtype=numpy.float32)
        self.stim.extra_global_params["spikeTimes"].push_to_device()

        self.model.timestep = 0
        self.path = None