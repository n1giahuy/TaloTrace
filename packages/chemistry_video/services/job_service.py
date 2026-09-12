import asyncio
import logging

from packages.chemistry_video.models.job import JobStatus, VideoJob
from packages.chemistry_video.repositories.memory import InMemoryJobRepository
from packages.chemistry_video.runtime import ChemistryVideoRuntime


logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        repository: InMemoryJobRepository,
        runtime: ChemistryVideoRuntime,
    ) -> None:
        self._repository = repository
        self._runtime = runtime
        self._tasks: set[asyncio.Task[None]] = set()

    async def create(self, query: str) -> VideoJob:
        job = await self._repository.create(VideoJob(query=query.strip()))
        task = asyncio.create_task(self._process(job.id), name=f"video-job-{job.id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def get(self, job_id: str) -> VideoJob | None:
        return await self._repository.get(job_id)

    async def list(self) -> list[VideoJob]:
        return await self._repository.list()

    async def _process(self, job_id: str) -> None:
        try:
            job = await self._repository.get(job_id)
            if job is None:
                return

            await self._repository.update(
                job_id,
                status=JobStatus.PROCESSING,
                error=None,
            )

            result = await self._runtime.generate(job_id=job_id, query=job.query)

            await self._repository.update(
                job_id,
                status=JobStatus.COMPLETED,
                artifact_path=result.artifact_path,
                error=None,
            )
        except Exception as exc:  # P1 keeps one understandable failure boundary.
            logger.exception("Video job %s failed", job_id)
            await self._repository.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
            )
