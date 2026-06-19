import numpy
import pygenn
import itertools
from tqdm import tqdm
import os

_NEURON = pygenn.create_neuron_model(
    "LifWithInhibition",
    params=["C", "TauM", "Vrest", "Vreset", "Vthresh", "TauRefrac", "TauInh", "Ioffset"],
    vars=[("V", "scalar"), ("RefracTime", "scalar"), ("Iinh", "scalar"), ("Iext", "scalar")],
    sim_code="""
        if (RefracTime > 0.0) {
            RefracTime -= dt;
        } else {
            scalar dV = (-(V - Vrest) + Isyn + Ioffset + Iext - Iinh) / TauM;
            V += dV * dt;
            Iinh -= (Iinh / TauInh) * dt;
            Iext = 0.0;
        }
        """,
    threshold_condition_code="RefracTime <= 0.0 && V >= Vthresh",
    reset_code="""
        V = Vreset;
        RefracTime = TauRefrac;
    """
)

_POISSON_INPUT = pygenn.create_neuron_model(
    "PoissonInput",
    params=[],
    vars=[("firingRate", "scalar")],
    sim_code="",
    threshold_condition_code="gennrand_uniform() < firingRate * dt / 1000.0",
    reset_code=""
)

_OJA_RULE = pygenn.create_weight_update_model(
    "OjaRule",
    params = ["eta", "maxWeight", "tauTrace"],
    vars = [("g", "scalar")],
    pre_vars = [("rPre", "scalar")],
    post_vars = [("rPost", "scalar")],
    pre_dynamics_code = "rPre -= (rPre / tauTrace) * dt;",
    post_dynamics_code = "rPost -= (rPost / tauTrace) * dt;",
    pre_spike_code = "rPre += 1.0;",
    post_spike_code = "rPost += 1.0;",
    post_spike_syn_code = """
    const scalar dg = eta * rPost * (rPre - rPost * g);
    g = fmax(0.0f, fmin(g + dg, maxWeight));
    """
)

ENV_SIZE = 75.0  # metres
NEURON_SPACING = 0.375  # metres (0.3 for robot length, + 0.075 for 25% safety margin)
LIDAR_RANGE = 12.0  # metres

CURRENT_CLAMP = 300  # nA
DURATION = 500  # ms

SPEED_CELL_AMOUNT = 75

HD_CELL_AMOUNT = 768

GRID_CELL_AMOUNT = 768
GRID_SIDE = 32

DISTANCE_BIN_AMOUNT = 60
PHI_BIN_AMOUNT = 30
BVC_AMOUNT = DISTANCE_BIN_AMOUNT * PHI_BIN_AMOUNT
OVC_AMOUNT = BVC_AMOUNT

PLACE_SIDE = int(ENV_SIZE / NEURON_SPACING)
PLACE_CELL_AMOUNT = PLACE_SIDE ** 2

CACHE_PATH = r"WPSNNCache"


class HESCC:
    def __init__(self):
        def createDirections(sourcePopSize, targetPopSize):
            sourceDirs = numpy.linspace(
                0.0,
                2 * numpy.pi * (1 - 1 / sourcePopSize),
                sourcePopSize
            )
            targetDirs = numpy.linspace(
                0.0,
                2 * numpy.pi * (1 - 1 / targetPopSize),
                targetPopSize
            )

            return numpy.cos(
                sourceDirs[:, None] - targetDirs[None, :]
            ).astype(numpy.float32)

        def getTwistedTorusCANSynapses(type: str, epsilon: float = 0.01,
                                       rows=numpy.arange(GRID_CELL_AMOUNT) // GRID_SIDE,
                                       cols=numpy.arange(GRID_CELL_AMOUNT) % GRID_SIDE) -> list:
            items = []

            if type == "pre":
                filePath = os.path.join(CACHE_PATH, "twistedTorusCANpre.npy")
            elif type == "post":
                filePath = os.path.join(CACHE_PATH, "twistedTorusCANpost.npy")
            elif type == "weights":
                filePath = os.path.join(CACHE_PATH, "twistedTorusCANweights.npy")

            if os.path.exists(filePath):
                print(f"    - Loading Twisted Torus {type} synapses from cache")
                data = self._load(filePath)
                return data.tolist()
            else:
                for i in tqdm(range(GRID_CELL_AMOUNT), desc="Creating Twisted Torus CAN"):
                    for j in range(GRID_CELL_AMOUNT):
                        dr = min(
                            abs(int(rows[i]) - int(rows[j])),
                            GRID_SIDE - abs(int(rows[i]) - int(rows[j]))
                        )
                        dc = min(
                            abs(int(cols[i]) - int(cols[j])),
                            GRID_SIDE - abs(int(cols[i]) - int(cols[j]))
                        )
                        d2 = dr ** 2 + dc ** 2

                        weight = calculateTwistedTorusCANSynapticWeight(d2)

                        if abs(weight) > epsilon:
                            if type == "pre":
                                items.append(j)
                            elif type == "post":
                                items.append(i)
                            elif type == "weights":
                                items.append(float(weight))
                self._save(filePath, numpy.array(items))
                return items

        def calculateTwistedTorusCANSynapticWeight(d2: float) -> float:
            weightExcitation = 1.0
            weightInhibition = 0.8
            sigmaExcitation = 2.0
            sigmaInhibition = 4.0

            return (
                    weightExcitation * numpy.exp(-d2 / (2 * sigmaExcitation ** 2))
                    - weightInhibition * numpy.exp(-d2 / (2 * sigmaInhibition ** 2))
            )

        def getSpatialMapSynapses(type: str, epsilon: float = 0.05):
            halfEnvironment = ENV_SIZE / 2.0
            gridXOrdinates = numpy.linspace(-halfEnvironment, halfEnvironment, GRID_SIDE)
            gridYOrdinates = numpy.linspace(-halfEnvironment, halfEnvironment, GRID_SIDE)
            gridXDimension, gridYDimension = numpy.meshgrid(gridXOrdinates, gridYOrdinates)
            world = numpy.stack([gridXDimension.ravel(), gridYDimension.ravel()], axis=1)

            sigmaPlace = NEURON_SPACING * 3.0
            epsilon = 0.05

            items = []

            if type == "pre":
                filePath = os.path.join(CACHE_PATH, "spatialMapSynapseGridPre.npy")
            elif type == "post":
                filePath = os.path.join(CACHE_PATH, "spatialMapSynapseGridPost.npy")
            elif type == "weights":
                filePath = os.path.join(CACHE_PATH, "spatialMapSynapseGridWeights.npy")

            if os.path.exists(filePath):
                print(f"    - Loading Spatial Map {type} synapses from cache")
                data = self._load(filePath)
                return data.tolist()
            else:
                for i in tqdm(range(PLACE_CELL_AMOUNT), desc="Creating Spatial Map SynapseGrid"):
                    cx, cy = self._coordsCache[i]
                    for j in range(GRID_CELL_AMOUNT):
                        gx, gy = world[j]
                        d2 = (cx - gx) ** 2 + (cy - gy) ** 2
                        weight = float(numpy.exp(-d2 / (2 * sigmaPlace ** 2)))
                        if weight > epsilon:
                            if type == "pre":
                                items.append(j)
                            elif type == "post":
                                items.append(i)
                            elif type == "weights":
                                items.append(weight)
                self._save(filePath, numpy.array(items))
                return items

        def getRecurrentSpatialMapSynapses(type: str):
            associativeSigma = NEURON_SPACING * 5.0
            cutoff = 3 * associativeSigma

            items = []

            if type == "pre":
                filePath = os.path.join(CACHE_PATH, "recurrentSpatialMapSynapseGridPre.npy")
            elif type == "post":
                filePath = os.path.join(CACHE_PATH, "recurrentSpatialMapSynapseGridPost.npy")
            elif type == "weights":
                filePath = os.path.join(CACHE_PATH, "recurrentSpatialMapSynapseGridWeights.npy")

            if os.path.exists(filePath):
                print(f"    - Loading Recurrent Spatial Map {type} synapses from cache")
                data = self._load(filePath)
                return data.tolist()
            else:
                for i in tqdm(range(PLACE_CELL_AMOUNT), desc="Creating Recurrent Spatial Map SynapseGrid"):
                    cx, cy = self._coordsCache[i]
                    differences = self._coordsCache - numpy.array([cx, cy])
                    distances = numpy.sqrt((differences ** 2).sum(axis=1))
                    neighbours = numpy.where(
                        (distances < cutoff) & (distances > 0)
                    )[0]
                    for j in neighbours:
                        weight = float(
                            numpy.exp(-distances[j] ** 2 / (2 * associativeSigma ** 2))
                        )
                        if weight > 0.05:
                            if type == "pre":
                                items.append(j)
                            elif type == "post":
                                items.append(i)
                            elif type == "weights":
                                items.append(weight)
            self._save(filePath, numpy.array(items))
            return items

        def getVCToSpatialMapConnectivity(vcType, synapsePart:str, fanout, seed, amount) -> list:
            items = []

            if synapsePart == "pre":
                filePath = os.path.join(CACHE_PATH, f"{vcType}pre.npy")
            elif synapsePart == "post":
                filePath = os.path.join(CACHE_PATH, f"{vcType}post.npy")

            if os.path.exists(filePath):
                print(f"    - Loading f{vcType} to Spatial Map {synapsePart} synapses from cache")
                data = self._load(filePath)
                return data.tolist()
            else:
                rng = numpy.random.default_rng(seed)

                if synapsePart == "pre":
                    items = numpy.repeat(
                        numpy.arange(amount),
                        fanout
                    )
                elif synapsePart == "post":
                    items = numpy.array([
                        rng.choice(PLACE_CELL_AMOUNT, fanout, replace = False) for _ in range(amount)
                    ]).ravel()
                self._save(filePath, items)
                return items.tolist()


        self.path = None

        self._lattice = self._initLattice()
        self._coordsCache = numpy.array(self._lattice)
        self._indexTable = self._initIndexTable()
        self._connectivityList = self._buildConnections()
        self._neighbourTable = self._initNeighbourTable()

        self._hdCoords = self._initHDPopCoords()
        self._bvcCoords = self._initBVCPopCoords()
        self._ovcCoords = self._initOVCPopCoords()

        self.model = pygenn.GeNNModel(
            precision="float",
            model_name="cognitiveEnvModel"
        )
        self.speedCellPop = self.model.add_neuron_population(
            pop_name="SPEED_CELL_POPULATION",
            num_neurons=SPEED_CELL_AMOUNT,
            neuron=_NEURON,
            params={
                "C": 1.0,
                "TauM": 20.0,
                "Vrest": -65.0,
                "Vreset": -65.0,
                "Vthresh": -50.0,
                "TauRefrac": 2.0,
                "TauInh": 5.0,
                "Ioffset": 0.0
            },
            vars={
                "V": -65.0,
                "RefracTime": 0.0,
                "Iinh": 0.0,
                "Iext" : 0.0
            }
        )
        self.speedInputPop = self.model.add_neuron_population(
            pop_name="SPEED_INPUT_POPULATION",
            num_neurons=SPEED_CELL_AMOUNT,
            neuron=_POISSON_INPUT,
            params={},
            vars={"firingRate": 0.0}
        )
        self.hdCellPop = self.model.add_neuron_population(
            pop_name="HD_CELL_POPULATION",
            num_neurons=HD_CELL_AMOUNT,
            neuron=_NEURON,
            params={
                "C": 1.0,
                "TauM": 20.0,
                "Vrest": -65.0,
                "Vreset": -65.0,
                "Vthresh": -50.0,
                "TauRefrac": 2.0,
                "TauInh": 10.0,
                "Ioffset": 0.0
            },
            vars={
                "V": -65.0,
                "RefracTime": 0.0,
                "Iinh": 0.0,
                "Iext" : 0.0
            }
        )
        self.hdInputPop = self.model.add_neuron_population(
            pop_name="HD_INPUT_POPULATION",
            num_neurons=HD_CELL_AMOUNT,
            neuron=_POISSON_INPUT,
            params={},
            vars={"firingRate": 0.0}
        )
        self.gridCellPop = self.model.add_neuron_population(
            pop_name="GRID_CELL_POPULATION",
            num_neurons=GRID_CELL_AMOUNT,
            neuron=_NEURON,
            params={
                "C": 1.0,
                "TauM": 20.0,
                "Vrest": -65.0,
                "Vreset": -65.0,
                "Vthresh": -50.0,
                "TauRefrac": 2.0,
                "TauInh": 50.0,
                "Ioffset": 0.0
            },
            vars={
                "V": -65.0,
                "RefracTime": 0.0,
                "Iinh": 0.0,
                "Iext" : 0.0
            }
        )
        self.gridCellPop.spike_recording_enabled = True
        self.BVCPop = self.model.add_neuron_population(
            pop_name="BVC_POPULATION",
            num_neurons=BVC_AMOUNT,
            neuron=_NEURON,
            params={
                "C": 1.0,
                "TauM": 20.0,
                "Vrest": -65.0,
                "Vreset": -65.0,
                "Vthresh": -50.0,
                "TauRefrac": 2.0,
                "TauInh": 100.0,
                "Ioffset": 0.0
            },
            vars={
                "V": -65.0,
                "RefracTime": 0.0,
                "Iinh": 0.0,
                "Iext" : 0.0
            }
        )  #
        self.OVCPop = self.model.add_neuron_population(
            pop_name="OVC_POPULATION",
            num_neurons=OVC_AMOUNT,
            neuron=_NEURON,
            params={
                "C": 1.0,
                "TauM": 20.0,
                "Vrest": -65.0,
                "Vreset": -65.0,
                "Vthresh": -50.0,
                "TauRefrac": 2.0,
                "TauInh": 100.0,
                "Ioffset": 0.0
            },
            vars={
                "V": -65.0,
                "RefracTime": 0.0,
                "Iinh": 0.0,
                "Iext" : 0.0
            }
        )
        self.spatialMap = self.model.add_neuron_population(
            pop_name="SPATIAL_MAP",
            num_neurons=PLACE_CELL_AMOUNT,
            neuron=_NEURON,
            params={
                "C": 1.0,
                "TauM": 20.0,
                "Vrest": -65.0,
                "Vreset": -65.0,
                "Vthresh": -50.0,
                "TauRefrac": 2.0,
                "TauInh": 100.0,
                "Ioffset": 0.0
            },
            vars={
                "V": -65.0,
                "RefracTime": 0.0,
                "Iinh": 0.0,
                "Iext" : 0.0
            }
        )
        self.spatialMap.spike_recording_enabled = True

        # Speed Cell Input Pop -> Speed Cell Neuron Pop Synapse Population
        self.speedInputToSpeedCellsSynapsePop = self.model.add_synapse_population(
            pop_name="SPEED_INPUT_TO_SPEED_CELL_SYNAPSE_POPULATION",
            matrix_type="DENSE",
            source=self.speedInputPop,
            target=self.speedCellPop,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": 1.0}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        # HD Cell Input Pop -> HD Cell Neuron Population Synapse Population
        self.hdInputToHDCellSynapsePop = self.model.add_synapse_population(
            pop_name="HD_INPUT_TO_HD_CELL_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.hdInputPop,
            target=self.hdCellPop,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": 30.0}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            ),
            connectivity_init = pygenn.init_sparse_connectivity("OneToOne")
        )
        # Speed Cell Pop -> Grid Cell Pop Synapse Population
        self.speedCellsToGridCellsSynapsePop = self.model.add_synapse_population(
            pop_name="SPEED_CELLS_TO_GRID_CELLS_SYNAPSE_POPULATION",
            matrix_type="DENSE",
            source=self.speedCellPop,
            target=self.gridCellPop,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": createDirections(SPEED_CELL_AMOUNT, GRID_CELL_AMOUNT).flatten().tolist()}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        #  HD Cell Pop -> Grid Cell Pop Synapse Population
        hdToGridGain = 4.0
        self.hdCellsToGridCellsSynapsePop = self.model.add_synapse_population(
            pop_name="HD_CELLS_TO_GRID_CELLS_SYNAPSE_POPULATION",
            matrix_type="DENSE",
            source=self.hdCellPop,
            target=self.gridCellPop,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": (hdToGridGain * createDirections(HD_CELL_AMOUNT, GRID_CELL_AMOUNT)).flatten().tolist()}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        # Grid Cell Population -> Grid Cell Population Recurrent Synapse Population
        self.gridCellRecurrentSynapsePop = self.model.add_synapse_population(
            pop_name="GRID_CELLS_RECURRENT_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.gridCellPop,
            target=self.gridCellPop,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": getTwistedTorusCANSynapses("weights")}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        self.gridCellRecurrentSynapsePop.set_sparse_connections(
            pre_indices=getTwistedTorusCANSynapses("pre"),
            post_indices=getTwistedTorusCANSynapses("post"),
        )
        # Grid Cell Population -> Spatial Map Population Synapse Population
        self.gridCellsToSpatialMapSynapsePop = self.model.add_synapse_population(
            pop_name="GRID_CELLS_TO_SPATIAL_MAP_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.gridCellPop,
            target=self.spatialMap,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": getSpatialMapSynapses("weights")}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 10.0}
            )
        )
        self.gridCellsToSpatialMapSynapsePop.set_sparse_connections(
            pre_indices=getSpatialMapSynapses("pre"),
            post_indices=getSpatialMapSynapses("post"),
        )
        # BVC Pop -> Spatial Map Pop Synapse Population
        self.BVCToSpatialMapSynapsePop = self.model.add_synapse_population(
            pop_name="BVC_TO_SPATIAL_MAP_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.BVCPop,
            target=self.spatialMap,
            weight_update_init = pygenn.init_weight_update(
                snippet = _OJA_RULE,
                params = {
                    "eta" : 0.005,
                    "maxWeight" : 5.0,
                    "tauTrace" : 20.0,
                },
                vars = {"g" : 0.5},
                pre_vars = {
                    "rPre" : 0.0
                },
                post_vars = {
                    "rPost" : 0.0
                }
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau" : 10.0}
            )
        )
        self.BVCToSpatialMapSynapsePop.set_sparse_connections(
            pre_indices = getVCToSpatialMapConnectivity(
                vcType = "BVC",
                synapsePart = "pre",
                fanout = 200,
                amount = BVC_AMOUNT,
                seed = 1
            ),
            post_indices = getVCToSpatialMapConnectivity(
                vcType = "BVC",
                synapsePart = "post",
                fanout = 200,
                amount = BVC_AMOUNT,
                seed = 1
            )
        )
        # OVC Pop -> Spatial Map Synapse Population
        self.OVCToSpatialMapSynapsePop = self.model.add_synapse_population(
            pop_name="OVC_TO_SPATIAL_MAP_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.OVCPop,
            target=self.spatialMap,
            weight_update_init=pygenn.init_weight_update(
                snippet=_OJA_RULE,
                params={
                    "eta": 0.005,
                    "maxWeight": 5.0,
                    "tauTrace": 20.0,
                },
                vars = {"g" : 0.1},
                pre_vars={
                    "rPre": 0.0
                },
                post_vars={
                    "rPost": 0.0
                }
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 10.0}
            )
        )
        self.OVCToSpatialMapSynapsePop.set_sparse_connections(
            pre_indices = getVCToSpatialMapConnectivity(
                vcType = "OVC",
                synapsePart = "pre",
                fanout = 200,
                amount = OVC_AMOUNT,
                seed = 2
            ),
            post_indices = getVCToSpatialMapConnectivity(
                vcType = "OVC",
                synapsePart = "post",
                fanout = 200,
                amount = OVC_AMOUNT,
                seed = 2
            )
        )

        # SpatialMap Lateral Synaptic Connections
        SMapToSMapPreSynapticConnections, SMapToSMapPostSynapticConnections, SMapToSMapSynapticWeights, SMapToSMapSynapticDelays = zip(
            *self._connectivityList)
        self.spatialMapSynapsePop = self.model.add_synapse_population(
            pop_name="SPATIAL_MAP_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.spatialMap,
            target=self.spatialMap,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulseDendriticDelay",
                {},
                {
                    "g": list(SMapToSMapSynapticWeights),
                    "d": list(SMapToSMapSynapticDelays)
                }
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        self.spatialMapSynapsePop.set_sparse_connections(
            pre_indices=list(SMapToSMapPreSynapticConnections),
            post_indices=list(SMapToSMapPostSynapticConnections)
        )
        self.spatialMapSynapsePop.max_dendritic_delay_timesteps = 2

        # Spatial Map -> Spatial Map Recurrent Synapse Population
        self.spatialMapRecurrentSynapsePop = self.model.add_synapse_population(
            pop_name="SPATIAL_MAP_RECURRENT_SYNAPSE_POPULATION",
            matrix_type="SPARSE",
            source=self.spatialMap,
            target=self.spatialMap,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse",
                {},
                {"g": getRecurrentSpatialMapSynapses("weights")}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 20.0}
            )
        )
        self.spatialMapRecurrentSynapsePop.set_sparse_connections(
            pre_indices=getRecurrentSpatialMapSynapses("pre"),
            post_indices=getRecurrentSpatialMapSynapses("post")
        )

        self.waveStim = self.model.add_neuron_population(
            pop_name="WAVE_STIM",
            num_neurons=PLACE_CELL_AMOUNT,
            neuron="SpikeSourceArray",
            params={},
            vars={
                "startSpike": numpy.zeros(PLACE_CELL_AMOUNT, dtype=numpy.uint32),
                "endSpike": numpy.zeros(PLACE_CELL_AMOUNT, dtype=numpy.uint32)
            }
        )
        self.waveStim.extra_global_params["spikeTimes"].set_init_values(
            numpy.full(PLACE_CELL_AMOUNT, numpy.finfo(numpy.float32).max, dtype=numpy.float32)
        )

        self.waveStimSynapses = self.model.add_synapse_population(
            pop_name="WAVE_STIM_SYNAPSES",
            matrix_type="SPARSE",
            source=self.waveStim,
            target=self.spatialMap,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulseConstantWeight",
                {"g": float(CURRENT_CLAMP)}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr",
                {"tau": 5.0}
            )
        )
        self.waveStimSynapses.set_sparse_connections(
            list(range(PLACE_CELL_AMOUNT)),
            list(range(PLACE_CELL_AMOUNT))
        )

        print("! Compiling Model")
        self.model.build(always_rebuild=False)
        print("! Loading Model onto Device")
        self.model.load(num_recording_timesteps=DURATION)
        print("! Model loaded onto device sucessfully")

    def _initLattice(self):
        envHalf = ENV_SIZE / 2.0
        coordinates = numpy.linspace(
            -envHalf + NEURON_SPACING / 2,
            envHalf - NEURON_SPACING / 2,
            PLACE_SIDE
        )
        return [
            (round(round(float(x), 10)), round(round(float(y), 10))) for y in coordinates for x in coordinates
        ]

    def _initIndexTable(self):
        return {coordinate: index for index, coordinate in enumerate(self._lattice)}

    def _buildConnections(self, weight=300.0, nonDiagonalDelay=1.0):
        diagonalDelay = round(
            numpy.sqrt(2), 10
        )

        connList = []
        for i, (x, y) in enumerate(self._lattice):
            for dx, dy in itertools.product([-NEURON_SPACING, 0.0, NEURON_SPACING], repeat=2):
                if dx == 0.0 and dy == 0.0:
                    continue
                neighbour = (
                    round(round(x + dx, 10)),
                    round(round(y + dy, 10))
                )
                if neighbour in self._indexTable:
                    if dx != 0.0 and dy != 0.0:
                        delay = diagonalDelay
                    else:
                        delay = nonDiagonalDelay
                    connList.append(
                        (i, self._indexTable[neighbour], weight, delay)
                    )

        return connList

    def _initNeighbourTable(self):
        neighbourTable = {}
        for pre, post, _, _ in self._connectivityList:
            if pre not in neighbourTable:
                neighbourTable[pre] = []
            neighbourTable[pre].append(post)
        return neighbourTable

    def _initHDPopCoords(self):
        return numpy.linspace(
            0.0,
            2 * numpy.pi * (1 - 1 / HD_CELL_AMOUNT),
            HD_CELL_AMOUNT
        )

    def _initBVCPopCoords(self):
        dCentres = numpy.linspace(
            0.1,
            LIDAR_RANGE - 0.1,
            DISTANCE_BIN_AMOUNT
        )
        phiCentres = numpy.linspace(
            0.0,
            2 * numpy.pi * (1 - 1 / PHI_BIN_AMOUNT),
            PHI_BIN_AMOUNT
        )
        dd, pp = numpy.meshgrid(dCentres, phiCentres)
        return numpy.stack([dd.ravel(), pp.ravel()], axis=1)

    def _initOVCPopCoords(self):
        dCentres = numpy.linspace(
            0.1,
            LIDAR_RANGE - 0.1,
            DISTANCE_BIN_AMOUNT
        )
        phiCentres = numpy.linspace(
            0.0,
            2 * numpy.pi * (1 - 1 / PHI_BIN_AMOUNT),
            PHI_BIN_AMOUNT
        )
        dd, pp = numpy.meshgrid(dCentres, phiCentres)
        return numpy.stack([dd.ravel(), pp.ravel()], axis=1)

    def _bin(self, x, y):
        half = ENV_SIZE / 2.0
        col = int(numpy.clip((x + half) / NEURON_SPACING, 0, PLACE_SIDE - 1))
        row = int(numpy.clip((y + half) / NEURON_SPACING, 0, PLACE_SIDE - 1))
        xBinned = round(-half + (col + 0.5) * NEURON_SPACING, 10)
        yBinned = round(-half + (row + 0.5) * NEURON_SPACING, 10)
        return xBinned, yBinned

    def injectGaussian(self, x, y, sigma: float = None):
        if sigma is None:
            sigma = NEURON_SPACING * 0.5

        distances = (
                (self._coordsCache[:, 0] - x) ** 2 + (self._coordsCache[:, 1] - y) ** 2
        )

        kernel = CURRENT_CLAMP * numpy.exp(
            -distances / (2.0 * sigma ** 2)
        )
        mask = distances < (3.0 * sigma) ** 2

        self.spatialMap.vars["Iinh"].pull_from_device()
        self.spatialMap.vars["Iinh"].view[mask] += kernel[mask]
        self.spatialMap.vars["Iinh"].push_to_device()

    def injectIntoBVCPopulation(self, d: float, phi: float):
        sigmaD = 0.5
        kappa = 2.0
        dDifferences = self._bvcCoords[:, 0] - d
        phiDifferences = self._bvcCoords[:, 1] - phi

        kernel = (
                numpy.exp(-dDifferences ** 2 / (2 * sigmaD ** 2)) *
                numpy.exp(kappa * (numpy.cos(phiDifferences) - 1.0))
        ).astype(numpy.float32)

        mask = kernel > 0.01

        self.BVCPop.vars["Iext"].pull_from_device()
        self.BVCPop.vars["Iext"].view[mask] += kernel[mask] * 50
        numpy.clip(self.BVCPop.vars["Iext"].view, 0.0, float(CURRENT_CLAMP),
                   out=self.BVCPop.vars["Iext"].view)
        self.BVCPop.vars["Iext"].push_to_device()

    def injectIntoOVCPopulation(self, d: float, phi: float):
        sigmaD = 0.5
        kappa = 2.0

        dDiffs = self._ovcCoords[:, 0] - d
        phiDiffs = self._ovcCoords[:, 1] - phi

        kernel = (
                numpy.exp(-dDiffs ** 2 / (2 * sigmaD ** 2)) *
                numpy.exp(kappa * (numpy.cos(phiDiffs) - 1.0))
        ).astype(numpy.float32)

        mask = kernel > 0.01

        self.OVCPop.vars["Iext"].pull_from_device()
        self.OVCPop.vars["Iext"].view[mask] += kernel[mask]
        numpy.clip(self.OVCPop.vars["Iext"].view, 0.0, float(CURRENT_CLAMP),
                   out=self.OVCPop.vars["Iext"].view)
        self.OVCPop.vars["Iext"].push_to_device()

    def decodePosition(self) -> numpy.ndarray:
        self.spatialMap.vars["V"].pull_from_device()
        rates = numpy.array(
            self.spatialMap.vars["V"].view, dtype=numpy.float32
        )
        rates = numpy.maximum(rates - (-65.0), 0.0)
        total = rates.sum()
        if total < 1e-9:
            return numpy.zeros(2)
        return (rates[:, None] * self._coordsCache).sum(axis=0) / total

    def decodeHeading(self) -> float:
        self.hdCellPop.vars["V"].pull_from_device()
        rates = numpy.array(
            self.hdCellPop.vars["V"].view, dtype=numpy.float32
        )
        rates = numpy.maximum(rates - (-65.0), 0.0)
        total = rates.sum()
        if total < 1e-9:
            return 0.0
        sinSum = (rates * numpy.sin(self._hdCoords)).sum()
        cosSum = (rates * numpy.cos(self._hdCoords)).sum()
        heading = float(numpy.arctan2(sinSum, cosSum))
        return heading % (2 * numpy.pi)

    def step(self):
        self.model.step_time()

    def propagateWave(self, robotX: float, robotY: float):
        bx, by = self._bin(robotX, robotY)
        key = (bx, by)
        if key not in self._indexTable:
            raise ValueError(
                f"Robot position ({robotX}, {robotY}) outside arena bounds."
            )
        i = self._indexTable[key]

        self.waveStim.extra_global_params["spikeTimes"].pull_from_device()
        self.waveStim.extra_global_params["spikeTimes"].view[i] = self.model.t + 2.0
        self.waveStim.extra_global_params["spikeTimes"].push_to_device()

        self.waveStim.vars["startSpike"].pull_from_device()
        self.waveStim.vars["endSpike"].pull_from_device()
        self.waveStim.vars["startSpike"].view[i] = i
        self.waveStim.vars["endSpike"].view[i] = i + 1
        self.waveStim.vars["startSpike"].push_to_device()
        self.waveStim.vars["endSpike"].push_to_device()

    def backpropagateWave(self, targetX: float, targetY: float, robotX: float, robotY: float):
        self.model.pull_recording_buffers_from_device()
        times, indices = self.spatialMap.spike_recording_data[0]

        firstSpike = {}
        for t, idx in zip(times, indices):
            idx = int(idx)
            if idx not in firstSpike or t < firstSpike[idx]:
                firstSpike[idx] = t

        tbx, tby = self._bin(targetX, targetY)
        rbx, rby = self._bin(robotX, robotY)

        targetKey = (tbx, tby)
        robotKey = (rbx, rby)

        if targetKey not in self._indexTable:
            raise ValueError(f"Target ({targetX}, {targetY}) outside arena bounds.")
        if robotKey not in self._indexTable:
            raise ValueError(f"Robot position ({robotX}, {robotY}) outside arena bounds.")

        targetIndex = self._indexTable[targetKey]
        robotIndex = self._indexTable[robotKey]

        if targetIndex not in firstSpike:
            raise RuntimeError(
                f"Wavefront did not reach target at ({tbx}, {tby})."
            )

        self.path = []
        currentIndex = targetIndex
        maxTime = firstSpike[targetIndex]

        while currentIndex != robotIndex:
            self.path.append(currentIndex)
            neighbours = self._neighbourTable.get(currentIndex, [])
            best, bestTime = None, maxTime

            for neighbour in neighbours:
                if neighbour in firstSpike and firstSpike[neighbour] < bestTime:
                    bestTime = firstSpike[neighbour]
                    best = neighbour

            if best is None:
                break

            maxTime = bestTime
            currentIndex = best

        self.path.append(robotIndex)

        print(f"Neurons that fired : {len(firstSpike)}")
        print(f"Target index       : {targetIndex}, first spike: {firstSpike.get(targetIndex, 'never')}")
        print(f"Robot origin index : {robotIndex}, first spike: {firstSpike.get(robotIndex, 'never')}")

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
        self.waveStim.vars["startSpike"].view[:] = numpy.zeros(
            PLACE_CELL_AMOUNT, dtype=numpy.uint32
        )
        self.waveStim.vars["endSpike"].view[:] = numpy.zeros(
            PLACE_CELL_AMOUNT, dtype=numpy.uint32
        )
        self.waveStim.vars["startSpike"].push_to_device()
        self.waveStim.vars["endSpike"].push_to_device()

        self.waveStim.extra_global_params["spikeTimes"].view[:] = numpy.full(
            PLACE_CELL_AMOUNT,
            numpy.finfo(numpy.float32).max,
            dtype=numpy.float32
        )
        self.waveStim.extra_global_params["spikeTimes"].push_to_device()

        self.model.timestep = 0
        self.path = None

    def setSpeedInput(self, speed_ms: float):
        maxSpeed = 2.0  # m/s — normalisation constant
        maxRate = 100.0  # Hz — maximum Poisson firing rate
        rate = float(numpy.clip(speed_ms / maxSpeed, 0.0, 1.0) * maxRate)
        self.speedInputPop.vars["firingRate"].view[:] = numpy.full(
            SPEED_CELL_AMOUNT, rate, dtype=numpy.float32
        )
        self.speedInputPop.vars["firingRate"].push_to_device()

    def setHDInput(self, heading_rad: float):
        kappa = 4.0  # sharpness of bump
        maxRate = 100.0  # Hz
        rates = (maxRate * numpy.exp(
            kappa * (numpy.cos(self._hdCoords - heading_rad) - 1.0)
        )).astype(numpy.float32)
        self.hdInputPop.vars["firingRate"].view[:] = rates
        self.hdInputPop.vars["firingRate"].push_to_device()

    def _load(self, filePath) -> numpy.ndarray:
        if not os.path.exists(filePath):
            return False
        else:
            return numpy.load(filePath)

    def _save(self, filePath, data: numpy.ndarray):
        numpy.save(
            file=filePath,
            arr=data
        )


if __name__ == "__main__":
    print("! Initialising HESCC model")
    model = HESCC()