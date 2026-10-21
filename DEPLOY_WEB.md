# Deploying Tip Masters as a web app

The app's web version is a static single-page site (built with `expo export --platform web`).
The backend (FastAPI + MongoDB, Bowlslink sync, logos) stays deployed on Emergent.

## 1. Deploy the backend on Emergent
1. Click **Publish** (top right) and deploy.
2. Copy the deployed URL, e.g. `https://your-app.emergent.host`.
   Opening it in a browser may show "details not found". That's expected; the API lives at `/api`.
   Check it: `https://your-app.emergent.host/api/teams` should list the 16 clubs.

## 2. Push the code to GitHub
Use **Save to GitHub** in Emergent.

## 3a. Host on Vercel
1. vercel.com → Add New → Project → import the GitHub repo.
2. **Root Directory:** `frontend`
3. Build settings come from `frontend/vercel.json` (build: `npx expo export --platform web`, output: `dist`, SPA rewrites).
4. **Environment Variable:** `EXPO_PUBLIC_BACKEND_URL` = your Emergent backend URL from step 1 (no `/api`, no trailing slash).
5. Deploy. You'll get a URL like `https://tip-masters.vercel.app`.

## 3b. Or host on Netlify
1. app.netlify.com → Add new site → Import from GitHub.
2. **Base directory:** `frontend` (build settings come from `frontend/netlify.toml`).
3. **Environment variable:** `EXPO_PUBLIC_BACKEND_URL` = your Emergent backend URL.
4. Deploy.

## Notes
- `EXPO_PUBLIC_BACKEND_URL` is baked in at build time. If you change it, redeploy the site.
- After code changes: redeploy the backend on Emergent (if backend changed), Save to GitHub again, and Vercel/Netlify rebuild automatically.
- Google sign-in returns to whatever domain the site runs on, so no extra setup is needed.
- Sign in with Apple is iOS-only and doesn't appear on the website.
- CORS on the backend allows any website origin, with Bearer-token auth.
