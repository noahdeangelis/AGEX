"""
Build and run the AGEX agent with customised tools.
Tools can be written below, you may use the calculator tool as an example.

Above your functions you must include:
@tool_registry.register(NAME, DESCRIPTION)

The name and descirption is given to the ai for guidelines.
"""
from tools import tool_registry
import os
import ast
import operator
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from ddgs import DDGS
from pathlib import Path
import difflib
import subprocess

SHELL_TIMEOUT = 60
SHELL_MAX_OUTPUT = 12000

# This calculator tool happens to be really large and complex, but you can write your own tools that are much smaller and simpler.
# It's only large because it has to safely evaluate mathematical expressions, which the python eval() function cannot do safely.
@tool_registry.register("calculator", "Perform basic mathematical calculations.")
def calculator(expression):
    """Safely evaluate a basic mathematical expression."""

    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node):
        # Numbers
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        # Binary operations: +, -, *, /, **, %
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)

            operation = allowed_operators.get(type(node.op))

            if operation is None:
                raise ValueError("Unsupported operator.")

            return operation(left, right)

        # Unary operations: -5, +5
        if isinstance(node, ast.UnaryOp):
            operand = evaluate(node.operand)

            operation = allowed_operators.get(type(node.op))

            if operation is None:
                raise ValueError("Unsupported operator.")

            return operation(operand)

        raise ValueError("Invalid mathematical expression.")

    try:
        tree = ast.parse(expression, mode="eval")
        return evaluate(tree.body)

    except Exception as e:
        return f"Calculator error: {e}"

@tool_registry.register("web_search", "Search the web for information and return relevant links.")
def web_search(query: str):
    try:
        results = DDGS().text(query, max_results=5)

        if not results:
            return {"error": f"No results found for: {query}"}

        return [
            {
                "title": result.get("title", "Untitled"),
                "url": result.get("href", ""),
                # "snippet": result.get("body", "")
            }
            for result in results
        ]

    except Exception as e:
        return {
            "error": f"Web search failed: {type(e).__name__}: {e}",
            "query": query
        }

@tool_registry.register("site_checker", "Fetch and read a specific webpage. The url argument MUST be an actual URL returned by web_search or provided by the user. Never use placeholder text such as 'result of web_search'.")
def site_checker(url):
    """Fetch and scrape a webpage."""

    try:
        headers = {"User-Agent": "AGEX/1.0"}
        response = requests.get(url, headers=headers, timeout=10)

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove things that aren't useful to the AI
        for element in soup(["script", "style", "noscript", "nav", "footer"]):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return text[:15000]
    
    except requests.RequestException as e:
        return f"Error fetching webpage: {e}. It may not exist or be accessible. Please check the URL and try again."

@tool_registry.register("site_button_finder", "Find all links on a webpage and return their absolute URLs. URL as argument.")
def site_button_finder(url):
    """Find and return all links on a webpage."""
    
    headers = {"User-Agent": "AGEX/1.0"}
    response = requests.get(url, headers=headers, timeout=10)

    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []

    for tag in soup.find_all("a", href=True):
        href = urljoin(url, tag["href"])

        # Ignore things like mailto:, javascript:, etc.
        if not href.startswith(("http://", "https://")):
            continue

        if href not in links:
            links.append(href)

    return links

@tool_registry.register("read_file", "Read the content of a local file.")
def read_file(file_path):
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}."

@tool_registry.register("list_directory", "List files and subdirectories at a specified path.")
def list_directory(path = "."):
    try:
        return sorted(os.listdir(path))
    except Exception as e:
        return f"Error listing directory: {e}."



#
# Confirm required tools
#
def confirm_operation(operation, target, preview, warning=None):
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLUE = "\033[38;5;75m"
    CYAN = "\033[38;5;109m"
    YELLOW = "\033[38;5;221m"
    GREEN = "\033[38;5;114m"
    RED = "\033[38;5;203m"
    WHITE = "\033[38;5;252m"

    print(f"\n{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{WHITE}  AGEX {DIM}›{RESET} {BOLD}{CYAN}{operation}{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}")

    print(f"{DIM}Target:{RESET} {BLUE}{target}{RESET}")

    if warning:
        print(f"\n{YELLOW}⚠  {warning}{RESET}")

    print(f"\n{DIM}Preview:{RESET}")
    print(f"{WHITE}{preview}{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}")

    answer = input(
        f"{BOLD}Allow operation? {GREEN}[y]{RESET} approve  "
        f"{RED}[n]{RESET} reject: "
    ).strip().lower()

    if answer in {"y", "yes"}:
        print(f"{GREEN}✓ Approved{RESET}")
        return True

    print(f"{RED}✗ Rejected{RESET}")
    return False


PROJECT_ROOT = Path(__file__).resolve().parent
def resolve_file_path(path: str) -> Path:
    """Resolve a path"""
    return (Path.home() / path).resolve()

@tool_registry.register("write_file", "Create a new file or replace an existing file's contents.")
def write_file(path: str, content: str):
    """Write content to a file after asking for confirmation."""

    try:
        target = resolve_file_path(path)

        if target.exists() and not target.is_file():
            return {"success": False, "error": "Target is not a regular file."}

        preview = content[:2000]

        if len(content) > 2000:
            preview += "\n... (preview truncated)"

        if target.exists():
            preview = "WARNING: THIS WILL OVERWRITE THE EXISTING FILE.\n\n" + preview

        if not confirm_operation(
            operation="Write file",
            target=str(target),
            preview=preview,
            warning=(
                "This will overwrite the existing file!"
                if target.exists()
                else None
            )
        ):
            return {
                "success": False,
                "cancelled": True,
                "message": "User declined the file operation."
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": str(target),
            "bytes_written": target.stat().st_size,
            "message": "File written successfully."
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}"
        }

@tool_registry.register("edit_file", "Replace a unique piece of text in an existing file. Only provide the text that needs to change.")
def edit_file(path: str, old_text: str, new_text: str):
    """Replace an exact text match in a file after asking for confirmation."""

    try:
        target = resolve_file_path(path)

        if not target.is_file():
            return {
                "success": False,
                "error": "File does not exist or is not a regular file."
            }

        original = target.read_text(encoding="utf-8")

        matches = original.count(old_text)

        if not old_text:
            return {
                "success": False,
                "error": "old_text cannot be empty."
            }

        if matches == 0:
            return {
                "success": False,
                "error": "The specified text was not found. No changes made."
            }

        if matches > 1:
            return {
                "success": False,
                "error": (
                    f"Found {matches} matches. "
                    "Provide more surrounding text to identify a unique match."
                )
            }

        updated = original.replace(old_text, new_text, 1)

        diff = difflib.unified_diff(
            original.splitlines(),
            updated.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm=""
        )

        preview = "\n".join(diff)

        if len(preview) > 4000:
            preview = preview[:4000] + "\n... (diff truncated)"

        if not confirm_operation(
            operation="Edit file",
            target=str(target),
            preview=preview,
            warning="This will modify the existing file."
        ):
            return {
                "success": False,
                "cancelled": True,
                "message": "User declined the file operation."
            }

        target.write_text(updated, encoding="utf-8")

        return {
            "success": True,
            "path": str(target),
            "message": "File edited successfully."
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}"
        }


@tool_registry.register(
    "shell",
    "Execute a shell command on the host computer. "
    "Use this to run programs, inspect files, execute Python scripts, "
    "and perform development tasks. Provide the command and optionally "
    "a working directory. Commands require user approval unless "
    "SHELL_AUTO_APPROVE is enabled."
)
def shell(command: str, cwd: str = "."):
    """Execute a shell command with configurable user approval."""

    if not command or not command.strip():
        return {
            "success": False,
            "error": "Command cannot be empty."
        }

    try:
        working_dir = Path(cwd).expanduser().resolve()

        if not working_dir.is_dir():
            return {
                "success": False,
                "error": f"Working directory does not exist: {working_dir}"
            }

        approved = confirm_operation(
            operation="Execute shell command",
            target=f"Working directory: {working_dir}",
            preview=command,
            warning=(
                "This command runs on your computer "
                "with your user permissions."
            )
        )

        if not approved:
            return {
                "success": False,
                "cancelled": True,
                "message": "User declined the command."
            }

        # Execute the command.
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT
        )

        stdout = result.stdout
        stderr = result.stderr

        # Limit output returned to the model.
        if len(stdout) > SHELL_MAX_OUTPUT:
            stdout = stdout[:SHELL_MAX_OUTPUT] + "\n[stdout truncated]"

        if len(stderr) > SHELL_MAX_OUTPUT:
            stderr = stderr[:SHELL_MAX_OUTPUT] + "\n[stderr truncated]"

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "cwd": str(working_dir)
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {SHELL_TIMEOUT} seconds."
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}"
        }