from app.engine.harness import run_harness
from app.engine.state import GraphState


async def tester_agent(state: GraphState) -> dict:
    artifacts = dict(state.get("generated_artifacts", {}))
    diff = str(artifacts.get("diff", ""))
    project_root = state.get("project_root", "")

    result = await run_harness(project_root=project_root, diff_text=diff)
    artifacts["harness"] = result

    return {
        "generated_artifacts": artifacts,
        "harness_result": result,
        "current_node": "tester_agent",
    }
