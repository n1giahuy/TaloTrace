import asyncio
from collections.abc import Iterable

from packages.chemistry_video.models.job import VideoJob, utc_now


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, VideoJob] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: VideoJob) -> VideoJob:
        async with self._lock:
            self._jobs[job.id] = job.model_copy(deep=True)
            return self._jobs[job.id].model_copy(deep=True)

    async def get(self, job_id: str) -> VideoJob | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    async def list(self) -> list[VideoJob]:
        async with self._lock:
            jobs: Iterable[VideoJob] = self._jobs.values()
            return sorted(
                (job.model_copy(deep=True) for job in jobs),
                key=lambda item: item.created_at,
                reverse=True,
            )

    async def update(self, job_id: str, **changes: object) -> VideoJob:
        async with self._lock:
            current = self._jobs[job_id]
            updated = current.model_copy(
                update={**changes, "updated_at": utc_now()},
                deep=True,
            )
            self._jobs[job_id] = updated
            return updated.model_copy(deep=True)
