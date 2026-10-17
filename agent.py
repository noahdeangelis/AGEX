import os
from dotenv import load_dotenv
import json
from openai import OpenAI
from tools import tool_registry
import requests
from platformdirs import user_desktop_dir
import time
from openai import APIStatusError

BLUE = "\033[94m"
YELLOW = "\033[38;5;221m"
RED = "\033[38;5;203m"
RESET = "\033[0m"

def is_tpm_rpm_limit(error_text):
    is_tpm = ("tokens per minute" in error_text or "token per minute" in error_text)
    is_rpm = ("requests per minute" in error_text or "request per minute" in error_text)
    return is_tpm or is_rpm

def is_usage_exhausted(error_text):
    texts = (
        "tokens per day",
        "requests per day",
        "insufficient_quota",
        "quota_exceeded",
        "usage limit",
        "daily limit",
    )
    return any(possible in error_text for possible in texts)

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
        self.system_prompt = SYSTEM

        if self.mode not in ("local", "openai"):
            raise ValueError("Invalid mode. Choose 'local' or 'openai'.")

        # If any local config
        self.local = os.getenv("LOCAL_MODEL_NAME")
        self.local_url = os.getenv("LOCAL_MODEL_URL")

        self.primary = ""
        self.backup = None
        self.backup_client = None

        # Every entry contains its own client and model configuration.
        self.model_configs = []

        if self.mode == "openai":
            primary = os.getenv("CLOUD_MODEL_NAME")
            primary_url = os.getenv("CLOUD_BASE_URL")
            primary_api = os.getenv("OPENAI_API_KEY")

            if not primary or not primary_url or not primary_api:
                raise ValueError("CLOUD_MODEL_NAME, CLOUD_BASE_URL and OPENAI_API_KEY must be configured for cloud mode.")

            self.model_configs.append({
                "name": primary,
                "model": primary,
                "client": OpenAI(api_key=primary_api, base_url=primary_url),
                "is_primary": True,
                "is_local": False,
                "is_backup": False,
                "backup_no": None,
            })

        # Discover any backups
        backup_no = 1 # Start at 1

        while True:
            model = os.getenv(f"BACKUP_{backup_no}_MODEL_NAME")
            if not model: # Doesn't exist
                break

            base_url = os.getenv(f"BACKUP_{backup_no}_BASE_URL")
            api_key = os.getenv(f"BACKUP_{backup_no}_API_KEY")

            if not base_url or not api_key:
                print(f"{YELLOW}[AGEX] Skipping incomplete backup {backup_no} config.{RESET}")
                backup_no += 1
                continue

            self.model_configs.append({
                "name": model,
                "model": model,
                "client": OpenAI(api_key=api_key, base_url=base_url),
                "is_primary": False,
                "is_local": False,
                "is_backup": True,
                "backup_no": backup_no,
            })

            print(f"{BLUE}[AGEX]{RESET} Registered backup {backup_no}: {model}")
            backup_no += 1

        # Configure the local model (if any)
        if self.local and self.local_url:
            self.local_client = OpenAI(base_url=self.local_url) # No API key

            # Local mode uses the local model as the primary model.
            # For now you can only have Local vs Cloud primarys.
            # You can always use a backup or more if you want cloud and local run.
            if self.mode == "local":
                self.model_configs.insert(0, {
                    "name": self.local,
                    "model": self.local,
                    "client": self.local_client,
                    "is_primary": True,
                    "is_local": True,
                    "is_backup": False,
                    "backup_no": None,
                })

            # In cloud mode you can use the local model as the final fallback/backup after all cloud backups hit their limits.
            elif os.getenv("LOCAL_MODEL_FALLBACK", "false").lower() in ("true", "1", "yes"):
                self.model_configs.append({
                    "name": self.local,
                    "model": self.local,
                    "client": self.local_client,
                    "is_primary": False,
                    "is_local": True,
                    "is_backup": False,
                    "backup_no": None,
                })

        # This should never occur
        if not self.model_configs:
            raise ValueError("No models are configured.")

        self.current_model = 0
        self.client = self.model_configs[0]["client"]
        self.backup = self.model_configs[1]["model"] if len(self.model_configs) > 1 else None
        self.backup_client = self.model_configs[1]["client"] if len(self.model_configs) > 1 else None

        self.history.append({"role": "system", "content": self.system_prompt})

    def get_models(self):
        """
        Returns models of the format: [(model_name, is_primary, is_local, is_backup, backup_no or None)] of size n models
        Backup count starts from 1.
        """
        return [
            (
                config["model"],
                config["is_primary"],
                config["is_local"],
                config["is_backup"],
                config["backup_no"],
            )
            for config in self.model_configs
        ]

    def set_model(self, model_name):
        """Switch the active model without clearing conversation history."""

        for index, config in enumerate(self.model_configs):
            if config["model"] == model_name:
                self.current_model = index
                self.client = config["client"]

                print(f"{BLUE}[AGEX]{RESET} Switched to {model_name}")
                return True

        print(f"{RED}[AGEX] Model '{model_name}' is not configured.{RESET}")
        return False

    # TODO: Add type specifications
    def get_response(self, max_retries=5, **kwargs):
        """Calls a request function and intercepts token errors (code 429)"""

        # If nothing is set up correctly
        if not self.model_configs:
            raise RuntimeError("No models are configured.")
        # Crazy bugs if this triggers
        if not 0 <= self.current_model < len(self.model_configs):
            raise RuntimeError("The selected model index is invalid.")

        for model_idx in range(self.current_model, len(self.model_configs)):
            config = self.model_configs[model_idx]

            model = config["model"]
            client = config["client"]

            attempt = 0 # Track attempts tpm/rpm retries before giving up

            while True:
                try:
                    response = client.chat.completions.create(model=model, **kwargs)

                    # Remember the model that successfully responded.
                    self.current_model = model_idx
                    self.client = client

                    print(model_idx)

                    return response
                
                except APIStatusError as e:
                    if e.status_code != 429: # TPM, RPM, Usage errors
                        raise

                    error_text = str(e).lower()
                    if is_tpm_rpm_limit(error_text):
                        if attempt >= max_retries:
                            raise

                        attempt += 1
                        print(f"\n{YELLOW}[AGEX] TPM/RPM limit on {model}. Waiting 60 seconds before continuing. Attempt {attempt}/{max_retries}{RESET}")
                        time.sleep(60)
                        continue

                    # Switch models if usage limit is hit
                    if is_usage_exhausted(error_text):
                        if model_idx + 1 < len(self.model_configs):
                            next_config = self.model_configs[model_idx + 1]
                            print(f"\n{YELLOW}[AGEX]: Usage limit reached on {model}. Switching to {next_config['model']}{RESET}")
                            self.current_model = model_idx + 1 # So it carries between messages
                            break

                        print(f"\n{RED}[AGEX] All configured models have exhuasted their usage limits.{RESET}")
                        raise
                raise # Unhandled error
        raise RuntimeError("No model returned a response.") # Just in case

    def chat(self, user_message: str):
        """
        Send a message to the AI agent and get a response.
        The agent will decide whether to use tools or respond directly.
        """
        # TODO: Implement streaming
        self.history.append({"role": "user", "content": user_message})

        while True:
            # Will get the response and auto switch from Primary to Backup or to Local
            response = self.get_response(
                max_retries=5,
                messages=self.history,
                tools=tool_registry.get_schemas(),
                tool_choice="auto",
                temperature=0.2,
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