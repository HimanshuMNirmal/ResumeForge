# Tailor web

Next.js (App Router) frontend for the resume tailoring API (FastAPI + PostgreSQL).

## Run
```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL to your backend
npm run dev
```

## Deploy (Vercel)
Import the repo, set `NEXT_PUBLIC_API_URL` (your AWS API) and `NEXT_PUBLIC_SITE_URL`. Allow your Vercel domain in the backend's CORS settings.

## Auth
`lib/api-client.ts` exposes `setTokenProvider(fn)`. Call it once (e.g. in `app/providers.tsx`) with a function returning your NextAuth/Clerk/JWT token. Until then requests go out without an Authorization header.

## Layout
- `types/api.ts` shared schemas · `lib/api-client.ts` typed client
- `components/{profile,keys,builder}` feature components
- `app/page.tsx` landing · `app/(dashboard)/{profile,builder,history,settings/keys}`
