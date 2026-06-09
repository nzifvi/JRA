#include "definitions.h"

struct MergedSynapseDendriticDelayUpdateGroup0
 {
    uint32_t* __restrict denDelayPtr;
    
}
;
struct MergedPresynapticUpdateGroup0
 {
    uint32_t* __restrict ind;
    float* __restrict outPost;
    uint32_t* __restrict rowLength;
    uint32_t* __restrict srcSpk;
    uint32_t* __restrict srcSpkCnt;
    
}
;
struct MergedPresynapticUpdateGroup1
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
static MergedSynapseDendriticDelayUpdateGroup0 mergedSynapseDendriticDelayUpdateGroup0[1];
void pushMergedSynapseDendriticDelayUpdateGroup0ToDevice(unsigned int idx, uint32_t* denDelayPtr) {
    mergedSynapseDendriticDelayUpdateGroup0[idx].denDelayPtr = denDelayPtr;
}
static MergedPresynapticUpdateGroup0 mergedPresynapticUpdateGroup0[1];
void pushMergedPresynapticUpdateGroup0ToDevice(unsigned int idx, uint32_t* ind, float* outPost, uint32_t* rowLength, uint32_t* srcSpk, uint32_t* srcSpkCnt) {
    mergedPresynapticUpdateGroup0[idx].ind = ind;
    mergedPresynapticUpdateGroup0[idx].outPost = outPost;
    mergedPresynapticUpdateGroup0[idx].rowLength = rowLength;
    mergedPresynapticUpdateGroup0[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup0[idx].srcSpkCnt = srcSpkCnt;
}
static MergedPresynapticUpdateGroup1 mergedPresynapticUpdateGroup1[1];
void pushMergedPresynapticUpdateGroup1ToDevice(unsigned int idx, uint8_t* d, float* denDelay, uint32_t* denDelayPtr, float* g, uint32_t* ind, uint32_t* rowLength, uint32_t* srcSpk, uint32_t* srcSpkCnt) {
    mergedPresynapticUpdateGroup1[idx].d = d;
    mergedPresynapticUpdateGroup1[idx].denDelay = denDelay;
    mergedPresynapticUpdateGroup1[idx].denDelayPtr = denDelayPtr;
    mergedPresynapticUpdateGroup1[idx].g = g;
    mergedPresynapticUpdateGroup1[idx].ind = ind;
    mergedPresynapticUpdateGroup1[idx].rowLength = rowLength;
    mergedPresynapticUpdateGroup1[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup1[idx].srcSpkCnt = srcSpkCnt;
}
void updateSynapses(float t) {
    // merged synapse dendritic delay update group 0
    for(unsigned int g = 0; g < 1; g++) {
        const auto *group = &mergedSynapseDendriticDelayUpdateGroup0[g]; 
        *group->denDelayPtr = (*group->denDelayPtr + 1) % 2;
    }
     {
        // merged presynaptic update group 0
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedPresynapticUpdateGroup0[g]; 
            
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
        // merged presynaptic update group 1
        for(unsigned int g = 0; g < 1; g++) {
            const auto *group = &mergedPresynapticUpdateGroup1[g]; 
            
            // process presynaptic events: True Spikes
            for (unsigned int i = 0; i < group->srcSpkCnt[0]; i++) {
                const unsigned int idPre = group->srcSpk[i];
                const unsigned int npost = group->rowLength[idPre];
                for (unsigned int j = 0; j < npost; j++) {
                    const uint32_t idSyn = ((uint32_t)idPre * (8u)) + j;
                    const unsigned int idPost = group->ind[idSyn];
                    group->denDelay[(((*group->denDelayPtr + group->d[idSyn]) % 2) * (5025u)) + idPost] += group->g[idSyn];
                }
            }
        }
    }
}
