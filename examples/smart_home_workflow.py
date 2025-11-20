import asyncio
import sys
import os

# Add parent directory to path to find 'workflow' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workflow.models import WorkflowDefinition, NodeConfig
from workflow.engine import WorkflowEngine

async def run_smart_home_demo(current_temp: float):
    print(f"\n--- Running Smart Home Demo (Current Temp: {current_temp}°C) ---")
    
    workflow_def = WorkflowDefinition(nodes=[
        # 1. Start Node (Input Temperature)
        NodeConfig(
            id="start",
            type="start",
            next_nodes=["get_price", "get_weather", "get_schedule"],
            params={}
        ),
        
        # 2. Parallel Data Fetching Nodes
        NodeConfig(
            id="get_price",
            type="http",
            next_nodes=["thermostat_agent"],
            params={
                "url": "mock://sleep/0.1", # Simulate API call
                # In a real app, this would return {"price": 0.15}
            }
        ),
        NodeConfig(
            id="get_weather",
            type="http",
            next_nodes=["thermostat_agent"],
            params={
                "url": "mock://sleep/0.1",
                # In a real app, this would return {"temp": 25, "condition": "Sunny"}
            }
        ),
        NodeConfig(
            id="get_schedule",
            type="http",
            next_nodes=["thermostat_agent"],
            params={
                "url": "mock://sleep/0.1",
                # In a real app, this would return {"user_home": True}
            }
        ),
        
        # 3. Agent Node (Decision Maker)
        NodeConfig(
            id="thermostat_agent",
            type="agent",
            description="Decides whether to turn on heater or AC based on context.",
            next_nodes=["turn_on_heater", "turn_on_ac"],
            params={
                "prompt": """
                Analyze the current situation.
                - 'initial_data' contains the 'current_temp'.
                - 'previous_results' contains mock data for price, weather, and schedule.
                
                Logic:
                - If current_temp < 18, turn on heater.
                - If current_temp > 26, turn on AC.
                - Otherwise, default to AC (just for this demo structure which requires a choice).
                
                Return the ID of the action to take.
                """,
                # Mock logic fallback if no API key
                "force_selection": "turn_on_heater" if current_temp < 18 else "turn_on_ac"
            }
        ),
        
        # 4. Action Nodes
        NodeConfig(
            id="turn_on_heater",
            type="http",
            next_nodes=["end"],
            params={
                "url": "mock://sleep/0.5",
                "method": "POST"
            }
        ),
        NodeConfig(
            id="turn_on_ac",
            type="http",
            next_nodes=["end"],
            params={
                "url": "mock://sleep/0.5",
                "method": "POST"
            }
        ),
        
        # 5. End Node
        NodeConfig(
            id="end",
            type="end",
            next_nodes=[],
            params={}
        )
    ])
    
    engine = WorkflowEngine(workflow_def)
    
    # Inject initial data
    initial_data = {"current_temp": current_temp}
    
    # We need to manually inject mock results for the HTTP nodes because our mock:// implementation 
    # in HttpNode just returns {"mock": "slept"}. 
    # In a real scenario, the HttpNode would return actual data.
    # For this demo, the Agent will see {"mock": "slept"} in previous_results.
    # So the Agent prompt logic above relies on 'current_temp' from initial_data mostly, 
    # or we can assume the Agent "hallucinates" the other data or we improve the mock.
    
    results = await engine.run(initial_data=initial_data)
    
    print("Workflow Execution Results:")
    for node_id, result in results.items():
        if result == "SKIPPED":
            print(f"  {node_id}: SKIPPED")
        else:
            print(f"  {node_id}: Executed")

async def main():
    # Case 1: Cold -> Heater
    await run_smart_home_demo(15)
    
    # Case 2: Hot -> AC
    await run_smart_home_demo(30)

if __name__ == "__main__":
    asyncio.run(main())
