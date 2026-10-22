from agent import AIAgent
import platform
import subprocess
import sys
import importlib.util
import mod

YELLOW = "\033[1;33m"
CYAN = "\033[36m"
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[38;5;203m"

BUILD_PROMPT = """
[BUILD MODE — FULL PROJECT IMPLEMENTATION]

Treat the user's request as a project that must be fully implemented, not merely explained.

WORKFLOW:
1. Analyze the user's request and inspect the existing project files before making changes.
2. Determine the requirements, identify the necessary components, and create a practical implementation plan.
3. Implement the project step by step, building one component or feature at a time instead of generating everything in one giant chunk.
4. Make sensible technical decisions independently. Choose appropriate technologies, architecture, libraries, and tools based on the project.
5. Write actual, functional code. Do not substitute placeholders, mock functionality, TODO comments, or incomplete implementations for requested features.
6. Integrate each component into the project and verify that it works before proceeding.
7. Test functionality, handle errors and edge cases, and fix problems as they arise.
8. Run the completed project, execute relevant tests, and fix build errors, runtime errors, and broken features.
9. Refine the result until it is functional, cohesive, and ready to use.
10. For web projects, use the Playwright browser tools to test the website
    throughout development. Open the site using browser_open with visible=false,
    inspect it with browser_inspect, and interact with its buttons, links, forms,
    and other features. Verify that each feature works before proceeding.
11. Repeat browser testing after making changes, fixing any issues discovered,
    and checking again until the website works as expected.

QUALITY STANDARDS:
- Use clean, maintainable, well-organized code.
- Follow appropriate development conventions and best practices.
- Create a modern, polished, responsive UI when the project requires one.
- Pay attention to usability, accessibility, performance, and security.
- Implement all requested features completely.
- Preserve existing functionality unless changes are necessary.
- Avoid unnecessary complexity, careless shortcuts, and destructive changes.
- Work directly with the existing project and its files.

IMPORTANT RULES:
- Do not stop after creating a plan or explaining how the project could be built.
- Do not deliver just a prototype when a complete implementation is requested.
- Do not attempt to write the entire project in one enormous response.
- Make actual changes to the files, work incrementally, and verify the results.
- If something fails, investigate the cause and attempt to fix it before continuing.
- Continue until the requested project is complete or a genuine limitation prevents further progress.
- Never claim a feature works unless it has been implemented and appropriately verified.

- For web projects, browser testing is mandatory. Use Playwright in headless mode (visible=false) to inspect and interact with the running website.
- Start the development server and verify that the website is accessible before testing it. Determine the correct URL and port from the project configuration.
- Test actual functionality, not just whether the page loads. Interact with relevant elements and verify the results using browser_inspect.
- Use browser_get_errors to check for JavaScript errors and failed network requests. Fix discovered issues and retest.
- Perform browser testing continuously during development, not just at the end.
- Do not claim a feature works unless you have tested it where practical.
- Do not open a visible browser window unless the user explicitly requests it.
- If browser testing fails, investigate the cause and attempt to resolve it before continuing.
- Use start_dev_server to start local websites before browser testing.
- Pass the project directory and desired port.
- Use the returned URL with browser_open(visible=false).
- Reuse an existing server instead of repeatedly restarting it.
- By default test with port 8000 unless requested otherwise by the user.
- If a `.venv` virtual environment exists in the project, use its Python interpreter and pip instead of the system Python and pip.
- When working on a Python project in a Linux environment, create a `.venv` virtual environment if one does not already exist, and use it for all project-specific Python operations and package installations.
- For all web projects, you MUST use start_dev_server to start the website and the Playwright browser tools to test it.
- DO NOT TERMINATE PYTHON. That will terminate you.
- When finished testing, use stop_dev_server to stop the development server you started, unless the user wants it left running.
- stop_dev_server will free up the port.
- Never use shell commands to kill processes or clear ports when stop_dev_server can handle it.

COMPLETION:
Provide a concise summary of the implementation, its major features, the tests performed, and the commands needed to run the project. Clearly disclose any remaining limitations.

The user's original request appears below. Treat it as the source of truth for what to build, and preserve all its specific requirements.
"""

def clear_screen():
    current_os = platform.system()
    if current_os == "Windows":
        subprocess.run("cls", shell=True)
    else:
        subprocess.run("clear", shell=True)


def ensure_playwright_chromium():
    """Install Playwright and Chromium if they are missing."""

    print("[AGEX] Installing Chromium dependencies. If this is your first time it may take a few minutes.")

    # Install Chromium if needed.
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError("Failed to install Chromium. Run: python -m playwright install chromium\n" + result.stderr)
    
if __name__ == "__main__":
    clear_screen()
    print("--- AGEX ---")

    from chat_storage import ChatStorage
    storage = ChatStorage()

    resume_id = None
    new_chat_name = None

    while True:
        print("\n--- AGEX CHAT HISTORY ---")
        print("[1] Continue a chat")
        print("[2] Start a new chat")
        print("[3] Delete a chat")
        print("[4] Exit")

        choice = input("Option: ").strip()

        if choice == "1":
            chats = storage.list_chats()

            if not chats:
                clear_screen()
                print("No saved chats. Start a new one instead.\n")
                continue

            for chat in chats:
                print(f"[{chat['id']}] {chat['title']}")

            try:
                chat_id = int(input("Chat ID to continue: ").strip())

                if any(chat["id"] == chat_id for chat in chats):
                    resume_id = chat_id
                    break

                clear_screen()
                print("Invalid chat ID.\n")

            except ValueError:
                clear_screen()
                print("Enter a valid numeric chat ID.\n")

        elif choice == "2":
            new_chat_name = input("Chat name: ").strip()

            if not new_chat_name:
                new_chat_name = "New chat"

            break

        elif choice == "3":
            chats = storage.list_chats()

            if not chats:
                clear_screen()
                print("No saved chats to delete.\n")
                continue

            for chat in chats:
                print(f"[{chat['id']}] {chat['title']}")

            try:
                chat_id = int(input("Chat ID to delete: ").strip())

                if any(chat["id"] == chat_id for chat in chats):
                    confirm = input(
                        f"Delete '{next(c['title'] for c in chats if c['id'] == chat_id)}'? (y/n): "
                    ).strip().lower()

                    if confirm == "y":
                        if storage.delete_chat(chat_id):
                            clear_screen()
                            print("Chat deleted.\n")
                        else:
                            clear_screen()
                            print("Failed to delete chat.\n")
                else:
                    clear_screen()
                    print("Invalid chat ID.\n")

            except ValueError:
                clear_screen()
                print("Enter a valid numeric chat ID.\n")

        elif choice == "4":
            print("Goodbye!")
            sys.exit(0)

        else:
            clear_screen()
            print("Please select 1, 2, 3, or 4.\n")

    clear_screen()
    ensure_playwright_chromium()
    print("Type 'exit' or 'quit' to stop.\n")

    try:
        print("SELECT A MODE:")
        print("[1] Cloud")
        print("[2] Local")

        while True:
            mode = input("Option: ")
            if mode == "1" or mode.lower() == "cloud":
                mode = "openai"
                break
            if mode == "2" or mode.lower() == "local":
                mode = "local"
                break
            print("Please select a valid mode.")

        clear_screen()

        agent = AIAgent(mode)
        if resume_id is not None:
            if not agent.load_history(resume_id):
                print("Could not load chat. Starting a new one.")
                agent.create_new_chat()
        elif new_chat_name is not None:
            agent.create_new_chat(name=new_chat_name)

        while True:
            user_message = input(f"{YELLOW}You: ").strip()
            print(f"{RESET}", end="")

            # Manage exiting and basic commands.
            if user_message.lower() in {"/exit", "/quit", "/clear", "/model", "/chats", "/new"} or user_message.lower().startswith("/resume "):
                if user_message.lower() == "/clear":
                    clear_screen()
                    continue

                elif user_message.lower() == "/model":
                    avail_models = agent.get_models()

                    if not avail_models:
                        print("No models configured.")
                        continue

                    for idx, model in enumerate(avail_models, start=1):
                        # Automatically label the models for ease of use
                        label = "Primary" if model[1] else "Local" if model[2] else f"Backup_{model[4]}" if model[3] else "Unknown"
                        print(f"[{idx}] {model[0]}: {label}")

                    while True:
                        model_choice = input("Choice (or 'q' to cancel): ").strip()
                        if model_choice.lower() == "q":
                            break

                        try:
                            choice = int(model_choice)

                            if 1 <= choice <= len(avail_models):
                                selected_model = avail_models[choice - 1][0]
                                agent.set_model(selected_model)
                                break
                            else:
                                print(f"Enter a number between 1 and {len(avail_models)}.")

                        except ValueError:
                            print("Invalid choice. Enter a number or 'q'.")
                    continue

                elif user_message.lower() == "/chats":
                    chats = agent.storage.list_chats()

                    if not chats:
                        print("No saved chats.")
                    else:
                        for chat in chats:
                            print(f"[{chat['id']}] {chat['title']}")

                    continue

                elif user_message.lower().startswith("/resume "):
                    try:
                        chat_id = int(user_message.split(maxsplit=1)[1])

                        if agent.load_history(chat_id):
                            print(f"Resumed chat {chat_id}.\n")

                    except ValueError:
                        print("Usage: /resume <chat_id>")

                    continue

                elif user_message.lower() == "/new":
                    agent.create_new_chat()
                    continue

                print("Goodbye!")
                break

            if not user_message:
                continue

            # Build mode: prepend the project implementation instructions.
            if user_message.lower() == "/build":
                print("Usage: /build <describe what you want to build>\n")
                continue

            if user_message.lower().startswith("/build "):
                build_request = user_message[7:].strip()

                if not build_request:
                    print("Please describe what you want to build.\n")
                    continue

                user_message = (
                    f"{BUILD_PROMPT}\n\n"
                    f"[USER'S PROJECT REQUEST]\n"
                    f"{build_request}"
                )

            try:
                response = agent.chat(user_message)
                print(f"{CYAN}AGEX:{RESET} {response}\n")
            except KeyboardInterrupt:
                print(f"{RED}Model stopped.{RESET}")
            except Exception as e:
                print(f"Error: {e}\n")


    except Exception as e:
        print(f"Failed to start local agent: {e}")