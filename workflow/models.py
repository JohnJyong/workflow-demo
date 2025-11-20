from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class NodeConfig(BaseModel):
    id: str
    type: Literal["start", "http", "end", "agent"]
    description: Optional[str] = None
    next_nodes: List[str] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)

class WorkflowDefinition(BaseModel):
    nodes: List[NodeConfig]

class WorkflowContext(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
