import os
import json
import tiktoken
from dotenv import load_dotenv

load_dotenv()

MAX_CONTEXT_TOKENS = int(os.getenv("AGEX_MAX_CONTEXT_TOKENS", "8000"))
BUFFER_TOKENS = int(os.getenv("AGEX_BUFFER_TOKENS", "2000"))
INPUT_TOKEN_BUDGET = MAX_CONTEXT_TOKENS - BUFFER_TOKENS

# cl100k_base is a reasonable general estimate.
ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text):
    """Count tokens in a string."""
    return len(ENCODING.encode(str(text)))


def count_messages(messages, tools=None):
    """Estimate tokens in conversation messages and tool schemas."""
    total = 0

    for message in messages:
        total += 4  # Approximate message formatting overhead

        for _, value in message.items():
            if value is None:
                continue

            if isinstance(value, str):
                total += count_tokens(value)
            else:
                total += count_tokens(json.dumps(value, ensure_ascii=False))

    if tools:
        total += count_tokens(json.dumps(tools, ensure_ascii=False))

    return total + 2  # Approximate conversation overhead