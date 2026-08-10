import numpy
import pygenn
import itertools
import threading

DISTANCE_BINS = 24
EGOCENTRIC_BEARING_BINS = 72
ALLOCENTRIC_BEARING_BINS = 72
HDC_COUNT = 72

LIDAR_RANGE = 1.0
CURRENT_CLAMP = 300.0
DURATION = 500

CACHE_PATH = r"WPSNNCache"


class TrigSpatialMap:
    DEBUG = False

    # SpatialMap neuron which represents a point in space in the SpatialMap neuron population.
    # - Inhibitory current (IInh) represents the presence of an object at the (x, y) position the neuron corresponds to.
    #    - low IInh = no object, high Iinh = object present.
    #    - Supplied via IinhIn synaptic channel between a SpatialMap neuron's corresponding MemoryMap neuron
    # - Inhibitory current decay (TauInh) achieves temporal dynamic behaviour by decaying the accumulated inhibitory current.
    #    - To implement persistence, a SpatialMap's corresponding MemoryMap neuron delivers an amount of inhibitory current to
    #      replenish the decayed inhibitory current. This occurs at a constant periodicity.
    # - The synaptic current is exclusively reserved for wavepropagation throughout the SpatialMap neuron population
    #    - Refer to comments discussing spike-source array (SSA).
    _NEURON = pygenn.create_neuron_model(
        "LifWithInhibition",
        params=["TauM", "Vrest", "Vreset", "Vthresh", "TauRefrac", "TauInh"],
        vars=[("V", "scalar"), ("RefracTime", "scalar"), ("Iinh", "scalar")],
        additional_input_vars=[("IinhIn", "scalar", 0.0)],
        sim_code="""
            Iinh += IinhIn;
            if (RefracTime > 0.0) {
                RefracTime -= dt;
            } else {
                V += ((-(V - Vrest) + Isyn - Iinh) / TauM) * dt;
            }
            Iinh -= (Iinh / TauInh) * dt;
            """,
        threshold_condition_code="RefracTime <= 0.0 && V >= Vthresh",
        reset_code="""
            V = Vreset;
            RefracTime = TauRefrac;
        """
    )

    # Bistable neuron forming MemoryMap neuron population.
    # - Synaptic current stems from lidar injections into neuron via current source model called _INJECTION. This results in any MemoryMap neuron to be driven by
    #   real-time observations
    # - LatchIn forms the recurrent autapse. The recurrent autapse can be disabled by setting latchGate = 0
    _MEMORY_NEURON = pygenn.create_neuron_model(
        "SpatialMapMemoryNeuron",
        params=["TauM", "Vrest", "Vreset", "Vthresh", "TauRefrac"],
        vars=[("V", "scalar"), ("RefracTime", "scalar"), ("latchGate", "scalar")],
        additional_input_vars=[("LatchIn", "scalar", 0.0)],
        sim_code="""
            if (RefracTime > 0.0) {
                RefracTime -= dt;
            } else {
                V += ((-(V - Vrest) + Isyn + latchGate * LatchIn) / TauM) * dt;
            }
            """,
        threshold_condition_code="RefracTime <= 0.0 && V >= Vthresh",
        reset_code="""
            V = Vreset;
            RefracTime = TauRefrac;
        """
    )

    # Current source model which acts as interface between model and lidar.
    _INJECTION = pygenn.create_current_source_model(
        "LidarInjection",
        vars=[("mag", "scalar")],
        injection_code="""
        injectCurrent(mag);
        """
    )

    # diagonal delay must be greater than orthogonal delay as per greek dude's theorem
    ORTHOGONAL_DELAY = 5
    DIAGONAL_DELAY   = 7

    _TAU_SYN  = 5.0
    _PSC_INIT = 0.90635

    AZIMUTH_SIGN   = 1.0
    AZIMUTH_OFFSET = 0.0

    # Shared so the two neuron models cannot drift apart.
    _LIF_BASE = {"TauM": 20.0, "Vrest": -65.0, "Vreset": -65.0, "Vthresh": -50.0}

    MEMORY_REFRAC  = 40.0  # sets the latch period, ~46 ms
    LATCH_WEIGHT   = 60.0
    LATCH_TAU      = 60.0  # NMDA-like; fast synapses cannot hold a stable rate
    SUPPRESSION    = 45.0
    MEMORY_TO_MAP  = 111.0
    INJECTION_GAIN = 10.0
    WEDGE_PAD      = numpy.radians(3.0)

    def __init__(self, xSize=2.5, ySize=2.5, neuronSpacing=0.1,
                 weight=50, currentClamp=300.0,
                 currentDecayConstant=100, duration=700):
        # UNITS: xSize / ySize / neuronSpacing  -> metres
        #        weight / currentClamp          -> nA
        #        currentDecayConstant, duration -> ms
        self._neuronSpacing = neuronSpacing
        self._weight        = weight
        self._currentClamp  = currentClamp
        self._duration      = duration

        self._xExtent = xSize
        self._yExtent = ySize
        self._xSize   = int(round(xSize / neuronSpacing))
        self._ySize   = int(round(ySize / neuronSpacing))
        self._nx      = 2 * self._xSize + 1
        self._ny      = 2 * self._ySize + 1
        self.extent   = (-self._xExtent, self._xExtent, -self._yExtent, self._yExtent)

        self.path         = None
        self._sourceIndex = None

        self._lattice              = self._initLattice()
        self._coordsCache          = numpy.array(self._lattice, dtype=numpy.float32)
        self._indexTable           = self._initIndexTable()
        pre, post, weights, delays = self._initSpatialMapSynapticConnections(weight)
        self._neighbourTable       = self._initNeighbourTable(pre, post)

        self._spatialMapNeuronParameters = dict(
            TrigSpatialMap._LIF_BASE,
            TauRefrac=float(duration),
            TauInh=float(currentDecayConstant)
        )
        self._lifInit = {"V": -65.0, "RefracTime": 0.0, "Iinh": 0.0}

        self._memoryMapNeuronParameters = dict(
            TrigSpatialMap._LIF_BASE,
            TauRefrac=TrigSpatialMap.MEMORY_REFRAC
        )
        self._memoryInit = {"V": -65.0, "RefracTime": 0.0, "latchGate": 1.0}

        self.model = pygenn.GeNNModel(precision="float", model_name="TrigSpatialMap")
        self.model.dt = 1.0

        n = len(self._lattice)

        self._magField = numpy.zeros(n, dtype=numpy.float32)

        # SPATIAL MAP (SM) NEURON POPULATION
        # - SM neuron population encodes the environment via inhibitory current.
        #    - High inhibitory current at a neuron = object present at (x, y) the neuron corresponds to
        #    - Low inhibitory current at a neuron = object is not present, or is unlikely to be present, at
        #      (x, y) the neuron corresponds to.
        self._spatialMapPop = self.model.add_neuron_population(
            "SpatialMap",
            n,
            TrigSpatialMap._NEURON,
            self._spatialMapNeuronParameters,
            self._lifInit
        )
        self._spatialMapPop.spike_recording_enabled = True
        self._spatialMapSynapsePop = self.model.add_synapse_population(
            "SpatialMapSynapses",
            "SPARSE",
            self._spatialMapPop,
            self._spatialMapPop,
            pygenn.init_weight_update(
                "StaticPulseDendriticDelay",
                {},
                {
                    "g": weights,
                    "d": delays
                }
            ),
            pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": TrigSpatialMap._TAU_SYN})
        )
        self._spatialMapSynapsePop.set_sparse_connections(pre, post)
        self._spatialMapSynapsePop.max_dendritic_delay_timesteps = TrigSpatialMap.DIAGONAL_DELAY + 1

        # MEMORY MAP (MM) NEURON POPULATION
        # - Each neuron in the MM neuron population is a bistable neuron with an autapse that achieves self-sustaining firing
        #   when specific conditions arise (refer to gaussianInject for more information). The bistability enables a temporally
        #   dynamic map whilst the self-sustaining firing enables persistence.
        # - Based on studies regarding persistent firing being correlated with working memory in studies on rats and primates.
        self._memoryMapPop = self.model.add_neuron_population(
            "MemoryMap",
            n,
            TrigSpatialMap._MEMORY_NEURON,
            self._memoryMapNeuronParameters,
            self._memoryInit
        )
        self._memoryMapPop.spike_recording_enabled = True
        # Lidar injection channels
        self._injectionSource = self.model.add_current_source(
            "LidarInjection",
            TrigSpatialMap._INJECTION,
            self._memoryMapPop,
            {},
            {"mag": 0.0}
        )
        # Autapse synapse population
        self._memoryMapLatchSynapsePop = self.model.add_synapse_population(
            "MemoryMapLatch", "SPARSE",
            self._memoryMapPop, self._memoryMapPop,
            pygenn.init_weight_update(
                "StaticPulseConstantWeight",
                {"g": TrigSpatialMap.LATCH_WEIGHT}
            ),
            pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": TrigSpatialMap.LATCH_TAU}
            ),
            pygenn.init_sparse_connectivity(
                "OneToOne",
                {}
            )
        )
        self._memoryMapLatchSynapsePop.axonal_delay_steps = 0
        self._memoryMapLatchSynapsePop.post_target_var = "LatchIn"
        self._memoryMapToSpatialMapSynapses = self.model.add_synapse_population(
            "MemoryToMapSynapses",
            "SPARSE",
            self._memoryMapPop,
            self._spatialMapPop,
            pygenn.init_weight_update(
                "StaticPulseConstantWeight",
                {"g": TrigSpatialMap.MEMORY_TO_MAP}
            ),
            pygenn.init_postsynaptic("DeltaCurr"),
            pygenn.init_sparse_connectivity("OneToOne", {})
        )
        # MemoryMap neuron delivers current in the form of inhibitory current via IinhIn channel as opposed
        # to synaptic channels (Isyn)
        # - SpatialMap Isyn channels are exclusively reserved for wave propagation
        # - MemoryMap neurons delivering current to SpatialMap via Isyn would interfere with wave propagation
        self._memoryMapToSpatialMapSynapses.post_target_var = "IinhIn"

        # SPIKE SOURCE ARRAY (SSA) NEURON POPULATION
        # - Used to initiate wavefront propagation from a source and target neuron.
        # - SSA neuron population has 1:1 synaptic connections, with the SM neuron population, to initiate on demand spikes and initiate
        #   chain reaction of spikes which propagate through the SM neuron population.
        self._ssa = self.model.add_neuron_population(
            "Stim", n, "SpikeSourceArray", {},
            {
                "startSpike": numpy.zeros(n, dtype=numpy.uint32),
                "endSpike": numpy.zeros(n, dtype=numpy.uint32)
            }
        )
        self._ssa.extra_global_params["spikeTimes"].set_init_values(
            numpy.full(n, numpy.finfo(numpy.float32).max, dtype=numpy.float32)
        )
        self._ssaSynapses = self.model.add_synapse_population(
            "StimSynapses", "SPARSE",
            self._ssa, self._spatialMapPop,
            pygenn.init_weight_update(
                "StaticPulseConstantWeight", {"g": float(weight)}
            ),
            pygenn.init_postsynaptic("ExpCurr", {"tau": TrigSpatialMap._TAU_SYN})
        )
        self._ssaSynapses.set_sparse_connections(list(range(n)), list(range(n)))

        self._deviceLock = threading.Lock()

        self.model.build()
        self.model.load(num_recording_timesteps=duration)

    def _initLattice(self):
        lattice = []
        for x in range(-self._xSize, self._xSize + 1):
            for y in range(-self._ySize, self._ySize + 1):
                lattice.append(
                    (
                        round(x * self._neuronSpacing, 10),
                        round(y * self._neuronSpacing, 10)
                    )
                )
        return lattice

    def _initIndexTable(self):
        return {coordinate: index for index, coordinate in enumerate(self._lattice)}

    def _initSpatialMapSynapticConnections(self, weight):
        preSynapticConnections  = []
        postSynapticConnections = []
        synapticWeights         = []
        synapticDelays          = []

        for i, (x, y) in enumerate(self._lattice):
            for dx, dy in itertools.product(
                    [-self._neuronSpacing, 0.0, self._neuronSpacing], repeat=2):
                if dx == 0.0 and dy == 0.0:
                    continue
                neighbour = (
                    round(x + dx, 10),
                    round(y + dy, 10)
                )
                if neighbour in self._indexTable:
                    if dx != 0.0 and dy != 0.0:
                        delay = float(TrigSpatialMap.DIAGONAL_DELAY)
                    else:
                        delay = float(TrigSpatialMap.ORTHOGONAL_DELAY)
                    preSynapticConnections.append(i)
                    postSynapticConnections.append(self._indexTable[neighbour])
                    synapticWeights.append(weight)
                    synapticDelays.append(delay)

        return (preSynapticConnections, postSynapticConnections,
                synapticWeights, synapticDelays)

    def _initNeighbourTable(self, pre, post):
        neighbourTable = {}
        for preIndex, postIndex in zip(pre, post):
            if preIndex not in neighbourTable:
                neighbourTable[preIndex] = []
            neighbourTable[preIndex].append(postIndex)
        return neighbourTable

    def _bin(self, xComponents, yComponents):
        xComponentsBinned = numpy.round(
            numpy.round(
                xComponents / self._neuronSpacing
            ) * self._neuronSpacing,
            10
        )
        yComponentsBinned = numpy.round(
            numpy.round(
                yComponents / self._neuronSpacing
            ) * self._neuronSpacing,
            10
        )
        return xComponentsBinned, yComponentsBinned

    def _binToIndices(self, xComponents, yComponents):
        xi = numpy.rint(numpy.asarray(xComponents) / self._neuronSpacing).astype(numpy.int64)
        yi = numpy.rint(numpy.asarray(yComponents) / self._neuronSpacing).astype(numpy.int64)
        inside = ((numpy.abs(xi) <= self._xSize) & (numpy.abs(yi) <= self._ySize))
        return (xi[inside] + self._xSize) * self._ny + (yi[inside] + self._ySize)

    def _transformCoordinates(self, distanceVec, azimuthVec, heading, robotX, robotY):

        psiVec = TrigSpatialMap.AZIMUTH_SIGN * (numpy.radians(azimuthVec) + TrigSpatialMap.AZIMUTH_OFFSET) + heading
        return numpy.stack(
            (
                distanceVec * numpy.cos(psiVec) + robotX,
                distanceVec * numpy.sin(psiVec) + robotY
            ),
            axis=1
        )

    def _packetWedge(self, distanceVec, azimuthVec, heading, robotX, robotY, radius):
        n = len(self._lattice)
        dx = self._coordsCache[:, 0] - robotX
        dy = self._coordsCache[:, 1] - robotY
        inRadius = (dx * dx + dy * dy) <= radius * radius # calculate cells within specified radius about robot

        valid = distanceVec > 0.0
        if not valid.any():
            return inRadius, numpy.zeros(n, dtype=bool)

        stride = self._neuronSpacing * 0.5 # amount to increment when searching for neurons along raycast beam
        reach = numpy.minimum(distanceVec[valid] + self._neuronSpacing, radius)
        steps = numpy.arange(numpy.ceil(reach.max() / stride) + 1) * stride
        d = numpy.clip(steps[None, :], 0.0, reach[:, None])

        world = self._transformCoordinates(
            d.ravel(),
            numpy.repeat(azimuthVec[valid], d.shape[1]),
            heading, robotX, robotY)

        inWedge = numpy.zeros(n, dtype=bool)
        inWedge[self._binToIndices(world[:, 0], world[:, 1])] = True
        return inRadius, inWedge & inRadius # return boolean mask which consists of neurons that are in radius and cells raycast beam intersected

    def gaussianInject(self, distanceVec, azimuthVec, heading, robotX, robotY, sigma=0.08, sensorRange=1.0):
        # Function performs injection by identifying 3 possible states, for all neurons in the MemoryMap neuron population, which result in different outcomes based on said state.
        # A neuron can have three possible states per injection:
        #     1) Occupied (within local neighbourhood)
        #        - State arises when a lidar return is observed at a neuron's corresponding x-and-y-ordinates. It should be noted that, due to binning, there are multiple possible x-and-y-ordinates
        #          that correspond to a given neuron.
        #        - Neuron must be within local neighbourhood
        #     2) Empty (within local neighbourhood)
        #        - State arises when no lidar return is observed at a neuron's corresponding x-and-y-ordinates.
        #        - Neuron must be within local neighbourhood.
        #     3) Outside local neighbourhood
        #        - State arises when neuron is outside the local neighbourhood. It should be noted that even if a lidar hit is observed at an x-and-y-ordinate outside it is disregarded
        #          if it is outside the local neighbourhood.

        n = len(self._lattice)
        occupancyField = numpy.zeros(n, dtype=numpy.float32)

        inRange = (distanceVec > 0.0) & (distanceVec <= sensorRange) # isolate components of distanceVec which form the positive field
        if inRange.any():
            cartesianPoints = self._transformCoordinates(
                distanceVec=distanceVec[inRange],
                azimuthVec=azimuthVec[inRange],
                heading=heading,
                robotX=robotX,
                robotY=robotY
            )

            # bin allocentric coordinates to identify the neuron they correspond to in the SpatialMap neuron pop
            binnedXComponents, binnedYComponents = self._bin(
                cartesianPoints[:, 0],
                cartesianPoints[:, 1]
            )
            binnedPoints = numpy.stack(
                (binnedXComponents, binnedYComponents),
                axis = 1
            )
            # disregard points which are out of bounds
            pointsInsideSpatialMap = (
                    (numpy.abs(binnedPoints[:, 0]) <= self._xExtent) &
                    (numpy.abs(binnedPoints[:, 1]) <= self._yExtent)
            )
            binnedPoints = binnedPoints[pointsInsideSpatialMap]

            if len(binnedPoints) > 0:
                uniqueGaussianCentres, counts = numpy.unique(
                    binnedPoints, axis=0, return_counts=True
                )

                dx = uniqueGaussianCentres[:, 0][:, None] - self._coordsCache[None, :, 0]
                dy = uniqueGaussianCentres[:, 1][:, None] - self._coordsCache[None, :, 1]
                distances = dx * dx + dy * dy

                kernel = 3 * numpy.exp(-distances / (2.0 * sigma ** 2))
                kernel[distances >= (3.0 * sigma) ** 2] = 0.0
                field = (kernel * numpy.minimum(counts, 2)[:, None]).sum(axis=0)
                occupancyField = (TrigSpatialMap.INJECTION_GAIN * field).astype(numpy.float32)

        inRadius, inWedge = self._packetWedge(
            distanceVec,
            azimuthVec,
            heading,
            robotX,
            robotY,
            sensorRange
        )

        with self._deviceLock:
            # do not inject inhibitory current into neurons outside the local temporal radius
            # - Implements possible state 3 (outside local neighbourhood)
            # - This results in neurons, outside of the local neighbourhood, having persistent memory
            self._magField[~inRadius] = 0.0

            observed = inWedge & (occupancyField > 0)

            # Apply a negative current to neurons, within the local neighbourhood, that have no lidar hit corresponding to their
            # location
            # - sets bistable latch to low (0): enabling inhibitory current decay to drain accumulated inhibitory current in MemoryMap neuron's
            #   corresponding SpatialMap neuron.
            self._magField[inWedge] = -TrigSpatialMap.SUPPRESSION

            # Apply the previously calculated current, by means of Gaussian injection, to neurons, within the local neighbourhood,
            # that have observed lidar hits.
            # - Sets bistable latch to high (1): resulting in MemoryMap achieving self-sustaining firing and replenishing decayed inhibitory current
            #   in a MemoryMap neuron's corresponding SpatialMap neuron
            self._magField[observed] = occupancyField[observed]

            mag = self._injectionSource.vars["mag"]
            mag.view[:] = self._magField
            mag.push_to_device()

            gate = self._memoryMapPop.vars["latchGate"]
            # Open gate for all MemoryMap neurons so MemoryMap neuron are primed to either cause self-sustaining firing or
            # not.
            # - Mag value is used to select the state.
            # - If a neuron receives a mag value associated with low (0), self-sustaining firing breaks down and ceases.
            # - If a neuron receives a mag value associated with high (1), the autapse enforces self-sustaining firing until
            #   a mag value associated with low (0) is received.
            gate.view[:] = 1.0
            gate.push_to_device()

    def step(self):
        self.model.step_time()

    def propagateWave(self, robotX, robotY):
        sourceXBinned, sourceYBinned = self._bin(robotX, robotY)
        sourceKey = (sourceXBinned, sourceYBinned)

        if sourceKey not in self._indexTable:
            raise ValueError(
                f"! ERROR: robot position, (x={robotX}, y={robotY}), is outside spatial map bounds"
            )

        i = self._indexTable[sourceKey]

        with self._deviceLock:
            view = self._spatialMapPop.vars["Iinh"]
            view.pull_from_device()
            # assumption: source neuron (where the robot is currently) has no objects overlapping on top of it
            view.view[i] = 0.0
            view.push_to_device()

            self._magField[i] = -TrigSpatialMap.SUPPRESSION

            self._sourceIndex = i

            self._ssa.extra_global_params["spikeTimes"].pull_from_device()
            self._ssa.extra_global_params["spikeTimes"].view[i] = self.model.t + 2.0
            self._ssa.extra_global_params["spikeTimes"].push_to_device()

            self._ssa.vars["startSpike"].pull_from_device()
            self._ssa.vars["endSpike"].pull_from_device()

            self._ssa.vars["startSpike"].view[i] = i
            self._ssa.vars["endSpike"].view[i] = i + 1

            self._ssa.vars["startSpike"].push_to_device()
            self._ssa.vars["endSpike"].push_to_device()

    def backpropagateWave(self, robotX, robotY, targetX, targetY) -> bool:
        if self._sourceIndex is None:
            self.propagateWave(robotX, robotY)

        with self._deviceLock:
            self.model.pull_recording_buffers_from_device()
            times, indices = self._spatialMapPop.spike_recording_data[0]

        firstSpike = {}
        for time, index in zip(times, indices):
            index = int(index)
            if index not in firstSpike or time < firstSpike[index]:
                firstSpike[index] = time

        xBinned, yBinned = self._bin(targetX, targetY)
        key = (xBinned, yBinned)
        if key not in self._indexTable:
            raise ValueError(
                f"! ERROR: no neuron exists at (x={xBinned}, y={yBinned}) in spatial map"
            )

        targetIndex = self._indexTable[key]
        if targetIndex not in firstSpike:
            self.path = None
            return False

        path = [targetIndex]
        currentIndex = targetIndex
        maxTime = firstSpike[targetIndex]

        while currentIndex != self._sourceIndex:
            neighbours = self._neighbourTable.get(currentIndex, [])
            best, bestTime = None, maxTime

            for neighbour in neighbours:
                if neighbour in firstSpike and firstSpike[neighbour] < bestTime:
                    bestTime = firstSpike[neighbour]
                    best = neighbour

            if best is None:
                self.path = None
                return False

            maxTime = bestTime
            currentIndex = best
            path.append(currentIndex)

        self.path = path
        return True

    def formPath(self):
        if self.path is None:
            raise RuntimeError(
                "Path not calculated. Please propagate wave through the spatial map"
            )
        return list(reversed(self.path))

    def resetWaveProp(self):
        n = len(self._lattice)

        with self._deviceLock:
            self._ssa.vars["startSpike"].view[:] = numpy.zeros(n, dtype=numpy.uint32)
            self._ssa.vars["endSpike"].view[:] = numpy.zeros(n, dtype=numpy.uint32)
            self._ssa.vars["startSpike"].push_to_device()
            self._ssa.vars["endSpike"].push_to_device()

            self._ssa.extra_global_params["spikeTimes"].view[:] = numpy.full(
                n, numpy.finfo(numpy.float32).max, dtype=numpy.float32
            )
            self._ssa.extra_global_params["spikeTimes"].push_to_device()

            self._spatialMapPop.vars["V"].view[:] = self._spatialMapNeuronParameters["Vrest"]
            self._spatialMapPop.vars["RefracTime"].view[:] = 0.0
            self._spatialMapPop.vars["V"].push_to_device()
            self._spatialMapPop.vars["RefracTime"].push_to_device()

        self.model.timestep = 0
        self.path = None
        self._sourceIndex = None

    def pathCoordinates(self):
        if self.path is None:
            return None
        return self._coordsCache[list(reversed(self.path))]  # (M, 2) metres, (x, y)