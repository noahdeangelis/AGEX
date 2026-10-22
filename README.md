# AGEX

**AGEX is a tool using AI agent.**

AGEX is an agent program that connects an LLM to a set of python tools, allowing it to perform calculations, do research, read files, run commands, etc.

There is a mod.py file which new tools can easily be added to.

AGEX currently allows local langauge models using the OpenAI style API, and features and optional choice to use a cloud model (OpenAI API).

> Note: There is no built binaries as of now, requiring a python install to use

## Setup
Simply configure the default .env file provided to connect local or cloud models.

## Features

### Best Features
- **Backup models** - Automatically switches to configured backups model when the primary model / other backups exhaust their usage limits. You can have as many as you want.
- **Local Backup** - If all the configured backup models exhaust their usage limits, you can have a local model continue the work (server must be already running)
- **TPM limit detection** - Detects TPM/RPM rate limits, waits 60 seconds, and retries the request automatically without interrupting the model (5 retries).

### Casual Features
- **Local AI inference** — Connect to locally hosted language models through an OpenAI-compatible API.
- **Tool calling** — Allow the model to request Python functions to perform tasks.
- **Modular tool system** — Register new tools using a simple decorator under mod.py
- **Configurable models** — Configure the model endpoint and model name through environment variables.

### Builtin Tools
- **Calculator** — Safely evaluate mathematical expressions using basic arithmetic operators.
- **Web search** — Search the web and return relevant results with titles and URLs.
- **Website reader** — Fetch webpages and extract readable text for the AI to analyse.
- **Link finder** — Find links on a webpage and convert relative URLs into absolute URLs.
- **File reader** — Read the contents of local files.
- **Directory listing** — List files and directories at a specified path.
- **File writer** — Create files or overwrite existing files after user confirmation.
- **File editor** — Replace a unique piece of text in an existing file, preview the changes, and request user confirmation.
- **Shell execution** — Execute shell commands on the host computer with configurable timeout and output limits, and user confirmation before execution.
- **Playwright** - Use the playwright tools to view, explore and debugs websites.

> Note: Any file or shell operations uses a confirm prompt allowing you to stop any edits, creations, shell commands, etc
**This confirm prompt can be implemented into custom tools too.**

### Commands

- **`/quit`** - Exit the program.
- **`/exit`** - Exit the program.
- **`/clear`** - Clear the terminal.
- **`/model`** - Switch between Primary, Backups and Local on the fly.
- **`/build <task>`** - Build, run, and test full apps by itself. E.g. /build make a modern todo list in HTML on my desktop in todo folder. (prepends prompt onto user message)
- **`/new`** - Start a new conversation while preserving existing saved chats.
- **`/chats`** - View saved conversations and select one to continue.
- **`/resume <id>`** - Resume a saved conversation by its chat ID, restoring its message history.

## Requirements

- A language model compatible with the OpenAI API style
- Internet access for the web search tool (optional)

A simple local server such as llama.cpp can work

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/noahdeangelis/AGEX.git
cd AGEX
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it:

**Linux:**

```bash
source .venv/bin/activate
```

**Windows:**

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the core dependencies:

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root if the default one isn't there and configure the values:
Or simply rename the .env.example file to .env and fill out the values.

```env
# Cloud model
OPENAI_API_KEY="your-api-key"
CLOUD_MODEL_NAME="model-name"
CLOUD_BASE_URL = "base-url"

# Cloud backup model
BACKUP_1_API_KEY="your-backup-api-key"
BACKUP_1_MODEL_NAME="model-name"
BACKUP_1_BASE_URL = "base-url"

# You can have as many backups as you want, just increment the number, e.g/:
# BACKUP_2_API_KEY="your-backup-api-key"
# BACKUP_2_MODEL_NAME="model-name"
# BACKUP_2_BASE_URL = "base-url"
#
# BACKUP_3_API_KEY="your-backup-api-key"
# BACKUP_3_MODEL_NAME="model-name"
# BACKUP_3_BASE_URL = "base-url"
#
# ... For as many as you want. The numbers must continue perfectly. 1, 2, 3 not 1, 3, 5 or 1, 3, 2 otherwise it wont detect them

# Local model
LOCAL_MODEL_URL="http://localhost:8080/v1"
LOCAL_MODEL_NAME="local-model-name"

# Use the local server if all backups run out
# Run the local model as a final backup basically (server must be running and this be set to true)
LOCAL_MODEL_FALLBACK=false

# Maximum context (often limited by your providers TPM)
AGEX_MAX_CONTEXT_TOKENS=8000
# How many tokens to leave for the models response. May be removed when streaming is added.
AGEX_BUFFER_TOKENS=2000

# Auto accept operations. Can be dangerous. Use at your own risk.
AUTO_ACCEPT_FILE_OPERATIONS=false
AUTO_ACCEPT_SHELL_OPERATIONS=false
```

## Running AGEX

Start your local model server first and ensure that its API is accessible. (If using local models)

For a local llama.cpp server listening on port `8080`, the local  base URL is typically:

```text
http://localhost:8080/v1
```

Then run AGEX:

```bash
source .venv/bin/activate
python main.py
```

You should see the AGEX command-line interface.

You can now interact with the agent through the terminal.

## Adding new tools

First add the decorator. The name and description are fed into the model, so it must be described well.

For example:

```python
@tool_registry.register(name="multiply", description="Multiplies two numbers.")
def multiply(a: float, b: float) -> float:
    return a * b
```

Once registered, the tool will automatically be discoverable by the model on startup.

## Current Limitations

AGEX is an evolving project.

Current limitations may include:

- Performance and tool calling reliability depend on the chosen large language model.
- Website inspection is limited by the retrieval and parsing capabilities of the implemented tools.
- Web-search results may be incomplete or inaccurate.
- Streaming responses is not implemented.
- Chats are currently not persistant
## Project Goals

AGEX aims to develop into a capable, modular AI agent with an emphasis on:

- **Local-first operation:** Run inference locally when possible.
- **Extensibility:** Add new capabilities through an easy to use tool interface.
- **Developer control:** Keep the agent's configurability easy for all developers
