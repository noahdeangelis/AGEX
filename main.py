from agent import AIAgent
import mod

YELLOW = "\033[1;33m"
CYAN = "\033[36m"
RESET = "\033[0m"

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

            if user_message.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            if not user_message:
                continue

            try:
                response = agent.chat(user_message)
                print(f"{CYAN}AGEX:{RESET} {response}\n")
            except Exception as e:
                print(f"Error: {e}\n")

    except Exception as e:
        print(f"Failed to start local agent: {e}")