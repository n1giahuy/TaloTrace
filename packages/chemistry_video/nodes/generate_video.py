import asyncio
import json
import logging
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from google import genai
from google.adk import Context
from google.adk.workflow import FunctionNode
from google.cloud import storage
from google.genai import types

from packages.chemistry_video.core.config import get_settings
from packages.chemistry_video.models.video_plan import ArtifactResult, VideoPlan


logger = logging.getLogger(__name__)
settings = get_settings()


def _download_gcs_uri(uri: str, destination: Path) -> None:
    parsed = urlparse(uri)
    if parsed.scheme != "gs" or not parsed.netloc:
        raise ValueError(f"Not a GCS URI: {uri}")

    bucket_name = parsed.netloc
    blob_name = parsed.path.lstrip("/")
    storage_client = storage.Client(project=settings.google_cloud_project)
    storage_client.bucket(bucket_name).blob(blob_name).download_to_filename(destination)


def _save_generated_video(client: genai.Client, video: types.Video, destination: Path) -> None:
    # Newer SDK responses can already contain bytes.
    if video.video_bytes:
        video.save(destination)
        return

    # Vertex may return a GCS URI when output_gcs_uri is configured.
    if video.uri and video.uri.startswith("gs://"):
        _download_gcs_uri(video.uri, destination)
        return

    # Otherwise ask the Gen AI SDK to hydrate the generated Video object,
    # then use its public save() helper.
    client.files.download(file=video)
    video.save(destination)


def _validate_mp4_artifact(path: Path, job_id: str) -> None:
    if not path.exists():
        raise RuntimeError(
            f"Artifact validation failed for job {job_id}: file is missing."
        )
    if path.stat().st_size <= 0:
        raise RuntimeError(
            f"Artifact validation failed for job {job_id}: file is empty."
        )

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Artifact validation failed: ffprobe is not installed.") from exc

    if result.returncode != 0:
        detail = (
            result.stderr.strip() or result.stdout.strip() or "unknown ffprobe error"
        )
        raise RuntimeError(
            f"Artifact validation failed for job {job_id}: {detail}"
        )

    try:
        streams = json.loads(result.stdout or "{}").get("streams", [])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Artifact validation failed for job {job_id}: invalid ffprobe output."
        ) from exc
    stream_types = {stream.get("codec_type") for stream in streams}
    if "video" not in stream_types:
        raise RuntimeError(
            f"Artifact validation failed for job {job_id}: no video stream."
        )
    if "audio" not in stream_types:
        raise RuntimeError(
            f"Artifact validation failed for job {job_id}: no audio stream."
        )

    logger.info(
        "Artifact validation passed for job %s: path=%s size_bytes=%s streams=%s",
        job_id,
        path,
        path.stat().st_size,
        sorted(stream_type for stream_type in stream_types if stream_type),
    )


def _generate_video_sync(plan: VideoPlan, job_id: str) -> ArtifactResult:
    destination = settings.artifact_dir / f"{job_id}.mp4"

    client = genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.veo_location,
    )

    config_kwargs: dict[str, object] = {
        "number_of_videos": 1,
        "duration_seconds": settings.veo_duration_seconds,
        "aspect_ratio": settings.veo_aspect_ratio,
        "resolution": settings.veo_resolution,
        "person_generation": "dont_allow",
        "generate_audio": True,
    }

    if settings.veo_output_gcs_uri:
        base = settings.veo_output_gcs_uri.rstrip("/")
        config_kwargs["output_gcs_uri"] = f"{base}/{job_id}/"

    logger.info("Submitting Veo generation for job %s", job_id)
    operation = client.models.generate_videos(
        model=settings.veo_model,
        source=types.GenerateVideosSource(prompt=plan.veo_prompt),
        config=types.GenerateVideosConfig(**config_kwargs),
    )

    while not operation.done:
        time.sleep(settings.veo_poll_seconds)
        operation = client.operations.get(operation)

    operation_error = getattr(operation, "error", None)
    response = operation.result or operation.response
    generated_videos = getattr(response, "generated_videos", None) or []
    rai_media_filtered_count = (
        getattr(response, "rai_media_filtered_count", None) if response else None
    )
    rai_media_filtered_reasons = (
        getattr(response, "rai_media_filtered_reasons", None) if response else None
    )

    logger.info(
        "Veo operation completed for job %s: operation=%s error=%s "
        "generated_video_count=%s rai_media_filtered_count=%s "
        "rai_media_filtered_reasons=%s",
        job_id,
        operation.name,
        operation_error,
        len(generated_videos),
        rai_media_filtered_count,
        rai_media_filtered_reasons,
    )

    if operation_error:
        raise RuntimeError(f"Veo operation failed: {operation_error}")

    if not generated_videos:
        if rai_media_filtered_count:
            raise RuntimeError(
                "Veo output was filtered by RAI policies: "
                f"{rai_media_filtered_reasons or 'no reason provided'}"
            )
        raise RuntimeError(
            "Veo completed without returning a generated video "
            f"(rai_media_filtered_count={rai_media_filtered_count}, "
            f"rai_media_filtered_reasons={rai_media_filtered_reasons})."
        )

    video = generated_videos[0].video
    if video is None:
        raise RuntimeError("Veo returned an empty video object.")

    _save_generated_video(client, video, destination)
    _validate_mp4_artifact(destination, job_id)

    return ArtifactResult(
        artifact_path=str(destination),
        size_bytes=destination.stat().st_size,
        title=plan.title,
    )


async def generate_video(ctx: Context, node_input: VideoPlan) -> ArtifactResult:
    job_id = str(ctx.state.get("job_id", "")).strip()
    if not job_id:
        raise ValueError("Workflow state is missing job_id.")

    return await asyncio.to_thread(_generate_video_sync, node_input, job_id)


# Keep retries out of Phase 2 unless a specific transient failure is identified.
generate_video_node = FunctionNode(
    func=generate_video,
    name="generate_video",
    timeout=600,
)
