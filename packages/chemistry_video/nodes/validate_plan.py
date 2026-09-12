from packages.chemistry_video.models.video_plan import VideoPlan


def validate_plan(node_input: VideoPlan) -> VideoPlan:
    prompt = node_input.veo_prompt.strip()
    if len(prompt) < 80:
        raise ValueError("Refined Veo prompt is too short to be useful.")
    if not node_input.learning_goal.strip():
        raise ValueError("Missing learning goal.")
    return node_input.model_copy(update={"veo_prompt": prompt})
