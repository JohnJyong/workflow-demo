import asyncio
import time
from workflow.models import WorkflowDefinition, NodeConfig
from workflow.engine import WorkflowEngine

async def run_demo(input_text: str, expected_path: str):
    print(f"\n--- Running demo with input: '{input_text}' ---")
    
    workflow_def = WorkflowDefinition(nodes=[
        NodeConfig(
            id="start",
            type="start",
            next_nodes=["agent"],
            params={}
        ),
        NodeConfig(
            id="agent",
            type="agent",
            next_nodes=["path_a", "path_b"],
            params={
                "prompt": "Decide based on input",
                # Mock logic in AgentNode checks for "B" in input to select path_b
            }
        ),
        NodeConfig(
            id="path_a",
            type="http",
            next_nodes=["end"],
            params={
                "url": "mock://sleep/0.1",
                "method": "GET"
            }
        ),
        NodeConfig(
            id="path_b",
            type="http",
            next_nodes=["end"],
            params={
                "url": "mock://sleep/0.1",
                "method": "GET"
            }
        ),
        NodeConfig(
            id="end",
            type="end",
            next_nodes=[],
            params={}
        )
    ])
    
    engine = WorkflowEngine(workflow_def)
    
    initial_data = {"user_input": input_text}
    results = await engine.run(initial_data=initial_data)
    
    print("Results:", results.keys())
    
    # Verification
    if expected_path in results and results[expected_path] != "SKIPPED":
        print(f"SUCCESS: {expected_path} was executed.")
    else:
        print(f"FAILURE: {expected_path} was NOT executed.")
        
    other_path = "path_b" if expected_path == "path_a" else "path_a"
    if other_path in results and results[other_path] == "SKIPPED":
        print(f"SUCCESS: {other_path} was skipped.")
    elif other_path not in results:
        # If it's not in results at all, that might be fine depending on implementation, 
        # but our engine puts everything in results.
        print(f"SUCCESS: {other_path} was skipped (not in results).")
    else:
        print(f"FAILURE: {other_path} was executed (result: {results[other_path]}).")

async def main():
    await run_demo("Go to A", "path_a")
    await run_demo("Go to B", "path_b")

if __name__ == "__main__":
    asyncio.run(main())
