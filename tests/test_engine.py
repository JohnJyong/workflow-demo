import pytest
from workflow.models import WorkflowDefinition, NodeConfig
from workflow.engine import WorkflowEngine

@pytest.mark.asyncio
async def test_engine_linear_execution():
    nodes = [
        NodeConfig(id="start", type="start", next_nodes=["end"]),
        NodeConfig(id="end", type="end")
    ]
    engine = WorkflowEngine(WorkflowDefinition(nodes=nodes))
    results = await engine.run()
    assert "start" in results
    assert "end" in results

@pytest.mark.asyncio
async def test_engine_parallel_execution():
    nodes = [
        NodeConfig(id="start", type="start", next_nodes=["p1", "p2"]),
        NodeConfig(id="p1", type="http", next_nodes=["end"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="p2", type="http", next_nodes=["end"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="end", type="end")
    ]
    engine = WorkflowEngine(WorkflowDefinition(nodes=nodes))
    results = await engine.run()
    assert "p1" in results
    assert "p2" in results
    assert "end" in results

@pytest.mark.asyncio
async def test_engine_conditional_skip():
    # Start -> Agent -> (A, B) -> End
    # Agent selects B. A should be skipped.
    nodes = [
        NodeConfig(id="start", type="start", next_nodes=["agent"]),
        NodeConfig(
            id="agent", 
            type="agent", 
            next_nodes=["a", "b"], 
            params={"force_selection": "b"}
        ),
        NodeConfig(id="a", type="http", next_nodes=["end"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="b", type="http", next_nodes=["end"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="end", type="end")
    ]
    engine = WorkflowEngine(WorkflowDefinition(nodes=nodes))
    results = await engine.run()
    
    assert results["agent"]["selected_node"] == "b"
    assert results["b"] != "SKIPPED"
    assert results["a"] == "SKIPPED"
    assert results["end"] != "SKIPPED" # End should run because B ran

@pytest.mark.asyncio
async def test_engine_skip_propagation():
    # Start -> Agent -> (A) -> End
    # Agent selects nothing (or invalid), forcing fallback to A? 
    # Let's test explicit skip.
    # Start -> Agent -> (A, B)
    # A -> A1 -> End
    # Agent selects B. A and A1 should be skipped.
    nodes = [
        NodeConfig(id="start", type="start", next_nodes=["agent"]),
        NodeConfig(
            id="agent", 
            type="agent", 
            next_nodes=["a", "b"], 
            params={"force_selection": "b"}
        ),
        NodeConfig(id="a", type="http", next_nodes=["a1"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="a1", type="http", next_nodes=["end"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="b", type="http", next_nodes=["end"], params={"url": "mock://sleep/0.01"}),
        NodeConfig(id="end", type="end")
    ]
    engine = WorkflowEngine(WorkflowDefinition(nodes=nodes))
    results = await engine.run()
    
    assert results["a"] == "SKIPPED"
    assert results["a1"] == "SKIPPED"
    assert results["b"] != "SKIPPED"
    assert results["end"] != "SKIPPED"
