from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from apps.api.schemas.jobs import CreateJobRequest, JobResponse
from packages.chemistry_video.bootstrap import job_service
from packages.chemistry_video.models.job import JobStatus


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(payload: CreateJobRequest) -> JobResponse:
    job = await job_service.create(payload.query)
    return JobResponse.from_job(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs() -> list[JobResponse]:
    return [JobResponse.from_job(job) for job in await job_service.list()]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = await job_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_job(job)


@router.get("/{job_id}/artifact", response_class=FileResponse)
async def get_artifact(job_id: str) -> FileResponse:
    job = await job_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETED or not job.artifact_path:
        raise HTTPException(status_code=409, detail="Video artifact is not ready")

    path = Path(job.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing")

    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=f"{job.id}.mp4",
    )
