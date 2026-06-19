#include "definitions.h"

struct MergedSynapseDendriticDelayUpdateGroup0
 {
    uint32_t* __restrict denDelayPtr;
    
}
;
struct MergedPresynapticUpdateGroup0
 {
    float* __restrict g;
    uint32_t* __restrict ind;
    float* __restrict outPost;
    uint32_t* __restrict rowLength;
    uint32_t* __restrict srcSpk;
    uint32_t* __restrict srcSpkCnt;
    uint32_t rowStride;
    
}
;
struct MergedPresynapticUpdateGroup1
 {
    float* __restrict g;
    float* __restrict outPost;
    uint32_t* __restrict srcSpk;
    uint32_t* __restrict srcSpkCnt;
    uint32_t numTrgNeurons;
    
}
;
struct MergedPresynapticUpdateGroup2
 {
    uint8_t* __restrict d;
    float* __restrict denDelay;
    uint32_t* __restrict denDelayPtr;
    float* __restrict g;
    uint32_t* __restrict ind;
    uint32_t* __restrict rowLength;
    uint32_t* __restrict srcSpk;
    uint32_t* __restrict srcSpkCnt;
    
}
;
struct MergedPresynapticUpdateGroup3
 {
    uint32_t* __restrict ind;
    float* __restrict outPost;
    uint32_t* __restrict rowLength;
    uint32_t* __restrict srcSpk;
    uint32_t* __restrict srcSpkCnt;
    
}
;
struct MergedPostsynapticUpdateGroup0
 {
    uint32_t* __restrict colLength;
    float* __restrict g;
    float* __restrict rPost;
    float* __restrict rPre;
    uint32_t* __restrict remap;
    uint32_t* __restrict trgSpk;
    uint32_t* __restrict trgSpkCnt;
    
}
;
static MergedSynapseDendriticDelayUpdateGroup0 mergedSynapseDendriticDelayUpdateGroup0[1];
void pushMergedSynapseDendriticDelayUpdateGroup0ToDevice(unsigned int idx, uint32_t* denDelayPtr) {
    mergedSynapseDendriticDelayUpdateGroup0[idx].denDelayPtr = denDelayPtr;
}
static MergedPresynapticUpdateGroup0 mergedPresynapticUpdateGroup0[4];
void pushMergedPresynapticUpdateGroup0ToDevice(unsigned int idx, float* g, uint32_t* ind, float* outPost, uint32_t* rowLength, uint32_t* srcSpk, uint32_t* srcSpkCnt, uint32_t rowStride) {
    mergedPresynapticUpdateGroup0[idx].g = g;
    mergedPresynapticUpdateGroup0[idx].ind = ind;
    mergedPresynapticUpdateGroup0[idx].outPost = outPost;
    mergedPresynapticUpdateGroup0[idx].rowLength = rowLength;
    mergedPresynapticUpdateGroup0[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup0[idx].srcSpkCnt = srcSpkCnt;
    mergedPresynapticUpdateGroup0[idx].rowStride = rowStride;
}
static MergedPresynapticUpdateGroup1 mergedPresynapticUpdateGroup1[3];
void pushMergedPresynapticUpdateGroup1ToDevice(unsigned int idx, float* g, float* outPost, uint32_t* srcSpk, uint32_t* srcSpkCnt, uint32_t numTrgNeurons) {
    mergedPresynapticUpdateGroup1[idx].g = g;
    mergedPresynapticUpdateGroup1[idx].outPost = outPost;
    mergedPresynapticUpdateGroup1[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup1[idx].srcSpkCnt = srcSpkCnt;
    mergedPresynapticUpdateGroup1[idx].numTrgNeurons = numTrgNeurons;
}
static MergedPresynapticUpdateGroup2 mergedPresynapticUpdateGroup2[1];
void pushMergedPresynapticUpdateGroup2ToDevice(unsigned int idx, uint8_t* d, float* denDelay, uint32_t* denDelayPtr, float* g, uint32_t* ind, uint32_t* rowLength, uint32_t* srcSpk, uint32_t* srcSpkCnt) {
    mergedPresynapticUpdateGroup2[idx].d = d;
    mergedPresynapticUpdateGroup2[idx].denDelay = denDelay;
    mergedPresynapticUpdateGroup2[idx].denDelayPtr = denDelayPtr;
    mergedPresynapticUpdateGroup2[idx].g = g;
    mergedPresynapticUpdateGroup2[idx].ind = ind;
    mergedPresynapticUpdateGroup2[idx].rowLength = rowLength;
    mergedPresynapticUpdateGroup2[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup2[idx].srcSpkCnt = srcSpkCnt;
}
static MergedPresynapticUpdateGroup3 mergedPresynapticUpdateGroup3[1];
void pushMergedPresynapticUpdateGroup3ToDevice(unsigned int idx, uint32_t* ind, float* outPost, uint32_t* rowLength, uint32_t* srcSpk, uint32_t* srcSpkCnt) {
    mergedPresynapticUpdateGroup3[idx].ind = ind;
    mergedPresynapticUpdateGroup3[idx].outPost = outPost;
    mergedPresynapticUpdateGroup3[idx].rowLength = rowLength;
    mergedPresynapticUpdateGroup3[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup3[idx].srcSpkCnt = srcSpkCnt;
}
static MergedPostsynapticUpdateGroup0 mergedPostsynapticUpdateGroup0[2];
void pushMergedPostsynapticUpdateGroup0ToDevice(unsigned int idx, uint32_t* colLength, float* g, float* rPost, float* rPre, uint32_t* remap, uint32_t* trgSpk, uint32_t* trgSpkCnt) {
    mergedPostsynapticUpdateGroup0[idx].colLength = colLength;
    mergedPostsynapticUpdateGroup0[idx].g = g;
    mergedPostsynapticUpdateGroup0[idx].rPost = rPost;
    mergedPostsynapticUpdateGroup0[idx].rPre = rPre;
    mergedPostsynapticUpdateGroup0[idx].remap = remap;
    mergedPostsynapticUpdateGroup0[idx].trgSpk = trgSpk;
    mergedPostsynapticUpdateGroup0[idx].trgSpkCnt = trgSpkCnt;
}
void updateSynapses(float t) {
    // merged synapse dendritic delay update group 0
    for(unsigned int g = 0; g < 1; g++) {
        const auto *group = &mergedSynapseDendriticDelayUpdateGroup0[g]; 
        *group->denDelayPtr = (*group->denDelayPtr + 1) % 2;
    }
     {
        // merged presynaptic update group 0
        for(unsigned int g = 0; g < 4; g++) {
            const auto *group = &mergedPresynapticUpdateGroup0[g]; 
            
            // process presynaptic events: True Spikes
            for (unsigned int i = 0; i < group->srcSpkCnt[0]; i++) {
                const unsigned int idPre = group->srcSpk[i];
                const unsigned int npost = group->rowLength[idPre];
                for (unsigned int j = 0; j < npost; j++) {
                    const uint32_t idSyn = ((uint32_t)idPre * group->rowStride) + j;
                    const unsigned int idPost = group->ind[idSyn];
                    group->outPost[idPost] += group->g[idSyn];
                }
            }
        }
    }
     {
        // merged presynaptic update group 1
        for(unsigned int g = 0; g < 3; g++) {
            const auto *group = &mergedPresynapticUpdateGroup1[g]; 
            
            // process presynaptic events: True Spikes
            for (unsigned int i = 0; i < group->srcSpkCnt[0]; i++) {
                const unsigned int idPre = group->srcSpk[i];
                for (unsigned int ipost = 0; ipost < group->numTrgNeurons; ipost++) {
                    const uint32_t idSyn = ((uint32_t)idPre * group->numTrgNeurons) + ipost;
                    group->outPost[ipost] += group->g[idSyn];
                }
            }
        }
    }
     {
        // merged presynaptic update group 2
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedPresynapticUpdateGroup2[g]; 
            
            // process presynaptic events: True Spikes
            for (unsigned int i = 0; i < group->srcSpkCnt[0]; i++) {
                const unsigned int idPre = group->srcSpk[i];
                const unsigned int npost = group->rowLength[idPre];
                for (unsigned int j = 0; j < npost; j++) {
                    const uint32_t idSyn = ((uint32_t)idPre * (8u)) + j;
                    const unsigned int idPost = group->ind[idSyn];
                    group->denDelay[(((*group->denDelayPtr + group->d[idSyn]) % 2) * (40000u)) + idPost] += group->g[idSyn];
                }
            }
        }
    }
     {
        // merged presynaptic update group 3
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedPresynapticUpdateGroup3[g]; 
            
            // process presynaptic events: True Spikes
            for (unsigned int i = 0; i < group->srcSpkCnt[0]; i++) {
                const unsigned int idPre = group->srcSpk[i];
                const unsigned int npost = group->rowLength[idPre];
                for (unsigned int j = 0; j < npost; j++) {
                    const uint32_t idSyn = ((uint32_t)idPre * (1u)) + j;
                    const unsigned int idPost = group->ind[idSyn];
                    group->outPost[idPost] += (3.000000000e+02f);
                }
            }
        }
    }
     {
        // merged postsynaptic update group 0
        for(unsigned int g = 0; g < 2; g++) {
            const auto *group = &mergedPostsynapticUpdateGroup0[g]; 
            const unsigned int numSpikes = group->trgSpkCnt[0];
            for (unsigned int j = 0; j < numSpikes; j++) {
                const unsigned int spike = group->trgSpk[j];
                const unsigned int npre = group->colLength[spike];
                for (unsigned int i = 0; i < npre; i++) {
                    const unsigned int colMajorIndex = (spike * (1800u)) + i;
                    const unsigned int rowMajorIndex = group->remap[colMajorIndex];
                    const unsigned int idPre = rowMajorIndex / (200u);
                    const float _dg = (5.000000000e-03f) * group->rPost[spike] * (group->rPre[idPre] - group->rPost[spike] * group->g[rowMajorIndex]);
                    group->g[rowMajorIndex] = fmax(0.0f, fmin(group->g[rowMajorIndex] + _dg, (5.000000000e+00f)));
                }
            }
            
        }
    }
}
