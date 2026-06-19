#include "definitions.h"

struct MergedNeuronUpdateGroup0
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    float* __restrict outPostInSyn1;
    float* __restrict outPostInSyn2;
    uint32_t* __restrict recordSpk;
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
    float* __restrict rPreOutSynWUMPre0;
    
}
;
struct MergedNeuronUpdateGroup2
 {
    float* __restrict Iext;
    float* __restrict Iinh;
    float* __restrict RefracTime;
    float* __restrict V;
    float* __restrict outPostInSyn0;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    float TauInh;
    uint32_t numNeurons;
    
}
;
struct MergedNeuronUpdateGroup3
 {
    uint32_t* __restrict endSpike;
    float* __restrict spikeTimes;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t* __restrict startSpike;
    
}
;
struct MergedNeuronUpdateGroup4
 {
    float* __restrict firingRate;
    uint32_t* __restrict spkCntSynSpike0;
    uint32_t* __restrict spkSynSpike0;
    uint32_t numNeurons;
    
}
;
struct MergedNeuronUpdateGroup5
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
void pushMergedNeuronUpdateGroup0ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0, float* outPostInSyn1, float* outPostInSyn2, uint32_t* recordSpk, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronUpdateGroup0[idx].Iext = Iext;
    mergedNeuronUpdateGroup0[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup0[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup0[idx].V = V;
    mergedNeuronUpdateGroup0[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup0[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronUpdateGroup0[idx].outPostInSyn2 = outPostInSyn2;
    mergedNeuronUpdateGroup0[idx].recordSpk = recordSpk;
    mergedNeuronUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup0[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronUpdateGroup1 mergedNeuronUpdateGroup1[2];
void pushMergedNeuronUpdateGroup1ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* rPreOutSynWUMPre0) {
    mergedNeuronUpdateGroup1[idx].Iext = Iext;
    mergedNeuronUpdateGroup1[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup1[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup1[idx].V = V;
    mergedNeuronUpdateGroup1[idx].rPreOutSynWUMPre0 = rPreOutSynWUMPre0;
}
static MergedNeuronUpdateGroup2 mergedNeuronUpdateGroup2[2];
void pushMergedNeuronUpdateGroup2ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* outPostInSyn0, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, float TauInh, uint32_t numNeurons) {
    mergedNeuronUpdateGroup2[idx].Iext = Iext;
    mergedNeuronUpdateGroup2[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup2[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup2[idx].V = V;
    mergedNeuronUpdateGroup2[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup2[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup2[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronUpdateGroup2[idx].TauInh = TauInh;
    mergedNeuronUpdateGroup2[idx].numNeurons = numNeurons;
}
static MergedNeuronUpdateGroup3 mergedNeuronUpdateGroup3[1];
void pushMergedNeuronUpdateGroup3ToDevice(unsigned int idx, uint32_t* endSpike, float* spikeTimes, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t* startSpike) {
    mergedNeuronUpdateGroup3[idx].endSpike = endSpike;
    mergedNeuronUpdateGroup3[idx].spikeTimes = spikeTimes;
    mergedNeuronUpdateGroup3[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup3[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronUpdateGroup3[idx].startSpike = startSpike;
}
static MergedNeuronUpdateGroup4 mergedNeuronUpdateGroup4[2];
void pushMergedNeuronUpdateGroup4ToDevice(unsigned int idx, float* firingRate, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0, uint32_t numNeurons) {
    mergedNeuronUpdateGroup4[idx].firingRate = firingRate;
    mergedNeuronUpdateGroup4[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup4[idx].spkSynSpike0 = spkSynSpike0;
    mergedNeuronUpdateGroup4[idx].numNeurons = numNeurons;
}
static MergedNeuronUpdateGroup5 mergedNeuronUpdateGroup5[1];
void pushMergedNeuronUpdateGroup5ToDevice(unsigned int idx, float* Iext, float* Iinh, float* RefracTime, float* V, float* denDelayInSyn5, uint32_t* denDelayPtrInSyn5, float* outPostInSyn0, float* outPostInSyn1, float* outPostInSyn2, float* outPostInSyn3, float* outPostInSyn4, float* outPostInSyn5, float* rPostInSynWUMPost0, float* rPostInSynWUMPost1, uint32_t* recordSpk, uint32_t* spkCntSynSpike0, uint32_t* spkSynSpike0) {
    mergedNeuronUpdateGroup5[idx].Iext = Iext;
    mergedNeuronUpdateGroup5[idx].Iinh = Iinh;
    mergedNeuronUpdateGroup5[idx].RefracTime = RefracTime;
    mergedNeuronUpdateGroup5[idx].V = V;
    mergedNeuronUpdateGroup5[idx].denDelayInSyn5 = denDelayInSyn5;
    mergedNeuronUpdateGroup5[idx].denDelayPtrInSyn5 = denDelayPtrInSyn5;
    mergedNeuronUpdateGroup5[idx].outPostInSyn0 = outPostInSyn0;
    mergedNeuronUpdateGroup5[idx].outPostInSyn1 = outPostInSyn1;
    mergedNeuronUpdateGroup5[idx].outPostInSyn2 = outPostInSyn2;
    mergedNeuronUpdateGroup5[idx].outPostInSyn3 = outPostInSyn3;
    mergedNeuronUpdateGroup5[idx].outPostInSyn4 = outPostInSyn4;
    mergedNeuronUpdateGroup5[idx].outPostInSyn5 = outPostInSyn5;
    mergedNeuronUpdateGroup5[idx].rPostInSynWUMPost0 = rPostInSynWUMPost0;
    mergedNeuronUpdateGroup5[idx].rPostInSynWUMPost1 = rPostInSynWUMPost1;
    mergedNeuronUpdateGroup5[idx].recordSpk = recordSpk;
    mergedNeuronUpdateGroup5[idx].spkCntSynSpike0 = spkCntSynSpike0;
    mergedNeuronUpdateGroup5[idx].spkSynSpike0 = spkSynSpike0;
}
static MergedNeuronSpikeQueueUpdateGroup0 mergedNeuronSpikeQueueUpdateGroup0[7];
void pushMergedNeuronSpikeQueueUpdateGroup0ToDevice(unsigned int idx, uint32_t* spkCntSynSpike0) {
    mergedNeuronSpikeQueueUpdateGroup0[idx].spkCntSynSpike0 = spkCntSynSpike0;
}
void pushMergedNeuronUpdate3spikeTimesToDevice(unsigned int idx, float* value) {
    mergedNeuronUpdateGroup3[idx].spikeTimes = value;
}
void updateNeurons(float t, unsigned int recordingTimestep) {
     {
        // merged neuron spike queue update group 0
        for(unsigned int g = 0; g < 7; g++) {
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
            const unsigned int numRecordingWords = ((768u) + 31) / 32;
            std::fill_n(&group->recordSpk[recordingTimestep * numRecordingWords], numRecordingWords, 0);
            
            for(unsigned int i = 0; i < (768u); i++) {
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
                 {
                    // postsynaptic model 1
                    float linSyn = group->outPostInSyn1[i];
                    Isyn += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn1[i] = linSyn;
                }
                 {
                    // postsynaptic model 2
                    float linSyn = group->outPostInSyn2[i];
                    Isyn += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn2[i] = linSyn;
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
                    _lIinh -= (_lIinh / (5.000000000e+01f)) * 5.000000000e-01f;
                    _lIext = 0.0f;
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
                group->Iinh[i] = _lIinh;
                group->RefracTime[i] = _lRefracTime;
                group->Iext[i] = _lIext;
            }
        }
    }
     {
        // merged neuron update group 1
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronUpdateGroup1[g]; 
            
            for(unsigned int i = 0; i < (1800u); i++) {
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
                
                 {
                    // presynaptic weight update 0
                    float _lrPre = group->rPreOutSynWUMPre0[i];
                    _lrPre -= (_lrPre / (2.000000000e+01f)) * 5.000000000e-01f;
                    group->rPreOutSynWUMPre0[i] = _lrPre;
                }
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                     {
                        // presynaptic weight update 0
                        float _lrPre = group->rPreOutSynWUMPre0[i];
                        _lrPre += 1.0f;
                        group->rPreOutSynWUMPre0[i] = _lrPre;
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
        // merged neuron update group 2
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronUpdateGroup2[g]; 
            
            for(unsigned int i = 0; i < group->numNeurons; i++) {
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
                    _lIinh -= (_lIinh / group->TauInh) * 5.000000000e-01f;
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
            
            for(unsigned int i = 0; i < (40000u); i++) {
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
     {
        // merged neuron update group 4
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedNeuronUpdateGroup4[g]; 
            
            for(unsigned int i = 0; i < group->numNeurons; i++) {
                float _lfiringRate = group->firingRate[i];
                // test whether spike condition was fulfilled previously
                // calculate membrane potential
                // test for and register a true spike
                if ((standardUniformDistribution(hostRNG) < _lfiringRate * 5.000000000e-01f / 1000.0f)) {
                     {
                        group->spkSynSpike0[group->spkCntSynSpike0[0]++] = i;
                    }
                }
                group->firingRate[i] = _lfiringRate;
            }
        }
    }
     {
        // merged neuron update group 5
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedNeuronUpdateGroup5[g]; 
            const unsigned int numRecordingWords = ((40000u) + 31) / 32;
            std::fill_n(&group->recordSpk[recordingTimestep * numRecordingWords], numRecordingWords, 0);
            
            for(unsigned int i = 0; i < (40000u); i++) {
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
                 {
                    // postsynaptic model 1
                    float linSyn = group->outPostInSyn1[i];
                    Isyn += (9.876035189e-01f) * linSyn;
                    linSyn *= (9.753099120e-01f);
                    group->outPostInSyn1[i] = linSyn;
                }
                 {
                    // postsynaptic model 2
                    float linSyn = group->outPostInSyn2[i];
                    Isyn += (9.754115100e-01f) * linSyn;
                    linSyn *= (9.512294245e-01f);
                    group->outPostInSyn2[i] = linSyn;
                }
                 {
                    // postsynaptic model 3
                    float linSyn = group->outPostInSyn3[i];
                    Isyn += (9.754115100e-01f) * linSyn;
                    linSyn *= (9.512294245e-01f);
                    group->outPostInSyn3[i] = linSyn;
                }
                 {
                    // postsynaptic model 4
                    float linSyn = group->outPostInSyn4[i];
                    Isyn += (9.754115100e-01f) * linSyn;
                    linSyn *= (9.512294245e-01f);
                    group->outPostInSyn4[i] = linSyn;
                }
                 {
                    // postsynaptic model 5
                    float linSyn = group->outPostInSyn5[i];
                    float *denDelayFront = &group->denDelayInSyn5[(*group->denDelayPtrInSyn5 * (40000u)) + i];
                    linSyn += *denDelayFront;
                    *denDelayFront = 0.000000000e+00f;
                    Isyn += (9.516258196e-01f) * linSyn;
                    linSyn *= (9.048374180e-01f);
                    group->outPostInSyn5[i] = linSyn;
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
                
                 {
                    // postsynaptic weight update 0
                    float _lrPost = group->rPostInSynWUMPost0[i];
                    _lrPost -= (_lrPost / (2.000000000e+01f)) * 5.000000000e-01f;
                    group->rPostInSynWUMPost0[i] = _lrPost;
                }
                 {
                    // postsynaptic weight update 1
                    float _lrPost = group->rPostInSynWUMPost1[i];
                    _lrPost -= (_lrPost / (2.000000000e+01f)) * 5.000000000e-01f;
                    group->rPostInSynWUMPost1[i] = _lrPost;
                }
                // test for and register a true spike
                if ((_lRefracTime <= 0.0f && _lV >= (-5.000000000e+01f))) {
                     {
                        // postsynaptic weight update 0
                        float _lrPost = group->rPostInSynWUMPost0[i];
                        _lrPost += 1.0f;
                        group->rPostInSynWUMPost0[i] = _lrPost;
                    }
                     {
                        // postsynaptic weight update 1
                        float _lrPost = group->rPostInSynWUMPost1[i];
                        _lrPost += 1.0f;
                        group->rPostInSynWUMPost1[i] = _lrPost;
                    }
                    group->recordSpk[(recordingTimestep * numRecordingWords) + (i / 32)] |= (1 << (i % 32));
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
}
