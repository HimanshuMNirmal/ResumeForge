
# ResumeForge

> AI-powered resume tailoring — multi-user SaaS, self-hostable on AWS.
>
> Paste a job description and generate a tailored, ATS-friendly DOCX and PDF resume using only facts you have provided. No invented skills, experience, qualifications, or achievements.

**User Profile (PostgreSQL) + Job Description → Tailored Resume (DOCX/PDF) + ATS Report**

ResumeForge combines a resume-generation engine with a multi-user web application. Users manage their professional profiles, configure their own LLM API keys, generate job-specific resumes, and access their resume history.

### Core Principles

- **Truth first:** The LLM may reword, reorder, and select existing facts, but must not invent qualifications or achievements.
- **Validated data:** Use structured, validated JSON between pipeline stages.
- **ATS-aware output:** Re-parse generated documents and evaluate their content and structure.
- **Secure credentials:** Encrypt user-supplied API keys using AES-256-GCM.
- **Private storage:** Store S3 object keys rather than hardcoded public URLs.
- **Multi-user isolation:** Keep profiles, API keys, and resume history scoped to their respective users.

---

## Architecture

```text
┌──────────────────────────────┐       ┌────────────────────────────┐
│      Next.js 15 Frontend     │ HTTPS │       FastAPI Backend      │
│      TypeScript / Vercel     │◄─────►│       AWS EC2 / Docker     │
└──────────────────────────────┘       └──────────────┬─────────────┘
                                                      │
                                     ┌────────────────┼──────────────┐
                                     │                │              │
                               ┌─────▼─────┐    ┌─────▼─────┐  ┌─────▼─────┐
                               │ PostgreSQL│    │ S3 / R2   │  │ LLM APIs  │
                               │  Database │    │  Storage  │  │ Providers │
                               └───────────┘    └───────────┘  └───────────┘
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 App Router, TypeScript, CSS Modules |
| Backend | FastAPI, Python 3.12 |
| Core engine | Python, Pydantic |
| Database | PostgreSQL 16, Docker |
| ORM | SQLAlchemy (async) |
| Migrations | Alembic |
| Authentication | JWT access tokens, opaque refresh tokens |
| Key encryption | AES-256-GCM |
| Object storage | AWS S3 / Cloudflare R2 |
| LLM providers | Anthropic, OpenAI, Google Gemini |
| Document generation | DOCX and PDF rendering |
| Testing | pytest |
| CI/CD | GitHub Actions, Amazon ECR, EC2 |
| Deployment | Docker, Docker Compose, Nginx |

---

## Features

### Resume Generation

- Tailor resumes to individual job descriptions.
- Select relevant experience, skills, and projects from an existing profile.
- Generate editable DOCX and PDF documents.
- Evaluate generated documents with an ATS-oriented report.
- Stream build progress using Server-Sent Events (SSE).
- Retain the original CLI workflow for standalone use.

### Profile Management

- Manage personal information, education, experience, skills, and projects.
- Store professional information in PostgreSQL.
- Import and export profiles as JSON.
- Configure career stage, resume length, date format, and paper size.
- Maintain a `never_claim` blocklist for skills or claims that must not appear.

### LLM Configuration

- Support Anthropic, OpenAI, and Gemini providers.
- Allow users to supply their own API keys.
- Encrypt stored API keys at rest.
- Activate one key at a time per user.
- Provide an optional platform-managed fallback key.
- Fall back to heuristic processing when no LLM key is configured, subject to the supported pipeline functionality.

### Multi-User SaaS

- User registration and login.
- Short-lived access tokens and rotating refresh tokens.
- User-specific profiles and API keys.
- Paginated resume history.
- Authenticated document downloads.
- Resume history and document deletion.

---

## Repository Layout

```text
ResumeForge/
├── src/
│   └── resume_builder/          # Core resume-generation engine
│       ├── pipeline.py          # End-to-end generation pipeline
│       ├── llm.py               # Anthropic / OpenAI / Gemini
│       ├── models.py            # Pydantic data models
│       └── ...                  # Parsing, matching, validation, rendering, ATS
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py              # Application factory, CORS, routers
│   │   ├── config.py            # Environment-based configuration
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── auth/                # Registration, login, refresh, logout, /me
│   │   ├── middleware/          # Authentication dependencies
│   │   ├── profile/             # Profile CRUD and import/export
│   │   ├── keys/                # Encrypted API key management
│   │   ├── resume/              # Resume build and SSE streaming
│   │   ├── history/             # Resume history and downloads
│   │   └── storage/             # S3-compatible storage integration
│   │
│   ├── migrations/              # Alembic migrations
│   ├── tests/                   # Backend tests
│   └── Dockerfile               # Backend container image
│
├── docker-compose.yml           # Local development
├── docker-compose.prod.yml      # Production overrides
├── nginx/
│   └── nginx.conf               # Reverse proxy, SSE, rate limiting
├── .github/
│   └── workflows/
│       ├── ci.yml               # CI checks
│       └── deploy.yml           # Production deployment
├── .env.example                 # Environment variable template
├── pyproject.toml               # Python package configuration, if present
└── README.md
```

The layout above describes the intended project organization. Consult the actual repository files for the current implementation and available configuration files.

---

## Database Schema

Alembic manages database schema migrations.

| Table | Purpose |
|---|---|
| `users` | User accounts and authentication data |
| `refresh_tokens` | Hashed refresh tokens and session rotation |
| `profiles` | User profile data stored in JSONB columns |
| `api_keys` | Encrypted, user-supplied LLM API keys |
| `resume_history` | Job description data, S3 object keys, and ATS scores |

### Important Constraints

- Email addresses must be unique.
- Only one API key per user can be active at a time.
- Refresh tokens are stored as SHA-256 hashes rather than raw tokens.
- Related records should follow the configured cascading deletion rules.
- Resume files are referenced using storage object keys rather than permanent public URLs.

Migrations are applied automatically during startup if configured by the deployment.

---

## API Documentation

Base path: `/api/v1`

Authenticated endpoints require:

```http
Authorization: Bearer <access_token>
```

### Authentication — `/api/v1/auth`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/register` | Create an account and issue tokens |
| `POST` | `/login` | Authenticate and issue tokens |
| `POST` | `/refresh` | Rotate the refresh token and issue a new access token |
| `POST` | `/logout` | Revoke the refresh token and clear the cookie |
| `GET` | `/me` | Return the authenticated user's information |

Access tokens expire after 15 minutes. Refresh tokens are opaque tokens delivered through an HttpOnly cookie, with a configured lifetime of seven days.

### Profile — `/api/v1/profile`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Retrieve the current user's profile |
| `PATCH` | `/basics` | Update personal information and links |
| `PATCH` | `/experience` | Replace the experience list |
| `PATCH` | `/skills` | Update skills, summary facts, and `never_claim` |
| `PATCH` | `/education` | Update education and certifications |
| `PATCH` | `/projects` | Replace the project list |
| `PATCH` | `/preferences` | Update resume generation preferences |
| `GET` | `/export` | Download the profile as JSON |
| `GET` | `/sample` | Download an annotated sample profile |
| `POST` | `/import` | Upload and validate a profile JSON file |

### API Keys — `/api/v1/keys`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | List API keys without exposing their raw values |
| `POST` | `/` | Add and encrypt an API key |
| `PUT` | `/{id}/activate` | Activate one key for the user |
| `DELETE` | `/{id}` | Delete an API key |
| `GET` | `/models` | List models available for the active provider |

### Resume Generation — `/api/v1/resume`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/build` | Start resume generation and stream progress events |

### Resume History — `/api/v1/history`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Get paginated history with temporary download URLs |
| `GET` | `/{id}` | Retrieve one history entry, including its job description |
| `DELETE` | `/{id}` | Delete a history entry and its associated stored objects |

---

## Profile Import and Export

ResumeForge supports JSON profile import and export for backups, migration, and local editing.

### Export a Profile

```http
GET /api/v1/profile/export
Authorization: Bearer <access_token>
```

Returns a downloadable, import-ready profile JSON file.

### Download the Sample Template

```http
GET /api/v1/profile/sample
```

This endpoint does not require authentication. It returns an example profile showing the supported structure and field values.

### Import a Profile

```http
POST /api/v1/profile/import
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Form field:

```text
file: <your-profile.json>
```

The uploaded JSON is parsed and validated before the profile is saved. Importing replaces the current profile when the operation succeeds.

Possible responses:

- `200 OK` — Profile imported successfully.
- `400 Bad Request` — Invalid JSON.
- `422 Unprocessable Entity` — Profile schema validation errors.

Example validation response:

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

The exact response schema depends on the implemented validation handlers.

---

## Local Development Setup

### Prerequisites

- Git
- Docker
- Docker Compose
- A configured LLM API key for AI-powered generation
- AWS S3 or an S3-compatible service if object storage is required

### 1. Clone the Repository

```bash
git clone https://github.com/HimanshuMNirmal/ResumeForge.git
cd ResumeForge
```

If the repository does not contain a `.env.example` file, create the environment configuration using the variables required by the application.

### 2. Configure Environment Variables

If `.env.example` exists:

```bash
cp .env.example .env
```

Generate a JWT signing secret:

```bash
openssl rand -hex 32
```

Generate a base64-encoded 32-byte encryption key:

```bash
python3 -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Set the required values in `.env`:

```dotenv
SECRET_KEY=<generated-jwt-secret>
ENCRYPTION_KEY=<generated-base64-encryption-key>
DB_PASSWORD=<strong-database-password>
```

Also configure the database URL, storage settings, allowed origins, and optional platform LLM keys as required by the application.

**Never commit `.env` or real credentials to Git.**

### 3. Start the Application

```bash
docker compose up --build
```

If the Compose configuration is wired for automatic initialization, it should:

1. Start PostgreSQL.
2. Wait for the database health check.
3. Apply database migrations.
4. Start the FastAPI backend.

When the backend is running on the default development port:

- API: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/health`

These addresses depend on the configured ports and routes.

### 4. Optional: pgAdmin

If the Compose configuration defines a `tools` profile:

```bash
docker compose --profile tools up --build
```

Use the configured pgAdmin URL and credentials. Do not expose development database tools publicly or retain default credentials in production.

### 5. Stop the Application

```bash
docker compose down
```

To remove the local database volume as well, use `docker compose down -v` only if you intentionally want to delete persisted development data.

---

## Testing the API

### Option A — Interactive API Documentation

Open:

`http://localhost:8000/api/docs`

Use the interactive documentation to inspect request schemas and test available endpoints.

### Option B — curl

The following examples assume the backend is running locally and the endpoints match the API implementation.

#### 1. Register

```bash
curl -c cookies.txt \
  -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "jane@example.com",
    "password": "Secure123"
  }'
```

Save the returned access token:

```bash
TOKEN="<paste-access-token-here>"
```

#### 2. Check Application Health

```bash
curl http://localhost:8000/health
```

#### 3. Retrieve the Profile

```bash
curl http://localhost:8000/api/v1/profile \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. Update Basic Information

```bash
curl -X PATCH http://localhost:8000/api/v1/profile/basics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Smith",
    "email": "jane@example.com",
    "location": "San Francisco, CA"
  }'
```

Adjust the field names to match the actual request schema.

#### 5. Add an LLM API Key

```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "My Anthropic Key",
    "provider": "anthropic",
    "raw_key": "<your-api-key>"
  }'
```

Use a real key only in a trusted local environment. Do not commit it or paste it into issue reports.

#### 6. Activate an API Key

```bash
curl -X PUT \
  "http://localhost:8000/api/v1/keys/<key-id>/activate" \
  -H "Authorization: Bearer $TOKEN"
```

Replace `<key-id>` with the ID returned by the API.

#### 7. Build a Resume

```bash
curl -N -X POST http://localhost:8000/api/v1/resume/build \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jd_text": "We are looking for a Python engineer...",
    "use_pdf": true
  }'
```

The endpoint returns Server-Sent Events if SSE streaming is enabled. Use the actual request schema documented by the running application.

#### 8. View Resume History

```bash
curl "http://localhost:8000/api/v1/history?limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

#### 9. Download the Sample Profile

```bash
curl http://localhost:8000/api/v1/profile/sample \
  -o profile_sample.json
```

#### 10. Import a Profile

```bash
curl -X POST http://localhost:8000/api/v1/profile/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@profile_sample.json"
```

#### 11. Export a Profile

```bash
curl http://localhost:8000/api/v1/profile/export \
  -H "Authorization: Bearer $TOKEN" \
  -o my_profile.json
```

#### 12. Refresh the Access Token

```bash
curl -c cookies.txt -b cookies.txt \
  -X POST http://localhost:8000/api/v1/auth/refresh
```

Cookie handling depends on the configured cookie name, domain, path, and security attributes.

### Option C — Run the Test Suite

If the backend container is running and includes pytest:

```bash
docker compose exec backend pytest tests/ -v
```

For local execution, install the project dependencies, start PostgreSQL, configure the required environment variables, and run the tests from the backend directory:

```bash
cd backend
pytest tests/ -v
```

The test suite should be checked for coverage of authentication, profile validation, API key management, authorization boundaries, and resume generation.

---

## Environment Variables

The exact names depend on the application's configuration. The following variables represent the documented configuration.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret |
| `ENCRYPTION_KEY` | Base64-encoded 32-byte AES-256 key |
| `DB_PASSWORD` | Database password used by Docker Compose |
| `AWS_ACCESS_KEY_ID` | AWS access key, if static credentials are used |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key, if static credentials are used |
| `S3_BUCKET_NAME` | Bucket for generated resume documents |
| `S3_REGION` | AWS region |
| `S3_ENDPOINT_URL` | Optional S3-compatible endpoint, such as Cloudflare R2 |
| `PLATFORM_ANTHROPIC_KEY` | Optional platform fallback key |
| `PLATFORM_OPENAI_KEY` | Optional platform fallback key |
| `ALLOWED_ORIGINS` | Allowed frontend origins |
| `DEBUG` | Development/debug configuration |

In production, prefer IAM roles or other short-lived credentials over long-lived AWS access keys where supported.

---

## Production Deployment on AWS

ResumeForge is designed to support a containerized deployment using AWS infrastructure.

### Infrastructure

A typical deployment consists of:

- A frontend hosted on Vercel or another compatible platform.
- A FastAPI backend running in Docker on EC2.
- PostgreSQL for user accounts, profiles, API keys, and history.
- S3 or compatible object storage for generated documents.
- ECR for container image storage.
- Nginx for reverse proxying, rate limiting, and SSE-compatible streaming.

For production use, ensure the database, application secrets, object storage, and network access are configured securely.

### EC2 Setup

On a supported Ubuntu EC2 instance:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin awscli
sudo usermod -aG docker ubuntu
```

After configuring Docker access and AWS credentials, prepare the application directory:

```bash
sudo mkdir -p /opt/resumeforge
sudo chown ubuntu:ubuntu /opt/resumeforge
cd /opt/resumeforge
```

For a direct Git-based deployment:

```bash
git clone https://github.com/HimanshuMNirmal/ResumeForge.git .
```

Configure production environment variables before starting the application. If deployment uses ECR images, follow the image-pull and deployment process defined by the repository's workflow instead of building directly from Git on the server.

### CI/CD

A GitHub Actions deployment workflow can perform the following steps:

1. Run linting and automated tests.
2. Build the backend Docker image.
3. Authenticate with Amazon ECR.
4. Push an image tagged with the commit SHA.
5. Deploy the image to EC2.
6. Apply database migrations.
7. Run a health check.
8. Fail the deployment if validation does not pass.

### GitHub Actions Secrets

Configure only the secrets actually referenced by your workflow.

| Secret | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS authentication, if using static credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_REGION` | AWS deployment region |
| `ECR_REGISTRY` | Amazon ECR registry address |
| `EC2_HOST` | EC2 hostname or IP |
| `EC2_SSH_KEY` | SSH private key for deployment, if used |

Use least-privilege IAM policies, protect deployment secrets, and restrict SSH access. Prefer OIDC-based AWS authentication for GitHub Actions when configured.

---

## Resume Build Pipeline

A typical resume build follows this sequence:

```text
POST /api/v1/resume/build
              │
              ▼
      Load user profile
              │
              ▼
      Parse job description
              │
              ▼
    Select relevant experience
              │
              ▼
       Tailor resume content
              │
              ▼
       Validate generated data
              │
              ▼
        Render DOCX document
              │
              ▼
          Convert to PDF
              │
              ▼
       Run ATS-oriented checks
              │
              ▼
     Upload files to S3 / R2
              │
              ▼
     Save resume history entry
              │
              ▼
      Stream completion event
```

The pipeline is designed to keep document generation separate from the web application's authentication, persistence, and storage layers.

Where configured, CPU-bound or blocking work can be moved to a thread pool so it does not block FastAPI's asynchronous event loop. Progress can be forwarded through an `asyncio.Queue` to an SSE response.

The exact sequence and execution model depend on the current implementation.

---

## LLM Key Resolution

The intended key-resolution order is:

```text
Incoming resume build request
              │
              ▼
     User has an active API key?
          /           \
        Yes            No
         │              │
         ▼              ▼
 Decrypt user key   Platform key configured?
                         /       \
                       Yes        No
                        │          │
                        ▼          ▼
                 Use platform   Use supported
                    key         heuristic mode
```

- User API keys are encrypted at rest using AES-256-GCM.
- The encryption key is supplied through environment configuration and is not stored in the application database.
- Platform keys, when enabled, should be subject to usage limits and monitoring.
- Heuristic mode should not imply AI-powered rewriting when no LLM is available.

---

## ATS and Content Validation

ResumeForge is designed to evaluate generated documents beyond the LLM response itself.

The intended safeguards include:

1. Validate structured input and intermediate data.
2. Select only information supported by the user's profile.
3. Prevent prohibited claims listed in `never_claim`.
4. Validate the generated resume structure.
5. Render the document into the requested format.
6. Re-parse the resulting document for ATS-oriented checks.
7. Return the generated documents and available report information.

ATS checks can help identify formatting or content issues, but they cannot guarantee compatibility with every applicant tracking system or predict hiring outcomes.

---

## Original CLI

The core engine is intended to remain usable independently of the web application.

From the repository root, install the package according to the actual `pyproject.toml` configuration:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all,dev]"
```

On Windows, activate the environment using:

```powershell
.venv\Scripts\Activate.ps1
```

Configure the LLM provider keys required for your chosen workflow. If the CLI commands below are supported by the installed version, you can use:

```bash
# Validate a profile JSON file
resume validate-profile

# Render a resume to inspect its layout
resume render

# Build a resume against a job description file
resume build --jd job.txt

# Build using a supported job description URL
resume build --jd https://example.com/jobs/123

# Read job description text from standard input
pbpaste | resume build --jd -
```

The `pbpaste` example is intended for macOS. On Linux, use an appropriate clipboard command or pipe text directly into the CLI.

---

## Profile JSON Format

The profile import/export format represents the candidate's factual background.

Example:

```json
{
  "basics": {
    "full_name": "Jane Smith",
    "email": "jane@example.com",
    "phone": "+1-555-0100",
    "location": "San Francisco, CA",
    "links": [
      {
        "label": "GitHub",
        "url": "https://github.com/janesmith"
      }
    ]
  },
  "preferences": {
    "career_stage": "experienced",
    "max_pages": 1,
    "date_format": "MMM YYYY",
    "paper_size": "Letter"
  },
  "summary_facts": [
    "5 years of Python experience"
  ],
  "skills": [
    {
      "name": "Python",
      "category": "Languages",
      "level": "strong",
      "years": 5,
      "aliases": ["py"]
    }
  ],
  "experience": [
    {
      "id": "exp-001",
      "company": "Acme Corp",
      "title": "Senior Engineer",
      "location": "San Francisco, CA",
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

This is an illustrative example. Use the sample profile endpoint or the current Pydantic models as the source of truth for accepted fields and values.

### Profile Rules

- Bullet IDs must be unique across experience and projects if required by the active schema.
- `never_claim` is intended to block specified skills or claims from appearing in generated resumes.
- `career_stage: "early_career"` can be used to prioritize education for early-career candidates if supported by the renderer.
- `paper_size` supports the formats accepted by the active configuration, such as `Letter` or `A4`.
- Profile facts should be accurate, complete, and verifiable by the candidate.

---

## Security Considerations

ResumeForge handles personal information, employment history, credentials, and generated documents. Security is a core design requirement.

- Hash refresh tokens before persistence.
- Encrypt user-supplied API keys at rest.
- Keep encryption and signing secrets outside the database.
- Enforce authorization checks on every user-specific resource.
- Never expose raw API keys through list or detail endpoints.
- Use short-lived presigned URLs for private document downloads.
- Store object keys rather than permanent public file URLs.
- Validate uploaded profile JSON before replacing existing profile data.
- Keep credentials out of logs and version control.
- Use HTTPS and secure cookie settings in production.
- Apply request limits to authentication and resource-intensive generation endpoints.
- Verify that document deletion removes the intended database records and stored objects.

These are security requirements and design goals; verify each one against the deployed implementation.

---

## Contributing

Contributions, bug reports, and improvements are welcome.

A useful contribution workflow is:

1. Fork the repository.
2. Create a feature branch.
3. Make a focused change.
4. Add or update tests.
5. Run the relevant checks.
6. Open a pull request describing the change.

Run the backend tests, where configured:

```bash
cd backend
pytest tests/ -v
```

Run Ruff if it is part of the development setup:

```bash
ruff check app/
```

Follow the existing project conventions and avoid committing secrets, generated credentials, or personal resume data.

---

## Project Status

ResumeForge combines a standalone resume-generation engine with a multi-user application architecture. Refer to the current source code, tests, and deployment configuration to determine which features are implemented and ready for use.

The project prioritizes factual accuracy, structured validation, secure credential handling, and ATS-aware document generation.

## License

Check the repository for a `LICENSE` file to determine the applicable usage and distribution terms.
