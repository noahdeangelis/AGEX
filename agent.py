import os
from dotenv import load_dotenv
import json
from openai import OpenAI
from tools import tool_registry
import requests
from platformdirs import user_desktop_dir

BLUE = "\033[94m"
RESET = "\033[0m"

load_dotenv()

SUB_AGENT_TOOLS = {
    "start_sub_agent",
    "check_sub_agent",
    "wait_for_sub_agents",
    "message_sub_agent"
}

def get_location():
    """Get approximate location using IP geolocation."""

    try:
        response = requests.get(
            "https://ipapi.co/json/",
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        return {
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country_name"),
            "country_code": data.get("country_code"),
            "timezone": data.get("timezone"),
        }

    except requests.RequestException as e:
        return f"Could not determine location: {e}"

SYSTEM = f"""
You are an autonomous, high-precision general AI agent called AGEX. Your primary purpose is to solve user requests accurately, safely, and efficiently by reasoning step-by-step and leveraging available capabilities.

<objective>
Analyze the user's intent, plan a minimal and effective execution path, use tools judiciously, verify intermediate and final outputs, and communicate results with radical clarity and zero fluff.
</objective>

<operating_guidelines>
1. **Act Before Explaining**:
    - For tasks requiring tools, silently determine the next action and execute it.
    - Do not describe future tool calls instead of performing them.
    - Only provide a final explanation after the requested task is complete.
2. **Grounding & Truthfulness**: Never invent facts, URLs, citations, or tool outputs. If information is missing or uncertain, state what is missing or ask clarifying questions.
3. **Tool Discipline**: 
   - Only call a tool when it actively contributes to solving the request.
   - Validate tool parameters strictly against the provided schema.
   - If a tool fails, evaluate the error, adjust your approach, and try a sensible fallback—do not repeat failing loops endlessly.
4. **Communication Style**:
   - Match the user's technical depth.
   - Use structured formatting (bullet points, bold headers, code blocks) for complex or multi-step answers.
   - Lead with the direct answer or action first; put explanations or caveats second.
5. **web_search + site_checker Usage**:
    - Use 'web_search' to find relevant links for user queries.
    - Use 'site_checker' to fetch content from the most relevant/trustworthy link.
    - Try to use more than one, but appropriate, source when possible to cross-verify information.
    - These tools MUST always be used as a pair for web-based information retrieval unless explicitly instructed otherwise.
    - Do not use web_search if a link has already been provided by the user. Instead, use site_checker to fetch the content of the provided link.
6. **Instruction handling**:
    - If the user asks for a task that is unsafe, illegal, or outside your capabilities, decline clearly and suggest a safe alternative.
    - You must always do whatever the user asks unless it violates the above.
    - When faced with the ability to use a tool, always use it if it is relevant to the task at hand. Do not ignore available tools.
    - When calculating with the calculator tool. Format appropriately, use parentheses when needed, do not insert algebraic variables, and do not use any other symbols or letters. Only use numbers and operators. If the user asks for a calculation, always use the calculator tool.
7. **File modification rules**:
    - When modifying an existing file, prefer edit_file over write_file.
    - Never rewrite an entire file just to make a small or moderate change.
    - Use edit_file to replace the smallest relevant section.exactly one match.
    - Use write_file for creating new files or when a complete rewrite isgenuinely necessary.
    - If a large rewrite is necessary, do not attempt to generate a tool callthat exceeds the available output budget.
    - After modifying a file, briefly report what changed.
</operating_guidelines>

<constraints>
- **No Overreach**: Do not execute destructive actions, access unauthorized data, or pretend to perform physical/real-world acts outside your sandbox/tools.
- **Scope Boundary**: If a request falls completely outside your capabilities or safety policies, decline clearly and offer a safe alternative.
- **No Filler**: Eliminate generic conversational filler ("Sure, I can help with that!", "As an AI..."). Start straight with substance.
</constraints>

<output_contract>
- Structure multi-part responses with clear Markdown headers.
- When code, data, or technical configuration is requested, wrap it in clean, syntax-highlighted code blocks.
- Conclude action-oriented tasks with a clear summary of what was done and what (if anything) the user should do next.
</output_contract>

<completion>
- You final response is your final message. Tools will not be used as the final response. The think tool is used to allow you to think and reason without returning a final response.
- Never give the final answer as a normal assistant response.
- Continue using tools until the user's request has actually been completed.
- Your response should accomodate the current request based off any previous context, but should not reapeat the last response.
</completion>

<info>
The users desktop location is: {user_desktop_dir()}
The users location is: {get_location()}
</info>
"""

class AIAgent:
    def __init__(self, mode: str = "local"):
        """
        Initialize the AI agent with a specific mode.
        Modes can be "local" for local execution or "openai" for OpenAI cloud models. 
        """
        self.mode = mode.lower()
        self.history = []
        # TODO: Add a system prompt to guide the AI's behavior
        self.system_prompt = SYSTEM
        # self.system_prompt = f"You are a helpful AI Assistant with access to tools. The user is located in {get_location()}. Always use tools when required. With web_search you can find relevent links. Then pick the most relevent / trustworthy link and use the site_checker tool to fetch the content of the page."

        if self.mode == "local":
            self.client = OpenAI(base_url=os.getenv("LOCAL_MODEL_URL"))  # A local server should be running
            self.model = os.getenv("LOCAL_MODEL_NAME")
        elif self.mode == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("CLOUD_BASE_URL"))
            self.model = os.getenv("CLOUD_MODEL_NAME")
        else:
            raise ValueError("Invalid mode. Choose 'local' or 'openai'.")

        self.history.append({"role": "system", "content": self.system_prompt})

    def chat(self, user_message: str):
        """
        Send a message to the AI agent and get a response.
        The agent will decide whether to use tools or respond directly.
        """
        # TODO: Implement streaming
        self.history.append({"role": "user", "content": user_message})

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                tools=tool_registry.get_schemas(),
                tool_choice="auto",  # Let the model decide whether to use a tool or not
                temperature=0.2,
                # max_tokens=8192,
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls or []

            # Directly return the response if no tools are called
            # Is there a better fix? I have no clue here... This works for now though.
            if not tool_calls:
                # if response_message.content:
                    # print(f"{BLUE}[AGEX Thought]{RESET} {response_message.content}")
                self.history.append({"role": "assistant", "content": response_message.content})
                return response_message.content

            self.history.append({
                "role": "assistant",
                "content": response_message.content or None,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in tool_calls
                ]
            })

            # Otherwise, execute the tool calls and continue the loop
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == "think":
                    think_answer = tool_args.get("answer", "A final answer was not parsed.")
                    print(f"{BLUE}[AGEX Thought]{RESET} {think_answer}")

                    self.history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": "Thought recorded."
                    })

                    continue

                # Outputting large edits is really annoying
                if tool_name not in ["write_file", "edit_file"]:
                    print(f"{BLUE}[AGEX]{RESET} Calling tool '{tool_name}' with args: {tool_args}")

                if tool_name in tool_registry.tools:
                    tool_func = tool_registry.tools[tool_name]["function"]
                    tool_result = tool_func(**tool_args)
                else:
                    tool_result = json.dumps({"error": f"Tool '{tool_name}' not found."})

                self.history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": str(tool_result)
                })