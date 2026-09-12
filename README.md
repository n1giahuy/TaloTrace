# AI Chemistry Video Request Service — Phase 1

Backend-only Phase 1 vertical slice for the coding challenge:

`FastAPI -> async job -> ADK 2.0 Workflow -> Gemini 3.1 Flash-Lite -> Veo 3.1 Lite -> MP4 artifact`

P1 intentionally keeps persistence in memory and does **not** add a test suite, docs folder, queue, database, retry policy, or production worker yet.

## Architecture

```text
POST /jobs
    |
    v
JobService -----------------> InMemoryJobRepository
    |
    | asyncio task
    v
ADK Runner -> App -> Workflow
                    |
                    +-> LlmAgent: prompt_refiner
                    |      Gemini 3.1 Flash-Lite @ global
                    |
                    +-> FunctionNode: validate_plan
                    |
                    +-> FunctionNode: generate_video
                           Veo 3.1 Lite @ us-central1
                    |
                    v
               artifacts/<job-id>.mp4
```

ADK owns orchestration. Gemini owns the uncertain reasoning/refinement step. Python code owns job lifecycle and the deterministic Veo call boundary.

## GCP setup

You need a billed Google Cloud project with access/quota for the selected models.

Enable the Vertex AI API:

```bash
gcloud services enable aiplatform.googleapis.com --project YOUR_PROJECT_ID
```

Create Application Default Credentials on the Linux host:

```bash
gcloud auth application-default login
mkdir -p secrets
cp ~/.config/gcloud/application_default_credentials.json secrets/adc.json
```

The credentials file is mounted read-only into Docker and is gitignored.

> `gemini-3.1-flash-lite` uses the `global` endpoint. `veo-3.1-lite-generate-001` is configured separately for `us-central1`.

## Configure

```bash
cp .env.example .env
nano .env
```

At minimum replace:

```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

Optional: if direct generated-video download is unavailable for your model access, create a GCS bucket and set `VEO_OUTPUT_GCS_URI=gs://...`. The code can download a returned `gs://` artifact back into the local `artifacts/` directory.

## Run

Use this command at the start of P1 and again after changes in later phases:

```bash
sudo docker compose up -d --build
```

Logs:

```bash
sudo docker compose logs -f api
```

Health check:

```bash
curl http://localhost:8000/health
```

## Acceptance run

### 1. pH scale

```bash
curl -s -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"query":"How does the pH scale work?"}'
```

### 2. Covalent bonds

```bash
curl -s -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"query":"Why do atoms form covalent bonds?"}'
```

### 3. Ionic vs covalent

```bash
curl -s -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the difference between ionic and covalent bonding?"}'
```

Each POST returns HTTP `202` and a job id. Poll it:

```bash
curl -s http://localhost:8000/jobs/JOB_ID
```

List all jobs:

```bash
curl -s http://localhost:8000/jobs
```

When `status` becomes `completed`, download/open the artifact:

```bash
curl -L http://localhost:8000/jobs/JOB_ID/artifact -o result.mp4
```

The generated file is also persisted on the host under `./artifacts/`.

## P1 API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `POST` | `/jobs` | Queue a chemistry video job |
| `GET` | `/jobs` | List jobs |
| `GET` | `/jobs/{id}` | Poll status |
| `GET` | `/jobs/{id}/artifact` | Retrieve completed MP4 |

## Phase boundary

P1 is deliberately the real end-to-end slice. Phase 2 should evolve this same repo with ADK `RetryConfig`, stronger plan/artifact quality gates, clearer failure taxonomy and concurrency controls. Phase 3 should focus on observability, submission polish and the final three committed generated videos.
