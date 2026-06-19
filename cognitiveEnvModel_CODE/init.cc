#include "definitions.h"
struct MergedNeuronInitGroup0
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict rPreOutSynWUMPre0;
    
}
;
struct MergedNeuronInitGroup1
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    float* __restrict outPostInSyn2;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedNeuronInitGroup2
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict denDelayInSyn5;
    uint32_t* __restrict denDelayPtrInSyn5;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    float* __restrict outPostInSyn2;
    float* __restrict outPostInSyn3;
    float* __restrict outPostInSyn4;
    float* __restrict outPostInSyn5;
    float* __restrict rPostInSynWUMPost0;
    float* __restrict rPostInSynWUMPost1;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedNeuronInitGroup3
 {
    float* __restrict firingRate;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t numNeurons;
    
}
;
struct MergedNeuronInitGroup4
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t numNeurons;
    
}
;
struct MergedNeuronInitGroup5
 {
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedSynapseInitGroup0
 {
    float* __restrict g;
    
}
;
struct MergedSynapseConnectivityInitGroup0
 {
    uint32_t* __restrict ind;
    uint32_t* __restrict rowLength;
    
}
;
struct MergedSynapseSparseInitGroup0
 {
    uint32_t* __restrict colLength;
    float* __restrict g;
    uint32_t* __restrict ind;
    uint32_t* __restrict remap;
    uint32_t* __restrict rowLength;
    float constantg;
    
}
;
struct MergedSynapseSparseInitGroup1
 {
    float* __restrict g;
    uint32_t* __restrict rowLength;
    
}
;
static MergedNeuronInitGroup0 mergedNeuronInitGroup0[2];
void pushMergedNeuronInitGroup0ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* rPreOutSynWUMPre0) {
    mergedNeuronInitGroup0[idx].Iext = Iext;
    mergedNeuronInitGroup0[idx].Iinh = Iinh;
    mergedNeuronInitGroup0[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup0[idx].V = V;
    mergedNeuronInitGroup0[idx].rPreOutSynWUMPre0 = rPreOutSynWUMPre0;
}
static MergedNeuronInitGroup1 mergedNeuronInitGroup1[1];
void pushMergedNeuronInitGroup1ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0, float* outPostInSyn1, float* outPostInSyn2, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronInitGroup1[idx].Iext = Iext;
    mergedNeuronInitGroup1[idx].Iinh = Iinh;
    mergedNeuronInitGroup1[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup1[idx].V = V;
    mergedNeuronInitGroup1[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronInitGroup1[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronInitGroup1[idx].outPostInSyn2 = outPostInSyn2;
    mergedNeuronInitGroup1[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup1[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronInitGroup2 mergedNeuronInitGroup2[1];
void pushMergedNeuronInitGroup2ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* denDelayInSyn5, uint32_t* denDelayPtrInSyn5, float* outPostInSyn0, float* outPostInSyn1, float* outPostInSyn2, float* outPostInSyn3, float* outPostInSyn4, float* outPostInSyn5, float* rPostInSynWUMPost0, float* rPostInSynWUMPost1, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronInitGroup2[idx].Iext = Iext;
    mergedNeuronInitGroup2[idx].Iinh = Iinh;
    mergedNeuronInitGroup2[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup2[idx].V = V;
    mergedNeuronInitGroup2[idx].denDelayInSyn5 = denDelayInSyn5;
    mergedNeuronInitGroup2[idx].denDelayPtrInSyn5 = denDelayPtrInSyn5;
    mergedNeuronInitGroup2[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronInitGroup2[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronInitGroup2[idx].outPostInSyn2 = outPostInSyn2;
    mergedNeuronInitGroup2[idx].outPostInSyn3 = outPostInSyn3;
    mergedNeuronInitGroup2[idx].outPostInSyn4 = outPostInSyn4;
    mergedNeuronInitGroup2[idx].outPostInSyn5 = outPostInSyn5;
    mergedNeuronInitGroup2[idx].rPostInSynWUMPost0 = rPostInSynWUMPost0;
    mergedNeuronInitGroup2[idx].rPostInSynWUMPost1 = rPostInSynWUMPost1;
    mergedNeuronInitGroup2[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup2[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronInitGroup3 mergedNeuronInitGroup3[2];
void pushMergedNeuronInitGroup3ToDevice(unsigned int idx, float* firingRate, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t numNeurons) {
    mergedNeuronInitGroup3[idx].firingRate = firingRate;
    mergedNeuronInitGroup3[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup3[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronInitGroup3[idx].numNeurons = numNeurons;
}
static MergedNeuronInitGroup4 mergedNeuronInitGroup4[2];
void pushMergedNeuronInitGroup4ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t numNeurons) {
    mergedNeuronInitGroup4[idx].Iext = Iext;
    mergedNeuronInitGroup4[idx].Iinh = Iinh;
    mergedNeuronInitGroup4[idx].RefracTime = RefracTime;
    mergedNeuronInitGroup4[idx].V = V;
    mergedNeuronInitGroup4[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronInitGroup4[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup4[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronInitGroup4[idx].numNeurons = numNeurons;
}
static MergedNeuronInitGroup5 mergedNeuronInitGroup5[1];
void pushMergedNeuronInitGroup5ToDevice(unsigned int idx, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronInitGroup5[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronInitGroup5[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedSynapseInitGroup0 mergedSynapseInitGroup0[1];
void pushMergedSynapseInitGroup0ToDevice(unsigned int idx, float* g) {
    mergedSynapseInitGroup0[idx].g = g;
}
static MergedSynapseConnectivityInitGroup0 mergedSynapseConnectivityInitGroup0[1];
void pushMergedSynapseConnectivityInitGroup0ToDevice(unsigned int idx, uint32_t* ind, uint32_t* rowLength) {
    mergedSynapseConnectivityInitGroup0[idx].ind = ind;
    mergedSynapseConnectivityInitGroup0[idx].rowLength = rowLength;
}
static MergedSynapseSparseInitGroup0 mergedSynapseSparseInitGroup0[2];
void pushMergedSynapseSparseInitGroup0ToDevice(unsigned int idx, uint32_t* colLength, float* g, uint32_t* ind, uint32_t* remap, uint32_t* rowLength, float constantg) {
    mergedSynapseSparseInitGroup0[idx].colLength = colLength;
    mergedSynapseSparseInitGroup0[idx].g = g;
    mergedSynapseSparseInitGroup0[idx].ind = ind;
    mergedSynapseSparseInitGroup0[idx].remap = remap;
    mergedSynapseSparseInitGroup0[idx].rowLength = rowLength;
    mergedSynapseSparseInitGroup0[idx].constantg = constantg;
}
static MergedSynapseSparseInitGroup1 mergedSynapseSparseInitGroup1[1];
void pushMergedSynapseSparseInitGroup1ToDevice(unsigned int idx, float* g, uint32_t* rowLength) {
    mergedSynapseSparseInitGroup1[idx].g = g;
    mergedSynapseSparseInitGroup1[idx].rowLength = rowLength;
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
                for (unsigned int i = 0; i < ((1800u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((1800u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((1800u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((1800u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iext[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((1800u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->rPreOutSynWUMPre0[i] = initVal;
                }
            }
        }
    }
     {
        // merged neuron init group 1
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronInitGroup1[g]; 
             {
                for (unsigned int i = 0; i < ((768u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((768u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((768u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((768u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iext[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((768u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
            for (unsigned int i = 0; i < ((768u)); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((768u)); i++) {
                group->outPostInSyn1[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((768u)); i++) {
                group->outPostInSyn2[i] = 0.000000000e+00f;
            }
        }
    }
     {
        // merged neuron init group 2
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronInitGroup2[g]; 
             {
                for (unsigned int i = 0; i < ((40000u)); i++) {
                    float initVal;
                    initVal = (-6.500000000e+01f);
                    group->V[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((40000u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->RefracTime[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((40000u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iinh[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((40000u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->Iext[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->outPostInSyn1[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->outPostInSyn2[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->outPostInSyn3[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->outPostInSyn4[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->outPostInSyn5[i] = 0.000000000e+00f;
            }
            for (unsigned int i = 0; i < ((40000u)); i++) {
                for(unsigned int d = 0; d < 2; d++) {
                    group->denDelayInSyn5[(d * (40000u)) + i] = 0.000000000e+00f;
                }
            }
            *group->denDelayPtrInSyn5 = 0;
             {
                for (unsigned int i = 0; i < ((40000u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->rPostInSynWUMPost0[i] = initVal;
                }
            }
             {
                for (unsigned int i = 0; i < ((40000u)); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->rPostInSynWUMPost1[i] = initVal;
                }
            }
        }
    }
     {
        // merged neuron init group 3
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronInitGroup3[g]; 
             {
                for (unsigned int i = 0; i < (group->numNeurons); i++) {
                    float initVal;
                    initVal = (0.000000000e+00f);
                    group->firingRate[i] = initVal;
                }
            }
            for (unsigned int i = 0; i < (group->numNeurons); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
        }
    }
     {
        // merged neuron init group 4
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronInitGroup4[g]; 
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
            for (unsigned int i = 0; i < (group->numNeurons); i++) {
                group->outPostInSyn0[i] = 0.000000000e+00f;
            }
        }
    }
     {
        // merged neuron init group 5
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronInitGroup5[g]; 
            for (unsigned int i = 0; i < ((40000u)); i++) {
                group->spkSynSpike0[i] = 0;
            }
            group->spkCntSynSpike0[0] = 0;
        }
    }
    // ------------------------------------------------------------------------
    // Synapse groups
     {
        // merged synapse init group 0
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedSynapseInitGroup0[g]; 
            for(unsigned int i = 0; i < (75u); i++) {
                 {
                    for (unsigned int j = 0; j < (75u); j++) {
                        const unsigned int idSyn = (i * (75u)) + j;
                        float initVal;
                        initVal = (1.000000000e+00f);
                        group->g[idSyn] = initVal;
                    }
                }
            }
        }
    }
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
     {
        // merged synapse connectivity init group 0
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedSynapseConnectivityInitGroup0[g]; 
            for (unsigned int i = 0; i < (768u); i++) {
                 {
                    const unsigned int idPost = i;
                    const unsigned int idSyn = (i * (1u)) + group->rowLength[i];
                    group->ind[idSyn] = idPost;
                    group->rowLength[i]++;
                }
                ;
            }
        }
    }
}

void initializeSparse() {
    // ------------------------------------------------------------------------
    // Synapse groups with sparse connectivity
     {
        // merged sparse synapse init group 0
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedSynapseSparseInitGroup0[g]; 
            // Loop through presynaptic neurons
            for (unsigned int i = 0; i < (1800u); i++) {
                 {
                    for (unsigned int j = 0; j < group->rowLength[i]; j++) {
                        const unsigned int idSyn = (i * (200u)) + j;
                        float initVal;
                        initVal = group->constantg;
                        group->g[idSyn] = initVal;
                    }
                }
                // Loop through synapses in corresponding matrix row
                for(unsigned int j = 0; j < group->rowLength[i]; j++) {
                    // Calculate index of this synapse in the row-major matrix
                    const unsigned int rowMajorIndex = (i * (200u)) + j;
                    // Using this, lookup postsynaptic target
                    const unsigned int postIndex = group->ind[rowMajorIndex];
                    // From this calculate index of this synapse in the column-major matrix)
                    const unsigned int colMajorIndex = (postIndex * (1800u)) + group->colLength[postIndex];
                    // Increment column length corresponding to this postsynaptic neuron
                    group->colLength[postIndex]++;
                    // Add remapping entry
                    group->remap[colMajorIndex] = rowMajorIndex;
                }
            }
        }
    }
     {
        // merged sparse synapse init group 1
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedSynapseSparseInitGroup1[g]; 
            // Loop through presynaptic neurons
            for (unsigned int i = 0; i < (768u); i++) {
                 {
                    for (unsigned int j = 0; j < group->rowLength[i]; j++) {
                        const unsigned int idSyn = (i * (1u)) + j;
                        float initVal;
                        initVal = (3.000000000e+01f);
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
