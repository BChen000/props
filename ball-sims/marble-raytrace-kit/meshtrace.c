/* meshtrace: the triangle-mesh version of boxtrace (BVH, smooth normals, clear glass), plus an `env` mode that
 * lights marble positions for compositor.py.
 *
 *   gcc -O3 -march=native -fopenmp -o meshtrace meshtrace.c -lm     (tracers.build() does this)
 *   ./meshtrace scene.txt out/g       -> the boxtrace G-buffer files plus the front glass layer: _GA.f32 alpha,
 *                                        _GC.f32 premultiplied color, _GZ.f32 depth (glass behind it is baked in)
 *   ./meshtrace scene.txt env pts.f32 out.f32
 *                                     -> per point (3 float32 in): key-light visibility, 6x3 ambient cube, gap below,
 *                                        shadow reach (21 float32 out); tracers.env_query() wraps this
 *
 * scene.txt: the boxtrace header lines, then `mesh path/to/mesh.bin`:
 *   int32 ntris, int32 nmats; nmats x 7 float32 (albedo rgb, gloss, rough, oid, glass 0/1);
 *   ntris x 19 float32 (v0 v1 v2, n0 n1 n2, material index)
 * Sampling is seeded per pixel / per point, so the output is the same bytes on the same machine.
 */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdint.h>

typedef struct { float alb[3], gloss, rough; int oid, glass; } Mat;
typedef struct { float v0[3], e1[3], e2[3], n0[3], n1[3], n2[3]; int mat; } Tri;
typedef struct { float mn[3], mx[3]; int left, right, count; } Node;

static int W, H, NS = 16, NA = 16;
static double cpos[3], cf[3], cr[3], cu[3], th, shx, shy;
static double L[3], Lang, Lc[3], skyZ[3], skyH[3], flo[3], fogS, fogD;
static double bgT[3], bgB[3], bgG[3], gpx, gpy, grad, vig, expo;
static double EskyUp[3], Lb1[3], Lb2[3];
static Mat *mats;
static Tri *tris;
static int ntri, nmat;
static Node *nodes;
static int nnodes;
static int *tidx;

static inline double dot3(const double *a, const double *b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
static inline void nrm3(double *a) { double l = sqrt(dot3(a, a)); a[0] /= l; a[1] /= l; a[2] /= l; }
static inline void cross3(const double *a, const double *b, double *o) {
  o[0] = a[1] * b[2] - a[2] * b[1]; o[1] = a[2] * b[0] - a[0] * b[2]; o[2] = a[0] * b[1] - a[1] * b[0];
}
static inline uint32_t hsh(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16; return x;
}
static inline double rnd(uint32_t *s) { *s = hsh(*s + 0x9e3779b9U); return (*s >> 8) * (1.0 / 16777216.0); }

static float *cent;
static int cmp_axis;
static int cmpf(const void *a, const void *b) {
  float x = cent[*(const int *)a * 3 + cmp_axis], y = cent[*(const int *)b * 3 + cmp_axis];
  return x < y ? -1 : (x > y ? 1 : 0);
}
static int build(int start, int count) {
  int ni = nnodes++;
  Node *n = &nodes[ni];
  for (int k = 0; k < 3; k++) { n->mn[k] = 1e30f; n->mx[k] = -1e30f; }
  float cmn[3] = {1e30f, 1e30f, 1e30f}, cmx[3] = {-1e30f, -1e30f, -1e30f};
  for (int i = start; i < start + count; i++) {
    Tri *t = &tris[tidx[i]];
    for (int k = 0; k < 3; k++) {
      float a = t->v0[k], b = t->v0[k] + t->e1[k], c = t->v0[k] + t->e2[k];
      float lo = fminf(a, fminf(b, c)), hi = fmaxf(a, fmaxf(b, c));
      if (lo < n->mn[k]) n->mn[k] = lo;
      if (hi > n->mx[k]) n->mx[k] = hi;
      float cc = cent[tidx[i] * 3 + k];
      if (cc < cmn[k]) cmn[k] = cc;
      if (cc > cmx[k]) cmx[k] = cc;
    }
  }
  if (count <= 4) { n->left = start; n->count = count; return ni; }
  int ax = 0;
  for (int k = 1; k < 3; k++) if (cmx[k] - cmn[k] > cmx[ax] - cmn[ax]) ax = k;
  cmp_axis = ax;
  qsort(tidx + start, count, sizeof(int), cmpf);
  int half = count / 2;
  n->count = 0;
  int l = build(start, half);
  int r = build(start + half, count - half);
  nodes[ni].left = l;
  nodes[ni].right = r;
  return ni;
}

typedef struct { double t, u, v; int tri; } Hit;

static inline int box_hit(const Node *n, const double *o, const double *inv, double tmax) {
  double t0 = 0, t1 = tmax;
  for (int k = 0; k < 3; k++) {
    double a = (n->mn[k] - o[k]) * inv[k], b = (n->mx[k] - o[k]) * inv[k];
    if (a > b) { double c = a; a = b; b = c; }
    if (a > t0) t0 = a;
    if (b < t1) t1 = b;
    if (t0 > t1) return 0;
  }
  return 1;
}

static int bvh_trace(const double *o, const double *d, double tmax, int skipglass, int anyhit, Hit *h) {
  double inv[3];
  for (int k = 0; k < 3; k++) inv[k] = 1.0 / (fabs(d[k]) < 1e-12 ? (d[k] < 0 ? -1e-12 : 1e-12) : d[k]);
  int stack[96], sp = 0, found = 0;
  stack[sp++] = 0;
  double best = tmax;
  while (sp) {
    const Node *n = &nodes[stack[--sp]];
    if (!box_hit(n, o, inv, best)) continue;
    if (n->count) {
      for (int i = n->left; i < n->left + n->count; i++) {
        const Tri *t = &tris[tidx[i]];
        if (skipglass && mats[t->mat].glass) continue;
        double e1[3] = {t->e1[0], t->e1[1], t->e1[2]}, e2[3] = {t->e2[0], t->e2[1], t->e2[2]};
        double p[3];
        cross3(d, e2, p);
        double det = dot3(e1, p);
        if (fabs(det) < 1e-12) continue;
        double id = 1.0 / det;
        double tv[3] = {o[0] - t->v0[0], o[1] - t->v0[1], o[2] - t->v0[2]};
        double u = dot3(tv, p) * id;
        if (u < 0 || u > 1) continue;
        double q[3];
        cross3(tv, e1, q);
        double v = dot3(d, q) * id;
        if (v < 0 || u + v > 1) continue;
        double tt = dot3(e2, q) * id;
        if (tt > 1e-5 && tt < best) {
          best = tt;
          found = 1;
          h->t = tt; h->u = u; h->v = v; h->tri = tidx[i];
          if (anyhit) return 1;
        }
      }
    } else {
      stack[sp++] = n->right;
      stack[sp++] = n->left;
    }
  }
  return found;
}


typedef struct { double t, n[3], ng[3]; int mat; int floor; } SHit;

static int trace(const double *o, const double *d, int skipglass, SHit *s) {
  Hit h;
  double best = 1e30;
  int got = 0;
  if (bvh_trace(o, d, 1e30, skipglass, 0, &h)) {
    best = h.t;
    got = 1;
    const Tri *t = &tris[h.tri];
    double w = 1 - h.u - h.v;
    for (int k = 0; k < 3; k++) s->n[k] = w * t->n0[k] + h.u * t->n1[k] + h.v * t->n2[k];
    nrm3(s->n);
    double e1[3] = {t->e1[0], t->e1[1], t->e1[2]}, e2[3] = {t->e2[0], t->e2[1], t->e2[2]};
    cross3(e1, e2, s->ng);
    nrm3(s->ng);
    if (dot3(s->ng, d) > 0) for (int k = 0; k < 3; k++) s->ng[k] = -s->ng[k];
    if (dot3(s->n, s->ng) < 0) for (int k = 0; k < 3; k++) s->n[k] = -s->n[k];
    if (dot3(s->n, d) > 0) for (int k = 0; k < 3; k++) s->n[k] = s->ng[k];
    s->mat = t->mat;
    s->floor = 0;
    s->t = h.t;
  }
  if (d[1] < -1e-9) {
    double tt = -o[1] / d[1];
    if (tt > 1e-6 && tt < best) {
      s->t = tt; s->n[0] = 0; s->n[1] = 1; s->n[2] = 0;
      s->ng[0] = 0; s->ng[1] = 1; s->ng[2] = 0;
      s->mat = -1; s->floor = 1; got = 1;
    }
  }
  return got;
}

static int occluded(const double *o, const double *d) {
  Hit h;
  return bvh_trace(o, d, 1e30, 1, 1, &h);
}

static void skyL(const double *w, double *out) {
  double h = w[1] < 0 ? 0 : w[1];
  double t = sqrt(h);
  for (int k = 0; k < 3; k++) out[k] = skyH[k] * (1 - t) + skyZ[k] * t;
}
static void background(double sx, double sy, double *out) {
  double t = sy < 0 ? 0 : (sy > 1 ? 1 : sy);
  t = t * t * (3 - 2 * t);
  double dx = sx - gpx, dy = (sy - gpy) * (1920.0 / 1080.0);
  double g = exp(-(dx * dx + dy * dy) / (grad * grad));
  for (int k = 0; k < 3; k++) out[k] = bgT[k] * (1 - t) + bgB[k] * t + bgG[k] * g;
}
static double vigf(double sx, double sy) {
  double dx = sx - 0.5, dy = (sy - 0.5) * (1920.0 / 1080.0) * 0.62;
  return 1.0 - vig * (dx * dx + dy * dy) * 2.2;
}
static double tm(double x) {
  x *= expo;
  double y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);
  y = y < 0 ? 0 : (y > 1 ? 1 : y);
  return y <= 0.0031308 ? 12.92 * y : 1.055 * pow(y, 1 / 2.4) - 0.055;
}

static void mat_of(const SHit *s, double *alb, double *gloss, double *rough, int *oid) {
  if (s->floor) { for (int k = 0; k < 3; k++) alb[k] = flo[k]; *gloss = 0; *rough = 0.5; *oid = 0; return; }
  const Mat *m = &mats[s->mat];
  for (int k = 0; k < 3; k++) alb[k] = m->alb[k];
  *gloss = m->gloss; *rough = m->rough; *oid = m->oid;
}

static int sphere_block(const double *o, const double *d, const double *c, double r) {
  double oc[3] = {o[0] - c[0], o[1] - c[1], o[2] - c[2]};
  double b = dot3(oc, d), cc = dot3(oc, oc) - r * r, disc = b * b - cc;
  if (disc <= 0) return 0;
  return -b - sqrt(disc) > 1e-4;
}

static void bounce_rad(const double *q, const SHit *s, const double *sph, double *out) {
  double o[3] = {q[0] + s->ng[0] * 1e-3, q[1] + s->ng[1] * 1e-3, q[2] + s->ng[2] * 1e-3};
  double v = occluded(o, L) ? 0.0 : 1.0;
  if (sph && v > 0 && sphere_block(o, L, sph, 1.0)) v = 0;
  double alb[3], gl, ro;
  int oid;
  mat_of(s, alb, &gl, &ro, &oid);
  double ndl = dot3(s->n, L);
  if (ndl < 0) ndl = 0;
  double sk = s->floor ? 1.0 : (0.5 + 0.5 * s->n[1]) * 0.8;
  for (int k = 0; k < 3; k++) out[k] = alb[k] / M_PI * (Lc[k] * ndl * v + EskyUp[k] * sk);
}

static void cone_dir(int i, int ms, uint32_t *seed, double *w) {
  double u = (i % ms + rnd(seed)) / ms, v = (i / ms + rnd(seed)) / ms;
  double ct = 1 - u * (1 - cos(Lang)), st = sqrt(1 - ct * ct), ph = 2 * M_PI * v;
  for (int k = 0; k < 3; k++) w[k] = L[k] * ct + Lb1[k] * st * cos(ph) + Lb2[k] * st * sin(ph);
}

static void shade(const double *p, const double *d, const SHit *s, uint32_t *seed, int ms, int ma, double *Dc,
                  double *Ac, double *Oc) {
  double alb[3], gloss, rough;
  int oid;
  mat_of(s, alb, &gloss, &rough, &oid);
  double o[3] = {p[0] + s->ng[0] * 2e-4, p[1] + s->ng[1] * 2e-4, p[2] + s->ng[2] * 2e-4};
  const double *n = s->n;
  double ndl = dot3(n, L), V = 0;
  if (ndl > 0 && dot3(s->ng, L) > -0.05) {
    for (int i = 0; i < ms * ms; i++) {
      double w[3];
      cone_dir(i, ms, seed, w);
      if (!occluded(o, w)) V += 1;
    }
    V /= ms * ms;
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
  int na = ma * ma;
  for (int i = 0; i < na; i++) {
    double u = (i % ma + rnd(seed)) / ma, v = (i / ma + rnd(seed)) / ma;
    double rr = sqrt(u), ph = 2 * M_PI * v, z = sqrt(1 - u);
    double w[3];
    for (int k = 0; k < 3; k++) w[k] = n[k] * z + b1[k] * rr * cos(ph) + b2[k] * rr * sin(ph);
    if (dot3(w, s->ng) < 0) for (int k = 0; k < 3; k++) w[k] -= 2 * dot3(w, s->ng) * s->ng[k];
    SHit s2;
    double c[3];
    if (!trace(o, w, 1, &s2)) skyL(w, c);
    else {
      double q[3] = {o[0] + w[0] * s2.t, o[1] + w[1] * s2.t, o[2] + w[2] * s2.t};
      bounce_rad(q, &s2, NULL, c);
    }
    for (int k = 0; k < 3; k++) acc[k] += c[k];
  }
  for (int k = 0; k < 3; k++) Ac[k] = alb[k] * acc[k] / na;
  for (int k = 0; k < 3; k++) Oc[k] = 0;
  if (gloss > 0) {
    double r[3], dn = dot3(d, n), c[3];
    for (int k = 0; k < 3; k++) r[k] = d[k] - 2 * dn * n[k];
    if (r[1] >= 0) skyL(r, c);
    else for (int k = 0; k < 3; k++) c[k] = flo[k] / M_PI * (Lc[k] * L[1] + EskyUp[k]);
    for (int k = 0; k < 3; k++) Oc[k] = gloss * F * c[k];
  }
}

static void glass_layer(const double *d, const SHit *s, double *col, double *alpha) {
  double ndv = fabs(dot3(s->n, d));
  double F = 0.04 + 0.96 * pow(1 - ndv, 5);
  double r[3], dn = dot3(d, s->n), c[3];
  for (int k = 0; k < 3; k++) r[k] = d[k] - 2 * dn * s->n[k];
  if (r[1] >= 0) skyL(r, c);
  else for (int k = 0; k < 3; k++) c[k] = flo[k] / M_PI * (Lc[k] * L[1] + EskyUp[k]);
  double a = 0.035 + 0.8 * F;
  if (a > 0.85) a = 0.85;
  double tint[3] = {0.55, 0.62, 0.72};
  for (int k = 0; k < 3; k++) col[k] = F * c[k] * 1.1 + 0.035 * tint[k];
  *alpha = a;
}

static void load_mesh(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { fprintf(stderr, "no mesh %s\n", path); exit(3); }
  if (fread(&ntri, 4, 1, f) != 1 || fread(&nmat, 4, 1, f) != 1) exit(3);
  float *mb = malloc(nmat * 7 * 4);
  if (fread(mb, 4, nmat * 7, f) != (size_t)nmat * 7) exit(3);
  mats = calloc(nmat, sizeof(Mat));
  for (int i = 0; i < nmat; i++) {
    for (int k = 0; k < 3; k++) mats[i].alb[k] = mb[i * 7 + k];
    mats[i].gloss = mb[i * 7 + 3]; mats[i].rough = mb[i * 7 + 4];
    mats[i].oid = (int)mb[i * 7 + 5]; mats[i].glass = mb[i * 7 + 6] > 0.5;
  }
  float *tb = malloc((size_t)ntri * 19 * 4);
  if (fread(tb, 4, (size_t)ntri * 19, f) != (size_t)ntri * 19) exit(3);
  fclose(f);
  tris = calloc(ntri, sizeof(Tri));
  cent = malloc((size_t)ntri * 3 * 4);
  for (int i = 0; i < ntri; i++) {
    float *q = tb + (size_t)i * 19;
    Tri *t = &tris[i];
    for (int k = 0; k < 3; k++) {
      t->v0[k] = q[k]; t->e1[k] = q[3 + k] - q[k]; t->e2[k] = q[6 + k] - q[k];
      t->n0[k] = q[9 + k]; t->n1[k] = q[12 + k]; t->n2[k] = q[15 + k];
      cent[i * 3 + k] = (q[k] + q[3 + k] + q[6 + k]) / 3;
    }
    t->mat = (int)q[18];
  }
  tidx = malloc(ntri * sizeof(int));
  for (int i = 0; i < ntri; i++) tidx[i] = i;
  nodes = calloc(2 * ntri + 8, sizeof(Node));
  nnodes = 0;
  build(0, ntri);
}

int main(int argc, char **argv) {
  if (argc < 3) return 1;
  FILE *f = fopen(argv[1], "r");
  char key[256], meshp[1024] = "";
  while (fscanf(f, "%255s", key) == 1) {
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
    } else if (!strcmp(key, "mesh")) {
      if (fscanf(f, "%1023s", meshp) != 1) return 2;
    }
  }
  fclose(f);
  load_mesh(meshp);
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
    double t[3] = {1, 0, 0};
    if (fabs(L[0]) > 0.9) { t[0] = 0; t[1] = 1; }
    cross3(L, t, Lb1); nrm3(Lb1);
    cross3(L, Lb1, Lb2);
  }
  int ms = (int)round(sqrt((double)NS)), ma = (int)round(sqrt((double)NA));

  if (!strcmp(argv[2], "env")) {
    FILE *pf = fopen(argv[3], "rb");
    fseek(pf, 0, SEEK_END);
    long nb = ftell(pf);
    fseek(pf, 0, SEEK_SET);
    int np = nb / 12;
    float *pts = malloc(nb);
    if (fread(pts, 1, nb, pf) != (size_t)nb) return 4;
    fclose(pf);
    float *out = calloc((size_t)np * 21, 4);
    double dirs[96][3];
    for (int i = 0; i < 96; i++) {
      double ii = i + 0.5, phi = acos(1 - 2 * ii / 96), tt = M_PI * (1 + sqrt(5.0)) * ii;
      dirs[i][0] = cos(tt) * sin(phi); dirs[i][1] = cos(phi); dirs[i][2] = sin(tt) * sin(phi);
    }
    double axes[6][3] = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
#pragma omp parallel for schedule(dynamic, 8)
    for (int pi = 0; pi < np; pi++) {
      double c[3] = {pts[pi * 3], pts[pi * 3 + 1], pts[pi * 3 + 2]};
      uint32_t seed = hsh(pi * 7919 + 17);
      int vis = 0;
      for (int i = 0; i < 36; i++) {
        double w[3];
        cone_dir(i, 6, &seed, w);
        if (!occluded(c, w)) vis++;
      }
      double cube[6][3] = {{0}};
      for (int i = 0; i < 96; i++) {
        SHit s;
        double rad[3];
        if (!trace(c, dirs[i], 1, &s)) skyL(dirs[i], rad);
        else {
          double q[3] = {c[0] + dirs[i][0] * s.t, c[1] + dirs[i][1] * s.t, c[2] + dirs[i][2] * s.t};
          bounce_rad(q, &s, c, rad);
        }
        for (int a = 0; a < 6; a++) {
          double wgt = dot3(dirs[i], axes[a]);
          if (wgt > 0) for (int k = 0; k < 3; k++) cube[a][k] += rad[k] * wgt * (4 * M_PI / 96);
        }
      }
      SHit s;
      double down[3] = {0, -1, 0};
      double gap = trace(c, down, 1, &s) ? s.t - 1.0 : 99.0;
      double reach = 0;
      double nL[3] = {-L[0], -L[1], -L[2]};
      double offs[5][3] = {{0, 0, 0}, {Lb1[0], Lb1[1], Lb1[2]}, {-Lb1[0], -Lb1[1], -Lb1[2]}, {Lb2[0], Lb2[1], Lb2[2]},
                           {-Lb2[0], -Lb2[1], -Lb2[2]}};
      for (int i = 0; i < 5; i++) {
        double o[3] = {c[0] + offs[i][0] * 0.98, c[1] + offs[i][1] * 0.98, c[2] + offs[i][2] * 0.98};
        double tt = trace(o, nL, 1, &s) ? s.t : 10.0;
        if (tt > reach) reach = tt;
      }
      reach = fmin(10.0, reach + 0.6);
      float *q = out + (size_t)pi * 21;
      q[0] = vis / 36.0f;
      for (int a = 0; a < 6; a++) for (int k = 0; k < 3; k++) q[1 + a * 3 + k] = (float)cube[a][k];
      q[19] = (float)gap;
      q[20] = (float)reach;
    }
    FILE *of = fopen(argv[4], "wb");
    fwrite(out, 4, (size_t)np * 21, of);
    fclose(of);
    return 0;
  }

  size_t NP = (size_t)W * H;
  float *bD = calloc(NP * 3, 4), *bA = calloc(NP * 3, 4), *bO = calloc(NP * 3, 4), *bZ = calloc(NP, 4),
        *bN = calloc(NP * 3, 4), *gA = calloc(NP, 4), *gC = calloc(NP * 3, 4), *gZ = calloc(NP, 4);
  uint8_t *bI = calloc(NP, 1), *pv = calloc(NP * 3, 1);
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
      double sx = (px + 0.5) / W, sy = (py + 0.5) / H, Bc[3];
      background(sx, sy, Bc);
      double o[3] = {cpos[0], cpos[1], cpos[2]};
      double ttot = 0, trans = 1, baked[3] = {0, 0, 0};
      double Dc[3] = {0, 0, 0}, Ac[3] = {0, 0, 0}, Oc[3] = {0, 0, 0};
      int first = 1, done = 0;
      gZ[ix] = 1e30f;
      for (int it = 0; it < 8 && !done; it++) {
        SHit s;
        if (!trace(o, d, 0, &s)) {
          for (int k = 0; k < 3; k++) Oc[k] = Bc[k];
          bZ[ix] = 1e30f;
          bI[ix] = 255;
          done = 1;
          break;
        }
        double p[3] = {o[0] + d[0] * s.t, o[1] + d[1] * s.t, o[2] + d[2] * s.t};
        if (!s.floor && mats[s.mat].glass) {
          double gc[3], ga;
          glass_layer(d, &s, gc, &ga);
          if (first) {
            gA[ix] = (float)ga;
            for (int k = 0; k < 3; k++) gC[ix * 3 + k] = (float)gc[k];
            gZ[ix] = (float)(ttot + s.t);
            first = 0;
          } else {
            for (int k = 0; k < 3; k++) baked[k] += trans * gc[k];
            trans *= 1 - ga;
          }
          ttot += s.t + 1e-3;
          for (int k = 0; k < 3; k++) o[k] = p[k] + d[k] * 1e-3;
          continue;
        }
        shade(p, d, &s, &seed, ms, ma, Dc, Ac, Oc);
        ttot += s.t;
        double alb[3], gl, ro;
        int oid;
        mat_of(&s, alb, &gl, &ro, &oid);
        bZ[ix] = (float)ttot;
        bI[ix] = (uint8_t)oid;
        for (int k = 0; k < 3; k++) bN[ix * 3 + k] = (float)s.n[k];
        double fg = ttot > fogS ? 1 - exp(-(ttot - fogS) / fogD) : 0;
        for (int k = 0; k < 3; k++) {
          Dc[k] *= (1 - fg);
          Ac[k] *= (1 - fg);
          Oc[k] = Oc[k] * (1 - fg) + fg * Bc[k];
        }
        done = 1;
      }
      for (int k = 0; k < 3; k++) {
        Dc[k] *= trans; Ac[k] *= trans; Oc[k] = Oc[k] * trans + baked[k];
        bD[ix * 3 + k] = (float)Dc[k]; bA[ix * 3 + k] = (float)Ac[k]; bO[ix * 3 + k] = (float)Oc[k];
      }
      double vg = vigf(sx, sy);
      for (int k = 0; k < 3; k++) {
        double c = (Dc[k] + Ac[k] + Oc[k]) * (1 - gA[ix]) + gC[ix * 3 + k];
        int v = (int)(tm(c * vg) * 255 + 0.5);
        pv[ix * 3 + k] = (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
      }
    }
  }
  char fn[1024];
#define DUMP(buf, sz, name) snprintf(fn, sizeof fn, "%s_%s", argv[2], name); f = fopen(fn, "wb"); fwrite(buf, 1, sz, f); fclose(f);
  DUMP(bD, NP * 12, "D.f32");
  DUMP(bA, NP * 12, "A.f32");
  DUMP(bO, NP * 12, "O.f32");
  DUMP(bZ, NP * 4, "Z.f32");
  DUMP(bN, NP * 12, "N.f32");
  DUMP(bI, NP, "I.u8");
  DUMP(gA, NP * 4, "GA.f32");
  DUMP(gC, NP * 12, "GC.f32");
  DUMP(gZ, NP * 4, "GZ.f32");
  snprintf(fn, sizeof fn, "%s_preview.ppm", argv[2]);
  f = fopen(fn, "wb");
  fprintf(f, "P6\n%d %d\n255\n", W, H);
  fwrite(pv, 1, NP * 3, f);
  fclose(f);
  return 0;
}
