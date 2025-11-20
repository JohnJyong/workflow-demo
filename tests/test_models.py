import pytest
from workflow.models import NodeConfig, WorkflowDefinition, WorkflowContext

def test_node_config_creation():
    config = NodeConfig(id="test_node", type="start")
    assert config.id == "test_node"
    assert config.type == "start"
    assert config.next_nodes == []
    assert config.params == {}

def test_node_config_with_params():
    config = NodeConfig(
        id="http_node", 
        type="http", 
        next_nodes=["end"], 
        params={"url": "http://example.com"}
    )
    assert config.params["url"] == "http://example.com"
    assert config.next_nodes == ["end"]

def test_workflow_definition():
    node1 = NodeConfig(id="start", type="start", next_nodes=["end"])
    node2 = NodeConfig(id="end", type="end")
    workflow = WorkflowDefinition(nodes=[node1, node2])
    assert len(workflow.nodes) == 2
    assert workflow.nodes[0].id == "start"

def test_workflow_context():
    context = WorkflowContext(data={"initial": "value"})
    assert context.data["initial"] == "value"
    assert context.results == {}
