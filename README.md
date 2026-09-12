# AI Chemistry Video Request Service

Backend-only prototype for generating short educational chemistry videos from learner questions.

```text
FastAPI -> async job -> ADK 2.x Workflow -> Gemini 3.1 Flash-Lite -> VideoPlan -> Veo 3.1 Lite -> MP4 artifact
```

The service intentionally stays lightweight: in-memory jobs, local artifact storage, Docker Compose, and no frontend, database, external queue, or test harness.

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

ADK owns deterministic orchestration. Gemini handles prompt refinement into a structured Pydantic `VideoPlan`. Python code validates that plan, calls Veo, saves the MP4 locally, and verifies the finished artifact before the job is marked completed.

## Job Lifecycle

`POST /jobs` returns HTTP `202` with a job id and initial `queued` status. The background task moves the job to `processing`, runs the ADK workflow, and finishes as either:

- `completed`: local MP4 exists, is non-empty, and contains both video and audio streams.
- `failed`: Gemini, Veo, safety/RAI filtering, empty output, artifact download, or MP4 validation failed with a clear error.

Public states remain:

```text
queued
processing
completed
failed
```

## Generation Boundary

Gemini and Veo are configured separately because Gemini can use `global` while Veo is regional. Veo generates native audio through `generate_audio=True`; there is no separate TTS or audio muxing step.

The Veo node logs the `job_id`, completed operation name, provider error, generated video count, `rai_media_filtered_count`, and `rai_media_filtered_reasons` when available. This keeps provider errors, safety filtering, empty results, and artifact validation failures distinguishable in Docker logs.

## Persistence and Artifacts

Job state is stored in memory and resets when the container restarts. MP4s are stored under `./artifacts` through the Compose volume mount. The final submission videos under `artifacts/*.mp4` are not ignored by `.gitignore`, so they can be committed when needed.

## Cost Notes

The demo uses one 8-second 720p video per required prompt and requests one output video per job. There are no retries by default, no extra VLM scoring pass, and no duplicate generation step, keeping Phase 2 cost predictable.

## Known Limitations

- Jobs are in-memory only.
- Work is processed by FastAPI background asyncio tasks in one container.
- Artifact validation checks container-level MP4 structure, not educational quality.
- GCP project access, model availability, regional Veo quota, billing, and ADC credentials must be configured outside the app.

## GCP Setup

Enable Vertex AI in a billed Google Cloud project with access to the selected models:

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

## Configure

Create `.env` with at least:

```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.1-flash-lite
VEO_MODEL=veo-3.1-lite-generate-001
VEO_LOCATION=us-central1
ARTIFACT_DIR=/app/artifacts
```

Optional: set `VEO_OUTPUT_GCS_URI=gs://...` if your Veo access returns GCS artifacts instead of directly downloadable video bytes.

## Run

```bash
sudo docker compose up -d --build
sudo docker compose logs --tail=200 api
```

Health check:

```bash
curl http://localhost:8088/health
```

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `POST` | `/jobs` | Queue a chemistry video job |
| `GET` | `/jobs` | List jobs |
| `GET` | `/jobs/{id}` | Poll status |
| `GET` | `/jobs/{id}/artifact` | Retrieve completed MP4 |

## Demo

Run the existing script against the Docker API on port `8088`:

```bash
bash scripts/run_demo.sh
```

It submits the three required prompts, polls each job to completion, downloads the artifacts through FastAPI, and writes:

```text
artifacts/demo_ph_scale.mp4
artifacts/demo_covalent_bonds.mp4
artifacts/demo_ionic_vs_covalent.mp4
```
