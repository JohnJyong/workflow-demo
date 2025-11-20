import pytest
from workflow.models import NodeConfig, WorkflowContext
from workflow.nodes import StartNode, HttpNode, EndNode, AgentNode

@pytest.mark.asyncio
async def test_start_node():
    config = NodeConfig(id="start", type="start", params={"foo": "bar"})
    node = StartNode(config)
    context = WorkflowContext()
    result = await node.execute(context)
    assert result == {"foo": "bar"}

@pytest.mark.asyncio
async def test_http_node_mock():
    config = NodeConfig(
        id="http", 
        type="http", 
        params={"url": "mock://sleep/0.01"}
    )
    node = HttpNode(config)
    context = WorkflowContext()
    result = await node.execute(context)
    assert result["mock"] == "slept"
    assert result["seconds"] == 0.01

@pytest.mark.asyncio
async def test_end_node():
    config = NodeConfig(id="end", type="end")
    node = EndNode(config)
    context = WorkflowContext(results={"prev": "data"})
    result = await node.execute(context)
    assert result == {"prev": "data"}

@pytest.mark.asyncio
async def test_end_node_output_key():
    config = NodeConfig(id="end", type="end", params={"output_key": "prev"})
    node = EndNode(config)
    context = WorkflowContext(results={"prev": "data", "other": "ignored"})
    result = await node.execute(context)
    assert result == "data"

@pytest.mark.asyncio
async def test_agent_node_fallback():
    # Test fallback logic when no API key
    config = NodeConfig(
        id="agent", 
        type="agent", 
        next_nodes=["a", "b"],
        params={"force_selection": "b"}
    )
    node = AgentNode(config)
    context = WorkflowContext()
    result = await node.execute(context)
    assert result["selected_node"] == "b"

@pytest.mark.asyncio
async def test_agent_node_default_fallback():
    # Test default fallback (first node)
    config = NodeConfig(
        id="agent", 
        type="agent", 
        next_nodes=["a", "b"]
    )
    node = AgentNode(config)
    context = WorkflowContext(data={"user_input": "nothing"})
    result = await node.execute(context)
    assert result["selected_node"] == "a"
