#include "definitions.h"

struct MergedNeuronUpdateGroup0
 {
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    
}
;
struct MergedNeuronUpdateGroup1
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    uint32_t* __restrict recordSpk;
    
}
;
struct MergedNeuronUpdateGroup2
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
struct MergedNeuronUpdateGroup3
 {
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    uint32_t* __restrict recordSpk;
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
void pushMergedNeuronUpdateGroup0ToDevice(unsigned int idx, float* RefracTime, float* V, float* outPostInSyn0, float* outPostInSyn1, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronUpdateGroup0[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup0[idx].V = V;
    mergedNeuronUpdateGroup0[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup0[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup0[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronUpdateGroup1 mergedNeuronUpdateGroup1[2];
void pushMergedNeuronUpdateGroup1ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0, uint32_t* recordSpk) {
    mergedNeuronUpdateGroup1[idx].Iext = Iext;
    mergedNeuronUpdateGroup1[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup1[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup1[idx].V = V;
    mergedNeuronUpdateGroup1[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup1[idx].recordSpk = recordSpk;
}
static MergedNeuronUpdateGroup2 mergedNeuronUpdateGroup2[3];
void pushMergedNeuronUpdateGroup2ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t numNeurons) {
    mergedNeuronUpdateGroup2[idx].Iext = Iext;
    mergedNeuronUpdateGroup2[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup2[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup2[idx].V = V;
    mergedNeuronUpdateGroup2[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup2[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronUpdateGroup2[idx].numNeurons = numNeurons;
}
static MergedNeuronUpdateGroup3 mergedNeuronUpdateGroup3[1];
void pushMergedNeuronUpdateGroup3ToDevice(unsigned int idx, float* RefracTime, float* V, float* outPostInSyn0, float* outPostInSyn1, uint32_t* recordSpk, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronUpdateGroup3[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup3[idx].V = V;
    mergedNeuronUpdateGroup3[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup3[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronUpdateGroup3[idx].recordSpk = recordSpk;
    mergedNeuronUpdateGroup3[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup3[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronSpikeQueueUpdateGroup0 mergedNeuronSpikeQueueUpdateGroup0[5];
void pushMergedNeuronSpikeQueueUpdateGroup0ToDevice(unsigned int idx, uint32_t* spkCntSynSpike0) {
    mergedNeuronSpikeQueueUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
}
void updateNeurons(float t, unsigned int recordingTimestep) {
     {
        // merged neuron spike queue update group 0
        for(unsigned int g = 0; g < 5; g++) {
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
            
            for(unsigned int i = 0; i < (15552u); i++) {
                float _IPW = 0.000000000e+00f;
                float _IHD = 0.000000000e+00f;
                float _lV = group->V[i];
                float _lRefracTime = group->RefracTime[i];
                 {
                    // postsynaptic model 0
                    float linSyn = group->outPostInSyn0[i];
                    _IHD += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn0[i] = linSyn;
                }
                 {
                    // postsynaptic model 1
                    float linSyn = group->outPostInSyn1[i];
                    _IPW += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn1[i] = linSyn;
                }
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                if(_lRefracTime > 0.0f)
                 {
                    _lRefracTime -= 5.000000000e-01f;
                }
                else
                 {
                    float _drive = (1.000000000e+02f) * _IPW * _IHD;
                    float _dV = (-(_lV - (-6.500000000e+01f)) + _drive) / (2.000000000e+01f);
                    _lV += _dV * 5.000000000e-01f;
                }
                
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                    // spike reset code
                    _lV = (-6.500000000e+01f);
                    _lRefracTime = (2.000000000e+00f);
                }
                group->V[i] = _lV;
                group->RefracTime[i] = _lRefracTime;
            }
        }
    }
     {
        // merged neuron update group 1
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronUpdateGroup1[g]; 
            const unsigned int numRecordingWords = ((432u) + 31) / 32;
            std::fill_n(&group->recordSpk[recordingTimestep * numRecordingWords], numRecordingWords, 0);
            
            for(unsigned int i = 0; i < (432u); i++) {
                float Isyn = 0;
                float _lV = group->V[i];
                float _lIinh = group->Iinh[i];
                float _lRefracTime = group->RefracTime[i];
                float _lIext = group->Iext[i];
                 {
                    // postsynaptic model 0
                    float linSyn = group->outPostInSyn0[i];
                    Isyn += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn0[i] = linSyn;
                }
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                if(_lRefracTime > 0.0f)
                 {
                    _lRefracTime -= 5.000000000e-01f;
                }
                else
                 {
                    float _dV = (-(_lV - (-6.500000000e+01f)) + Isyn + (0.000000000e+00f) + _lIext - _lIinh) / (2.000000000e+01f);
                    _lV += _dV * 5.000000000e-01f;
                    _lIinh -= (_lIinh / (1.000000000e+02f)) * 5.000000000e-01f;
                    _lIext = 0.0f;
                }
                
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                    group->recordSpk[(recordingTimestep * numRecordingWords) + (i / 32)] |= (1 << (i % 32));
                    // spike reset code
                    _lV = (-6.500000000e+01f);
                    _lRefracTime = (2.000000000e+00f);
                }
                group->V[i] = _lV;
                group->Iinh[i] = _lIinh;
                group->RefracTime[i] = _lRefracTime;
                group->Iext[i] = _lIext;
            }
        }
    }
     {
        // merged neuron update group 2
        for(unsigned int g = 0; g < 3; g++) {
            const auto *group = &mergedNeuronUpdateGroup2[g]; 
            
            for(unsigned int i = 0; i < group->numNeurons; i++) {
                float Isyn = 0;
                float _lV = group->V[i];
                float _lIinh = group->Iinh[i];
                float _lRefracTime = group->RefracTime[i];
                float _lIext = group->Iext[i];
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                if(_lRefracTime > 0.0f)
                 {
                    _lRefracTime -= 5.000000000e-01f;
                }
                else
                 {
                    float _dV = (-(_lV - (-6.500000000e+01f)) + Isyn + (0.000000000e+00f) + _lIext - _lIinh) / (2.000000000e+01f);
                    _lV += _dV * 5.000000000e-01f;
                    _lIinh -= (_lIinh / (1.000000000e+02f)) * 5.000000000e-01f;
                    _lIext = 0.0f;
                }
                
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                    // spike reset code
                    _lV = (-6.500000000e+01f);
                    _lRefracTime = (2.000000000e+00f);
                }
                group->V[i] = _lV;
                group->Iinh[i] = _lIinh;
                group->RefracTime[i] = _lRefracTime;
                group->Iext[i] = _lIext;
            }
        }
    }
     {
        // merged neuron update group 3
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronUpdateGroup3[g]; 
            const unsigned int numRecordingWords = ((15552u) + 31) / 32;
            std::fill_n(&group->recordSpk[recordingTimestep * numRecordingWords], numRecordingWords, 0);
            
            for(unsigned int i = 0; i < (15552u); i++) {
                float _IPW = 0.000000000e+00f;
                float _IHD = 0.000000000e+00f;
                float _lV = group->V[i];
                float _lRefracTime = group->RefracTime[i];
                 {
                    // postsynaptic model 0
                    float linSyn = group->outPostInSyn0[i];
                    _IHD += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn0[i] = linSyn;
                }
                 {
                    // postsynaptic model 1
                    float linSyn = group->outPostInSyn1[i];
                    _IPW += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn1[i] = linSyn;
                }
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                if(_lRefracTime > 0.0f)
                 {
                    _lRefracTime -= 5.000000000e-01f;
                }
                else
                 {
                    float _drive = (1.000000000e+02f) * _IPW * _IHD;
                    float _dV = (-(_lV - (-6.500000000e+01f)) + _drive) / (2.000000000e+01f);
                    _lV += _dV * 5.000000000e-01f;
                }
                
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                    group->recordSpk[(recordingTimestep * numRecordingWords) + (i / 32)] |= (1 << (i % 32));
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                    // spike reset code
                    _lV = (-6.500000000e+01f);
                    _lRefracTime = (2.000000000e+00f);
                }
                group->V[i] = _lV;
                group->RefracTime[i] = _lRefracTime;
            }
        }
    }
}
