# ResumeForge

> AI-powered resume tailoring — multi-user SaaS, self-hostable on AWS.  
> Paste a job description, get a tailored, ATS-safe DOCX + PDF resume in seconds — strictly from facts you provided, never invented.

```
User Profile (PostgreSQL)  +  Job Description  →  resume.docx / resume.pdf  +  ATS report
```

**Core design rules:** truth first (LLM may reword, reorder, select — never invent) · validated JSON between every step · every output re-parsed as an ATS would · per-user API key encryption · S3 object-key-only storage (no hardcoded URLs).

---

## Architecture

```
┌──────────────────────────────┐        ┌────────────────────────┐
│   Next.js 15 Frontend        │  HTTPS │   FastAPI Backend       │
│   (Vercel)                   │◄──────►│   (AWS EC2 + Docker)   │
└──────────────────────────────┘        └──────┬─────────┬────────┘
                                               │         │
                                        ┌──────▼──┐  ┌───▼───────┐
                                        │Postgres │  │ S3 Bucket │
                                        │(Docker) │  │(AWS / R2) │
                                        └─────────┘  └───────────┘
```

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router) · TypeScript · CSS Modules |
| Backend | FastAPI · Python 3.12 |
| Database | PostgreSQL 16 (Docker) |
| Migrations | Alembic (async) |
| Storage | AWS S3 / Cloudflare R2 (S3-compatible) |
| Auth | JWT access tokens (15 min) + opaque refresh tokens (HttpOnly cookie, 7 days) |
| Key encryption | AES-256-GCM — user API keys encrypted at rest, encryption key never touches DB |
| CI/CD | GitHub Actions → ECR → EC2 |

---

## Repository Layout

```
resume-builder/
├── src/resume_builder/      ← Core engine (unchanged — pipeline, LLM, renderer, ATS)
│   ├── pipeline.py          ← ingest → parse JD → select → tailor → validate → render → ATS
│   ├── llm.py               ← Anthropic / OpenAI / Gemini
│   ├── models.py            ← Pydantic models: Profile, JD, Resume
│   └── ...
├── backend/                 ← FastAPI application (new)
│   ├── app/
│   │   ├── main.py          ← App factory, CORS, routers
│   │   ├── config.py        ← Pydantic Settings (all env vars)
│   │   ├── database.py      ← Async SQLAlchemy engine
│   │   ├── auth/            ← register · login · refresh · logout · /me
│   │   ├── middleware/      ← JWT Bearer dependency
│   │   ├── profile/         ← CRUD + import/export
│   │   ├── keys/            ← AES-encrypted API key management
│   │   ├── resume/          ← SSE streaming build endpoint
│   │   ├── history/         ← Paginated history with presigned S3 URLs
│   │   └── storage/         ← boto3 S3 wrapper
│   ├── migrations/          ← Alembic (5 tables, auto-applied on startup)
│   ├── tests/               ← pytest integration tests
│   └── Dockerfile           ← Multi-stage, LibreOffice, non-root
├── docker-compose.yml       ← Local dev (postgres + backend + optional pgAdmin)
├── docker-compose.prod.yml  ← Production overrides (ECR image, nginx)
├── nginx/nginx.conf         ← HTTPS, SSE buffering off, rate limiting
└── .github/workflows/
    ├── ci.yml               ← Lint + test on every PR
    └── deploy.yml           ← Build → ECR → SSH deploy → migrate → health check
```

---

## Database Schema

All tables are created automatically by Alembic on first startup — you never run SQL manually.

| Table | Purpose |
|-------|---------|
| `users` | Email/password accounts |
| `refresh_tokens` | Opaque tokens (stored as SHA-256 hash) for session rotation |
| `profiles` | Per-user profile data in JSONB columns |
| `api_keys` | User-supplied LLM keys (AES-256-GCM encrypted) |
| `resume_history` | JD text + S3 object keys (never full URLs) + ATS score |

**Key constraints:** unique email, unique active API key per user (partial index `WHERE is_active = true`), cascading deletes.

---

## API Endpoints

All authenticated endpoints require `Authorization: Bearer <access_token>`.

### Auth — `/api/v1/auth`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Create account → returns access token + sets refresh cookie |
| POST | `/login` | → access token + refresh cookie |
| POST | `/refresh` | Rotate refresh token → new access token |
| POST | `/logout` | Revoke refresh token, clear cookie |
| GET  | `/me` | Validate session, return user info |

### Profile — `/api/v1/profile`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Full profile |
| PATCH | `/basics` | Name, email, phone, location, links |
| PATCH | `/experience` | Replace experience list |
| PATCH | `/skills` | Replace skills + summary facts + never_claim |
| PATCH | `/education` | Replace education + certifications |
| PATCH | `/projects` | Replace projects |
| PATCH | `/preferences` | career_stage, max_pages, date_format, paper_size |
| GET | `/export` | **Download profile as JSON file** (auth required) |
| GET | `/sample` | **Download annotated sample JSON** (no auth) |
| POST | `/import` | **Upload + validate JSON → replaces profile** |

### API Keys — `/api/v1/keys`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List keys (preview only — never exposes raw key) |
| POST | `/` | Add key (encrypted immediately) |
| PUT | `/{id}/activate` | Set as active (deactivates all others) |
| DELETE | `/{id}` | Remove key |
| GET | `/models` | Available models for the active provider |

### Resume — `/api/v1/resume`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/build` | Start build → SSE stream of progress events |

### History — `/api/v1/history`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Paginated list (`?limit=20&offset=0`) with presigned download URLs |
| GET | `/{id}` | Single entry with full JD text |
| DELETE | `/{id}` | Delete entry + S3 objects |

---

## Profile Import / Export

The profile editor supports JSON import and export — useful for migrating data, bulk-editing locally, or backing up.

### Download your profile
```
GET /api/v1/profile/export
Authorization: Bearer <token>
```
Downloads `profile_jane_smith.json` — a valid import-ready file.

### Download the sample template
```
GET /api/v1/profile/sample
```
No auth needed. Downloads `profile_sample.json` with comments showing every field and accepted value.

### Import from JSON
```
POST /api/v1/profile/import
Authorization: Bearer <token>
Content-Type: multipart/form-data
file: <your-profile.json>
```

**On success:** returns the saved profile (HTTP 200).  
**On invalid JSON:** HTTP 400 with `"Invalid JSON: <reason>"`.  
**On schema errors:** HTTP 422 with a detailed error list:
```json
{
  "message": "Profile JSON has 3 validation error(s). Fix them and try again.",
  "errors": [
    "basics.email: required field is missing or empty",
    "experience[0].bullets[1].id: required field is missing",
    "Duplicate bullet id: 'b-001' — all bullet ids must be unique"
  ]
}
```

---

## Local Development Setup

### Prerequisites
- Docker + Docker Compose
- Git

### 1. Clone and configure
```bash
git clone https://github.com/yourname/resume-builder
cd resume-builder
cp .env.example .env
```

Edit `.env` — fill in the three required values:

```bash
# Generate a JWT signing key (paste the output into .env)
openssl rand -hex 32

# Generate an AES-256 encryption key for user API keys
python3 -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

# Pick any DB password
DB_PASSWORD=choose_something_strong
```

### 2. Start everything
```bash
docker compose up
```

**That's it.** Docker Compose automatically:
1. Starts PostgreSQL and creates the `resume_builder` database
2. Waits for Postgres to be healthy
3. Runs `alembic upgrade head` → creates all 5 tables + indexes
4. Starts uvicorn with hot-reload

API is live at **http://localhost:8000**  
Interactive docs (dev mode): **http://localhost:8000/api/docs**

### 3. Optional pgAdmin (DB browser)
```bash
docker compose --profile tools up
```
Opens at **http://localhost:5050** (email: `admin@local.dev` / password: `admin`).  
Connect to host `db`, port `5432`, user `resume`.

---

## Testing the API

### Option A — Interactive docs (easiest)
Open **http://localhost:8000/api/docs** in your browser. All endpoints are listed with request/response schemas. Use the "Try it out" button.

### Option B — curl

```bash
# 1. Register
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Smith","email":"jane@example.com","password":"Secure123"}'

# Response: {"user":{...}, "access_token":"eyJ...", "token_type":"bearer"}
TOKEN="paste_access_token_here"

# 2. Health check
curl http://localhost:8000/health

# 3. Get profile (starts empty)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/profile

# 4. Update basics
curl -X PATCH http://localhost:8000/api/v1/profile/basics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Jane Smith","email":"jane@example.com","location":"SF, CA"}'

# 5. Add an API key (your real Anthropic/OpenAI/Gemini key)
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"label":"My Anthropic Key","provider":"anthropic","raw_key":"sk-ant-..."}'

# 6. Activate the key (use the id from the response above)
curl -X PUT http://localhost:8000/api/v1/keys/<key-id>/activate \
  -H "Authorization: Bearer $TOKEN"

# 7. Build a resume (SSE stream)
curl -N -X POST http://localhost:8000/api/v1/resume/build \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jd_text":"We are looking for a Senior Python Engineer...","use_pdf":true}'

# 8. View history
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/history?limit=5"

# 9. Download sample profile template (no auth needed)
curl http://localhost:8000/api/v1/profile/sample -o profile_sample.json

# 10. Import a profile from JSON
curl -X POST http://localhost:8000/api/v1/profile/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@profile_sample.json"

# 11. Export your profile
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/profile/export -o my_profile.json

# 12. Refresh access token (uses the HttpOnly cookie set during login/register)
curl -c cookies.txt -b cookies.txt -X POST \
  http://localhost:8000/api/v1/auth/refresh
```

### Option C — Run the test suite
```bash
# Inside Docker
docker compose exec backend pytest tests/ -v

# Or locally (requires Postgres running separately)
cd backend
DATABASE_URL="postgresql+asyncpg://resume:yourpassword@localhost/resume_builder" \
SECRET_KEY="test-secret-32-chars-minimum-ok" \
ENCRYPTION_KEY="$(python3 -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")" \
S3_BUCKET_NAME="test-bucket" \
pytest tests/ -v
```

Tests cover: register, login, duplicate email, protected routes, all profile section updates, import/export validation.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | ✅ | JWT signing key (≥ 32 random chars) |
| `ENCRYPTION_KEY` | ✅ | AES-256 key for user API keys (32 bytes, base64-encoded) |
| `DB_PASSWORD` | ✅ | PostgreSQL password (Docker Compose only) |
| `AWS_ACCESS_KEY_ID` | For S3 | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | For S3 | AWS credentials |
| `S3_BUCKET_NAME` | For S3 | Bucket for resume storage |
| `S3_REGION` | For S3 | e.g. `us-east-1` |
| `S3_ENDPOINT_URL` | Optional | Cloudflare R2 or MinIO endpoint |
| `PLATFORM_ANTHROPIC_KEY` | Optional | Fallback LLM key for users without their own |
| `PLATFORM_OPENAI_KEY` | Optional | Fallback LLM key (OpenAI) |
| `ALLOWED_ORIGINS` | Optional | JSON array of allowed CORS origins |
| `DEBUG` | Optional | `true` enables OpenAPI docs + SQL logging |

---

## Production Deployment (AWS)

### One-time EC2 setup
```bash
# On your EC2 instance (Ubuntu 22.04+)
sudo apt-get install -y docker.io docker-compose-plugin awscli
sudo usermod -aG docker ubuntu

mkdir -p /opt/resume-builder
cd /opt/resume-builder
git clone https://github.com/yourname/resume-builder .
cp .env.example .env   # fill in production values (no DEBUG, real S3/keys)
```

### GitHub Secrets required for CI/CD
| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | IAM user with ECR + S3 access |
| `AWS_SECRET_ACCESS_KEY` | — |
| `AWS_REGION` | e.g. `us-east-1` |
| `ECR_REGISTRY` | `123456789.dkr.ecr.us-east-1.amazonaws.com` |
| `EC2_HOST` | Your EC2 public IP or domain |
| `EC2_SSH_KEY` | PEM private key content |

### Deploy flow (automatic on every push to `main`)
1. GitHub Actions builds the Docker image
2. Pushes to Amazon ECR with the commit SHA as the tag
3. SSHs into EC2, pulls the new image, recreates only the `backend` container
4. Runs `alembic upgrade head` inside the new container
5. Hits `/health` — fails the deploy if it doesn't return `200`

---

## How the Build Pipeline Works

```
POST /api/v1/resume/build  →  SSE stream
  │
  ├─ [thread pool] Load profile from DB → write temp profile.json
  ├─ [thread pool] ingest.load_jd_text(jd_text)
  ├─ [thread pool] jd_parser.parse_jd()          → progress event
  ├─ [thread pool] matcher.select()              → progress event
  ├─ [thread pool] writer.tailor()               → progress event
  ├─ [thread pool] validator.validate()
  ├─ [thread pool] render.render_docx()          → progress event
  ├─ [thread pool] render.docx_to_pdf()
  ├─ [thread pool] ats_check.check_file()
  ├─ [async] upload DOCX + PDF to S3            → progress event
  ├─ [async] write resume_history row to DB
  └─ SSE done event: { history_id, ats_score, download_urls }
```

The core engine runs in a `ThreadPoolExecutor` (4 workers) so it never blocks the async event loop. Progress is forwarded through an `asyncio.Queue`.

---

## LLM Key Resolution (per-request)

```
Request comes in
  │
  ├─ User has an active API key in DB?  → decrypt (AES-256-GCM) → use it
  │
  ├─ No key → PLATFORM_ANTHROPIC_KEY set? → use platform key (rate-limited)
  │
  └─ No platform key → heuristic mode (JD parsing heuristic, no rewording)
```

User keys are encrypted with AES-256-GCM. The encryption key lives only in `ENCRYPTION_KEY` env var — never in the database.

---

## Original CLI (still works)

The core engine is unchanged and can still be used standalone:

```bash
cd resume-builder
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all,dev]"
cp .env.example .env    # add ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY

# Validate your profile JSON
resume validate-profile

# Full render without AI (check layout)
resume render

# Build against a JD
resume build --jd job.txt
resume build --jd https://example.com/jobs/123
pbpaste | resume build --jd -
```

---

## Profile JSON Format

The import/export format. Download the sample at `GET /api/v1/profile/sample` (no auth needed).

```json
{
  "basics": {
    "full_name": "Jane Smith",
    "email": "jane@example.com",
    "phone": "+1-555-0100",
    "location": "San Francisco, CA",
    "links": [
      { "label": "GitHub", "url": "https://github.com/janesmith" }
    ]
  },
  "preferences": {
    "career_stage": "experienced",
    "max_pages": 1,
    "date_format": "MMM YYYY",
    "paper_size": "Letter"
  },
  "summary_facts": ["5 years of Python experience"],
  "skills": [
    { "name": "Python", "category": "Languages", "level": "strong", "years": 5, "aliases": ["py"] }
  ],
  "experience": [
    {
      "id": "exp-001",
      "company": "Acme Corp",
      "title": "Senior Engineer",
      "location": "SF, CA",
      "start": "Jan 2023",
      "end": null,
      "bullets": [
        {
          "id": "b-001",
          "text": "Built caching layer reducing latency by 60%.",
          "skills": ["Python"],
          "metrics": ["60%"],
          "themes": ["performance"]
        }
      ]
    }
  ],
  "projects": [],
  "education": [
    {
      "id": "edu-001",
      "institution": "UC Berkeley",
      "degree": "B.S. Computer Science",
      "start": "Aug 2017",
      "end": "May 2021",
      "details": ["GPA: 3.8"]
    }
  ],
  "certifications": [],
  "never_claim": ["Kubernetes", "Go"]
}
```

**Rules:**
- All bullet `id` values must be **globally unique** across experience and projects
- `never_claim` is a hard block-list — skills here will never appear in a generated resume
- `career_stage: "early_career"` puts Education before Experience
- `paper_size`: `"Letter"` or `"A4"`

---

## Contributing

```bash
# Run tests before opening a PR
cd backend && pytest tests/ -v

# Lint
pip install ruff && ruff check app/
```

The CI pipeline runs both automatically on every PR.
