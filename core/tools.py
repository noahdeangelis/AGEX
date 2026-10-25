import inspect
import json

# Registers tools with a custom API
class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, description: str):
        """Register a python function as a tool."""
        def decorator(func):
            sig = inspect.signature(func)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                param_type = "string" # Default to string
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"

                properties[param_name] = {"type": param_type, "description": f"The {param_name} parameter."}
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            self.tools[name] = {
                "function": func,
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            return func
        return decorator

    def get_schemas(self, exclude_names=None):
        excluded = set(exclude_names or ())

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for tool in self.tools.values()
            if tool["name"] not in excluded
        ]
tool_registry = ToolRegistry()

#
# Hard coded tools. Required
#
# This tool seemed to help smaller models.
@tool_registry.register("think", "Simply get a chance to think about the task. This tool does not return anything to the user.")
def think(answer: str):
    return answer

#
# Removed for now
#

# @tool_registry.register("start_sub_agent", "Launch an independent AI sub-agent to complete a task. Returns an agent_id for checking its progress and result. Use for tasks that can be delegated independently.")
# def start_sub_agent(objective: str, role: str, context: str = ""):
#     from agent import get_current_mode
#     from subagents import sub_agents

#     result = sub_agents.start_sub_agent(objective, role, context, get_current_mode())
#     return json.dumps(result)

# @tool_registry.register("check_sub_agent", "Check the status of a sub-agent and retrieve its result.")
# def check_sub_agent(agent_id: str):
#     from subagents import sub_agents

#     result = sub_agents.check_sub_agent(agent_id)
#     return json.dumps(result)

# @tool_registry.register("wait_for_sub_agents", "Wait for multiple sub-agents to finish. Python handles the waiting internally, avoiding repeated model polling. Provide agent_ids as a JSON array string, e.g. '[\"agent_12345678\", \"agent_abcdefgh\"]'.")
# def wait_for_sub_agents(agent_ids: str, timeout_seconds: int = 600, poll_interval: float = 2.0):
#     from subagents import sub_agents

#     try:
#         ids = json.loads(agent_ids)

#         if not isinstance(ids, list):
#             return json.dumps({"error": "agent_ids must be a JSON array."})

#         result = sub_agents.wait_for_sub_agents(ids, timeout_seconds=timeout_seconds, poll_interval=poll_interval)
#         return json.dumps(result, ensure_ascii=False)

#     except json.JSONDecodeError:
#         return json.dumps({"error": "agent_ids must be a valid JSON array string."})

# @tool_registry.register("message_sub_agent", "Queue additional instructions for a running sub-agent.")
# def message_sub_agent(agent_id: str, message: str):
#     from subagents import sub_agents

#     result = sub_agents.message(agent_id, message)
#     return json.dumps(result)