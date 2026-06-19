#include "definitions.h"

extern "C" {
// ------------------------------------------------------------------------
// global variables
// ------------------------------------------------------------------------
std::mt19937 hostRNG;
std::uniform_real_distribution<float> standardUniformDistribution(0.000000000e+00f, 1.000000000e+00f);
std::normal_distribution<float> standardNormalDistribution(0.000000000e+00f, 1.000000000e+00f);
std::exponential_distribution<float> standardExponentialDistribution(1.000000000e+00f);


// ------------------------------------------------------------------------
// timers
// ------------------------------------------------------------------------
double initTime = 0.0;
double initSparseTime = 0.0;
double neuronUpdateTime = 0.0;
double presynapticUpdateTime = 0.0;
double postsynapticUpdateTime = 0.0;
double synapseDynamicsTime = 0.0;
// ------------------------------------------------------------------------
// merged group arrays
// ------------------------------------------------------------------------
}  // extern "C"
void allocateMem() {
    // ------------------------------------------------------------------------
    // global variables
    // ------------------------------------------------------------------------
     {
        uint32_t seedData[std::mt19937::state_size];
        std::random_device seedSource;
        for(int i = 0; i < std::mt19937::state_size; i++) {
            seedData[i] = seedSource();
        }
        std::seed_seq seeds(std::begin(seedData), std::end(seedData));
        hostRNG.seed(seeds);
    }
    
    // ------------------------------------------------------------------------
    // timers
    // ------------------------------------------------------------------------
}

void freeMem() {
    // ------------------------------------------------------------------------
    // global variables
    // ------------------------------------------------------------------------
    
    // ------------------------------------------------------------------------
    // timers
    // ------------------------------------------------------------------------
}

void stepTime(unsigned long long timestep, unsigned long long numRecordingTimesteps) {
    const float t = timestep * 5.000000000e-01f;
    updateSynapses(t);
    updateNeurons(t, (unsigned int)(timestep % numRecordingTimesteps)); 
}

