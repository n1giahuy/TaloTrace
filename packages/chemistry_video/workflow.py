from google.adk import START, Workflow
from google.adk.workflow import FunctionNode

from packages.chemistry_video.agents.prompt_refiner import prompt_refiner
from packages.chemistry_video.nodes.generate_video import generate_video_node
from packages.chemistry_video.nodes.validate_plan import validate_plan


validate_plan_node = FunctionNode(
    validate_plan,
    name="validate_plan",
)

chemistry_video_workflow = Workflow(
    name="chemistry_video_workflow",
    edges=[
        (
            START,
            prompt_refiner,
            validate_plan_node,
            generate_video_node,
        )
    ],
)

root_agent = chemistry_video_workflow
