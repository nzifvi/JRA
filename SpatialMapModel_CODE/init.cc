#include "definitions.h"
struct MergedNeuronInitGroup0
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    
}
;
struct MergedNeuronInitGroup1
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t numNeurons;
    
}
;
struct MergedNeuronInitGroup2
 {
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedSynapseSparseInitGroup0
 {
    float* __restrict g;
    uint32_t* __restrict rowLength;
    uint32_t numSrcNeurons;
    uint32_t rowStride;
    
}
;
static MergedNeuronInitGroup0 mergedNeuronInitGroup0[2];
void pushMergedNeuronInitGroup0ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0) {
    mergedNeuronInitGroup0[idx].Iext = Iext;
    mergedNeuronInitGroup0[idx].Iinh = Iinh;
    mergedNeuronInitGroup0[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup0[idx].V = V;
    mergedNeuronInitGroup0[idx].outPostInSyn0 = outPostInSyn0;
}
static MergedNeuronInitGroup1 mergedNeuronInitGroup1[3];
void pushMergedNeuronInitGroup1ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t numNeurons) {
    mergedNeuronInitGroup1[idx].Iext = Iext;
    mergedNeuronInitGroup1[idx].Iinh = Iinh;
    mergedNeuronInitGroup1[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup1[idx].V = V;
    mergedNeuronInitGroup1[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup1[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronInitGroup1[idx].numNeurons = numNeurons;
}
static MergedNeuronInitGroup2 mergedNeuronInitGroup2[2];
void pushMergedNeuronInitGroup2ToDevice(unsigned int idx, float* RefracTime, float* V, float* outPostInSyn0, float* outPostInSyn1, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronInitGroup2[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup2[idx].V = V;
    mergedNeuronInitGroup2[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronInitGroup2[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronInitGroup2[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup2[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedSynapseSparseInitGroup0 mergedSynapseSparseInitGroup0[6];
void pushMergedSynapseSparseInitGroup0ToDevice(unsigned int idx, float* g, uint32_t* rowLength, uint32_t numSrcNeurons, uint32_t rowStride) {
    mergedSynapseSparseInitGroup0[idx].g = g;
    mergedSynapseSparseInitGroup0[idx].rowLength = rowLength;
    mergedSynapseSparseInitGroup0[idx].numSrcNeurons = numSrcNeurons;
    mergedSynapseSparseInitGroup0[idx].rowStride = rowStride;
}
void initializeHost() {
}
void initialize() {
    // ------------------------------------------------------------------------
    // Neuron groups
     {
        // merged neuron init group 0
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronInitGroup0[g]; 
             {
                for (unsigned int i = 0; i < ((432u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((432u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((432u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((432u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iext[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((432u)); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
        }
    }
     {
        // merged neuron init group 1
        for(unsigned int g = 0; g < 3; g++) {
            const auto *group = &mergedNeuronInitGroup1[g]; 
             {
                for (unsigned int i = 0; i < (group->numNeurons); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < (group->numNeurons); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < (group->numNeurons); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < (group->numNeurons); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iext[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < (group->numNeurons); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
        }
    }
     {
        // merged neuron init group 2
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronInitGroup2[g]; 
             {
                for (unsigned int i = 0; i < ((15552u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((15552u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((15552u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
            for (unsigned int i = 0; i < ((15552u)); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((15552u)); i++) {
                group->outPostInSyn1[i] = 0.000000000e+00f;
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
     {
        // merged sparse synapse init group 0
        for(unsigned int g = 0; g < 6; g++) {
            const auto *group = &mergedSynapseSparseInitGroup0[g]; 
            // Loop through presynaptic neurons
            for (unsigned int i = 0; i < group->numSrcNeurons; i++) {
                 {
                    for (unsigned int j = 0; j < group->rowLength[i]; j++) {
                        const unsigned int idSyn = (i * group->rowStride) + j;
                        float initVal;
                        initVal = (1.500000000e+00f);
                        group->g[idSyn] = initVal;
                    }
                }
            }
        }
    }
    // ------------------------------------------------------------------------
    // Custom sparse WU update groups
    // ------------------------------------------------------------------------
    // Custom connectivity update sparse init groups
}
