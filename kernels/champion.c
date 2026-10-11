#include <arm_neon.h>
#include <dispatch/dispatch.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

static inline float dot_neon(const float* __restrict w,
                             const float* __restrict x, int n) {
    float32x4_t a0 = vdupq_n_f32(0.0f);
    float32x4_t a1 = vdupq_n_f32(0.0f);
    float32x4_t a2 = vdupq_n_f32(0.0f);
    float32x4_t a3 = vdupq_n_f32(0.0f);
    int j = 0;
    for (; j + 15 < n; j += 16) {
        a0 = vfmaq_f32(a0, vld1q_f32(w + j),      vld1q_f32(x + j));
        a1 = vfmaq_f32(a1, vld1q_f32(w + j + 4),  vld1q_f32(x + j + 4));
        a2 = vfmaq_f32(a2, vld1q_f32(w + j + 8),  vld1q_f32(x + j + 8));
        a3 = vfmaq_f32(a3, vld1q_f32(w + j + 12), vld1q_f32(x + j + 12));
    }
    a0 = vaddq_f32(a0, a1);
    a2 = vaddq_f32(a2, a3);
    a0 = vaddq_f32(a0, a2);
    float sum = vaddvq_f32(a0);
    for (; j < n; j++) sum += w[j] * x[j];
    return sum;
}

void matmul(float* xout, float* x, float* w, int n, int d) {
    if (d <= 0) return;
    if (d < 48) {
        for (int i = 0; i < d; i++)
            xout[i] = dot_neon(w + (size_t)i * n, x, n);
        return;
    }
    /* Split rows into ~2 chunks per core so GCD can load-balance. */
    const int TARGET_CHUNKS = 24;
    int nchunk = TARGET_CHUNKS;
    if (nchunk > d) nchunk = d;
    int chunk = (d + nchunk - 1) / nchunk;
    nchunk = (d + chunk - 1) / chunk;

    dispatch_apply(nchunk,
        dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0),
        ^(size_t t) {
            int start = (int)t * chunk;
            int end   = start + chunk;
            if (end > d) end = d;
            for (int i = start; i < end; i++) {
                xout[i] = dot_neon(w + (size_t)i * n, x, n);
            }
        });
}