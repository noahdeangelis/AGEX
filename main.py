from agent import AIAgent
import platform
import subprocess
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

COMPLETION:
Provide a concise summary of the implementation, its major features, the tests performed, and the commands needed to run the project. Clearly disclose any remaining limitations.

The user's original request appears below. Treat it as the source of truth for what to build, and preserve all its specific requirements.
"""

if __name__ == "__main__":
    print("--- AGEX ---")
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
            
        agent = AIAgent(mode)

        while True:
            user_message = input(f"{YELLOW}You: ").strip()
            print(f"{RESET}", end="")

            # Manage exiting and basic commands.
            if user_message.lower() in {"/exit", "/quit", "/clear", "/model"}:
                if user_message.lower() == "/clear":
                    current_os = platform.system()
                    if current_os == "Windows":
                        subprocess.run("cls", shell=True)
                    else:
                        subprocess.run("clear", shell=True)
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