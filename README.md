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
- **Backup model** - Automatically switches to a configured backup model when the primary model exhausts its usage limits.
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

> Note: Any file or shell operations uses a confirm prompt allowing you to stop any edits, creations, shell commands, etc
**This confirm prompt can be implemented into custom tools too.**

### Commands

- **/quit** - Exit the program.
- **/exit** - Exit the program.
- **/clear** - Clear the terminal.
- **/model** - Switch between Primary, Backups and Local on the fly.

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
# Doesn't have to be the same provider (e.g. main is OpenAI, backup is Groq)
BACKUP_OPENAI_API_KEY="your-backup-api-key"
BACKUP_CLOUD_MODEL_NAME="model-name"
BACKUP_CLOUD_BASE_URL = "base-url"

# Local model
LOCAL_MODEL_URL="http://localhost:8080/v1"
LOCAL_MODEL_NAME="local-model-name"
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
