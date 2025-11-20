import asyncio
import time
import sys
import os

# Add parent directory to path to find 'workflow' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workflow.models import WorkflowDefinition, NodeConfig
from workflow.engine import WorkflowEngine

async def main():
    # Define a workflow: Start -> (Http1, Http2) -> End
    # Http1 and Http2 should run in parallel.
    
    workflow_def = WorkflowDefinition(nodes=[
        NodeConfig(
            id="start",
            type="start",
            next_nodes=["http1", "http2"],
            params={"initial": "data"}
        ),
        NodeConfig(
            id="http1",
            type="http",
            next_nodes=["end"],
            params={
                "url": "mock://sleep/2", # 2 seconds delay
                "method": "GET"
            }
        ),
        NodeConfig(
            id="http2",
            type="http",
            next_nodes=["end"],
            params={
                "url": "mock://sleep/2", # 2 seconds delay
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
    
    print("Starting workflow...")
    start_time = time.time()
    
    results = await engine.run()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\nWorkflow completed.")
    print(f"Total duration: {duration:.2f} seconds")
    
    # Validation: If parallel, duration should be ~2s, not ~4s.
    if duration < 3.5:
        print("SUCCESS: Nodes ran in parallel.")
    else:
        print("FAILURE: Nodes ran sequentially.")
        
    print("Results:", results.keys())

if __name__ == "__main__":
    asyncio.run(main())
