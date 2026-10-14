# SkillForge Frontend — Adaptive Teacher

React + Vite UI for the SkillForge Teacher Agent: sign in / sign up / email
verification / password reset, dashboard, VNR V Semester curriculum (subject →
unit → topic), teacher session (lesson → adaptive questions → feedback),
learning report, progress, timetable, and a "How it works" page. Plain CSS, no
extra dependencies.

## Run

```
npm install
npm run dev
```

Opens on http://localhost:5173. Requests to `/api` are proxied to the backend
at http://127.0.0.1:8000 (start it separately:
`cd ../backend && uvicorn skillforge.api.app:app --port 8000`). Set
`SKILLFORGE_API` to proxy to a different backend address.

Because the API is reached through the proxy, the browser sees a single
origin and the HttpOnly session cookie stays first-party. All data on screen
comes from the signed-in student's account; the backend enforces access.

`npm run build` produces `dist/`; `npm run preview` serves it on port 4173
with the same proxy.

The original e-commerce practice pages (`src/pages/Overview.jsx`, `Learn.jsx`,
`Practice.jsx`, `Cases.jsx`, `Progress.jsx`, `PolicyReference.jsx`) and their
stylesheet (`src/legacy.css`) are kept in the repo but no longer routed.
