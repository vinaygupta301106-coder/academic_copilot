
/* Academic Pathway Copilot — Ollama chat controller */
(() => {
  let busy = false;
  let conversationHistory = [];
  let conversationStudentId = null;

  window.Copilot = {
    sendQuickPrompt
  };

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("copilot-chat-form");
    const input = document.getElementById("copilot-input");

    form?.addEventListener("submit", e => {
      e.preventDefault();
      sendMessage(input?.value || "");
    });

    input?.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input.value);
      }
    });

    bindPromptButtons();
    setupSuggestedQuestions();
  });

  async function sendQuickPrompt(prompt) {
    const input = document.getElementById("copilot-input");
    if (input) input.value = prompt;
    await sendMessage(prompt);
  }

  const SUGGESTED_QUESTIONS = {
    eligibility: {
      label: "Eligibility & prerequisites",
      questions: [
        "Am I eligible for CS401?",
        "What prerequisites am I missing for CS402?",
        "Which courses am I currently eligible to take?",
        "Why is CS403 locked?"
      ]
    },
    planning: {
      label: "Course planning",
      questions: [
        "What should I take next semester?",
        "What courses should I complete first?",
        "Which eligible courses can I take together?",
        "What should I prioritize to stay on track?"
      ]
    },
    comparison: {
      label: "Course comparison",
      questions: [
        "Which should I choose: CS401 or CS402?",
        "What should I choose out of CS401, CS402 and MATH201?",
        "Compare CS401 and CS402 for my current pathway.",
        "Which of these courses is the best priority for me right now?"
      ]
    },
    course_info: {
      label: "Course information",
      questions: [
        "Tell me about CS401.",
        "What about CS402?",
        "What are the prerequisites for MATH201?",
        "What happens if I choose CS402?"
      ]
    },
    progress: {
      label: "Progress & completion",
      questions: [
        "What courses have I completed?",
        "How many credits have I completed?",
        "How am I progressing in my degree?",
        "How many curriculum courses are remaining?"
      ]
    }
  };

  function bindPromptButtons() {
    document.querySelectorAll(".ai-prompt-pill").forEach(btn => {
      btn.addEventListener("click", () => sendMessage(btn.textContent.trim()));
    });
  }

  function setupSuggestedQuestions() {
    const select = document.getElementById("ai-question-category");
    if (!select) return;
    select.addEventListener("change", () => renderSuggestedQuestions(select.value));
    renderSuggestedQuestions(select.value || "eligibility");
  }

  function renderSuggestedQuestions(category) {
    const data = SUGGESTED_QUESTIONS[category] || SUGGESTED_QUESTIONS.eligibility;
    const list = document.getElementById("ai-prompt-list");
    const label = document.getElementById("ai-suggest-current");
    if (!list) return;
    list.innerHTML = data.questions.map(question =>
      `<button type="button" class="ai-prompt-pill">${App.escapeHtml(question)}</button>`
    ).join("");
    if (label) label.textContent = data.label;
    bindPromptButtons();
  }

  async function sendMessage(rawText) {
    const text = String(rawText || "").trim();
    if (!text || busy) return;

    const input = document.getElementById("copilot-input");
    const empty = document.getElementById("chat-empty");
    empty?.remove();
    if (input) input.value = "";

    appendMessage("user", text);
    setBusy(true);

    const started = performance.now();

    try {
      const student = App.state.currentUser || { id: 1, track: "AI & Data Science" };
      if (conversationStudentId !== Number(student.id)) {
        conversationHistory = [];
        conversationStudentId = Number(student.id);
      }
      const response = await fetch(`${App.API_BASE}/copilot/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(typeof App?.demoRoleHeaders === "function" ? App.demoRoleHeaders() : { "X-Demo-Role": "Student", "X-Demo-Student-Id": String(student.id) }) },
        body: JSON.stringify({
          user_id: Number(student.id),
          user_message: text,
          target_track: student.track || "AI & Data Science",
          completed_courses: [...App.state.completedCodes],
          conversation_history: conversationHistory.slice(-6)
        })
      });

      if (!response.ok) {
        let detail = "";
        try { detail = (await response.json())?.detail || ""; } catch {}
        throw new Error(detail || `Copilot request failed (${response.status})`);
      }

      const data = await response.json();
      const answer = data?.copilot_response || "The Copilot returned an empty response.";
      const latency = Math.round(performance.now() - started);
      const usageText = (typeof data?.usage_count === "number" && typeof data?.daily_limit === "number")
        ? ` • ${data.usage_count}/${data.daily_limit} today`
        : "";
      setText("llm-status", `${data?.llm_provider || "LLM"} • ${latency} ms${usageText}`);
      appendMessage("assistant", answer);
      renderSources(data?.sources || []);
      conversationHistory.push({ role: "user", content: text });
      conversationHistory.push({ role: "assistant", content: answer });
      conversationHistory = conversationHistory.slice(-6);
    } catch (err) {
      console.error(err);
      setText("llm-status", "Offline");
      appendMessage("assistant",
        `**Copilot is unavailable right now.**\n\n${friendlyError(err)}\n\nMake sure FastAPI is running and the Ollama service is available to the backend.`
      );
    } finally {
      setBusy(false);
    }
  }


  function renderSources(sources) {
    const container = document.getElementById("chat-messages-container");
    if (!container || !Array.isArray(sources) || !sources.length) return;
    const box = document.createElement("div");
    box.className = "ai-source-note";
    box.innerHTML = `<strong>Verified sources</strong><ul>${sources.map(s => `<li>${App.escapeHtml(String(s.source || "Source"))} — ${App.escapeHtml(String(s.scope || ""))}</li>`).join("")}</ul>`;
    container.appendChild(box);
    container.scrollTop = container.scrollHeight;
  }

  function setBusy(value) {
    busy = value;
    const indicator = document.getElementById("ai-typing-indicator");
    const button = document.getElementById("copilot-send-btn");
    indicator?.classList.toggle("hidden", !value);
    if (button) button.disabled = value;
    const container = document.getElementById("chat-messages-container");
    if (container) container.scrollTop = container.scrollHeight;
  }

  function appendMessage(sender, text) {
    const container = document.getElementById("chat-messages-container");
    if (!container) return;

    const row = document.createElement("div");
    row.className = `message-row ${sender === "user" ? "user" : "bot"}`;

    const avatar = document.createElement("div");
    avatar.className = `message-avatar ${sender === "user" ? "user" : "bot"}`;
    avatar.innerHTML = `<i data-lucide="${sender === "user" ? "user" : "bot"}" class="h-3.5 w-3.5"></i>`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = renderMarkdown(text);

    row.appendChild(avatar);
    row.appendChild(bubble);
    container.appendChild(row);

    lucide.createIcons();
    container.scrollTop = container.scrollHeight;
  }

  function renderMarkdown(value) {
    // Lightweight safe renderer for the simple markdown returned by an LLM.
    let text = App.escapeHtml(value);
    const lines = text.split(/\r?\n/);
    const output = [];
    let inList = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (/^[-*•]\s+/.test(trimmed)) {
        if (!inList) {
          output.push("<ul>");
          inList = true;
        }
        output.push(`<li>${formatInline(trimmed.replace(/^[-*•]\s+/, ""))}</li>`);
      } else {
        if (inList) {
          output.push("</ul>");
          inList = false;
        }
        if (!trimmed) {
          output.push("<div class='h-1'></div>");
        } else {
          output.push(`<p>${formatInline(trimmed)}</p>`);
        }
      }
    }

    if (inList) output.push("</ul>");
    return output.join("");
  }

  function formatInline(text) {
    return text
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/__([^_]+)__/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }

  function friendlyError(err) {
    const message = err?.message || "Unknown error.";
    if (message.includes("Failed to fetch")) {
      return "The frontend cannot reach the FastAPI server at http://127.0.0.1:8000.";
    }
    if (message.includes("Daily AI question limit reached")) {
      return message;
    }
    return message;
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }
})();
