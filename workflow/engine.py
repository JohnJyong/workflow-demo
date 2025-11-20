import asyncio
from typing import Dict, List, Set
from .models import WorkflowDefinition, WorkflowContext, NodeConfig
from .nodes import Node, StartNode, HttpNode, EndNode, AgentNode

class WorkflowEngine:
    def __init__(self, definition: WorkflowDefinition):
        self.definition = definition
        self.nodes: Dict[str, Node] = {}
        self.adjacency: Dict[str, List[str]] = {}
        self.in_degree: Dict[str, int] = {}
        self._initialize_graph()

    def _initialize_graph(self):
        node_map: Dict[str, NodeConfig] = {n.id: n for n in self.definition.nodes}
        
        for config in self.definition.nodes:
            # Instantiate nodes
            if config.type == "start":
                self.nodes[config.id] = StartNode(config)
            elif config.type == "http":
                self.nodes[config.id] = HttpNode(config)
            elif config.type == "end":
                self.nodes[config.id] = EndNode(config)
            elif config.type == "agent":
                self.nodes[config.id] = AgentNode(config)
            else:
                raise ValueError(f"Unknown node type: {config.type}")
            
            # Build graph
            self.adjacency[config.id] = config.next_nodes
            if config.id not in self.in_degree:
                self.in_degree[config.id] = 0
            
            for next_node_id in config.next_nodes:
                self.in_degree[next_node_id] = self.in_degree.get(next_node_id, 0) + 1

    async def run(self, initial_data: Dict = None, workflow_id: int = None, session_factory = None) -> Dict:
        context = WorkflowContext(data=initial_data or {})
        
        run_record = None
        db_session = None
        
        if workflow_id and session_factory:
            from .database import WorkflowRun
            from datetime import datetime
            db_session = next(session_factory())
            run_record = WorkflowRun(workflow_id=workflow_id, status="running", start_time=datetime.utcnow())
            db_session.add(run_record)
            db_session.commit()
            db_session.refresh(run_record)

        try:
            # Find start nodes (indegree 0)
            queue = [nid for nid, degree in self.in_degree.items() if degree == 0]
            
            # Current ready nodes
            ready_nodes = queue
            
            results = await self._execute_dag(ready_nodes, context)
            
            if run_record and db_session:
                from datetime import datetime
                run_record.status = "completed"
                run_record.end_time = datetime.utcnow()
                run_record.results = results
                db_session.add(run_record)
                db_session.commit()
                
            return results
        except Exception as e:
            if run_record and db_session:
                from datetime import datetime
                run_record.status = "failed"
                run_record.end_time = datetime.utcnow()
                run_record.error = str(e)
                db_session.add(run_record)
                db_session.commit()
            raise e

    async def _execute_dag(self, start_nodes: List[str], context: WorkflowContext):
        # Map of node_id -> Future
        futures: Dict[str, asyncio.Future] = {}
        
        # We need to know the parents of each node to wait for them
        parents: Dict[str, List[str]] = {}
        for nid, children in self.adjacency.items():
            for child in children:
                if child not in parents:
                    parents[child] = []
                parents[child].append(nid)

        async def run_node(node_id: str):
            # Wait for parents
            if node_id in parents:
                parent_ids = parents[node_id]
                # Wait for all parent futures to complete
                await asyncio.gather(*(futures[p] for p in parent_ids))
                
                # Check for skips
                should_skip = False
                
                # 1. Check if any direct parent is an AgentNode that explicitly didn't select us
                for p in parent_ids:
                    parent_node = self.nodes[p]
                    if parent_node.config.type == "agent":
                        parent_result = futures[p].result()
                        # If parent was skipped, it's result is "SKIPPED", so .get might fail if it's a string
                        if isinstance(parent_result, dict):
                            selected = parent_result.get("selected_node")
                            if selected and selected != node_id:
                                should_skip = True
                                break
                
                # 2. If not explicitly skipped by an agent, check if all parents were skipped
                # (Implicit skip propagation)
                if not should_skip and parent_ids:
                    all_parents_skipped = True
                    for p in parent_ids:
                        if futures[p].result() != "SKIPPED":
                            all_parents_skipped = False
                            break
                    if all_parents_skipped:
                        should_skip = True
                
                if should_skip:
                    print(f"Skipping node: {node_id}")
                    return "SKIPPED"
            
            # Execute current node
            node = self.nodes[node_id]
            print(f"Executing node: {node_id} ({node.config.type})")
            try:
                result = await node.execute(context)
                context.results[node_id] = result
            except Exception as e:
                print(f"Error in node {node_id}: {e}")
                raise e
            
            return result

        # Create futures for all nodes
        # But we can only schedule them if we know the topology. 
        # Actually, we can create the coroutines and schedule them, but they will block on `await parents`.
        # This is a valid pattern in asyncio.
        
        # Create a future for every node in the definition
        for node_config in self.definition.nodes:
            futures[node_config.id] = asyncio.Future()

        # Define the wrapper that sets the future result
        async def node_wrapper(node_id: str):
            try:
                res = await run_node(node_id)
                futures[node_id].set_result(res)
            except Exception as e:
                futures[node_id].set_exception(e)

        # Schedule all nodes
        tasks = []
        for node_config in self.definition.nodes:
            tasks.append(asyncio.create_task(node_wrapper(node_config.id)))
            
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        return context.results
