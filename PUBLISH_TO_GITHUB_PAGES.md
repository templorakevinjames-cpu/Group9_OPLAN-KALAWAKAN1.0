# Publishing this to GitHub Pages

You have three files:
- `index.html` — the project page
- `downloads/OplanKalawakan.zip` — the downloadable game (source + a README.txt with run instructions)
- this file (you don't need to upload this one, it's just for you)

## Steps

1. Create a new **public** repository on GitHub (e.g. `oplan-kalawakan`).
2. Upload `index.html` and the `downloads/` folder (with the zip inside it) to the **root** of that repo — keep the folder structure exactly as-is, so the download button's link (`downloads/OplanKalawakan.zip`) keeps working.
3. On GitHub, go to **Settings → Pages**.
4. Under "Build and deployment," set **Source** to `Deploy from a branch`, branch `main`, folder `/ (root)`. Save.
5. GitHub will give you a live URL, usually `https://<your-username>.github.io/<repo-name>/` — that's the link you submit.

## Before you submit, swap the placeholders

- **Screenshots**: the three dashed boxes under "Screenshots" are placeholders. Take real screenshots of your game (main menu, gameplay, a boss fight), and either replace those `<div class="shot">` blocks with `<img>` tags, or ask me and I'll wire them in once you upload the images.
- **Developer section**: open `index.html`, find the `<!-- Add your name / team name and section here -->` comment near the bottom, and replace it with your name(s) and section.
- If you rename the zip or move it, update the `href="downloads/OplanKalawakan.zip"` link in `index.html` to match.
