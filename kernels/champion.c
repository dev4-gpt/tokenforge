#include <arm_neon.h>
#include <stdint.h>
#include <dispatch/dispatch.h>

/* 2 rows at a time with 4 independent NEON accumulators per row.
   Row A & B share the x-vector loads (x is small, stays hot in L1),
   doubling in-flight FMAs per iteration to keep both FMA pipes busy.
   Per-row reduction pattern matches the previous champion exactly,
   so results are bit-identical. */
static inline void mm_block(float* restrict xout, const float* restrict x,
                            const float* restrict w, int n,
                            int start, int end)
{
    const int n16 = n & ~15;
    int i = start;

    for (; i + 1 < end; i += 2) {
        const float* wp0 = w + (size_t)i * (size_t)n;
        const float* wp1 = wp0 + (size_t)n;

        float32x4_t a0 = vdupq_n_f32(0.0f), a1 = a0, a2 = a0, a3 = a0;
        float32x4_t b0 = a0, b1 = a0, b2 = a0, b3 = a0;

        int j = 0;
        for (; j < n16; j += 16) {
            const float32x4_t x0 = vld1q_f32(x + j);
            const float32x4_t x1 = vld1q_f32(x + j + 4);
            const float32x4_t x2 = vld1q_f32(x + j + 8);
            const float32x4_t x3 = vld1q_f32(x + j + 12);

            a0 = vfmaq_f32(a0, vld1q_f32(wp0 + j),      x0);
            a1 = vfmaq_f32(a1, vld1q_f32(wp0 + j + 4),  x1);
            a2 = vfmaq_f32(a2, vld1q_f32(wp0 + j + 8),  x2);
            a3 = vfmaq_f32(a3, vld1q_f32(wp0 + j + 12), x3);

            b0 = vfmaq_f32(b0, vld1q_f32(wp1 + j),      x0);
            b1 = vfmaq_f32(b1, vld1q_f32(wp1 + j + 4),  x1);
            b2 = vfmaq_f32(b2, vld1q_f32(wp1 + j + 8),  x2);
            b3 = vfmaq_f32(b3, vld1q_f32(wp1 + j + 12), x3);
        }

        float32x4_t s0 = vaddq_f32(vaddq_f32(a0, a1), vaddq_f32(a2, a3));
        float32x4_t s1 = vaddq_f32(vaddq_f32(b0, b1), vaddq_f32(b2, b3));
        float v0 = vaddvq_f32(s0);
        float v1 = vaddvq_f32(s1);

        for (; j < n; j++) {
            const float xj = x[j];
            v0 += wp0[j] * xj;
            v1 += wp1[j] * xj;
        }
        xout[i]     = v0;
        xout[i + 1] = v1;
    }

    if (i < end) {
        const float* wp = w + (size_t)i * (size_t)n;
        float32x4_t a0 = vdupq_n_f32(0.0f), a1 = a0, a2 = a0, a3 = a0;
        int j = 0;
        for (; j < n16; j += 16) {
            a0 = vfmaq_f32(a0, vld1q_f32(wp + j),      vld1q_f32(x + j));
            a1 = vfmaq_f32(a1, vld1q_f32(wp + j + 4),  vld1q_f32(x + j + 4));
            a2 = vfmaq_f32(a2, vld1q_f32(wp + j + 8),  vld1q_f32(x + j + 8));
            a3 = vfmaq_f32(a3, vld1q_f32(wp + j + 12), vld1q_f32(x + j + 12));
        }
        float32x4_t s = vaddq_f32(vaddq_f32(a0, a1), vaddq_f32(a2, a3));
        float val = vaddvq_f32(s);
        for (; j < n; j++) val += wp[j] * x[j];
        xout[i] = val;
    }
}

typedef struct {
    float*       xout;
    const float* x;
    const float* w;
    int          n;
    int          d;
    int          chunk;
} mm_ctx;

static void mm_worker(void* p, size_t k)
{
    mm_ctx* c = (mm_ctx*)p;
    int start = (int)k * c->chunk;
    int end   = start + c->chunk;
    if (end > c->d) end = c->d;
    if (start < c->d)
        mm_block(c->xout, c->x, c->w, c->n, start, end);
}

void matmul(float* xout, float* x, float* w, int n, int d)
{
    if (d <= 0 || n <= 0) return;

    int chunk = 16;
    while (chunk < d && (d + chunk - 1) / chunk > 96) chunk *= 2;

    mm_ctx c;
    c.xout = xout; c.x = x; c.w = w; c.n = n; c.d = d; c.chunk = chunk;

    int nchunks = (d + chunk - 1) / chunk;
    dispatch_apply_f((size_t)nchunks, DISPATCH_APPLY_AUTO, &c, mm_worker);
}