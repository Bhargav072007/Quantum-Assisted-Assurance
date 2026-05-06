function showToast(message, ok) {
  const node = document.createElement("div");
  node.className = "result-toast";
  node.style.color = ok ? "var(--success)" : "var(--danger)";
  node.textContent = message;
  document.body.appendChild(node);
  window.setTimeout(() => node.remove(), 3200);
}

function updateGauge(score) {
  const arc = document.getElementById("gauge-arc");
  const text = document.getElementById("gauge-score");
  const circumference = 314;
  if (!arc) return;
  const normalized = Math.max(0, Math.min(100, Number(score) || 0));
  const dash = (normalized / 100) * circumference;
  arc.style.strokeDasharray = `${dash} ${circumference - dash}`;
  arc.style.stroke = normalized < 40 ? "#10B981" : normalized < 70 ? "#F59E0B" : "#EF4444";
  if (text) text.textContent = `${normalized}`;
}

function animateShowcaseGauge() {
  const arc = document.getElementById("showcase-arc");
  const text = document.getElementById("showcase-score");
  const breakdown = document.getElementById("gauge-breakdown");
  const verdict = document.getElementById("gauge-verdict");
  if (!arc || !text || !breakdown || !verdict) return;

  const target = 73;
  const circumference = 503;
  let start = null;

  function step(timestamp) {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / 2000, 1);
    const score = Math.round(progress * target);
    const dash = (score / 100) * circumference;
    arc.style.strokeDasharray = `${dash} ${circumference - dash}`;
    arc.style.stroke = score < 40 ? "#10B981" : score < 70 ? "#F59E0B" : "#EF4444";
    text.textContent = `${score}`;
    if (progress < 1) {
      window.requestAnimationFrame(step);
    } else {
      breakdown.style.opacity = "1";
      verdict.style.opacity = "1";
    }
  }

  window.requestAnimationFrame(step);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function postRun(endpoint, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Running...";
  return fetch(endpoint, { method: "POST" })
    .then((response) => response.json().then((data) => ({ response, data })))
    .then(({ response, data }) => {
      showToast(data.message || "Run finished.", response.ok && data.ok !== false);
      if (response.ok && data.ok !== false) {
        window.setTimeout(() => window.location.reload(), 900);
      }
    })
    .catch((error) => {
      showToast(error.message || "Run failed.", false);
    })
    .finally(() => {
      button.disabled = false;
      button.textContent = original;
    });
}

function setActiveMode(mode) {
  document.querySelectorAll(".mode-chip").forEach((node) => {
    node.classList.toggle("active", node.dataset.mode === mode);
  });
  const input = document.querySelector("[data-assistant-form] input[name='mode']");
  if (input) input.value = mode;
}

function renderThreadList(threads, activeThreadId) {
  const node = document.querySelector("[data-thread-list]");
  if (!node) return;
  if (!threads || !threads.length) {
    node.innerHTML = "<p class='empty-copy'>No threads yet. Start one from the composer.</p>";
    return;
  }
  node.innerHTML = threads
    .slice(0, 10)
    .map(
      (thread) => `
        <a class="thread-item ${thread.thread_id === activeThreadId ? "active" : ""}" href="/app/assistant?thread=${thread.thread_id}" data-thread-id="${thread.thread_id}">
          <strong>${escapeHtml(thread.title)}</strong>
          <span>${escapeHtml(thread.mode.charAt(0).toUpperCase() + thread.mode.slice(1))} mode</span>
        </a>
      `
    )
    .join("");
}

function renderAssistantResult(data) {
  const chartNode = document.querySelector("[data-assistant-chart]");
  if (!chartNode) return;
  const points = data.chart_points || [];
  if (!points.length) {
    chartNode.innerHTML = "<p class='empty-copy'>No chart data available.</p>";
    return;
  }
  const max = Math.max(...points.map((point) => Number(point.value) || 0), 1);
  chartNode.innerHTML = points
    .map((point) => {
      const height = Math.max(10, Math.round((Number(point.value) / max) * 100));
      return `
        <div class="chart-bar">
          <div class="chart-bar-track">
            <div class="chart-bar-fill" style="height:${height}%"></div>
          </div>
          <strong>${point.value}${point.unit || ""}</strong>
          <span class="chart-label">${escapeHtml(point.label)}</span>
        </div>
      `;
    })
    .join("");
}

function appendUserMessage(prompt, mode) {
  const log = document.querySelector("[data-chat-log]");
  if (!log) return;
  const empty = log.querySelector(".chat-empty");
  if (empty) empty.remove();
  const wrapper = document.createElement("div");
  wrapper.className = "chat-message user";
  wrapper.innerHTML = `
    <div class="chat-meta">
      <strong>You</strong>
      <span>${escapeHtml(mode.charAt(0).toUpperCase() + mode.slice(1))} mode</span>
    </div>
    <div class="chat-body">${escapeHtml(prompt)}</div>
  `;
  log.appendChild(wrapper);
  log.scrollTop = log.scrollHeight;
}

function appendAssistantMessage(text, metaText) {
  const log = document.querySelector("[data-chat-log]");
  if (!log) return;
  const wrapper = document.createElement("div");
  wrapper.className = "chat-message assistant";
  wrapper.innerHTML = `
    <div class="chat-meta">
      <strong>Meghyan Analyst</strong>
      <span>${escapeHtml(metaText)}</span>
    </div>
    <div class="chat-body">${escapeHtml(text)}</div>
  `;
  log.appendChild(wrapper);
  log.scrollTop = log.scrollHeight;
}

function severityBadgeClass(severity) {
  const normalized = String(severity || "low").toLowerCase();
  if (normalized === "critical") return "badge-critical";
  if (normalized === "high") return "badge-high";
  if (normalized === "medium") return "badge-medium";
  return "badge-low";
}

function renderDemoResults(data) {
  const shell = document.querySelector("[data-demo-results]");
  const failureCount = document.querySelector("[data-failure-count]");
  const scenarioLabel = document.querySelector("[data-scenario-label]");
  const severityPills = document.querySelector("[data-severity-pills]");
  const topFailures = document.querySelector("[data-top-failures]");
  const meta = document.querySelector("[data-demo-meta]");
  if (!shell || !failureCount || !scenarioLabel || !severityPills || !topFailures || !meta) return;

  shell.hidden = false;
  updateGauge(data.risk_score);
  failureCount.textContent = `${data.failures_found || 0} failures discovered`;
  scenarioLabel.textContent = String(data.scenario_type || "").replace(/^\w/, (char) => char.toUpperCase());

  const failures = Array.isArray(data.top_failures) ? data.top_failures.slice(0, 3) : [];
  const severityCounts = failures.reduce((counts, item) => {
    const level = String(item.severity || "low").toLowerCase();
    counts[level] = (counts[level] || 0) + 1;
    return counts;
  }, {});

  severityPills.innerHTML = Object.entries(severityCounts)
    .map(([level, count]) => `<span class="${severityBadgeClass(level)}">${count} ${escapeHtml(level)}</span>`)
    .join("") || "<span class='badge-low'>No severe hits</span>";

  topFailures.innerHTML = failures
    .map(
      (item) => `
        <article class="failure-card">
          <div class="failure-card-header">
            <strong>${escapeHtml(item.type || item.label || "Scenario risk")}</strong>
            <span class="${severityBadgeClass(item.severity)}">${escapeHtml(item.severity || "low")}</span>
          </div>
          <p>${escapeHtml(item.description || item.reason || "Rare-event behavior flagged by the live pipeline.")}</p>
        </article>
      `
    )
    .join("") || "<article class='failure-card'><p>No top failures returned for this run.</p></article>";

  meta.innerHTML = `Powered by IBM Qiskit · Teacher accuracy: <strong>${Number(data.teacher_accuracy || 0).toFixed(3)}</strong> · Backend: <strong>${escapeHtml(data.quantum_backend || "qiskit-statevector")}</strong>`;
}

function setDemoStatus(message) {
  const node = document.querySelector("[data-demo-status]");
  if (node) node.innerHTML = message;
}

function resetProgress() {
  const fill = document.querySelector("[data-demo-progress]");
  if (fill) fill.style.width = "0%";
  document.querySelectorAll("[data-progress-stage]").forEach((node) => node.classList.remove("active"));
}

function advanceProgress(stages) {
  const fill = document.querySelector("[data-demo-progress]");
  if (!fill) return [];
  resetProgress();
  return stages.map(({ key, width, delay }) =>
    window.setTimeout(() => {
      fill.style.width = `${width}%`;
      document.querySelectorAll("[data-progress-stage]").forEach((node) => {
        node.classList.toggle("active", node.dataset.progressStage === key);
      });
    }, delay)
  );
}

function initDemoRunner() {
  const runButton = document.querySelector("[data-demo-run]");
  const scenarioButtons = document.querySelectorAll("[data-scenario]");
  if (!runButton || !scenarioButtons.length) return;

  let currentScenario = "collision";
  scenarioButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentScenario = button.dataset.scenario;
      scenarioButtons.forEach((node) => node.classList.toggle("active", node === button));
    });
  });

  runButton.addEventListener("click", async () => {
    const timers = advanceProgress([
      { key: "teacher", width: 40, delay: 100 },
      { key: "quantum", width: 80, delay: 2100 },
      { key: "student", width: 100, delay: 5100 },
    ]);
    const original = runButton.textContent;
    runButton.disabled = true;
    runButton.textContent = "Running...";
    setDemoStatus("Teacher analyzing behavior landscape...");

    const stageMessages = [
      { delay: 2100, text: "Quantum refinement prioritizing rare-risk regions..." },
      { delay: 5100, text: "Distilled student scoring final scenarios..." },
    ];
    const messageTimers = stageMessages.map((item) => window.setTimeout(() => setDemoStatus(item.text), item.delay));

    try {
      const response = await fetch("/api/demo/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_type: currentScenario }),
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) {
        throw new Error(data.message || data.error || "Demo run failed.");
      }
      renderDemoResults(data);
      setDemoStatus(`Run complete. <strong>${data.remaining_runs ?? 0} demo runs</strong> remaining this hour.`);
    } catch (error) {
      setDemoStatus("The live run could not be completed right now.");
      showToast(error.message || "Demo run failed.", false);
      resetProgress();
    } finally {
      timers.forEach((timer) => window.clearTimeout(timer));
      messageTimers.forEach((timer) => window.clearTimeout(timer));
      runButton.disabled = false;
      runButton.textContent = original;
    }
  });
}

function initPricingPage() {
  const billingButtons = document.querySelectorAll("[data-billing-mode]");
  if (billingButtons.length) {
    const setMode = (mode) => {
      billingButtons.forEach((button) => button.classList.toggle("active", button.dataset.billingMode === mode));
      document.querySelectorAll("[data-price-run]").forEach((node) => {
        node.hidden = mode !== "run";
      });
      document.querySelectorAll("[data-price-monthly]").forEach((node) => {
        node.hidden = mode === "run";
      });
      document.querySelectorAll("[data-price-label]").forEach((node, index) => {
        if (index === 0) node.textContent = mode === "run" ? "/run" : "/month";
        else if (index === 1) node.textContent = mode === "run" ? "/scenario" : "/month";
        else node.textContent = mode === "run" ? "/audit" : "/month";
      });
    };

    billingButtons.forEach((button) => button.addEventListener("click", () => setMode(button.dataset.billingMode)));
    setMode("run");
  }

  document.querySelectorAll("[data-faq-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const answer = button.nextElementSibling;
      const marker = button.querySelector("strong");
      const isHidden = answer.hasAttribute("hidden");
      if (isHidden) answer.removeAttribute("hidden");
      else answer.setAttribute("hidden", "");
      if (marker) marker.textContent = isHidden ? "−" : "+";
    });
  });
}

function initStudioUpload() {
  const zone = document.getElementById("upload-zone");
  const input = document.getElementById("file-input");
  const status = document.getElementById("upload-status");
  const filename = document.getElementById("status-filename");
  if (!zone || !input || !status || !filename) return;

  function handleFile(file) {
    if (!file) return;
    filename.textContent = `${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
    zone.style.display = "none";
    status.style.display = "flex";
  }

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("drag-over");
    handleFile(event.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => handleFile(input.files[0]));
}

function initFeatureAnimations() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;

      if (el.id === "chat-demo-1") {
        const messages = [
          { role: "user", text: "I run a chartered plane service. How do I find the failure points in my routing AI?" },
          { role: "agent", text: "I'll run a Quantum Tree red team on your routing policy. Give me 60 seconds." },
          { role: "system", text: "Running: Teacher → Quantum → Student..." },
          { role: "agent", text: "Found 3 critical scenarios. Worst case: FL290, crossing intruder at 90°. Separation drops to 2.1 NM." },
          { role: "user", text: "What should I do about it?" },
          { role: "agent", text: "Flagged in your report with the full decision trace. Want 50 more scenarios like this?" },
        ];
        messages.forEach((message, index) => {
          window.setTimeout(() => {
            const div = document.createElement("div");
            div.className = `chat-msg ${message.role}`;
            div.textContent = message.text;
            el.appendChild(div);
            window.requestAnimationFrame(() => div.classList.add("visible"));
          }, index * 820);
        });
        io.unobserve(el);
      }

      if (el.classList.contains("feature-terminal")) {
        const lines = [
          { id: "term-line-1", text: "$ meghyan scenarios generate --type collision --count 500", color: "#F5F5F5" },
          { id: "term-line-2", text: "  Quantum Tree sampling...", color: "#9CA3AF" },
          { id: "term-line-3", text: "  500 rare-event scenarios generated", color: "#10B981" },
          { id: "term-output", text: "  Saved: scenarios_collision_20260502.json (2.3 MB)", color: "#3B82F6" },
        ];
        let delay = 200;
        lines.forEach((line) => {
          window.setTimeout(() => {
            const target = document.getElementById(line.id);
            if (!target) return;
            target.style.color = line.color;
            let cursor = 0;
            const interval = window.setInterval(() => {
              cursor += 1;
              target.textContent = line.text.slice(0, cursor);
              if (cursor >= line.text.length) window.clearInterval(interval);
            }, 24);
          }, delay);
          delay += line.text.length * 24 + 360;
        });
        io.unobserve(el);
      }

      if (el.classList.contains("feature-gauge-showcase")) {
        animateShowcaseGauge();
        io.unobserve(el);
      }

      if (el.classList.contains("feature-report")) {
        el.querySelectorAll(".report-row, .report-actions").forEach((row) => row.classList.add("in-view"));
        io.unobserve(el);
      }
    });
  }, { threshold: 0.12 });

  [
    document.getElementById("chat-demo-1"),
    document.querySelector(".feature-terminal"),
    document.querySelector(".feature-gauge-showcase"),
    document.querySelector(".feature-report"),
  ].forEach((target) => {
    if (target) io.observe(target);
  });
}

function initNavState() {
  const nav = document.querySelector("[data-nav]");
  if (!nav) return;
  const sync = () => {
    nav.classList.toggle("compact", window.scrollY > 60);
  };
  sync();
  window.addEventListener("scroll", sync, { passive: true });
}

function initAssistant() {
  const assistantForm = document.querySelector("[data-assistant-form]");
  if (!assistantForm) return;

  const initialChart = document.getElementById("assistant-chart-data");
  if (initialChart) {
    try {
      renderAssistantResult({ chart_points: JSON.parse(initialChart.textContent || "[]") });
    } catch (error) {
      console.warn("Unable to load initial assistant chart.", error);
    }
  }

  document.querySelectorAll(".mode-chip").forEach((button) => {
    button.addEventListener("click", () => setActiveMode(button.dataset.mode));
  });

  document.querySelectorAll("[data-assistant-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      const textarea = assistantForm.querySelector("textarea[name='prompt']");
      if (!textarea) return;
      textarea.value = button.dataset.assistantPrompt || "";
      textarea.focus();
    });
  });

  assistantForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = assistantForm.querySelector("button[type='submit']");
    const promptField = assistantForm.querySelector("textarea[name='prompt']");
    const prompt = promptField?.value?.trim();
    const mode = assistantForm.querySelector("input[name='mode']")?.value || "internal";
    const threadId = assistantForm.querySelector("input[name='thread_id']")?.value || "";
    if (!prompt) {
      showToast("Enter a question for the analyst.", false);
      return;
    }
    appendUserMessage(prompt, mode);
    if (promptField) promptField.value = "";
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "Thinking...";
    try {
      const response = await fetch("/api/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, mode, thread_id: threadId }),
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) {
        throw new Error(data.message || "Analysis failed.");
      }
      renderThreadList(data.threads || [], data.thread?.thread_id);
      appendAssistantMessage(data.answer, `${data.model} via ${data.provider} · ${data.tokens_used} tokens`);
      renderAssistantResult(data);
      showToast(data.message || "Analysis ready.", true);
    } catch (error) {
      showToast(error.message || "Analysis failed.", false);
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("visible");
      entry.target.classList.add("in");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.05, rootMargin: "0px 0px -24px 0px" });
  // rAF ensures CSS is applied before we start observing so transitions fire
  requestAnimationFrame(() => {
    document.querySelectorAll(".reveal, [data-anim]").forEach((node) => observer.observe(node));
  });

  document.querySelectorAll(".js-run").forEach((button) => {
    button.addEventListener("click", () => postRun(button.dataset.endpoint, button));
  });

  initDemoRunner();
  initPricingPage();
  initStudioUpload();
  initFeatureAnimations();
  initNavState();
  initAssistant();
});
