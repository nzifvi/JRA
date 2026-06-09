import numpy
import pygenn
import itertools

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

    def __init__(self, radius = 1, neuronSpacing = 0.1,  currentDecayConstant = 100, currentClamp = 300, duration = 500):
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
        self.currentDecayConstant = currentDecayConstant
        self.currentClamp         = currentClamp
        self.duration             = duration

        self.model    = pygenn.GeNNModel("float", "WPSNN")
        self.model.dt = 1.0

        self.path                       = None
        self.lattice                    = self._initLattice()
        self.coordsCache                = numpy.array(self.lattice)
        self.indexTable                 = self._initIndexTable()
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
            len(self.lattice),
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
        self.synapses.max_dendritic_delay_timesteps = 2


        self.stim = self.model.add_neuron_population(
            "Stim",
            len(self.lattice),
            "SpikeSourceArray",
            {},
            {
                "startSpike" : numpy.zeros(len(self.lattice), dtype = numpy.uint32),
                "endSpike"   : numpy.zeros(len(self.lattice), dtype = numpy.uint32)
            }
        )
        self.stim.extra_global_params["spikeTimes"].set_init_values(
            numpy.full(
                len(self.lattice),
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
            list(range(len(self.lattice))),
            list(range(len(self.lattice))),
        )

        self.model.build()
        self.model.load(num_recording_timesteps=self.duration)


    def _initLattice(self):
        lattice = []
        i = int(self.radius / self.neuronSpacing)
        for x in range(-i, i + 1):
            for y in range(-i, i + 1):
                xOrdinate = round(x * self.neuronSpacing, 10)
                yOrdinate = round(y * self.neuronSpacing, 10)

                if xOrdinate**2 + yOrdinate**2 <= self.radius**2:
                    lattice.append(
                        (xOrdinate, yOrdinate)
                    )
        return lattice

    def _initIndexTable(self):
        return {coordinate:index for index, coordinate in enumerate(self.lattice)}

    def _buildConnections(self, weight=300.0, nonDiagonalDelay=1.0):
        diagonalDelay = round(
            numpy.sqrt(2), 10
        )

        connList = []
        for i, (x, y) in enumerate(self.lattice):
            for dx, dy in itertools.product([-self.neuronSpacing, 0.0, self.neuronSpacing], repeat = 2):
                if dx == 0.0 and dy == 0.0:
                    continue
                neighbour = (
                    round(x + dx, 10),
                    round(y + dy, 10)
                )
                if neighbour in self.indexTable:
                    if dx != 0.0 and dy != 0.0:
                        delay = diagonalDelay
                    else:
                        delay = nonDiagonalDelay
                    connList.append(
                        (i, self.indexTable[neighbour], weight, delay)
                    )

        return connList

    def _initNeighbourTable(self):
        neighbourTable = {}
        for pre, post, _, _ in self.connList:
            if pre not in neighbourTable:
                neighbourTable[pre] = []
            neighbourTable[pre].append(post)
        return neighbourTable

    def _bin(self, x, y):
        xBinned = round(
            round(x / self.neuronSpacing) * self.neuronSpacing, 10
        )
        yBinned = round(
            round(y / self.neuronSpacing) * self.neuronSpacing, 10
        )
        return xBinned, yBinned

    def inject(self, x, y):
        xBinned, yBinned = self._bin(x, y)
        neuronKey = (xBinned, yBinned)
        if neuronKey not in self.indexTable:
            raise ValueError(
                f"No neuron at binned coordinate (x={xBinned}, y={yBinned})"
            )
        i = self.indexTable[neuronKey]

        self.neurons.vars["Iinh"].pull_from_device()
        self.neurons.vars["Iinh"].view[i] += float(self.currentClamp)
        self.neurons.vars["Iinh"].push_to_device()

    def injectGaussian(self, x, y, sigma:float = None):
        if sigma is None:
            sigma = self.neuronSpacing * 0.5

        distances = (
        (self.coordsCache[:, 0] - x) ** 2 + (self.coordsCache[:, 1] - y) ** 2
        )

        kernel = self.currentClamp * numpy.exp(
            -distances / (2.0 * sigma ** 2)
        )
        mask = distances < (3.0 * sigma) ** 2

        self.neurons.vars["Iinh"].pull_from_device()
        self.neurons.vars["Iinh"].view[mask] += kernel[mask]
        self.neurons.vars["Iinh"].push_to_device()

    def step(self):
        self.model.step_time()

    def propagateWave(self): # EGOCENTRIC IMPLEMENTATION (always initiates from origin)
        i = self.indexTable[(0.0, 0.0)]

        self.stim.extra_global_params["spikeTimes"].pull_from_device()
        self.stim.extra_global_params["spikeTimes"].view[i] = self.model.t + 2.0
        self.stim.extra_global_params["spikeTimes"].push_to_device()

        self.stim.vars["startSpike"].pull_from_device()
        self.stim.vars["endSpike"].pull_from_device()
        self.stim.vars["startSpike"].view[i] = i
        self.stim.vars["endSpike"].view[i] = i + 1
        self.stim.vars["startSpike"].push_to_device()
        self.stim.vars["endSpike"].push_to_device()

    def backpropagateWave(self, targetX, targetY):
        self.model.pull_recording_buffers_from_device()
        times, indices = self.neurons.spike_recording_data[0]

        firstSpike = {}
        for t, i in zip(times, indices):
            i = int(i)
            if i not in firstSpike or t < firstSpike[i]:
                firstSpike[i] = t

        xBinned, yBinned = self._bin(targetX, targetY)
        key = (xBinned, yBinned)
        if key not in self.indexTable:
            raise ValueError(f"No neuron at binned coordinate (x={xBinned}, y={yBinned})")
        targetIndex = self.indexTable[key]

        if targetIndex not in firstSpike:
            raise RuntimeError(
                f"Wavefront did not reach target neuron at (x={xBinned}, y={yBinned})"
            )

        self.path = []
        currentIndex = targetIndex
        originIndex = self.indexTable[(0.0, 0.0)]
        maxTime = firstSpike[targetIndex]

        while currentIndex != originIndex:
            self.path.append(currentIndex)

            neighbours = self.neighbourTable.get(currentIndex, [])
            best, bestTime = None, maxTime
            for neighbour in neighbours:
                if neighbour in firstSpike and firstSpike[neighbour] < bestTime:
                    bestTime = firstSpike[neighbour]
                    best = neighbour

            if best is None:
                break

            maxTime = bestTime
            currentIndex = best

        self.path.append(originIndex)
        print(f"Neurons that fired: {len(firstSpike)}")
        print(f"Target index: {targetIndex}, first spike time: {firstSpike.get(targetIndex, 'never')}")
        print(f"Origin index: {originIndex}, first spike time: {firstSpike.get(originIndex, 'never')}")


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
        n = len(self.lattice)
        self.stim.vars["startSpike"].view[:] = numpy.zeros(n, dtype=numpy.uint32)
        self.stim.vars["endSpike"].view[:] = numpy.zeros(n, dtype=numpy.uint32)
        self.stim.vars["startSpike"].push_to_device()
        self.stim.vars["endSpike"].push_to_device()

        self.stim.extra_global_params["spikeTimes"].view[:] = numpy.full(n, numpy.finfo(numpy.float32).max,
                                                                         dtype=numpy.float32)
        self.stim.extra_global_params["spikeTimes"].push_to_device()

        self.model.timestep = 0
        self.path = None
