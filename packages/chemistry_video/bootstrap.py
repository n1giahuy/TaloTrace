from packages.chemistry_video.repositories.memory import InMemoryJobRepository
from packages.chemistry_video.runtime import ChemistryVideoRuntime
from packages.chemistry_video.services.job_service import JobService


job_repository = InMemoryJobRepository()
chemistry_video_runtime = ChemistryVideoRuntime()
job_service = JobService(job_repository, chemistry_video_runtime)
