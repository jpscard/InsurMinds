/**
 * InsureAlert — Frontend Application Logic
 *
 * Gerencia a comunicação com a API backend, renderização de dados
 * e animações do pipeline de agentes inteligentes.
 */

const API_BASE = "";

// ═══════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════

let isRunning = false;
let lastResult = null;

// ═══════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
  initUserSession();
  updateClock();
  setInterval(updateClock, 1000);

  await checkApiStatus();
  await loadPolicyholders();
  await loadLastResult();
});

function initUserSession() {
  const sessionStr = localStorage.getItem("insureAlert_session") || sessionStorage.getItem("insureAlert_session");
  if (!sessionStr) {
    window.location.href = "/login";
    return;
  }
  try {
    const session = JSON.parse(sessionStr);
    const userNameEl = document.getElementById("userName");
    const userAvatarEl = document.getElementById("userAvatar");
    if (userNameEl) {
      userNameEl.textContent = session.name || session.email || "Usuário";
    }
    if (userAvatarEl) {
      const initial = (session.name ? session.name[0] : (session.email ? session.email[0] : "U")).toUpperCase();
      userAvatarEl.textContent = initial;
    }
  } catch (e) {
    console.error("Erro ao ler dados da sessão:", e);
  }
}

function updateClock() {
  const now = new Date();
  const el = document.getElementById("headerTime");
  if (el) {
    el.textContent = now.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }
}

async function checkApiStatus() {
  const dot = document.querySelector(".status-dot");
  const text = document.querySelector(".status-text");

  try {
    const res = await fetch(`${API_BASE}/api/policyholders`);
    if (res.ok) {
      dot.classList.add("online");
      dot.classList.remove("error");
      text.textContent = "Sistema Online";
    } else {
      throw new Error("API error");
    }
  } catch {
    dot.classList.add("error");
    dot.classList.remove("online");
    text.textContent = "Offline";
  }
}

// ═══════════════════════════════════════════════════════════
// PIPELINE EXECUTION
// ═══════════════════════════════════════════════════════════

async function runPipeline() {
  if (isRunning) return;
  isRunning = true;

  const btn = document.getElementById("runPipelineBtn");
  btn.disabled = true;
  btn.classList.add("running");
  btn.innerHTML = '<span class="spinner"></span> Executando Pipeline...';

  // Reset steps
  resetPipelineSteps();

  // Animate steps sequentially
  await animateStep(1, "Consultando API do INMET...");

  try {
    const response = await fetch(`${API_BASE}/api/pipeline/run`, {
      method: "POST",
    });
    const data = await response.json();

    if (!data.success) throw new Error(data.detail || "Erro no pipeline");

    lastResult = data;

    // Animate completed steps
    for (const step of data.steps) {
      await sleep(600);
      completeStep(step.step, step.status, step.detail);
    }

    await sleep(400);

    // Update stats
    updateStats(data.summary);

    // Render results
    renderEvents(data.events);
    renderNotifications(data.notifications);

  } catch (err) {
    console.error("Pipeline error:", err);
    for (let i = 1; i <= 4; i++) {
      const el = document.getElementById(`step${i}`);
      if (!el.classList.contains("completed")) {
        el.classList.add("error");
        el.classList.remove("active");
      }
    }
  } finally {
    isRunning = false;
    btn.disabled = false;
    btn.classList.remove("running");
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>
      Executar Pipeline
    `;
  }
}

function resetPipelineSteps() {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`step${i}`);
    el.classList.remove("active", "completed", "error");
    document.getElementById(`step${i}Status`).textContent = "";
  }
}

async function animateStep(step, message) {
  const el = document.getElementById(`step${step}`);
  el.classList.add("active");
  document.getElementById(`step${step}Status`).innerHTML =
    `<span class="spinner"></span> ${message}`;
}

function completeStep(step, status, detail) {
  const el = document.getElementById(`step${step}`);
  el.classList.remove("active");
  el.classList.add(status === "success" ? "completed" : "error");

  const icon = status === "success" ? "✅" : "❌";
  document.getElementById(`step${step}Status`).textContent = `${icon} ${detail}`;

  // Activate next step
  if (status === "success" && step < 4) {
    const nextEl = document.getElementById(`step${step + 1}`);
    nextEl.classList.add("active");
    const loadingMsgs = [
      "",
      "Consultando API do INMET...",
      "Classificando eventos climáticos...",
      "Cruzando com base de segurados...",
      "Gerando mensagens com IA...",
    ];
    document.getElementById(`step${step + 1}Status`).innerHTML =
      `<span class="spinner"></span> ${loadingMsgs[step + 1] || "Processando..."}`;
  }
}

// ═══════════════════════════════════════════════════════════
// DATA LOADING
// ═══════════════════════════════════════════════════════════

async function loadPolicyholders() {
  try {
    const res = await fetch(`${API_BASE}/api/policyholders`);
    const data = await res.json();

    if (data.success) {
      renderPolicyholders(data.policyholders);
      document.getElementById("phBadge").textContent = data.count;
    }
  } catch (err) {
    console.error("Error loading policyholders:", err);
  }
}

async function loadLastResult() {
  try {
    const res = await fetch(`${API_BASE}/api/pipeline/status`);
    const data = await res.json();

    if (data.success && data.has_result) {
      lastResult = data.result;
      updateStats({
        events_collected: data.result.events_collected,
        events_relevant: data.result.events_relevant,
        policyholders_matched: data.result.policyholders_matched,
        notifications_generated: data.result.notifications_generated,
      });
      renderEvents(data.result.events);
      renderNotifications(data.result.notifications.map(n => ({...n})));
    }
  } catch (err) {
    // No previous result
  }
}

// ═══════════════════════════════════════════════════════════
// RENDERING
// ═══════════════════════════════════════════════════════════

function updateStats(summary) {
  animateCounter("statAlertsValue", summary.events_collected);
  animateCounter("statEventsValue", summary.events_relevant);
  animateCounter("statPolicyholdersValue", summary.policyholders_matched);
  animateCounter("statNotificationsValue", summary.notifications_generated);
}

function animateCounter(elementId, targetValue) {
  const el = document.getElementById(elementId);
  const start = parseInt(el.textContent) || 0;
  const duration = 800;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (targetValue - start) * eased);
    el.textContent = current;

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

function renderEvents(events) {
  const container = document.getElementById("eventsList");
  const badge = document.getElementById("eventsBadge");
  badge.textContent = events.length;

  if (!events.length) {
    container.innerHTML = '<div class="empty-state"><p>Nenhum evento detectado</p></div>';
    return;
  }

  container.innerHTML = events
    .map((event, i) => {
      const severity = event.severity || "baixa";
      const eventType = (event.event_type || "desconhecido")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
      const states = (event.affected_states || []).slice(0, 5).join(", ");
      const desc = event.description || "";

      return `
        <div class="event-item" style="animation-delay: ${i * 100}ms">
          <div class="event-header">
            <span class="event-title">${escapeHtml(event.title || eventType)}</span>
            <span class="severity-badge severity-${severity}">${severity.toUpperCase()}</span>
          </div>
          <div class="event-meta">
            <span>🌪️ ${eventType}</span>
            ${states ? `<span>📍 ${escapeHtml(states)}</span>` : ""}
            <span>📰 ${escapeHtml(event.source || "—")}</span>
          </div>
          ${desc ? `<div class="event-description">${escapeHtml(desc).substring(0, 200)}${desc.length > 200 ? "..." : ""}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderNotifications(notifications) {
  const container = document.getElementById("notificationsList");
  const badge = document.getElementById("notificationsBadge");
  badge.textContent = notifications.length;

  if (!notifications.length) {
    container.innerHTML =
      '<div class="empty-state"><p>Nenhuma notificação gerada</p></div>';
    return;
  }

  container.innerHTML = notifications
    .map((n, i) => {
      const channelIcons = {
        sms: "📱",
        email: "📧",
        push: "🔔",
        whatsapp: "💬",
      };
      const channelIcon = channelIcons[n.channel] || "📨";
      const preview = n.short_message || n.message || "";

      return `
        <div class="notification-item" onclick='showNotificationDetail(${JSON.stringify(n).replace(/'/g, "&#39;")})'
             style="animation-delay: ${i * 80}ms">
          <div class="notification-header">
            <span class="notification-name">${escapeHtml(n.policyholder_name)}</span>
            <span class="channel-badge">${channelIcon} ${(n.channel || "").toUpperCase()}</span>
          </div>
          <div class="notification-subject">${escapeHtml(n.subject || "")}</div>
          <div class="notification-preview">${escapeHtml(preview).substring(0, 120)}${preview.length > 120 ? "..." : ""}</div>
          <div class="notification-footer">
            <span>📍 ${escapeHtml(n.city || "")}/${escapeHtml(n.state || "")}</span>
            <span class="sent-badge">✓ Enviada (simulação)</span>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderPolicyholders(policyholders) {
  const tbody = document.getElementById("policyholdersBody");

  tbody.innerHTML = policyholders
    .map((ph) => {
      const tags = (ph.policies || [])
        .map((p) => {
          const type = p.type || "residencial";
          return `<span class="insurance-tag ${type}">${type}</span>`;
        })
        .join("");

      const channelIcons = {
        sms: "📱 SMS",
        email: "📧 Email",
        push: "🔔 Push",
        whatsapp: "💬 WhatsApp",
      };

      return `
        <tr>
          <td><strong>${escapeHtml(ph.id)}</strong></td>
          <td>${escapeHtml(ph.name)}</td>
          <td>${escapeHtml(ph.city)}/${escapeHtml(ph.state)}</td>
          <td><div class="insurance-tags">${tags}</div></td>
          <td>${channelIcons[ph.preferred_channel] || ph.preferred_channel}</td>
          <td><span class="status-active">Ativo</span></td>
        </tr>
      `;
    })
    .join("");
}

// ═══════════════════════════════════════════════════════════
// MODAL
// ═══════════════════════════════════════════════════════════

function showNotificationDetail(notification) {
  const modal = document.getElementById("notificationModal");
  const body = document.getElementById("modalBody");
  const title = document.getElementById("modalTitle");

  title.textContent = `📨 Notificação — ${notification.policyholder_name}`;

  const severity = notification.severity || "media";
  const eventType = (notification.event_type || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const recommendations = (notification.recommendations || [])
    .map((r) => `<li>${escapeHtml(r)}</li>`)
    .join("");

  body.innerHTML = `
    <div class="modal-field">
      <div class="modal-field-label">Segurado</div>
      <div class="modal-field-value">${escapeHtml(notification.policyholder_name)} — ${escapeHtml(notification.city || "")}/${escapeHtml(notification.state || "")}</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">Evento / Severidade</div>
      <div class="modal-field-value">
        ${eventType}
        <span class="severity-badge severity-${severity}" style="margin-left: 8px">${severity.toUpperCase()}</span>
      </div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">Tipo de Seguro</div>
      <div class="modal-field-value">${escapeHtml((notification.insurance_type || "").replace(/_/g, " "))}</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">Canal de Envio</div>
      <div class="modal-field-value">${(notification.channel || "").toUpperCase()}</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">Assunto</div>
      <div class="modal-field-value">${escapeHtml(notification.subject || "")}</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">Mensagem Completa</div>
      <div class="modal-message-box">${escapeHtml(notification.message || "")}</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">Versão SMS (160 caracteres)</div>
      <div class="modal-message-box">${escapeHtml(notification.short_message || "")}</div>
    </div>

    ${
      recommendations
        ? `
      <div class="modal-field">
        <div class="modal-field-label">Recomendações Preventivas</div>
        <ul class="modal-recommendations">${recommendations}</ul>
      </div>
    `
        : ""
    }

    <div class="modal-field">
      <div class="modal-field-label">Status do Envio</div>
      <div class="modal-field-value">
        <span class="sent-badge">✓ Enviada com sucesso (simulação)</span>
      </div>
    </div>
  `;

  modal.classList.add("active");
}

function closeModal() {
  document.getElementById("notificationModal").classList.remove("active");
}

// Close modal on overlay click
document.getElementById("notificationModal")?.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    closeModal();
  }
});

// Close modal on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

// ═══════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = String(str);
  return div.innerHTML;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
