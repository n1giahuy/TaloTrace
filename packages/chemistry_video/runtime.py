from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from packages.chemistry_video.models.video_plan import ArtifactResult
from packages.chemistry_video.workflow import root_agent


class ChemistryVideoRuntime:
    def __init__(self) -> None:
        self.app = App(
            name="chemistry_video_app",
            root_agent=root_agent,
        )
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app=self.app,
            session_service=self.session_service,
        )

    async def generate(self, *, job_id: str, query: str) -> ArtifactResult:
        user_id = "chemistry-video-api"
        session_id = f"job-{job_id}"

        await self.session_service.create_session(
            app_name=self.app.name,
            user_id=user_id,
            session_id=session_id,
        )

        final_output: object | None = None
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=query)],
            ),
            state_delta={"job_id": job_id},
        ):
            # Workflow emits its terminal result as Event.output.
            if event.author == root_agent.name and event.output is not None:
                final_output = event.output

        if final_output is None:
            raise RuntimeError("ADK workflow completed without an artifact result.")

        return ArtifactResult.model_validate(final_output)
