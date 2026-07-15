# CIP Frontend

Next.js 14 (App Router) + Tailwind. A dashboard shell over the CIP API.

## Pages

- `/`      Overview — KPIs + a form to trigger a discovery run
- `/leads` Leads table with category filters

## Local dev

```bash
npm install
# Point at your backend (defaults to http://localhost:8000)
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000. Make sure the backend is running and CORS allows
the frontend origin (it allows `*` by default in Phase 1).
