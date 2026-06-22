#include "definitions.h"

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
static MergedPresynapticUpdateGroup0 mergedPresynapticUpdateGroup0[6];
void pushMergedPresynapticUpdateGroup0ToDevice(unsigned int idx, float* g, uint32_t* ind, float* outPost, uint32_t* rowLength, uint32_t* srcSpk, uint32_t* srcSpkCnt, uint32_t rowStride) {
    mergedPresynapticUpdateGroup0[idx].g = g;
    mergedPresynapticUpdateGroup0[idx].ind = ind;
    mergedPresynapticUpdateGroup0[idx].outPost = outPost;
    mergedPresynapticUpdateGroup0[idx].rowLength = rowLength;
    mergedPresynapticUpdateGroup0[idx].srcSpk = srcSpk;
    mergedPresynapticUpdateGroup0[idx].srcSpkCnt = srcSpkCnt;
    mergedPresynapticUpdateGroup0[idx].rowStride = rowStride;
}
void updateSynapses(float t) {
     {
        // merged presynaptic update group 0
        for(unsigned int g = 0; g < 6; g++) {
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
}
