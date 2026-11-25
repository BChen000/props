/* boxtrace: path-traces the static set of a box scene once, as a 2x-size G-buffer for compositor.py.
 *
 *   gcc -O3 -march=native -fopenmp -o boxtrace boxtrace.c -lm      (tracers.build() does this)
 *   ./boxtrace scene.txt out/g        -> out/g_D.f32 key light, _A.f32 sky + one-bounce light, _O.f32 reflections
 *                                        and fog, _Z.f32 depth, _N.f32 normals, _I.u8 object ids, _preview.ppm
 *
 * scene.txt (written by look.write_scene_header + look.write_boxes):
 *   res W H | cam pos fwd right up tan(fovy/2) shiftx shifty | light dir angle(rad) rgb | sky zenith horizon
 *   floor rgb | fog start dist | bg top bottom glow glowx glowy glowrad vignette exposure | samples key ambient
 *   box min max rotz pivot albedo gloss rough oid      (up to 128 boxes; rotz turns the box about z at pivot)
 * Sampling is seeded per pixel, so a scene always renders to the same bytes on the same machine.
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdint.h>

typedef struct {
  double mn[3], mx[3], rot, piv[3], c, s, alb[3], gloss, rough;
  int oid;
} Box;

static int W = 0, H = 0, NS = 16, NA = 16, NB = 0;
static double cpos[3], cf[3], cr[3], cu[3], th, shx, shy;
static double L[3], Lang, Lc[3];
static double skyZ[3], skyH[3], flo[3];
static double fogS, fogD;
static double bgT[3], bgB[3], bgG[3], gpx, gpy, grad, vig, expo;
static Box bx[128];
static double EskyUp[3];
static double Lb1[3], Lb2[3];

static inline double dot3(const double *a, const double *b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
static inline void nrm3(double *a) {
  double l = sqrt(dot3(a, a));
  a[0] /= l; a[1] /= l; a[2] /= l;
}
static inline void cross3(const double *a, const double *b, double *o) {
  o[0] = a[1] * b[2] - a[2] * b[1];
  o[1] = a[2] * b[0] - a[0] * b[2];
  o[2] = a[0] * b[1] - a[1] * b[0];
}

static inline int hitbox(const Box *b, const double *o, const double *d, double tmax, double *tout, double *nout) {
  double ol[3], dl[3];
  if (b->rot != 0.0) {
    double ox = o[0] - b->piv[0], oy = o[1] - b->piv[1];
    ol[0] = b->c * ox + b->s * oy;
    ol[1] = -b->s * ox + b->c * oy;
    ol[2] = o[2] - b->piv[2];
    dl[0] = b->c * d[0] + b->s * d[1];
    dl[1] = -b->s * d[0] + b->c * d[1];
    dl[2] = d[2];
  } else {
    ol[0] = o[0]; ol[1] = o[1]; ol[2] = o[2];
    dl[0] = d[0]; dl[1] = d[1]; dl[2] = d[2];
  }
  double t0 = 1e-7, t1 = tmax, sg = 0;
  int ax = -1;
  for (int k = 0; k < 3; k++) {
    double dk = dl[k];
    if (fabs(dk) < 1e-12) dk = dk < 0 ? -1e-12 : 1e-12;
    double inv = 1.0 / dk;
    double ta = (b->mn[k] - ol[k]) * inv, tb = (b->mx[k] - ol[k]) * inv;
    double sa = -1;
    if (ta > tb) { double tmp = ta; ta = tb; tb = tmp; sa = 1; }
    if (ta > t0) { t0 = ta; ax = k; sg = sa; }
    if (tb < t1) t1 = tb;
    if (t0 > t1) return 0;
  }
  if (ax < 0) return 0;
  *tout = t0;
  if (nout) {
    double nl[3] = {0, 0, 0};
    nl[ax] = sg;
    if (b->rot != 0.0) {
      nout[0] = b->c * nl[0] - b->s * nl[1];
      nout[1] = b->s * nl[0] + b->c * nl[1];
      nout[2] = nl[2];
    } else {
      nout[0] = nl[0]; nout[1] = nl[1]; nout[2] = nl[2];
    }
  }
  return 1;
}

static int trace(const double *o, const double *d, double tmax, double *t, double *n, int *id) {
  double best = tmax, bn[3] = {0, 0, 0};
  int bi = -2;
  for (int i = 0; i < NB; i++) {
    double tt, nn[3];
    if (hitbox(&bx[i], o, d, best, &tt, nn)) {
      if (tt < best) { best = tt; bi = i; bn[0] = nn[0]; bn[1] = nn[1]; bn[2] = nn[2]; }
    }
  }
  if (d[1] < -1e-9) {
    double tt = -o[1] / d[1];
    if (tt > 1e-7 && tt < best) { best = tt; bi = -1; bn[0] = 0; bn[1] = 1; bn[2] = 0; }
  }
  if (bi == -2) return 0;
  *t = best; *id = bi;
  n[0] = bn[0]; n[1] = bn[1]; n[2] = bn[2];
  return 1;
}

static int occluded(const double *o, const double *d) {
  for (int i = 0; i < NB; i++) {
    double tt;
    if (hitbox(&bx[i], o, d, 1e30, &tt, NULL)) return 1;
  }
  return 0;
}

static inline uint32_t hsh(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
  return x;
}
static inline double rnd(uint32_t *s) {
  *s = hsh(*s + 0x9e3779b9U);
  return (*s >> 8) * (1.0 / 16777216.0);
}

static void skyL(const double *w, double *out) {
  double h = w[1];
  if (h < 0) h = 0;
  double t = sqrt(h);
  for (int k = 0; k < 3; k++) out[k] = skyH[k] * (1 - t) + skyZ[k] * t;
}

static void background(double sx, double sy, double *out) {
  double t = sy < 0 ? 0 : (sy > 1 ? 1 : sy);
  t = t * t * (3 - 2 * t);
  double dx = sx - gpx, dy = (sy - gpy) * ((double)H / W);
  double g = exp(-(dx * dx + dy * dy) / (grad * grad));
  for (int k = 0; k < 3; k++) out[k] = bgT[k] * (1 - t) + bgB[k] * t + bgG[k] * g;
}

static double vigf(double sx, double sy) {
  double dx = (sx - 0.5), dy = (sy - 0.5) * ((double)H / W) * 0.62;
  return 1.0 - vig * (dx * dx + dy * dy) * 2.2;
}

static double tm(double x) {
  x *= expo;
  double y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);
  if (y < 0) y = 0;
  if (y > 1) y = 1;
  return y <= 0.0031308 ? 12.92 * y : 1.055 * pow(y, 1 / 2.4) - 0.055;
}

static void bounce_radiance(const double *p, const double *n, int id, double *out) {
  double o[3] = {p[0] + n[0] * 1e-4, p[1] + n[1] * 1e-4, p[2] + n[2] * 1e-4};
  double v = occluded(o, L) ? 0.0 : 1.0;
  if (id == -1) {
    for (int k = 0; k < 3; k++) out[k] = flo[k] / M_PI * (Lc[k] * L[1] * v + EskyUp[k]);
  } else {
    double ndl = dot3(n, L);
    if (ndl < 0) ndl = 0;
    double sk = (0.5 + 0.5 * n[1]) * 0.75;
    for (int k = 0; k < 3; k++) out[k] = bx[id].alb[k] / M_PI * (Lc[k] * ndl * v + EskyUp[k] * sk);
  }
}

int main(int argc, char **argv) {
  if (argc < 3) { fprintf(stderr, "usage: static scene.txt outprefix\n"); return 1; }
  FILE *f = fopen(argv[1], "r");
  char key[64];
  while (fscanf(f, "%63s", key) == 1) {
    if (!strcmp(key, "res")) { if (fscanf(f, "%d %d", &W, &H) != 2) return 2; }
    else if (!strcmp(key, "cam")) {
      for (int k = 0; k < 3; k++) if (fscanf(f, "%lf", &cpos[k]) != 1) return 2;
      for (int k = 0; k < 3; k++) if (fscanf(f, "%lf", &cf[k]) != 1) return 2;
      for (int k = 0; k < 3; k++) if (fscanf(f, "%lf", &cr[k]) != 1) return 2;
      for (int k = 0; k < 3; k++) if (fscanf(f, "%lf", &cu[k]) != 1) return 2;
      if (fscanf(f, "%lf %lf %lf", &th, &shx, &shy) != 3) return 2;
    } else if (!strcmp(key, "light")) {
      if (fscanf(f, "%lf %lf %lf %lf %lf %lf %lf", &L[0], &L[1], &L[2], &Lang, &Lc[0], &Lc[1], &Lc[2]) != 7) return 2;
    } else if (!strcmp(key, "sky")) {
      if (fscanf(f, "%lf %lf %lf %lf %lf %lf", &skyZ[0], &skyZ[1], &skyZ[2], &skyH[0], &skyH[1], &skyH[2]) != 6) return 2;
    } else if (!strcmp(key, "floor")) {
      if (fscanf(f, "%lf %lf %lf", &flo[0], &flo[1], &flo[2]) != 3) return 2;
    } else if (!strcmp(key, "fog")) {
      if (fscanf(f, "%lf %lf", &fogS, &fogD) != 2) return 2;
    } else if (!strcmp(key, "bg")) {
      if (fscanf(f, "%lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf", &bgT[0], &bgT[1], &bgT[2], &bgB[0], &bgB[1],
                 &bgB[2], &bgG[0], &bgG[1], &bgG[2], &gpx, &gpy, &grad, &vig, &expo) != 14) return 2;
    } else if (!strcmp(key, "samples")) {
      if (fscanf(f, "%d %d", &NS, &NA) != 2) return 2;
    } else if (!strcmp(key, "box")) {
      Box *b = &bx[NB++];
      double oid;
      if (fscanf(f, "%lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf", &b->mn[0], &b->mn[1], &b->mn[2],
                 &b->mx[0], &b->mx[1], &b->mx[2], &b->rot, &b->piv[0], &b->piv[1], &b->piv[2], &b->alb[0], &b->alb[1],
                 &b->alb[2], &b->gloss, &b->rough, &oid) != 16) return 2;
      b->oid = (int)oid;
      b->c = cos(b->rot);
      b->s = sin(b->rot);
    }
  }
  fclose(f);

  {
    double acc[3] = {0, 0, 0};
    int n = 0;
    for (int i = 0; i < 200; i++)
      for (int j = 0; j < 400; j++) {
        double ct = (i + 0.5) / 200.0, st = sqrt(1 - ct * ct), ph = 2 * M_PI * (j + 0.5) / 400.0;
        double w[3] = {st * cos(ph), ct, st * sin(ph)}, c[3];
        skyL(w, c);
        for (int k = 0; k < 3; k++) acc[k] += c[k] * ct;
        n++;
      }
    for (int k = 0; k < 3; k++) EskyUp[k] = acc[k] / n * 2 * M_PI;
  }
  {
    double t[3] = {1, 0, 0};
    if (fabs(L[0]) > 0.9) { t[0] = 0; t[1] = 1; }
    cross3(L, t, Lb1); nrm3(Lb1);
    cross3(L, Lb1, Lb2);
  }

  size_t NP = (size_t)W * H;
  float *bD = calloc(NP * 3, 4), *bA = calloc(NP * 3, 4), *bO = calloc(NP * 3, 4), *bZ = calloc(NP, 4),
        *bN = calloc(NP * 3, 4);
  uint8_t *bI = calloc(NP, 1), *pv = calloc(NP * 3, 1);
  int ms = (int)round(sqrt((double)NS)), ma = (int)round(sqrt((double)NA));
  NS = ms * ms; NA = ma * ma;
  double cosA = cos(Lang);
  double asp = (double)W / H;

#pragma omp parallel for schedule(dynamic, 2)
  for (int py = 0; py < H; py++) {
    for (int px = 0; px < W; px++) {
      size_t ix = (size_t)py * W + px;
      uint32_t seed = hsh((uint32_t)ix * 2654435761U + 12345U);
      double nx = (px + 0.5) / W * 2 - 1 + shx, ny = 1 - (py + 0.5) / H * 2 + shy;
      double d[3];
      for (int k = 0; k < 3; k++) d[k] = cf[k] + nx * th * asp * cr[k] + ny * th * cu[k];
      nrm3(d);
      double sx = (px + 0.5) / W, sy = (py + 0.5) / H;
      double Bc[3];
      background(sx, sy, Bc);
      double t, n[3];
      int id;
      double Dc[3] = {0, 0, 0}, Ac[3] = {0, 0, 0}, Oc[3] = {0, 0, 0};
      if (!trace(cpos, d, 1e30, &t, n, &id)) {
        for (int k = 0; k < 3; k++) Oc[k] = Bc[k];
        bZ[ix] = 1e30f;
        bI[ix] = 255;
      } else {
        double p[3] = {cpos[0] + d[0] * t, cpos[1] + d[1] * t, cpos[2] + d[2] * t};
        double alb[3], gloss = 0, rough = 0.5;
        int oid;
        if (id == -1) { alb[0] = flo[0]; alb[1] = flo[1]; alb[2] = flo[2]; oid = 0; }
        else {
          for (int k = 0; k < 3; k++) alb[k] = bx[id].alb[k];
          gloss = bx[id].gloss; rough = bx[id].rough; oid = bx[id].oid;
        }
        double o[3] = {p[0] + n[0] * 2e-4, p[1] + n[1] * 2e-4, p[2] + n[2] * 2e-4};
        double ndl = dot3(n, L);
        double V = 0;
        if (ndl > 0) {
          for (int i = 0; i < NS; i++) {
            double u = (i % ms + rnd(&seed)) / ms;
            double v = (i / ms + rnd(&seed)) / ms;
            double ct = 1 - u * (1 - cosA), st = sqrt(1 - ct * ct), ph = 2 * M_PI * v;
            double w[3];
            for (int k = 0; k < 3; k++) w[k] = L[k] * ct + Lb1[k] * st * cos(ph) + Lb2[k] * st * sin(ph);
            if (!occluded(o, w)) V += 1;
          }
          V /= NS;
        } else ndl = 0;
        double ndv = -dot3(n, d);
        if (ndv < 0) ndv = 0;
        double F = 0.04 + 0.96 * pow(1 - ndv, 5);
        double hv[3] = {L[0] - d[0], L[1] - d[1], L[2] - d[2]};
        nrm3(hv);
        double ndh = dot3(n, hv);
        if (ndh < 0) ndh = 0;
        double pe = 2.0 / (rough * rough) - 2.0;
        double specL = gloss * F * (pe + 8) / (8 * M_PI) * pow(ndh, pe) * ndl * V;
        for (int k = 0; k < 3; k++) Dc[k] = alb[k] / M_PI * Lc[k] * ndl * V + specL * Lc[k];

        double tb[3] = {1, 0, 0};
        if (fabs(n[0]) > 0.9) { tb[0] = 0; tb[1] = 1; }
        double b1[3], b2[3];
        cross3(n, tb, b1); nrm3(b1);
        cross3(n, b1, b2);
        double acc[3] = {0, 0, 0};
        for (int i = 0; i < NA; i++) {
          double u = (i % ma + rnd(&seed)) / ma, v = (i / ma + rnd(&seed)) / ma;
          double rr = sqrt(u), ph = 2 * M_PI * v, z = sqrt(1 - u);
          double w[3];
          for (int k = 0; k < 3; k++) w[k] = n[k] * z + b1[k] * rr * cos(ph) + b2[k] * rr * sin(ph);
          double t2, n2[3];
          int id2;
          double c[3];
          if (!trace(o, w, 1e30, &t2, n2, &id2)) skyL(w, c);
          else {
            double q[3] = {o[0] + w[0] * t2, o[1] + w[1] * t2, o[2] + w[2] * t2};
            bounce_radiance(q, n2, id2, c);
          }
          for (int k = 0; k < 3; k++) acc[k] += c[k];
        }
        for (int k = 0; k < 3; k++) Ac[k] = alb[k] * acc[k] / NA;

        if (gloss > 0) {
          double r[3];
          double dn = dot3(d, n);
          for (int k = 0; k < 3; k++) r[k] = d[k] - 2 * dn * n[k];
          double c[3];
          if (r[1] >= 0) skyL(r, c);
          else for (int k = 0; k < 3; k++) c[k] = flo[k] / M_PI * (Lc[k] * L[1] + EskyUp[k]);
          for (int k = 0; k < 3; k++) Oc[k] = gloss * F * c[k];
        }
        double fg = t > fogS ? 1 - exp(-(t - fogS) / fogD) : 0;
        for (int k = 0; k < 3; k++) {
          Dc[k] *= 1 - fg;
          Ac[k] *= 1 - fg;
          Oc[k] = Oc[k] * (1 - fg) + fg * Bc[k];
        }
        bZ[ix] = (float)t;
        bI[ix] = (uint8_t)oid;
        for (int k = 0; k < 3; k++) bN[ix * 3 + k] = (float)n[k];
      }
      for (int k = 0; k < 3; k++) {
        bD[ix * 3 + k] = (float)Dc[k];
        bA[ix * 3 + k] = (float)Ac[k];
        bO[ix * 3 + k] = (float)Oc[k];
      }
      double vg = vigf(sx, sy);
      for (int k = 0; k < 3; k++) {
        double c = (Dc[k] + Ac[k] + Oc[k]) * vg;
        int v = (int)(tm(c) * 255 + 0.5);
        pv[ix * 3 + k] = (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
      }
    }
  }

  char fn[1024];
#define DUMP(buf, sz, name) \
  snprintf(fn, sizeof fn, "%s_%s", argv[2], name); \
  f = fopen(fn, "wb"); fwrite(buf, 1, sz, f); fclose(f);
  DUMP(bD, NP * 12, "D.f32");
  DUMP(bA, NP * 12, "A.f32");
  DUMP(bO, NP * 12, "O.f32");
  DUMP(bZ, NP * 4, "Z.f32");
  DUMP(bN, NP * 12, "N.f32");
  DUMP(bI, NP, "I.u8");
  snprintf(fn, sizeof fn, "%s_preview.ppm", argv[2]);
  f = fopen(fn, "wb");
  fprintf(f, "P6\n%d %d\n255\n", W, H);
  fwrite(pv, 1, NP * 3, f);
  fclose(f);
  return 0;
}
