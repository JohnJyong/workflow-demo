import httpx
from abc import ABC, abstractmethod
from typing import Any, Dict
from .models import NodeConfig, WorkflowContext

class Node(ABC):
    def __init__(self, config: NodeConfig):
        self.config = config

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> Any:
        pass

class StartNode(Node):
    async def execute(self, context: WorkflowContext) -> Any:
        # Start node simply passes initial params to the context or returns them
        # In this design, we'll assume initial data is injected into context before run,
        # or StartNode can merge its params into the data stream.
        return self.config.params

class HttpNode(Node):
    async def execute(self, context: WorkflowContext) -> Any:
        url = self.config.params.get("url")
        method = self.config.params.get("method", "GET")
        headers = self.config.params.get("headers", {})
        
        if url.startswith("mock://sleep/"):
            import asyncio
            seconds = float(url.split("/")[-1])
            await asyncio.sleep(seconds)
            return {"mock": "slept", "seconds": seconds}

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers)
            response.raise_for_status()
            return response.json()

class EndNode(Node):
    async def execute(self, context: WorkflowContext) -> Any:
        # Collects results from previous nodes or specific keys
        output_key = self.config.params.get("output_key")
        if output_key:
            return context.results.get(output_key)
        # Return a shallow copy to avoid circular reference if this result is stored back in context.results
        return context.results.copy()

class AgentNode(Node):
    async def execute(self, context: WorkflowContext) -> Any:
        import os
        import json
        
        # Configuration
        api_key = self.config.params.get("api_key") or os.environ.get("OPENAI_API_KEY")
        base_url = self.config.params.get("base_url", "https://api.openai.com/v1")
        model = self.config.params.get("model", "gpt-4o")
        prompt_template = self.config.params.get("prompt", "Select the best next node based on the input.")
        
        if not api_key:
            # Fallback for demo without key: use mock logic or raise error
            # For now, we'll print a warning and fallback to mock logic for safety if no key provided
            print("WARNING: No API key provided for AgentNode. Falling back to mock logic.")
            user_input = context.data.get("user_input", "")
            if "B" in user_input or "b" in user_input:
                 if len(self.config.next_nodes) > 1:
                     return {"selected_node": self.config.next_nodes[1]}
            return {"selected_node": self.config.next_nodes[0] if self.config.next_nodes else None}

        # 1. Construct Prompt
        # We need descriptions of next nodes. 
        # Since we don't have direct access to other node configs here easily without passing them in,
        # we might need to rely on the user providing descriptions in the params or we need to change Node signature.
        # However, we updated NodeConfig to have description. 
        # But `Node` class doesn't have access to the full `WorkflowDefinition` or other nodes.
        # We can pass the `WorkflowEngine` or `WorkflowDefinition` to `execute`? 
        # Or we can assume the `AgentNode` config has the necessary info.
        
        # WAIT: The `Node` is initialized with `NodeConfig`. It doesn't know about *other* nodes.
        # To fix this properly, we should probably pass the `engine` or `definition` to `execute`.
        # BUT, changing the signature of `execute` is a breaking change for the interface.
        # A simpler way for now: The user must provide the options in the `params` OR we assume the `next_nodes` IDs are descriptive enough.
        
        # Let's assume the IDs are descriptive enough for now, or the user puts descriptions in `params['options']`.
        
        options_str = ", ".join(self.config.next_nodes)
        
        system_prompt = (
            "You are a workflow routing assistant. "
            f"You must select exactly one next step from the following options: [{options_str}]. "
            "Return ONLY the ID of the selected node in JSON format like {\"id\": \"selected_id\"}."
        )
        
        user_content = f"Context: {json.dumps(context.data)}\nInstruction: {prompt_template}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # 2. Call LLM
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result_json = response.json()
                content = result_json["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                selected_id = parsed.get("id")
                
                # Validate
                if selected_id not in self.config.next_nodes:
                    print(f"LLM returned invalid ID: {selected_id}. Options: {self.config.next_nodes}")
                    # Fallback to first
                    selected_id = self.config.next_nodes[0] if self.config.next_nodes else None
                
                print(f"AgentNode selected path: {selected_id}")
                return {"selected_node": selected_id}
                
            except Exception as e:
                print(f"Error calling LLM: {e}")
                # Fallback
                return {"selected_node": self.config.next_nodes[0] if self.config.next_nodes else None}
