# ADK-compatible entrypoint. The FastAPI app uses the same root workflow.
from packages.chemistry_video.workflow import root_agent

__all__ = ["root_agent"]
