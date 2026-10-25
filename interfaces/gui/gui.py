import os
import re
import threading
from pathlib import Path
import uuid
from threading import Event, Lock
import json
import queue

from core.agent import AIAgent
import core.mod

import webview
from dotenv import dotenv_values, set_key, unset_key
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

agent = AIAgent(mode="openai")

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

ENV_LOCK = threading.Lock()

CONFIRMATIONS = {}
CONFIRMATION_LOCK = Lock()

AGENT_LOCK = Lock()

@app.route("/api/chats/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    with AGENT_LOCK:
        deleted = agent.storage.delete_chat(chat_id)

        if not deleted:
            return jsonify({"error": "Chat not found."}), 404

        # If deleting the open chat, reset the agent to an unsaved new chat.
        if agent.chat_id == chat_id:
            agent.chat_id = None
            agent.history = [
                {"role": "system", "content": agent.system_prompt}
            ]

    return jsonify({"success": True})

@app.route("/api/model", methods=["GET"])
def get_active_model():
    with AGENT_LOCK:
        model = agent.model_configs[agent.current_model]["model"]
    return jsonify({"model": model})

@app.route("/api/confirm", methods=["GET"])
def get_confirmation():
    with CONFIRMATION_LOCK:
        for confirmation in CONFIRMATIONS.values():
            if confirmation["approved"] is None:
                return jsonify({
                    "id": confirmation["id"],
                    "operation": confirmation["operation"],
                    "target": confirmation["target"],
                    "preview": confirmation["preview"],
                    "warning": confirmation["warning"],
                })

    return jsonify(None)


@app.route("/api/confirm/<confirmation_id>", methods=["POST"])
def respond_to_confirmation(confirmation_id):
    data = request.get_json(silent=True) or {}
    approved = data.get("approved")

    if not isinstance(approved, bool):
        return jsonify({"error": "Invalid response."}), 400

    with CONFIRMATION_LOCK:
        confirmation = CONFIRMATIONS.get(confirmation_id)

        if confirmation is None:
            return jsonify({"error": "Confirmation not found."}), 404

        if confirmation["approved"] is not None:
            return jsonify({"error": "Already answered."}), 409

        confirmation["approved"] = approved
        confirmation["event"].set()

    return jsonify({"success": True})

def read_env():
    """Read the .env file."""
    if not ENV_FILE.exists():
        return {}

    return {
        key: value
        for key, value in dotenv_values(ENV_FILE).items()
        if value is not None
    }


def save_env_value(key, value):
    """Update or remove an entry in .env."""
    if value is None:
        unset_key(str(ENV_FILE), key)
    else:
        set_key(str(ENV_FILE), key, str(value), quote_mode="always")


def get_backup_numbers(env):
    """Get all configured backup numbers."""
    numbers = set()

    for key in env:
        match = re.fullmatch(
            r"BACKUP_(\d+)_(?:API_KEY|MODEL_NAME|BASE_URL)",
            key
        )

        if match:
            numbers.add(int(match.group(1)))

    return sorted(numbers)


def settings_payload(env):
    """Get model settings for the GUI."""
    backups = []

    for number in get_backup_numbers(env):
        prefix = f"BACKUP_{number}_"

        backups.append({
            "model": env.get(prefix + "MODEL_NAME", ""),
            "base_url": env.get(prefix + "BASE_URL", ""),
            "api_key": env.get(prefix + "API_KEY", ""),
        })

    return {
        "primary": {
            "model": env.get("CLOUD_MODEL_NAME", ""),
            "base_url": env.get("CLOUD_BASE_URL", ""),
            "api_key": env.get("OPENAI_API_KEY", ""),
        },
        "local": {
            "model": env.get("LOCAL_MODEL_NAME", ""),
            "url": env.get("LOCAL_MODEL_URL", "http://localhost:8080/v1"),
            "fallback": env.get("LOCAL_MODEL_FALLBACK", "false").lower()
            in ("true", "1", "yes"),
        },
        "backups": backups,
    }


@app.route("/")
def index():
    return render_template("index.html")


# @app.route("/chat", methods=["POST"])
# def chat():
#     data = request.get_json(silent=True) or {}
#     message = data.get("message", "")

#     # Replace this with the actual AGEX agent.
#     response = f"You said: {message}"

#     return jsonify({"response": response})

@app.route("/api/chats", methods=["GET"])
def list_chats():
    return jsonify(agent.storage.list_chats())


@app.route("/api/chats/<int:chat_id>", methods=["POST"])
def load_chat(chat_id):
    with AGENT_LOCK:
        chat_info = next(
            (chat for chat in agent.storage.list_chats()
             if chat["id"] == chat_id),
            None,
        )

        if chat_info is None:
            return jsonify({"error": "Chat not found."}), 404

        messages = agent.storage.load_messages(chat_id)

        # Restore all saved conversation/tool messages for the model.
        agent.chat_id = chat_id
        agent.history = [
            {"role": "system", "content": agent.system_prompt},
            *messages,
        ]

    tool_results = {
        item.get("tool_call_id"): item
        for item in messages
        if item.get("role") == "tool"
    }

    visible_messages = []

    for item in messages:
        if item.get("role") == "user":
            visible_messages.append({
                "role": "user",
                "content": item.get("content", ""),
            })

        elif item.get("role") == "assistant":
            calls = item.get("tool_calls") or []

            # Display any tool calls stored on this assistant-history entry.
            tools = []
            for call in calls:
                function = call.get("function", {})
                result = tool_results.get(call.get("id"), {})

                try:
                    arguments = json.loads(function.get("arguments", "{}"))
                except (TypeError, json.JSONDecodeError):
                    arguments = function.get("arguments", "")

                tools.append({
                    "name": function.get("name", "Unknown tool"),
                    "arguments": arguments,
                    "result": result.get("content", "No result was saved."),
                })

            content = item.get("content") or ""
            if content or tools:
                visible_messages.append({
                    "role": "assistant",
                    "content": content,
                    "tools": tools,
                })

    return jsonify({
        "id": chat_id,
        "title": chat_info["title"],
        "messages": visible_messages,
    })


@app.route("/api/chats/new", methods=["POST"])
def start_new_chat():
    with AGENT_LOCK:
        # Keep it unsaved until its first message supplies the title.
        agent.chat_id = None
        agent.history = [
            {"role": "system", "content": agent.system_prompt}
        ]

    return jsonify({"success": True})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    events = queue.Queue()

    def run_agent():
        try:
            with AGENT_LOCK:
                if agent.chat_id is None:
                    title = message[:20].strip() or "New chat"
                    agent.chat_id = agent.storage.create_chat(title=title, model=agent.model_configs[agent.current_model]["model"])
                    events.put({
                        "type": "chat_created",
                        "id": agent.chat_id,
                        "title": title,
                    })
                response = agent.chat(message, on_tool_event=events.put)
                active_model = agent.model_configs[agent.current_model]["model"]

            events.put({"type": "final", "response": response or "", "model": active_model})
        except Exception as error:
            events.put({"type": "error", "error": f"{type(error).__name__}: {error}"})
        finally:
            events.put(None)

    def generate_events():
        threading.Thread(target=run_agent, daemon=True).start()

        while True:
            try:
                event = events.get(timeout=15)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue

            if event is None:
                break

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate_events()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

@app.route("/api/settings", methods=["GET"])
def get_settings():
    with ENV_LOCK:
        return jsonify(settings_payload(read_env()))


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid settings data."}), 400

    primary = data.get("primary")
    local = data.get("local")
    backups = data.get("backups")

    if not isinstance(primary, dict):
        return jsonify({"error": "Primary settings are missing."}), 400

    if not isinstance(local, dict):
        return jsonify({"error": "Local settings are missing."}), 400

    if not isinstance(backups, list) or len(backups) > 20:
        return jsonify({"error": "Invalid backup list. Maximum: 20 backups."}), 400

    def clean_string(value, label, required=False):
        if not isinstance(value, str):
            value = ""

        value = value.strip()

        if required and not value:
            raise ValueError(f"{label} is required.")

        if any(char in value for char in ("\n", "\r", "\x00")):
            raise ValueError(f"{label} contains invalid characters.")

        return value

    try:
        primary_model = clean_string(primary.get("model"), "Primary model", required=True)
        primary_url = clean_string(primary.get("base_url"), "Primary base URL", required=True)
        primary_key = clean_string(primary.get("api_key"), "Primary API key")

        local_model = clean_string(local.get("model"), "Local model")
        local_url = clean_string(local.get("url"), "Local URL")

        fallback = local.get("fallback", False)

        if not isinstance(fallback, bool):
            raise ValueError("Invalid local fallback setting.")

        clean_backups = []

        for number, backup in enumerate(backups, start=1):
            if not isinstance(backup, dict):
                raise ValueError(f"Backup {number} is invalid.")

            clean_backups.append({
                "model": clean_string(
                    backup.get("model"),
                    f"Backup {number} model",
                    required=True,
                ),
                "base_url": clean_string(
                    backup.get("base_url"),
                    f"Backup {number} base URL",
                    required=True,
                ),
                "api_key": clean_string(
                    backup.get("api_key"),
                    f"Backup {number} API key",
                ),
            })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with ENV_LOCK:
        if not ENV_FILE.exists():
            return jsonify({"error": "The .env file does not exist."}), 400

        old_env = read_env()

        # Keep the existing primary key if the field is empty.
        if not primary_key:
            primary_key = old_env.get("OPENAI_API_KEY", "")

        # Load existing backup configurations.
        old_backups = []

        for number in get_backup_numbers(old_env):
            prefix = f"BACKUP_{number}_"

            old_backups.append({
                "model": old_env.get(prefix + "MODEL_NAME", ""),
                "base_url": old_env.get(prefix + "BASE_URL", ""),
                "api_key": old_env.get(prefix + "API_KEY", ""),
            })

        # Preserve backup keys when their model and URL match.
        used_old = set()

        for backup in clean_backups:
            if backup["api_key"]:
                continue

            for index, old_backup in enumerate(old_backups):
                if index in used_old:
                    continue

                if (
                    backup["model"] == old_backup["model"]
                    and backup["base_url"] == old_backup["base_url"]
                ):
                    backup["api_key"] = old_backup["api_key"]
                    used_old.add(index)
                    break

        # If a backup was edited, preserve the key at its previous position
        # when that key has not already been assigned elsewhere.
        for index, backup in enumerate(clean_backups):
            if backup["api_key"] or index >= len(old_backups):
                continue

            if index not in used_old:
                backup["api_key"] = old_backups[index]["api_key"]
                used_old.add(index)

        if not primary_key:
            return jsonify({"error": "A primary API key is required."}), 400

        for number, backup in enumerate(clean_backups, start=1):
            if not backup["api_key"]:
                return jsonify({"error": f"Backup {number} needs an API key."}), 400

        # Save primary and local settings.
        save_env_value("OPENAI_API_KEY", primary_key)
        save_env_value("CLOUD_MODEL_NAME", primary_model)
        save_env_value("CLOUD_BASE_URL", primary_url)

        save_env_value("LOCAL_MODEL_NAME", local_model)
        save_env_value("LOCAL_MODEL_URL", local_url)
        save_env_value("LOCAL_MODEL_FALLBACK", "true" if fallback else "false")

        # Remove old backups so their numbering can be rebuilt consecutively.
        for number in get_backup_numbers(old_env):
            prefix = f"BACKUP_{number}_"

            for suffix in ("API_KEY", "MODEL_NAME", "BASE_URL"):
                save_env_value(prefix + suffix, None)

        # Save backups in their new order.
        for number, backup in enumerate(clean_backups, start=1):
            prefix = f"BACKUP_{number}_"

            save_env_value(prefix + "API_KEY", backup["api_key"])
            save_env_value(prefix + "MODEL_NAME", backup["model"])
            save_env_value(prefix + "BASE_URL", backup["base_url"])

    return jsonify({
        "success": True,
        "message": "Settings saved. Restart AGEX for changes to take effect.",
    })


def run_gui():
    os.environ["AGEX_INTERFACE"] = "gui"

    server = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
    )
    server.start()

    webview.create_window(
        "AGEX",
        "http://127.0.0.1:5000",
        width=1000,
        height=700,
        min_size=(600, 400),
    )
    webview.start()


if __name__ == "__main__":
    run_gui()