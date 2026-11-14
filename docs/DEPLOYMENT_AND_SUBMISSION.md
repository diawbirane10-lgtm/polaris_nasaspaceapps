# Publish POLARIS and submit to NASA Space Apps

## Hosting decision: Vercel now, not Azure / GoDaddy

A fully functional FastAPI app with a static HTML client requires one public HTTPS origin. Vercel works with the included `vercel.json`. Azure App Service or Cloud Run could work but needs more setup and billing verification. GoDaddy offers branding/domain only, not scientifically meaningful features; postpone domain registration until after submission.

## Publish the source on GitHub

1. Create a **new public** repository named `polaris-spaceapps-2026` under your personal GitHub account. Do not copy POLARIS into an unrelated existing repo.
2. Extract the latest POLARIS zip, open a terminal at its root, and run:

```bash
git init
git add .
git commit -m "NASA Space Apps 2026: POLARIS v0.5"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/polaris-spaceapps-2026.git
git push -u origin main
```

3. Confirm public access to README, `data/nasa`, `docs/`, tests, and `LICENSE`. The archived original NASA rasters and NAIF kernels are not included: download URLs and SHA256s enable reproduction.

## Vercel (the shortest deployment path)

1. In https://vercel.com/new select the GitHub repo and import it.
2. Root directory: repository root. Framework: Other (or allow detection if Vercel recognizes Python). Do **not** select a frontend-only subdirectory.
3. The included `vercel.json` builds `api/index.py` as an @vercel/python function and `public/` as static files.
4. Deploy and test these routes:
  - `/` HTML landing page
  - `/api/health`
  - `/api/nasa-sites`
  - `/api/nasa-reference/connecting_ridge`
  - `/api/replan?site=connecting_ridge&start=2026-11-14T00:00Z&hours=24&delay=48`
  - `/api/science-sources`
  - `/api/spice-validation`
5. Check button interactions, Moon Trek imagery, smartphone layout and APIs on the live domain.

## NASA submission

Submission page is on your NASA Space Apps **team's Project tab**, not on GitHub. Add the project description, open-source repo, live preview, explicit NASA datasets and source credits, a screenshot and a short demo/video or slides according to the current guide. Current official close: Sunday 15 November 2026 at 23:59 local time; local organizers may set an earlier presentation time.

## Minimum honesty / scientific disclosure

- SPICE verifies Sun/Earth geometry for sampled cases only.
- 6 km local horizon is *not* a long-range visibility estimate; optimistic upper-bound for direct Earth line of sight.
- Moon Trek WMTS maps are historic/aggregate context layers, **not date-specific observations**.
- Live custom-coordinate calculations are geometric-horizon only.
- Power/SoC system is an illustrative fixed-parameter engineering model, no verified thermal or radio system.
- See `data/analysis/spice_crosscheck_2026-11-14.json` for comparison metrics and NAIF kernel hashes.
