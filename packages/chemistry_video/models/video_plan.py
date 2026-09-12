from pydantic import BaseModel, Field


class VideoPlan(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    learning_goal: str = Field(min_length=10, max_length=300)
    veo_prompt: str = Field(min_length=80, max_length=5000)


class ArtifactResult(BaseModel):
    artifact_path: str
    content_type: str = "video/mp4"
    size_bytes: int
    title: str
