#include "definitions.h"
struct MergedNeuronInitGroup0
 {
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict denDelayInSyn1;
    uint32_t* __restrict denDelayPtrInSyn1;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedNeuronInitGroup1
 {
    uint32_t* __restrict endSpike;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t* __restrict startSpike;
    
}
;
static MergedNeuronInitGroup0 mergedNeuronInitGroup0[1];
void pushMergedNeuronInitGroup0ToDevice(unsigned int idx, float* Iinh, float* RefracTime, float* V, float* denDelayInSyn1, uint32_t* denDelayPtrInSyn1, float* outPostInSyn0, float* outPostInSyn1, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronInitGroup0[idx].Iinh = Iinh;
    mergedNeuronInitGroup0[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup0[idx].V = V;
    mergedNeuronInitGroup0[idx].denDelayInSyn1 = denDelayInSyn1;
    mergedNeuronInitGroup0[idx].denDelayPtrInSyn1 = denDelayPtrInSyn1;
    mergedNeuronInitGroup0[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronInitGroup0[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronInitGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup0[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronInitGroup1 mergedNeuronInitGroup1[1];
void pushMergedNeuronInitGroup1ToDevice(unsigned int idx, uint32_t* endSpike, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t* startSpike) {
    mergedNeuronInitGroup1[idx].endSpike = endSpike;
    mergedNeuronInitGroup1[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup1[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronInitGroup1[idx].startSpike = startSpike;
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
                for (unsigned int i = 0; i < ((341u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((341u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((341u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((341u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
            for (unsigned int i = 0; i < ((341u)); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((341u)); i++) {
                group->outPostInSyn1[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((341u)); i++) {
                for(unsigned int d = 0; d < 8; d++) {
                    group->denDelayInSyn1[(d * (341u)) + i] = 0.000000000e+00f;
                }
            }
            *group->denDelayPtrInSyn1 = 0;
        }
    }
     {
        // merged neuron init group 1
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronInitGroup1[g]; 
             {
                for (unsigned int i = 0; i < ((1u)); i++) {
                    uint32_t initVal;
                    initVal = (0.000000000e+00f);
                    group->startSpike[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((1u)); i++) {
                    uint32_t initVal;
                    initVal = (1.000000000e+00f);
                    group->endSpike[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((1u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
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
