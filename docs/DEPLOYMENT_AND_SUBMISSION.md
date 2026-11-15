# POLARIS — Deployment and NASA Space Apps submission

**Public home:** https://polaris-spaceapps-2026.vercel.app/  
**Seven-slide project overview:** https://polaris-spaceapps-2026.vercel.app/submission-slides.html  
**Interactive engineering demo:** https://polaris-spaceapps-2026.vercel.app/demo  
**Current source:** https://github.com/diawbirane10-lgtm/polaris_nasaspaceapps

Vercel builds `api/index.py` with the Python runtime and `public/` as static assets. The root page offers two entry points; the demo has eight navigation views. No authentication is required.

## Verify before NASA submission

1. Open the three public links in a private browsing window; no login prompt.
2. Confirm seven slides and a working arrow-key presentation; do not submit a link to the slide editor or a private drive.
3. In the live demo verify navigation, NASA/LOLA evidence, PV–battery energy calculations, Copilot recalculation, and Decision Review reports.
4. Run `python -m pytest -q` and examine GitHub Actions on the submission commit.
5. In the team's NASA Project tab, provide the public slides URL under **Project Demonstration** and the root POLARIS URL under **Project**. Complete the project summary, details, NASA sources, other software/asset credits and SI/AI disclosure.
6. Check required originality/terms statements yourself, choose **Save Progress**, then **Submit for Judging**. Saving alone is not a submission.

Deadline stated in the official project form: **15 November 2026, 23:59**, according to the registered team event's local timezone. Submission status and participation certificate must be confirmed on NASA's own site.

## Engineering validity

The demonstration provides preliminary geometry and energy feasibility, **not flight-qualified landing safety**. 6 km local skyline and six-hour observations limit precision; local Earth clearance is not a verified communications link. See [Electrical engineering model](ELECTRICAL_ENGINEERING_CONTRIBUTION.md) and [Submission summary](NASA_PROJECT_SUBMISSION_DRAFT.md).
