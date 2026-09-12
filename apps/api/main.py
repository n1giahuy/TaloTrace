import logging

from fastapi import FastAPI

from apps.api.routes.jobs import router as jobs_router
from packages.chemistry_video.core.config import get_settings


settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(
    title="AI Chemistry Video Request Service",
    version="0.1.0-p1",
)
app.include_router(jobs_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "phase": "p1"}
