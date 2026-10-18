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

import socket
import time
@tool_registry.register("start_dev_server", "Start a local web server in the backround and return its URL. Runs python3 -m http.server port --bind 127.0.0.1 with the given params")
def start_dev_server(cwd: str, port: int = 3000):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return f"Server already running: http://127.0.0.1:{port}"
    except OSError:
        pass

    # Start the server in the background.
    process = subprocess.Popen(
        ["python3", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Wait up to 5 seconds for startup.
    for _ in range(10):
        time.sleep(0.5)

        if process.poll() is not None:
            return "Server failed to start."

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return f"Server started: http://127.0.0.1:{port}"
        except OSError:
            continue

    return "Server timed out while starting."

#
# I embarrasingly had ChatGPT port over the tools for playwright as I lack experience with it.
# TODO: Have a HUMAN write the tools nicely and better
#

# ==========================================
# PLAYWRIGHT BROWSER TOOLS
# ==========================================

import threading
from urllib.parse import urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

_BROWSER_LOCK = threading.RLock()
_PLAYWRIGHT = None
_BROWSER = None
_BROWSER_CONTEXT = None
_BROWSER_PAGE = None
_BROWSER_VISIBLE = False

_BROWSER_ERRORS = {
    "console": [],
    "page": [],
    "network": [],
}


def _browser_get_page():
    """Return the persistent browser page or raise an error."""

    if (
        _BROWSER_PAGE is None
        or _BROWSER_PAGE.is_closed()
        or _BROWSER is None
        or not _BROWSER.is_connected()
    ):
        raise RuntimeError(
            "No browser is open. Use browser_open first."
        )

    return _BROWSER_PAGE


def _browser_validate_url(url: str) -> str:
    """Restrict browser navigation to localhost by default."""

    url = url.strip()

    if not url:
        raise ValueError("URL cannot be empty.")

    if "://" not in url:
        url = "http://" + url

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname:
        raise ValueError("Invalid URL.")

    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed.")

    allowed_hosts = {"localhost", "127.0.0.1", "::1"}

    # Explicitly approved additional hosts can be configured in .env.
    allowed_hosts.update(
        host.strip().lower()
        for host in os.getenv(
            "AGEX_BROWSER_ALLOWED_HOSTS", ""
        ).split(",")
        if host.strip()
    )

    hostname = parsed.hostname.lower()

    if hostname not in allowed_hosts:
        raise ValueError(
            f"Host '{hostname}' is not allowed. "
            "Browser navigation is restricted to localhost by default. "
            "Use AGEX_BROWSER_ALLOWED_HOSTS to allow trusted hosts."
        )

    return url


def _browser_attach_listeners(page):
    """Collect browser errors for later inspection."""

    page.on(
        "console",
        lambda message: _BROWSER_ERRORS["console"].append(
            message.text
        ) if message.type == "error" else None
    )

    page.on(
        "pageerror",
        lambda error: _BROWSER_ERRORS["page"].append(str(error))
    )

    page.on(
        "requestfailed",
        lambda request: _BROWSER_ERRORS["network"].append(
            f"{request.method} {request.url}: "
            f"{request.failure or 'Request failed'}"
        )
    )


def _browser_start(visible=False):
    """Create a persistent Playwright browser session."""

    global _PLAYWRIGHT
    global _BROWSER
    global _BROWSER_CONTEXT
    global _BROWSER_PAGE
    global _BROWSER_VISIBLE

    with _BROWSER_LOCK:
        if (
            _BROWSER is not None
            and _BROWSER.is_connected()
            and _BROWSER_PAGE is not None
            and not _BROWSER_PAGE.is_closed()
        ):
            if _BROWSER_VISIBLE == visible:
                return _BROWSER_PAGE

            _browser_shutdown()

        _PLAYWRIGHT = sync_playwright().start()

        _BROWSER = _PLAYWRIGHT.chromium.launch(
            headless=not visible
        )

        _BROWSER_CONTEXT = _BROWSER.new_context(
            viewport={
                "width": 1440,
                "height": 900,
            }
        )

        _BROWSER_PAGE = _BROWSER_CONTEXT.new_page()

        _BROWSER_PAGE.set_default_timeout(10000)

        _BROWSER_VISIBLE = visible

        _browser_attach_listeners(_BROWSER_PAGE)

        return _BROWSER_PAGE


def _browser_shutdown():
    """Close the browser and release its resources."""

    global _PLAYWRIGHT
    global _BROWSER
    global _BROWSER_CONTEXT
    global _BROWSER_PAGE

    with _BROWSER_LOCK:
        try:
            if _BROWSER is not None:
                _BROWSER.close()
        finally:
            try:
                if _PLAYWRIGHT is not None:
                    _PLAYWRIGHT.stop()
            finally:
                _PLAYWRIGHT = None
                _BROWSER = None
                _BROWSER_CONTEXT = None
                _BROWSER_PAGE = None


def _browser_find(target: str, role: str = ""):
    """
    Find an element using its accessible name, label or placeholder.
    CSS selectors are supported as a fallback.
    """

    page = _browser_get_page()

    target = target.strip()

    if not target:
        raise ValueError("Element target cannot be empty.")

    if role:
        return page.get_by_role(
            role,
            name=target,
            exact=True,
        ).first

    candidates = [
        lambda: page.get_by_role(
            "button", name=target, exact=True
        ),
        lambda: page.get_by_role(
            "link", name=target, exact=True
        ),
        lambda: page.get_by_label(
            target, exact=True
        ),
        lambda: page.get_by_placeholder(
            target, exact=True
        ),
        lambda: page.get_by_text(
            target, exact=True
        ),
    ]

    for find_candidate in candidates:
        try:
            locator = find_candidate().first

            if locator.count() > 0:
                return locator

        except Exception:
            continue

    # Fall back to a CSS selector.
    return page.locator(target).first


@tool_registry.register(
    "browser_open",
    "Open a website in a persistent Chromium browser. "
    "Provide a URL and optionally visible=true to show the browser window."
)
def browser_open(url: str, visible: bool = False):
    """Open a website and report its initial state."""

    try:
        url = _browser_validate_url(url)
        page = _browser_start(visible=visible)

        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=15000,
        )

        try:
            page.wait_for_load_state(
                "networkidle",
                timeout=2500,
            )
        except PlaywrightTimeoutError:
            pass

        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "http_status": (
                response.status if response else None
            ),
            "visible_browser": visible,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_inspect",
    "Inspect the current website. Returns visible text, headings, "
    "buttons, links, inputs and dropdowns."
)
def browser_inspect():
    """Inspect visible page elements."""

    try:
        page = _browser_get_page()

        elements = page.evaluate("""
            () => {
                const visible = el => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);

                    return rect.width > 0
                        && rect.height > 0
                        && style.display !== "none"
                        && style.visibility !== "hidden"
                        && Number(style.opacity) !== 0;
                };

                const describe = el => ({
                    tag: el.tagName.toLowerCase(),
                    text: (
                        el.getAttribute("aria-label")
                        || el.innerText
                        || el.value
                        || el.placeholder
                        || el.getAttribute("title")
                        || ""
                    ).trim().replace(/\\\\s+/g, " ").slice(0, 150),
                    type: el.getAttribute("type") || "",
                    placeholder: el.getAttribute("placeholder") || "",
                    disabled: !!el.disabled,
                    href: el.href || null
                });

                const selectors = {
                    headings: "h1,h2,h3,h4",
                    buttons: "button,[role=button],input[type=submit]",
                    links: "a[href]",
                    inputs: "input:not([type=hidden]),textarea",
                    dropdowns: "select",
                    checkboxes: "input[type=checkbox],input[type=radio]"
                };

                const result = {};

                for (const [name, selector] of Object.entries(selectors)) {
                    result[name] = Array.from(
                        document.querySelectorAll(selector)
                    )
                    .filter(visible)
                    .slice(0, 50)
                    .map(describe);
                }

                result.visible_text = (
                    document.body?.innerText || ""
                ).slice(0, 6000);

                return result;
            }
        """)

        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            **elements,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_click",
    "Click a website element by accessible name, label, text or CSS selector. "
    "Optionally specify its role, such as button or link."
)
def browser_click(target: str, role: str = ""):
    """Click an element and report the resulting page state."""

    try:
        page = _browser_get_page()

        _browser_find(target, role).click()

        try:
            page.wait_for_load_state(
                "domcontentloaded",
                timeout=1500,
            )
        except PlaywrightTimeoutError:
            pass

        return {
            "success": True,
            "clicked": target,
            "url": page.url,
            "title": page.title(),
            "visible_text": page.locator(
                "body"
            ).inner_text()[:2500],
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_type",
    "Enter text into a website input or textarea using its label, "
    "placeholder or CSS selector."
)
def browser_type(
    target: str,
    text: str,
    clear_first: bool = True,
):
    """Fill an input or type text into an element."""

    try:
        element = _browser_find(target)

        if clear_first:
            element.fill(text)
        else:
            element.press_sequentially(text)

        return {
            "success": True,
            "target": target,
            "text_entered": text,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_press_key",
    "Press a keyboard key on the page or a specified element, "
    "such as Enter, Escape, Tab or ArrowDown."
)
def browser_press_key(key: str, target: str = "body"):
    """Press a keyboard key."""

    try:
        element = _browser_find(target)
        element.press(key)

        page = _browser_get_page()

        return {
            "success": True,
            "key": key,
            "url": page.url,
            "visible_text": page.locator(
                "body"
            ).inner_text()[:2000],
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_select",
    "Select a dropdown option by its visible label or option value."
)
def browser_select(target: str, value: str):
    """Select a dropdown option."""

    try:
        element = _browser_find(target)

        try:
            element.select_option(label=value)
        except Exception:
            element.select_option(value=value)

        return {
            "success": True,
            "target": target,
            "selected": value,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_scroll",
    "Scroll the current webpage up, down, to the top or to the bottom."
)
def browser_scroll(direction: str = "down", amount: int = 650):
    """Scroll the current page."""

    try:
        page = _browser_get_page()
        direction = direction.lower()

        if direction == "top":
            page.evaluate("window.scrollTo(0, 0)")
        elif direction == "bottom":
            page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
        elif direction in {"up", "down"}:
            amount = max(1, min(int(amount), 5000))

            delta = amount if direction == "down" else -amount

            page.evaluate(
                "(delta) => window.scrollBy(0, delta)",
                delta,
            )
        else:
            return {
                "success": False,
                "error": "direction must be up, down, top or bottom.",
            }

        return {
            "success": True,
            "scroll_y": page.evaluate("window.scrollY"),
            "url": page.url,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_screenshot",
    "Capture the current webpage as a PNG screenshot and return the saved path."
)
def browser_screenshot(
    filename: str = "current_page.png",
    full_page: bool = True,
):
    """Capture a screenshot of the browser page."""

    try:
        page = _browser_get_page()

        screenshot_dir = Path(
            os.getenv(
                "AGEX_BROWSER_SCREENSHOT_DIR",
                str(Path.home() / ".agex" / "screenshots"),
            )
        ).expanduser().resolve()

        screenshot_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Only accept a filename, not an arbitrary filesystem path.
        filename = Path(filename).name

        if not filename.lower().endswith(".png"):
            filename += ".png"

        destination = screenshot_dir / filename

        page.screenshot(
            path=str(destination),
            full_page=full_page,
            animations="disabled",
        )

        return {
            "success": True,
            "screenshot": str(destination),
            "url": page.url,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_get_errors",
    "Retrieve JavaScript console errors, page exceptions and failed "
    "network requests captured during the browser session. "
    "Optionally clear the collected errors afterward."
)
def browser_get_errors(clear: bool = False):
    """Retrieve collected browser errors."""

    result = {
        name: errors[-100:]
        for name, errors in _BROWSER_ERRORS.items()
    }

    if clear:
        for errors in _BROWSER_ERRORS.values():
            errors.clear()

    return result


@tool_registry.register(
    "browser_reload",
    "Reload the current webpage and return its title and visible text."
)
def browser_reload():
    """Reload the current browser page."""

    try:
        page = _browser_get_page()
        response = page.reload(
            wait_until="domcontentloaded",
            timeout=15000,
        )

        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "http_status": (
                response.status if response else None
            ),
            "visible_text": page.locator(
                "body"
            ).inner_text()[:2000],
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }


@tool_registry.register(
    "browser_close",
    "Close the persistent Chromium browser and release its resources."
)
def browser_close():
    """Close the browser session."""

    try:
        _browser_shutdown()

        return {
            "success": True,
            "message": "Browser closed.",
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
        }