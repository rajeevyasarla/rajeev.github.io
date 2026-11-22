# rajeev.github.io

The website template is taken from [Harsh Agarwal](https://github.com/dexter1691)

## Maintaining the homepage

This is the source for https://rajeevyasarla.github.io/rajeev.github.io/.
Edit `index.html` for the biography, research, news, teaching, projects, and service.
Edit `publications.json` and matching `img/assets/reference/` entries together.
Keep the existing publication figures, demo video, and historical teaching entries.

The November 21, 2026 refresh uses the applicant's current Staff Researcher
materials and the latest supplied MAPLE v3, GeRo v2, and RoCA v3 manuscripts.
Acceptance, promotion, awards, and demo-leadership descriptions follow the
applicant's records. No live Scholar counts were inferred; CV statistics remain
explicitly dated October 30, 2026. The public CV omits referee contact details.
The applicant confirmed the news months: RoCA and WACV Area Chair selection in
July 2026, the SDAD honorable mention in September 2026, and the Staff Researcher
promotion in November 2026. News is ordered newest first. WACV 2027 is a
forthcoming Area Chair appointment, not a past event.

Build `files/CV.tex` with `files/resume.cls` using Tectonic or pdfLaTeX, then
run the read-only checks:

```bash
python3 scripts/verify_site.py
python3 -m http.server 8000
```

Preview through HTTP so the publication JSON loads. The site retains its
existing Bootstrap design; research, teaching history, service, and the existing
RoCA video are integrated without changing historical publications or assets.

GitHub Pages publishing uses the existing `main` branch. Never put credentials
in a remote URL, source file, or commit.

## MAPLE comparison demo

The homepage uses RoCA's 3-row × 2-column video format: construction obstacles,
a blocked intersection, and a left turn into traffic appear simultaneously,
with MAPLE left and DeepSight right. The video matches RoCA's 1920x1620 dimensions
and 20-second duration. Each row is one continuous excerpt retaining its
synchronized method pair, simulation timestamps, speeds, bird's-eye insets, and
2x playback. Scenario rows use different start times. These selected simulated
routes are illustrative, not aggregate benchmark evidence; incomplete DeepSight
result statuses are not classified as failures.

To reproduce it from the existing comparison exports (without overwriting assets):

```bash
python3 scripts/build_maple_grid_demo.py /path/to/visualization/MAPLE_vs_DeepSight
```

The MP4 uses H.264/yuv420p with fast-start metadata and no audio. The matching
JSON records source hashes, excerpt times, output hashes, and encoding properties.
The earlier sequential 27-second reel and its builder remain available locally
but are no longer embedded on the homepage. Original comparison recordings and
the RoCA video are unchanged.

The RoCA card explicitly describes the comparison as ORION + RoCA (left) versus
the ORION baseline without RoCA (right), following the applicant's clarification.
Both cards use a 1920x1620 comparison-frame poster; the RoCA poster is extracted
from the unchanged existing RoCA video at five seconds.
