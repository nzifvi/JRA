import numpy
import pygenn
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

_GFTC_NEURON = pygenn.create_neuron_model(
    "GFTCMultiplicative",
    params=["C", "TauM", "Vrest", "Vreset", "Vthresh", "TauRefrac", "gain"],
    vars=[("V", "scalar"), ("RefracTime", "scalar")],
    additional_input_vars=[
        ("IPW", "scalar", 0.0),
        ("IHD", "scalar", 0.0)
    ],
    sim_code="""
        if (RefracTime > 0.0) {
            RefracTime -= dt;
        } else {
            scalar drive = gain * IPW * IHD;
            scalar dV = (-(V - Vrest) + drive) / TauM;
            V += dV * dt;
        }
    """,
    threshold_condition_code="RefracTime <= 0.0 && V >= Vthresh",
    reset_code="""
        V = Vreset;
        RefracTime = TauRefrac;
    """
)

DISTANCE_BINS            = 12
EGOCENTRIC_BEARING_BINS  = 36
ALLOCENTRIC_BEARING_BINS = 36
HDC_COUNT                = 36

LIDAR_RANGE   = 6.0
CURRENT_CLAMP = 300.0
DURATION      = 500

CACHE_PATH = r"WPSNNCache"

# Standard LIF parameter / variable dictionaries
_LIF_PARAMS = {
    "C": 1.0, "TauM": 20.0, "Vrest": -65.0, "Vreset": -65.0,
    "Vthresh": -50.0, "TauRefrac": 2.0, "TauInh": 100.0, "Ioffset": 0.0
}
_LIF_VARS = {"V": -65.0, "RefracTime": 0.0, "Iinh": 0.0, "Iext": 0.0}

_GFTC_PARAMS = {
    "C": 1.0, "TauM": 20.0, "Vrest": -65.0, "Vreset": -65.0,
    "Vthresh": -50.0, "TauRefrac": 2.0, "gain": 100.0
}
_GFTC_VARS = {"V": -65.0, "RefracTime": 0.0}


class HESCC:
    def __init__(self):
        os.makedirs(CACHE_PATH, exist_ok=True)

        self.PWbCount     = DISTANCE_BINS * EGOCENTRIC_BEARING_BINS
        self.PWoCount     = DISTANCE_BINS * EGOCENTRIC_BEARING_BINS
        self.HDCCount     = HDC_COUNT
        self.PWbGFTCCount = self.PWbCount * self.HDCCount
        self.PWoGFTCCount = self.PWoCount * self.HDCCount
        self.BVCCount     = DISTANCE_BINS * ALLOCENTRIC_BEARING_BINS
        self.OVCCount     = DISTANCE_BINS * ALLOCENTRIC_BEARING_BINS

        self._hdCoords  = self._initHDPopCoords()
        self._pwbCoords = self._initEgocentricCoords()
        self._pwoCoords = self._pwbCoords

        self.model = pygenn.GeNNModel(
            precision="float",
            model_name="SpatialMapModel"
        )

        self.PWbPop = self.model.add_neuron_population(
            "PWbPop", self.PWbCount, _NEURON, _LIF_PARAMS, _LIF_VARS
        )
        self.PWoPop = self.model.add_neuron_population(
            "PWoPop", self.PWoCount, _NEURON, _LIF_PARAMS, _LIF_VARS
        )

        self.HDCPop = self.model.add_neuron_population(
            "HDCPop", self.HDCCount, _NEURON, _LIF_PARAMS, _LIF_VARS
        )

        self.PWbGFTC = self.model.add_neuron_population(
            "PWbGFTC", self.PWbGFTCCount, _GFTC_NEURON, _GFTC_PARAMS, _GFTC_VARS
        )
        self.PWoGFTC = self.model.add_neuron_population(
            "PWoGFTC", self.PWoGFTCCount, _GFTC_NEURON, _GFTC_PARAMS, _GFTC_VARS
        )

        self.BVCPop = self.model.add_neuron_population(
            "BVCPop", self.BVCCount, _NEURON, _LIF_PARAMS, _LIF_VARS
        )
        self.OVCPop = self.model.add_neuron_population(
            "OVCPop", self.OVCCount, _NEURON, _LIF_PARAMS, _LIF_VARS
        )

        pwbPre,  pwbPost  = self._buildPWToGFTC("PWb")
        pwoPre,  pwoPost  = self._buildPWToGFTC("PWo")
        hdPre,   hdPost   = self._buildHDCToGFTC("HDCToGFTC")
        vcPre,   vcPost   = self._buildGFTCToVC("GFTCToVC")

        self.PWbToGFTC = self._addSynapse("PWbToGFTC", self.PWbPop, self.PWbGFTC, 1.5)
        self.PWbToGFTC.post_target_var = "IPW"
        self.PWbToGFTC.set_sparse_connections(pre_indices=pwbPre, post_indices=pwbPost)

        self.PWoToGFTC = self._addSynapse("PWoToGFTC", self.PWoPop, self.PWoGFTC, 1.5)
        self.PWoToGFTC.post_target_var = "IPW"
        self.PWoToGFTC.set_sparse_connections(pre_indices=pwoPre, post_indices=pwoPost)

        self.HDCToPWbGFTC = self._addSynapse("HDCToPWbGFTC", self.HDCPop, self.PWbGFTC, 1.5)
        self.HDCToPWbGFTC.post_target_var = "IHD"
        self.HDCToPWbGFTC.set_sparse_connections(pre_indices=hdPre, post_indices=hdPost)

        self.HDCToPWoGFTC = self._addSynapse("HDCToPWoGFTC", self.HDCPop, self.PWoGFTC, 1.5)
        self.HDCToPWoGFTC.post_target_var = "IHD"
        self.HDCToPWoGFTC.set_sparse_connections(pre_indices=hdPre, post_indices=hdPost)

        self.PWbGFTCToBVC = self._addSynapse("PWbGFTCToBVC", self.PWbGFTC, self.BVCPop, 1.5)
        self.PWbGFTCToBVC.set_sparse_connections(pre_indices=vcPre, post_indices=vcPost)

        self.PWoGFTCToOVC = self._addSynapse("PWoGFTCToOVC", self.PWoGFTC, self.OVCPop, 1.5)
        self.PWoGFTCToOVC.set_sparse_connections(pre_indices=vcPre, post_indices=vcPost)

        self.PWbGFTC.spike_recording_enabled = True
        self.BVCPop.spike_recording_enabled  = True
        self.OVCPop.spike_recording_enabled  = True

        print("! Building model")
        self.model.build()
        print("! Loading model onto device")
        self.model.load(num_recording_timesteps=DURATION)
        print("! Model ready")

    def _addSynapse(self, name, source, target, weight):
        return self.model.add_synapse_population(
            pop_name=name,
            matrix_type="SPARSE",
            source=source,
            target=target,
            weight_update_init=pygenn.init_weight_update(
                "StaticPulse", {}, {"g": float(weight)}
            ),
            postsynaptic_init=pygenn.init_postsynaptic(
                "ExpCurr", {"tau": 5.0}
            )
        )

    def _buildPWToGFTC(self, variant):
        """Row fan-out: each PW cell -> its HDCCount heading copies."""
        prePath  = os.path.join(CACHE_PATH, f"{variant}_PWtoGFTC_pre.npy")
        postPath = os.path.join(CACHE_PATH, f"{variant}_PWtoGFTC_post.npy")
        if os.path.exists(prePath) and os.path.exists(postPath):
            print(f"    - Loading cached {variant} PW->GFTC connectivity")
            return self._load(prePath).tolist(), self._load(postPath).tolist()

        pre, post = [], []
        for ego in range(self.PWbCount):
            for k in range(self.HDCCount):
                pre.append(ego)
                post.append(ego * self.HDCCount + k)

        pre, post = numpy.array(pre), numpy.array(post)
        assert pre.max()  < self.PWbCount,     "PW->GFTC pre index out of range"
        assert post.max() < self.PWbGFTCCount, "PW->GFTC post index out of range"
        self._save(prePath, pre)
        self._save(postPath, post)
        return pre.tolist(), post.tolist()

    def _buildHDCToGFTC(self, variant):
        prePath  = os.path.join(CACHE_PATH, f"{variant}_HDCtoGFTC_pre.npy")
        postPath = os.path.join(CACHE_PATH, f"{variant}_HDCtoGFTC_post.npy")
        if os.path.exists(prePath) and os.path.exists(postPath):
            print(f"    - Loading cached {variant} HDC->GFTC connectivity")
            return self._load(prePath).tolist(), self._load(postPath).tolist()

        pre, post = [], []
        for ego in range(self.PWbCount):
            for k in range(self.HDCCount):
                pre.append(k)
                post.append(ego * self.HDCCount + k)

        pre, post = numpy.array(pre), numpy.array(post)
        assert pre.max()  < self.HDCCount,     "HDC->GFTC pre index out of range"
        assert post.max() < self.PWbGFTCCount, "HDC->GFTC post index out of range"
        self._save(prePath, pre)
        self._save(postPath, post)
        return pre.tolist(), post.tolist()

    def _buildGFTCToVC(self, variant):
        prePath  = os.path.join(CACHE_PATH, f"{variant}_GFTCtoVC_pre.npy")
        postPath = os.path.join(CACHE_PATH, f"{variant}_GFTCtoVC_post.npy")
        if os.path.exists(prePath) and os.path.exists(postPath):
            print(f"    - Loading cached {variant} GFTC->VC connectivity")
            return self._load(prePath).tolist(), self._load(postPath).tolist()

        pre, post = [], []
        for dist in range(DISTANCE_BINS):
            for phi_e in range(EGOCENTRIC_BEARING_BINS):
                ego = dist * EGOCENTRIC_BEARING_BINS + phi_e
                for k in range(self.HDCCount):
                    g = ego * self.HDCCount + k
                    phi_a = (phi_e + k) % ALLOCENTRIC_BEARING_BINS
                    a = dist * ALLOCENTRIC_BEARING_BINS + phi_a
                    pre.append(g)
                    post.append(a)

        pre, post = numpy.array(pre), numpy.array(post)
        assert pre.max()  < self.PWbGFTCCount, "GFTC->VC pre index out of range"
        assert post.max() < self.BVCCount,     "GFTC->VC post index out of range"
        self._save(prePath, pre)
        self._save(postPath, post)
        return pre.tolist(), post.tolist()

    def _initHDPopCoords(self):
        return numpy.linspace(
            0.0, 2 * numpy.pi * (1 - 1 / self.HDCCount), self.HDCCount
        )

    def _initEgocentricCoords(self):
        dCentres = numpy.linspace(0.15, LIDAR_RANGE, DISTANCE_BINS)
        phiCentres = numpy.linspace(
            0.0, 2 * numpy.pi * (1 - 1 / EGOCENTRIC_BEARING_BINS), EGOCENTRIC_BEARING_BINS
        )
        dd, pp = numpy.meshgrid(dCentres, phiCentres, indexing="ij")
        return numpy.stack([dd.ravel(), pp.ravel()], axis=1)

    def _injectEgocentric(self, pop, coords, d, phi, sigma = 0.25, hitCurrent = 4.0):
        radii  = coords[:, 0]
        thetas = coords[:, 1]

        dSquared = (radii**2 + d**2) - (2.0 * radii * d * numpy.cos(thetas - phi))

        kernel = hitCurrent * numpy.exp(-dSquared / (2.0 * sigma**2))

        pop.vars["Iext"].pull_from_device()
        # if summing external current, rather than just reassigning, it appears that membrane voltage appears to be
        # more noisy
        # - reassignment, rather than simulation, produces a cleaner membrane voltage.
        pop.vars["Iext"].view[:] += kernel
        numpy.clip(
            a = pop.vars["Iext"].view[:],
            a_min = 0.0,
            a_max = CURRENT_CLAMP,
            out = pop.vars["Iext"].view[:]
        )
        pop.vars["Iext"].push_to_device()

    def injectIntoPWb(self, d, phi):
        self._injectEgocentric(self.PWbPop, self._pwbCoords, d, phi)

    def injectIntoPWo(self, d, phi):
        self._injectEgocentric(self.PWoPop, self._pwoCoords, d, phi)

    def setHDInput(self, heading_rad, scale=50.0):
        kappa = 7.0
        rates = numpy.exp(
            kappa * (numpy.cos(self._hdCoords - heading_rad) - 1.0)
        ).astype(numpy.float32)
        self.HDCPop.vars["Iext"].pull_from_device()
        self.HDCPop.vars["Iext"].view[:] = rates * scale
        numpy.clip(self.HDCPop.vars["Iext"].view, 0.0, CURRENT_CLAMP,
                   out=self.HDCPop.vars["Iext"].view)
        self.HDCPop.vars["Iext"].push_to_device()

    def step(self):
        self.model.step_time()

    def readVoltage(self, pop):
        pop.vars["V"].pull_from_device()
        return numpy.maximum(
            numpy.array(pop.vars["V"].view, dtype=numpy.float32) - (-65.0), 0.0
        )

    def _load(self, filePath):
        return numpy.load(filePath)

    def _save(self, filePath, data):
        numpy.save(filePath, data)


if __name__ == "__main__":
    print("! Initialising HESCC model")
    model = HESCC()
    print(f"  PWb={model.PWbCount}  GFTC={model.PWbGFTCCount}  "
          f"HDC={model.HDCCount}  BVC={model.BVCCount}")
    print([a for a in dir(model.HDCToPWbGFTC) if "target" in a.lower()])

    for _ in range(500):
        model.injectIntoPWb(d=1.0, phi=0.0)
        model.setHDInput(0.0)
        model.step()

    print("PWb max:", model.readVoltage(model.PWbPop).max())
    print("HDC max:", model.readVoltage(model.HDCPop).max())
    print("GFTC V max:", numpy.array(model.PWbGFTC.vars["V"].view).max())
    print("BVC max:", model.readVoltage(model.BVCPop).max())