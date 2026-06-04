#include "definitions.h"

struct MergedNeuronUpdateGroup0
 {
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedNeuronSpikeQueueUpdateGroup0
 {
    uint32_t* __restrict spkCntSynSpike0;
    
}
;
static MergedNeuronUpdateGroup0 mergedNeuronUpdateGroup0[1];
void pushMergedNeuronUpdateGroup0ToDevice(unsigned int idx, float* RefracTime, float* V, float* outPostInSyn0, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronUpdateGroup0[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup0[idx].V = V;
    mergedNeuronUpdateGroup0[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup0[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronSpikeQueueUpdateGroup0 mergedNeuronSpikeQueueUpdateGroup0[1];
void pushMergedNeuronSpikeQueueUpdateGroup0ToDevice(unsigned int idx, uint32_t* spkCntSynSpike0) {
    mergedNeuronSpikeQueueUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
}
void updateNeurons(float t) {
     {
        // merged neuron spike queue update group 0
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronSpikeQueueUpdateGroup0[g]; 
             {
                // spike queue update 0
                group->spkCntSynSpike0[0] = 0;
            }
        }
    }
     {
        // merged neuron update group 0
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronUpdateGroup0[g]; 
            
            for(unsigned int i = 0; i < (2u); i++) {
                float Isyn = 0;
                float _lV = group->V[i];
                float _lRefracTime = group->RefracTime[i];
                 {
                    // postsynaptic model 0
                    float linSyn = group->outPostInSyn0[i];
                    Isyn += (9.063462346e-01f) * linSyn;
                    linSyn *= (8.187307531e-01f);
                    group->outPostInSyn0[i] = linSyn;
                }
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                if(_lRefracTime <= 0.0f)
                 {
                    float _alpha = ((Isyn + (0.000000000e+00f)) * (2.000000000e+01f)) + (-6.500000000e+01f);
                    _lV = _alpha - ((9.512294245e-01f) * (_alpha - _lV));
                }
                else
                 {
                    _lRefracTime -= 1.000000000e+00f;
                }
                
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                    // spike reset code
                    _lV = (-6.500000000e+01f);
                    _lRefracTime = (5.000000000e+01f);
                }
                group->V[i] = _lV;
                group->RefracTime[i] = _lRefracTime;
            }
        }
    }
}
