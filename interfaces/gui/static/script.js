
marked.setOptions({
    gfm: true,
    breaks: true
});


function renderMarkdown(text) {
    let source = String(text ?? "");
    const mathBlocks = [];

    // Protect display and inline LaTeX before Markdown can modify it.
    source = source.replace(
        /\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|(?<!\\)\$(?!\$)[^\n$]+(?<!\\)\$(?!\$)/g,
        match => {
            const index = mathBlocks.length;
            mathBlocks.push(match);
            return `MATHPLACEHOLDER${index}END`;
        }
    );

    // Parse the remaining Markdown normally.
    let html = marked.parse(source);

    // Restore the original LaTeX expressions.
    html = html.replace(
        /MATHPLACEHOLDER(\d+)END/g,
        (_, index) => mathBlocks[Number(index)]
    );

    // Sanitize before rendering the maths.
    const container = document.createElement("div");
    container.innerHTML = DOMPurify.sanitize(html);

    if (typeof renderMathInElement === "function") {
        renderMathInElement(container, {
            delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "\\[", right: "\\]", display: true },
                { left: "\\(", right: "\\)", display: false },
                { left: "$", right: "$", display: false }
            ],
            throwOnError: false,
            ignoredTags: [
                "script", "noscript", "style", "textarea",
                "pre", "code"
            ]
        });
    }

    return container.innerHTML;
}

const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const chat = document.getElementById("chat");
const button = form.querySelector("button");

const settingsModal = document.getElementById("settings-modal");
const settingsForm = document.getElementById("settings-form");
const backupList = document.getElementById("backup-list");
const backupCount = document.getElementById("backup-count");
const addBackupButton = document.getElementById("add-backup");
const saveSettingsButton = document.getElementById("save-settings");

const settingsError = document.getElementById("settings-error");
const settingsSuccess = document.getElementById("settings-success");

const primaryModelInput = settingsForm.elements["primary-model"];
const primaryUrlInput = settingsForm.elements["primary-url"];
const primaryKeyInput = settingsForm.elements["primary-key"];

const localModelInput = settingsForm.elements["local-model"];
const localUrlInput = settingsForm.elements["local-url"];
const localFallbackInput = settingsForm.elements["local-fallback"];

const confirmModal = document.getElementById("confirm-modal");
const confirmTitle = document.getElementById("confirm-title");
const confirmTarget = document.getElementById("confirm-target");
const confirmPreview = document.getElementById("confirm-preview");
const confirmWarning = document.getElementById("confirm-warning");

const confirmApprove = document.getElementById("confirm-approve");
const confirmReject = document.getElementById("confirm-reject");

const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatContainer = document.getElementById("chat");

let isGenerating = false;
let currentChatId = null;

async function loadProfileName() {
    const nameElement = document.getElementById("profile-name");

    try {
        const response = await fetch("/api/profile");
        if (!response.ok) return;

        const profile = await response.json();

        if (profile.name) {
            nameElement.textContent = profile.name;
            return;
        }

        const enteredName = prompt("What should AGEX call you?");
        if (!enteredName?.trim()) return;

        const saveResponse = await fetch("/api/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: enteredName.trim() }),
        });

        const savedProfile = await saveResponse.json();

        if (!saveResponse.ok) {
            throw new Error(savedProfile.error || "Could not save your name.");
        }

        nameElement.textContent = savedProfile.name;
    } catch (error) {
        console.error("Could not load profile name:", error);
    }
}

loadProfileName();

async function updateModelTag() {
    const response = await fetch("/api/model");
    if (!response.ok) return;

    const data = await response.json();
    document.getElementById("model").textContent = data.model;
}

updateModelTag();

function addMessage(role, content) {
    const wrapper = document.createElement("div");
    wrapper.className = role === "assistant"
        ? "assistant-response"
        : "user-response";

    const message = document.createElement("div");
    message.className = `message ${role}`;
    // message.innerHTML = renderMarkdown(content);
    if (role === "assistant") {
        message.innerHTML = renderMarkdown(content);
    } else {
        message.textContent = content;
    }

    wrapper.appendChild(message);
    chatContainer.appendChild(wrapper);

    chatContainer.scrollTop = chatContainer.scrollHeight;

    return message;
}

function addStoredToolLog(parent, tool) {
    const details = document.createElement("details");
    details.className = "tool-log";

    const summary = document.createElement("summary");
    const name = tool.name
        .replace(/_/g, " ")
        .replace(/\b\w/g, letter => letter.toUpperCase());
    summary.textContent = `Used tool: ${name}`;

    const content = document.createElement("div");
    content.className = "tool-content";

    const args = document.createElement("pre");
    args.textContent =
        `Arguments:\n${JSON.stringify(tool.arguments, null, 2)}`;

    const result = document.createElement("pre");
    result.textContent = `Result:\n${tool.result}`;

    content.append(args, result);
    details.append(summary, content);
    parent.appendChild(details);
}

async function loadChats() {
    const response = await fetch("/api/chats");
    if (!response.ok) return;

    const chats = await response.json();
    const history = document.getElementById("chat-history");
    history.replaceChildren();

    for (const item of chats) {
        const row = document.createElement("div");
        row.className = "history-row";

        const chatButton = document.createElement("button");
        chatButton.type = "button";
        chatButton.className = "history-item";
        chatButton.textContent = item.title;
        chatButton.classList.toggle("active", item.id === currentChatId);

        chatButton.addEventListener("click", async () => {
            const response = await fetch(`/api/chats/${item.id}`, {
                method: "POST",
            });
            const data = await response.json();

            if (!response.ok) {
                console.error(data.error || "Could not load chat.");
                return;
            }

            currentChatId = data.id;
            document.getElementById("title").textContent = data.title;
            chatContainer.replaceChildren();

            let pendingTools = [];

            for (const message of data.messages) {
                const tools = message.tools || [];

                // Saved tool-call entries often have no visible assistant text.
                // Hold their logs until the assistant's reply is rendered.
                if (message.role === "assistant" && tools.length && !message.content) {
                    pendingTools.push(...tools);
                    continue;
                }

                const messageElement = addMessage(message.role, message.content);

                if (message.role === "assistant") {
                    const wrapper = messageElement.parentElement;
                    const toolsToShow = [...pendingTools, ...tools];

                    toolsToShow.forEach(tool => addStoredToolLog(wrapper, tool));

                    if (toolsToShow.length) {
                        // Keep the tool dropdowns above the assistant reply.
                        wrapper.appendChild(messageElement);
                    }

                    pendingTools = [];
                }
            }

            await loadChats();
        });

        const moreButton = document.createElement("button");
        moreButton.type = "button";
        moreButton.className = "chat-more";
        moreButton.textContent = "⋯";
        moreButton.setAttribute("aria-label", `Options for ${item.title}`);

        const menu = document.createElement("div");
        menu.className = "chat-menu";
        menu.hidden = true;

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.textContent = "Delete";

        moreButton.addEventListener("click", event => {
            event.stopPropagation();
            const selfstate = menu.hidden

            document.querySelectorAll(".chat-menu").forEach(openMenu => {
                openMenu.hidden = true;
            });

            menu.hidden = !selfstate;

            if (!menu.hidden) {
                const rect = moreButton.getBoundingClientRect();

                menu.style.right = `${window.innerWidth - rect.right}px`;
                menu.style.top = `${Math.min(
                    rect.bottom + 4,
                    window.innerHeight - menu.offsetHeight - 8
                )}px`;
            }
        });

        deleteButton.addEventListener("click", async () => {
            if (!confirm(`Delete "${item.title}"? This cannot be undone.`)) {
                return;
            }

            const response = await fetch(`/api/chats/${item.id}`, {
                method: "DELETE",
            });
            const data = await response.json();

            if (!response.ok) {
                console.error(data.error || "Could not delete chat.");
                return;
            }

            if (currentChatId === item.id) {
                currentChatId = null;
                document.getElementById("title").textContent = "New Chat";
                chatContainer.replaceChildren();
                addMessage("assistant", "Hello! I'm AGEX. How can I help?");
            }

            await loadChats();
        });

        menu.appendChild(deleteButton);
        row.append(chatButton, moreButton, menu);
        history.appendChild(row);
    }
}

document.getElementById("new-chat").addEventListener("click", async () => {
    const response = await fetch("/api/chats/new", { method: "POST" });
    if (!response.ok) return;

    currentChatId = null;
    document.getElementById("title").textContent = "New Chat";
    chatContainer.replaceChildren();
    addMessage("assistant", "Hello! I'm AGEX. How can I help?");
    await loadChats();
});

loadChats();

async function readChatStream(response, responseMessage) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const toolLogs = new Map();
    let buffer = "";

    while (true) {
        const { value, done } = await reader.read();

        if (value) {
            buffer += decoder.decode(value, { stream: !done });
        }

        buffer = buffer.replace(/\r\n/g, "\n");

        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);

            const dataLine = frame
                .split("\n")
                .find(line => line.startsWith("data:"));

            if (!dataLine) continue;

            const event = JSON.parse(dataLine.slice(5).trim());

            if (event.type === "tool_start") {
                const details = document.createElement("details");
                details.className = "tool-log";

                const summary = document.createElement("summary");
                const name = event.name
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, letter => letter.toUpperCase());
                summary.textContent = `Running tool: ${name}`;

                const content = document.createElement("div");
                content.className = "tool-content";

                const args = document.createElement("pre");
                args.textContent = `Arguments:\n${JSON.stringify(event.arguments, null, 2)}`;

                const result = document.createElement("pre");
                result.textContent = "Result: Running…";

                content.append(args, result);
                details.append(summary, content);
                responseMessage.parentElement.insertBefore(details, responseMessage);
                toolLogs.set(event.id, { details, summary, result, name });
            }

            if (event.type === "tool_finish") {
                const log = toolLogs.get(event.id);
                if (log) {
                    log.summary.textContent = `Used tool: ${log.name}`;
                    log.result.textContent = `Result:\n${event.result}`;
                }
            }

            if (event.type === "tool_error") {
                const log = toolLogs.get(event.id);
                if (log) {
                    log.summary.textContent = `Used tool: ${log.name}`;
                    log.result.textContent = `Error:\n${event.error}`;
                    log.details.open = true;
                }
            }

            if (event.type === "error") {
                responseMessage.textContent = `Error: ${event.error}`;
            }


            if (event.type === "final") {
                responseMessage.innerHTML = renderMarkdown(
                    event.response || "AGEX returned an empty response."
                );

                if (event.model) {
                    document.getElementById("model").textContent = event.model;
                }
            }


            if (event.type === "error") {
                throw new Error(event.error);
            }

            if (event.type === "chat_created") {
                currentChatId = event.id;
                document.getElementById("title").textContent = event.title;
                loadChats();
            }
        }

        if (done) break;
    }
}

chatForm.addEventListener("submit", async event => {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!message || isGenerating) {
        return;
    }

    isGenerating = true;
    button.disabled = true;

    addMessage("user", message);
    messageInput.value = "";

    const responseMessage = addMessage("assistant", "Thinking...");

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || "AGEX failed to respond.");
        }

        await readChatStream(response, responseMessage);

    } catch (error) {
        responseMessage.textContent = `Error: ${error.message}`;
    } finally {
        isGenerating = false;
        button.disabled = false;
        messageInput.focus();

        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});

let activeConfirmation = null;
let confirmationBusy = false;

function showConfirmation(data) {
    activeConfirmation = data;

    confirmTitle.textContent = data.operation;
    confirmTarget.textContent = data.target;
    confirmPreview.textContent = data.preview;

    confirmWarning.textContent = data.warning || "";
    confirmWarning.hidden = !data.warning;

    confirmModal.hidden = false;
    document.body.classList.add("confirm-open");
}

function hideConfirmation() {
    confirmModal.hidden = true;
    document.body.classList.remove("confirm-open");
    activeConfirmation = null;
}

async function respondToConfirmation(approved) {
    if (!activeConfirmation || confirmationBusy) {
        return;
    }

    confirmationBusy = true;
    confirmApprove.disabled = true;
    confirmReject.disabled = true;

    const confirmation = activeConfirmation;

    try {
        const response = await fetch(
            `/api/confirm/${confirmation.id}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ approved })
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not submit confirmation.");
        }

        hideConfirmation();
    } catch (error) {
        confirmWarning.textContent = error.message;
        confirmWarning.hidden = false;
    } finally {
        confirmationBusy = false;
        confirmApprove.disabled = false;
        confirmReject.disabled = false;
    }
}

confirmApprove.addEventListener("click", () => {
    respondToConfirmation(true);
});

confirmReject.addEventListener("click", () => {
    respondToConfirmation(false);
});

async function pollConfirmations() {
    if (activeConfirmation) {
        return;
    }

    try {
        const response = await fetch("/api/confirm");

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        if (data && !activeConfirmation) {
            showConfirmation(data);
        }
    } catch (error) {
        console.error("Confirmation polling failed:", error);
    }
}

setInterval(pollConfirmations, 500);
pollConfirmations();

function showSettingsMessage(type, message) {
    settingsError.hidden = true;
    settingsSuccess.hidden = true;

    const element = type === "error" ? settingsError : settingsSuccess;
    element.textContent = message;
    element.hidden = false;
}

function clearSettingsMessages() {
    settingsError.hidden = true;
    settingsSuccess.hidden = true;
}

function createSettingsField(labelText, name, placeholder, type = "text") {
    const label = document.createElement("label");
    label.className = "settings-field";

    const caption = document.createElement("span");
    caption.textContent = labelText;

    const input = document.createElement("input");
    input.type = type;
    input.name = name;
    input.placeholder = placeholder;
    input.autocomplete = type === "password" ? "new-password" : "off";

    label.append(caption, input);

    return { label, input };
}

function updateBackupCount() {
    const count = backupList.querySelectorAll(".backup-card").length;
    backupCount.textContent = `${count} BACKUP${count === 1 ? "" : "S"}`;
    addBackupButton.disabled = count >= 20;
}

function addBackupCard(backup = {}) {
    const existingCards = backupList.querySelectorAll(".backup-card");

    if (existingCards.length >= 20) {
        showSettingsMessage("error", "You can configure a maximum of 20 backups.");
        return;
    }

    const index = existingCards.length + 1;

    const card = document.createElement("div");
    card.className = "backup-card";

    const header = document.createElement("div");
    header.className = "backup-card-header";

    const title = document.createElement("strong");
    title.className = "backup-title";
    title.textContent = `Backup ${index}`;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "backup-remove";
    removeButton.textContent = "Remove";

    removeButton.addEventListener("click", () => {
        card.remove();
        renumberBackups();
        updateBackupCount();
        clearSettingsMessages();
    });

    header.append(title, removeButton);

    const model = createSettingsField(
        "Model name",
        "backup-model",
        "openai/gpt-oss-20b"
    );

    const url = createSettingsField(
        "Base URL",
        "backup-url",
        "https://api.example.com/v1",
        "url"
    );

    const key = createSettingsField(
        "API key",
        "backup-key",
        "Enter API key",
        "text"
    );

    model.input.value = backup.model || "";
    url.input.value = backup.base_url || "";

    const keyStatus = document.createElement("small");
    keyStatus.className = "backup-key-status";
    key.input.value = backup.api_key || "";
    keyStatus.textContent = "API key";

    card.append(
        header,
        model.label,
        url.label,
        key.label,
        keyStatus
    );

    backupList.appendChild(card);
    updateBackupCount();
}

function renumberBackups() {
    backupList.querySelectorAll(".backup-card").forEach((card, index) => {
        card.querySelector(".backup-title").textContent = `Backup ${index + 1}`;
    });
}

async function loadSettings() {
    clearSettingsMessages();

    try {
        const response = await fetch("/api/settings");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load settings.");
        }

        primaryModelInput.value = data.primary.model || "";
        primaryUrlInput.value = data.primary.base_url || "";
        primaryKeyInput.value = data.primary.api_key || "";

        document.querySelector('[data-key-status="primary"]').textContent =
            data.primary.has_api_key
                ? "An API key is saved. Leave blank to keep it."
                : "No saved API key.";

        localModelInput.value = data.local.model || "";
        localUrlInput.value = data.local.url || "";
        localFallbackInput.checked = Boolean(data.local.fallback);

        backupList.replaceChildren();

        for (const backup of data.backups || []) {
            addBackupCard(backup);
        }

        updateBackupCount();
    } catch (error) {
        showSettingsMessage("error", error.message);
    }
}

async function openSettings() {
    settingsModal.hidden = false;
    document.body.classList.add("settings-open");

    await loadSettings();
}

function closeSettings() {
    settingsModal.hidden = true;
    document.body.classList.remove("settings-open");
}

document.querySelector(".settings-bar").addEventListener("click", openSettings);

document.querySelectorAll("[data-close-settings]").forEach(button => {
    button.addEventListener("click", closeSettings);
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !settingsModal.hidden) {
        closeSettings();
    }
});

addBackupButton.addEventListener("click", () => {
    addBackupCard();
    clearSettingsMessages();
});

settingsForm.addEventListener("submit", async event => {
    event.preventDefault();
    clearSettingsMessages();

    const backups = Array.from(
        backupList.querySelectorAll(".backup-card")
    ).map(card => ({
        model: card.querySelector('[name="backup-model"]').value.trim(),
        base_url: card.querySelector('[name="backup-url"]').value.trim(),
        api_key: card.querySelector('[name="backup-key"]').value
    }));

    const payload = {
        primary: {
            model: primaryModelInput.value.trim(),
            base_url: primaryUrlInput.value.trim(),
            api_key: primaryKeyInput.value
        },
        local: {
            model: localModelInput.value.trim(),
            url: localUrlInput.value.trim(),
            fallback: localFallbackInput.checked
        },
        backups
    };

    saveSettingsButton.disabled = true;
    saveSettingsButton.textContent = "Saving…";

    try {
        const response = await fetch("/api/settings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not save settings.");
        }

        primaryKeyInput.value = "";
        backupList.querySelectorAll('[name="backup-key"]').forEach(input => {
            input.value = "";
        });

        showSettingsMessage(
            "success",
            `${result.message} Your existing conversation history will not be cleared by saving these settings.`
        );

        await loadSettings();

        showSettingsMessage(
            "success",
            `${result.message} Your existing conversation history will not be cleared by saving these settings.`
        );
    } catch (error) {
        showSettingsMessage("error", error.message);
    } finally {
        saveSettingsButton.disabled = false;
        saveSettingsButton.textContent = "Save settings";
    }
});