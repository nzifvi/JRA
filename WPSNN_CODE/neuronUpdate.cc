#include "definitions.h"

struct MergedNeuronUpdateGroup0
 {
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict denDelayInSyn1;
    uint32_t* __restrict denDelayPtrInSyn1;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    uint32_t* __restrict recordSpk;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedNeuronUpdateGroup1
 {
    uint32_t* __restrict endSpike;
    float* __restrict spikeTimes;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t* __restrict startSpike;
    
}
;
struct MergedNeuronSpikeQueueUpdateGroup0
 {
    uint32_t* __restrict spkCntSynSpike0;
    
}
;
static MergedNeuronUpdateGroup0 mergedNeuronUpdateGroup0[1];
void pushMergedNeuronUpdateGroup0ToDevice(unsigned int idx, float* Iinh, float* RefracTime, float* V, float* denDelayInSyn1, uint32_t* denDelayPtrInSyn1, float* outPostInSyn0, float* outPostInSyn1, uint32_t* recordSpk, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronUpdateGroup0[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup0[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup0[idx].V = V;
    mergedNeuronUpdateGroup0[idx].denDelayInSyn1 = denDelayInSyn1;
    mergedNeuronUpdateGroup0[idx].denDelayPtrInSyn1 = denDelayPtrInSyn1;
    mergedNeuronUpdateGroup0[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup0[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronUpdateGroup0[idx].recordSpk = recordSpk;
    mergedNeuronUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup0[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronUpdateGroup1 mergedNeuronUpdateGroup1[1];
void pushMergedNeuronUpdateGroup1ToDevice(unsigned int idx, uint32_t* endSpike, float* spikeTimes, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t* startSpike) {
    mergedNeuronUpdateGroup1[idx].endSpike = endSpike;
    mergedNeuronUpdateGroup1[idx].spikeTimes = spikeTimes;
    mergedNeuronUpdateGroup1[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup1[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronUpdateGroup1[idx].startSpike = startSpike;
}
static MergedNeuronSpikeQueueUpdateGroup0 mergedNeuronSpikeQueueUpdateGroup0[2];
void pushMergedNeuronSpikeQueueUpdateGroup0ToDevice(unsigned int idx, uint32_t* spkCntSynSpike0) {
    mergedNeuronSpikeQueueUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
}
void pushMergedNeuronUpdate1spikeTimesToDevice(unsigned int idx, float* value) {
    mergedNeuronUpdateGroup1[idx].spikeTimes = value;
}
void updateNeurons(float t, unsigned int recordingTimestep) {
     {
        // merged neuron spike queue update group 0
        for(unsigned int g = 0; g < 2; g++) {
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
            const unsigned int numRecordingWords = ((5025u) + 31) / 32;
            std::fill_n(&group->recordSpk[recordingTimestep * numRecordingWords], numRecordingWords, 0);
            
            for(unsigned int i = 0; i < (5025u); i++) {
                float Isyn = 0;
                float _lV = group->V[i];
                float _lIinh = group->Iinh[i];
                float _lRefracTime = group->RefracTime[i];
                 {
                    // postsynaptic model 0
                    float linSyn = group->outPostInSyn0[i];
                    Isyn += (9.063462346e-01f) * linSyn;
                    linSyn *= (8.187307531e-01f);
                    group->outPostInSyn0[i] = linSyn;
                }
                 {
                    // postsynaptic model 1
                    float linSyn = group->outPostInSyn1[i];
                    float *denDelayFront = &group->denDelayInSyn1[(*group->denDelayPtrInSyn1 * (5025u)) + i];
                    linSyn += *denDelayFront;
                    *denDelayFront = 0.000000000e+00f;
                    Isyn += (9.063462346e-01f) * linSyn;
                    linSyn *= (8.187307531e-01f);
                    group->outPostInSyn1[i] = linSyn;
                }
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                if(_lRefracTime > 0.0f)
                 {
                    _lRefracTime -= 1.000000000e+00f;
                }
                else
                 {
                    float _dV = (-(_lV - (-6.500000000e+01f)) + Isyn + (0.000000000e+00f) - _lIinh) / (2.000000000e+01f);
                    _lV += _dV * 1.000000000e+00f;
                    _lIinh -= (_lIinh / (1.000000000e+02f)) * 1.000000000e+00f;
                }
                
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                    group->recordSpk[(recordingTimestep * numRecordingWords) + (i / 32)] |= (1 << (i % 32));
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                    // spike reset code
                    _lV = (-6.500000000e+01f);
                    _lRefracTime = (5.000000000e+01f);
                }
                group->V[i] = _lV;
                group->Iinh[i] = _lIinh;
                group->RefracTime[i] = _lRefracTime;
            }
        }
    }
     {
        // merged neuron update group 1
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronUpdateGroup1[g]; 
            
            for(unsigned int i = 0; i < (5025u); i++) {
                uint32_t _lstartSpike = group->startSpike[i];
                const uint32_t _lendSpike = group->endSpike[i];
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                // test for and register a true spike
                if ((_lstartSpike != _lendSpike && t >= group->spikeTimes[_lstartSpike])) {
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                    // spike reset code
                    _lstartSpike++;
                }
                group->startSpike[i] = _lstartSpike;
            }
        }
    }
}
