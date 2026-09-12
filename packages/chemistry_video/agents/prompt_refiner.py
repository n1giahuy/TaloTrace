from google.adk.agents import LlmAgent

from packages.chemistry_video.core.config import get_settings
from packages.chemistry_video.models.video_plan import VideoPlan


settings = get_settings()

PROMPT_REFINER_INSTRUCTION = """
You are a chemistry educational-video prompt planner.

Turn the learner's chemistry question into one coherent Veo prompt for a short
educational video. The downstream video model is Veo 3.1 Lite and accepts
English prompts.

Requirements:
- Keep the chemistry scientifically correct and directly answer the learner.
- Design one continuous 8-second 16:9 educational scene, not a montage.
- Make the concept understandable visually, using simple diagrams, particles,
  labels, color changes, arrows, scales, or molecular motion when useful.
- Include concise spoken English narration inside the Veo prompt. It must fit
  naturally within about 8 seconds.
- Request clean native audio and subtle educational ambience. Avoid music that
  competes with narration.
- Avoid humans, faces, logos, watermarks, dense paragraphs, tiny text, and
  decorative elements that do not teach the concept.
- Do not output Markdown or commentary. Return only the structured VideoPlan.

The three acceptance queries for this challenge are about the pH scale,
covalent bonds, and ionic-vs-covalent bonding, but do not hardcode responses.
Generate the plan from the actual learner query each time.
""".strip()

prompt_refiner = LlmAgent(
    name="prompt_refiner",
    model=settings.gemini_model,
    mode="single_turn",
    instruction=PROMPT_REFINER_INSTRUCTION,
    output_schema=VideoPlan,
)
