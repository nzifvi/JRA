#include "definitions.h"
struct MergedNeuronInitGroup0
 {
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
static MergedNeuronInitGroup0 mergedNeuronInitGroup0[1];
void pushMergedNeuronInitGroup0ToDevice(unsigned int idx, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronInitGroup0[idx].Iinh = Iinh;
    mergedNeuronInitGroup0[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup0[idx].V = V;
    mergedNeuronInitGroup0[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronInitGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup0[idx].spkSynSpike0 = spkSynSpike0;
}
void initializeHost() {
}
void initialize() {
    // ------------------------------------------------------------------------
    // Neuron groups
     {
        // merged neuron init group 0
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronInitGroup0[g]; 
             {
                for (unsigned int i = 0; i < ((2u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((2u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((2u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((2u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
            for (unsigned int i = 0; i < ((2u)); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
        }
    }
    // ------------------------------------------------------------------------
    // Synapse groups
    // ------------------------------------------------------------------------
    // Custom update groups
    // ------------------------------------------------------------------------
    // Custom connectivity presynaptic update groups
    // ------------------------------------------------------------------------
    // Custom connectivity postsynaptic update groups
    // ------------------------------------------------------------------------
    // Custom WU update groups
    // ------------------------------------------------------------------------
    // Synapse sparse connectivity
}

void initializeSparse() {
    // ------------------------------------------------------------------------
    // Synapse groups with sparse connectivity
    // ------------------------------------------------------------------------
    // Custom sparse WU update groups
    // ------------------------------------------------------------------------
    // Custom connectivity update sparse init groups
}
