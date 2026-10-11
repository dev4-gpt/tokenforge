# Public judge report

The report is already self-contained in `docs/index.html`, generated offline from the validated final run. It needs no secrets, Atlas connection, or Python server once published.

## Vercel

Published and verified: https://tokenforge-results.vercel.app. This production deployment contains the generated public report only. It was deployed as a static snapshot; future report changes require redeployment.

Import `dev4-gpt/tokenforge` from GitHub. Use repository root, framework preset **Other**, and the checked-in `vercel.json`: no build command, output directory `docs`. Deploy to production and verify the report URL in a signed-out browser. Do not add `.env` or Atlas credentials. If project-level settings override the file, set output directory to `docs` and disable the build command.

Vercel hosts this static judge report. The interactive Streamlit dashboard remains a separate app.

## GitHub Pages alternative

Repository Settings → Pages → Deploy from a branch → `main` → `/docs` → Save. The expected URL is https://dev4-gpt.github.io/tokenforge/. GitHub Pages has not been verified; Vercel is the verified submission link.

The finished visual demo is public at https://www.youtube.com/watch?v=2ZHimN2vUzo (the user approved Public visibility). Use the report link for evidence and this watch link for the video submission field.
