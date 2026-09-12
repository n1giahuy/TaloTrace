from datetime import datetime

from pydantic import BaseModel, Field

from packages.chemistry_video.models.job import JobStatus, VideoJob


class CreateJobRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)


class JobResponse(BaseModel):
    id: str
    query: str
    status: JobStatus
    artifact_url: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_job(cls, job: VideoJob) -> "JobResponse":
        return cls(
            id=job.id,
            query=job.query,
            status=job.status,
            artifact_url=(
                f"/jobs/{job.id}/artifact"
                if job.status == JobStatus.COMPLETED and job.artifact_path
                else None
            ),
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
