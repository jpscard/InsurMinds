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
let allPolicyholders = [];
let allNotifications = [];
let filteredNotifications = [];
let currentChannelFilter = 'all';
let activeNotificationIndex = 0;
let currentFormat = 'whatsapp';

function setGlobalProgress(percent) {
  const bar = document.getElementById("globalProgress");
  if (!bar) return;
  if (percent <= 0) {
    bar.style.display = "block";
    bar.style.width = "0%";
  } else if (percent >= 100) {
    bar.style.display = "block";
    bar.style.width = "100%";
    setTimeout(() => {
      bar.style.display = "none";
      bar.style.width = "0%";
    }, 600);
  } else {
    bar.style.display = "block";
    bar.style.width = `${percent}%`;
  }
}

// ═══════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
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

  setGlobalProgress(15);

  // Set visual loading states in events and WhatsApp pane
  const eventsContainer = document.getElementById("eventsList");
  const waChatList = document.getElementById("waChatList");
  const waChatBody = document.getElementById("waChatBody");
  if (eventsContainer) {
    eventsContainer.innerHTML = `
      <div class="empty-state-guided" style="opacity: 0.9">
        <div class="spinner" style="width:28px;height:28px;border-width:3px;border-color:rgba(0,210,255,0.2);border-top-color:#00d2ff;margin-bottom:8px"></div>
        <p>Consultando INMET e classificando eventos meteorológicos...</p>
      </div>
    `;
  }
  if (waChatList) {
    waChatList.innerHTML = `
      <div class="wa-empty-chat" style="padding: 24px;">
        <div class="spinner" style="width:28px;height:28px;border-width:3px;border-color:rgba(0,168,132,0.2);border-top-color:#00a884;margin-bottom:12px;"></div>
        <p style="font-size:0.82rem;color:#8696a0;">Cruzando apólices e acionando IA...</p>
      </div>
    `;
  }
  if (waChatBody) {
    waChatBody.innerHTML = `
      <div class="wa-empty-chat">
        <div class="spinner" style="width:36px;height:36px;border-width:3px;border-color:rgba(0,168,132,0.2);border-top-color:#00a884;margin-bottom:16px;"></div>
        <h4>Gerando Mensagens Personalizadas</h4>
        <p>Aguarde enquanto os agentes inteligentes redigem orientações de proteção para cada segurado...</p>
      </div>
    `;
  }

  // Reset steps
  resetPipelineSteps();

  // Animate steps sequentially
  await animateStep(1, "Consultando API do INMET...");
  setGlobalProgress(25);

  try {
    const response = await fetch(`${API_BASE}/api/pipeline/run`, {
      method: "POST",
    });
    const data = await response.json();

    if (!data.success) throw new Error(data.detail || "Erro no pipeline");

    lastResult = data;

    // Animate completed steps
    const stepProgress = [35, 60, 80, 95];
    for (let i = 0; i < data.steps.length; i++) {
      const step = data.steps[i];
      await sleep(600);
      completeStep(step.step, step.status, step.detail);
      setGlobalProgress(stepProgress[i] || 90);
    }

    await sleep(400);
    setGlobalProgress(100);

    // Update stats
    updateStats(data.summary);

    // Render results
    renderEvents(data.events);
    renderNotifications(data.notifications);

  } catch (err) {
    console.error("Pipeline error:", err);
    setGlobalProgress(100);
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
      allPolicyholders = data.policyholders || [];
      renderPolicyholders(allPolicyholders);
      const phBadge = document.getElementById("phBadge");
      if (phBadge) phBadge.textContent = data.count;
      const tabBadge = document.getElementById("tabBadgePolicyholders");
      if (tabBadge) tabBadge.textContent = data.count;
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
  document.querySelectorAll(".stat-value.init").forEach((el) => el.classList.remove("init"));
  animateCounter("statAlertsValue", summary.events_collected);
  animateCounter("statEventsValue", summary.events_relevant);
  animateCounter("statPolicyholdersValue", summary.policyholders_matched);
  animateCounter("statNotificationsValue", summary.notifications_generated);
}

function animateCounter(elementId, targetValue) {
  const el = document.getElementById(elementId);
  if (!el) return;
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

function switchDashTab(tab) {
  const tabs = ['whatsapp', 'events', 'policyholders'];
  tabs.forEach(t => {
    const btn = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const pane = document.getElementById(`pane${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (btn) btn.classList.toggle('active', t === tab);
    if (pane) pane.classList.toggle('active', t === tab);
  });
}

function renderEvents(events) {
  const container = document.getElementById("eventsList");
  const badge = document.getElementById("eventsBadge");
  if (badge) badge.textContent = events.length;
  const tabBadge = document.getElementById("tabBadgeEvents");
  if (tabBadge) tabBadge.textContent = events.length;

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

// ═══════════════════════════════════════════════════════════
// WHATSAPP / CENTRAL DE COMUNICAÇÕES MULTICANAL
// ═══════════════════════════════════════════════════════════

function renderNotifications(notifications) {
  allNotifications = notifications || [];
  
  const tabBadge = document.getElementById("tabBadgeWhatsapp");
  if (tabBadge) tabBadge.textContent = allNotifications.length;

  filterWhatsAppList();

  if (allNotifications.length > 0) {
    selectWhatsAppChat(0);
  } else {
    const chatBody = document.getElementById("waChatBody");
    if (chatBody) {
      chatBody.innerHTML = `
        <div class="wa-empty-chat">
          <div class="wa-empty-chat-icon">💬</div>
          <h4>Nenhuma conversa gerada ainda</h4>
          <p>Clique em <strong>Executar Pipeline</strong> acima para acionar a IA e gerar comunicados preventivos personalizados.</p>
        </div>
      `;
    }
    const footer = document.getElementById("waChatFooter");
    if (footer) footer.style.display = "none";
  }
}

function filterByChannel(channel, btnEl) {
  currentChannelFilter = channel;
  document.querySelectorAll('.wa-filter-chip').forEach(c => c.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  filterWhatsAppList();
}

function filterWhatsAppList() {
  const input = document.getElementById("waSearchInput");
  const query = (input ? input.value : "").toLowerCase().trim();

  filteredNotifications = allNotifications.filter(n => {
    const matchesChannel = currentChannelFilter === 'all' || (n.channel || '').toLowerCase() === currentChannelFilter;
    const name = (n.policyholder_name || '').toLowerCase();
    const city = (n.city || '').toLowerCase();
    const eventType = (n.event_type || '').toLowerCase();
    const matchesQuery = !query || name.includes(query) || city.includes(query) || eventType.includes(query);
    return matchesChannel && matchesQuery;
  });

  const countBadge = document.getElementById("waSidebarCount");
  if (countBadge) countBadge.textContent = filteredNotifications.length;

  renderWhatsAppList(filteredNotifications);

  if (filteredNotifications.length > 0) {
    if (activeNotificationIndex >= filteredNotifications.length) {
      activeNotificationIndex = 0;
    }
    selectWhatsAppChat(activeNotificationIndex);
  } else {
    const chatBody = document.getElementById("waChatBody");
    if (chatBody) {
      chatBody.innerHTML = `
        <div class="wa-empty-chat">
          <div class="wa-empty-chat-icon">🔍</div>
          <h4>Nenhum resultado encontrado</h4>
          <p>Nenhuma mensagem corresponde ao filtro pesquisado.</p>
        </div>
      `;
    }
    const footer = document.getElementById("waChatFooter");
    if (footer) footer.style.display = "none";
  }
}

function renderWhatsAppList(items) {
  const container = document.getElementById("waChatList");
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="wa-empty-chat" style="padding: 24px;">
        <p style="font-size:0.82rem;color:#8696a0;">Nenhum segurado encontrado para este filtro.</p>
      </div>
    `;
    return;
  }

  const channelIcons = {
    whatsapp: '💬 WhatsApp',
    sms: '📱 SMS',
    email: '📧 E-mail',
    push: '🔔 Push'
  };

  container.innerHTML = items.map((n, idx) => {
    const initial = (n.policyholder_name ? n.policyholder_name[0] : 'S').toUpperCase();
    const insType = (n.insurance_type || 'residencial').toLowerCase().replace(/_/g, '');
    const severity = (n.severity || 'media').toLowerCase();
    const isActive = idx === activeNotificationIndex;
    const preview = n.short_message || n.message || '';

    return `
      <div class="wa-chat-item ${isActive ? 'active' : ''}" onclick="selectWhatsAppChat(${idx})" id="waChat_${idx}">
        <div class="wa-chat-avatar ${insType}">
          ${escapeHtml(initial)}
          <span class="wa-severity-indicator ${severity}"></span>
        </div>
        <div class="wa-chat-info">
          <div class="wa-chat-top-row">
            <span class="wa-chat-name">${escapeHtml(n.policyholder_name)}</span>
            <span class="wa-chat-time">Hoje</span>
          </div>
          <div class="wa-chat-bottom-row">
            <span class="wa-chat-snippet">
              <span class="wa-checkmarks">✓✓</span> ${escapeHtml(preview).substring(0, 40)}...
            </span>
            <span class="wa-chat-meta-tag">${channelIcons[n.channel] || n.channel}</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function selectWhatsAppChat(index) {
  activeNotificationIndex = index;
  document.querySelectorAll('.wa-chat-item').forEach((el, i) => {
    el.classList.toggle('active', i === index);
  });

  const n = filteredNotifications[index] || allNotifications[0];
  if (!n) return;

  const initial = (n.policyholder_name ? n.policyholder_name[0] : 'S').toUpperCase();
  const insType = (n.insurance_type || 'residencial').toLowerCase().replace(/_/g, '');

  const avatarEl = document.getElementById("waActiveAvatar");
  if (avatarEl) {
    avatarEl.textContent = initial;
    avatarEl.className = `wa-chat-avatar ${insType}`;
  }

  const nameEl = document.getElementById("waActiveName");
  if (nameEl) nameEl.textContent = n.policyholder_name;

  const subEl = document.getElementById("waActiveSubtitle");
  if (subEl) {
    const formattedIns = (n.insurance_type || 'Residencial').replace(/_/g, ' ');
    subEl.innerHTML = `📍 ${escapeHtml(n.city || '')}/${escapeHtml(n.state || '')} &bull; <span style="color:#00a884;font-weight:600;">Seguro ${escapeHtml(formattedIns)}</span> &bull; online agora`;
  }

  const footer = document.getElementById("waChatFooter");
  if (footer) footer.style.display = 'flex';

  renderActiveMessage();
}

function switchChannelPreview(format) {
  currentFormat = format;
  const formats = ['whatsapp', 'sms', 'email', 'push'];
  formats.forEach(f => {
    const btn = document.getElementById(`btnFmt${f.charAt(0).toUpperCase() + f.slice(1)}`);
    if (btn) btn.classList.toggle('active', f === format);
  });
  renderActiveMessage();
}

function renderActiveMessage() {
  const container = document.getElementById("waChatBody");
  if (!container) return;

  const n = filteredNotifications[activeNotificationIndex] || allNotifications[0];
  if (!n) {
    container.innerHTML = `
      <div class="wa-empty-chat">
        <div class="wa-empty-chat-icon">💬</div>
        <h4>Nenhuma conversa selecionada</h4>
      </div>
    `;
    return;
  }

  const severity = (n.severity || 'media').toLowerCase();
  const eventName = (n.event_type || 'Climático').replace(/_/g, ' ').toUpperCase();
  const recommendations = (n.recommendations || []);

  if (currentFormat === 'whatsapp') {
    const recsHtml = recommendations.length ? `
      <div class="wa-checklist-card">
        <div class="wa-checklist-title">📋 Ações Preventivas Recomendadas:</div>
        ${recommendations.map(r => `<div class="wa-checklist-item">${escapeHtml(r)}</div>`).join('')}
      </div>
    ` : '';

    container.innerHTML = `
      <div class="wa-date-pill">Hoje &bull; Alerta Preventivo Automatizado por IA</div>
      <div class="wa-bubble">
        <div class="wa-bubble-header">
          <span class="wa-bubble-title">⛈️ ${escapeHtml(n.subject || `Alerta de ${eventName}`)}</span>
          <span class="wa-bubble-badge severity-${severity}">${severity.toUpperCase()}</span>
        </div>
        <div class="wa-bubble-text">${escapeHtml(n.message || '')}</div>
        ${recsHtml}
        <div class="wa-action-buttons">
          <button class="wa-action-btn" onclick="showToast('Ligando para a Defesa Civil (199)...')">📞 Ligar para Defesa Civil (199)</button>
          <button class="wa-action-btn" onclick="showToast('Acionando Central 24h da Seguradora (0800)...')">🛡️ Assistência 24h Seguradora (0800)</button>
          <button class="wa-action-btn" onclick="showToast('Confirmação de recebimento registrada com sucesso!')">✅ Confirmar Recebimento do Alerta</button>
        </div>
        <div class="wa-bubble-footer">
          <span>14:22</span>
          <span class="wa-checkmarks">✓✓</span>
        </div>
      </div>
    `;
  } else if (currentFormat === 'sms') {
    const text = n.short_message || n.message || '';
    const count = text.length;

    container.innerHTML = `
      <div class="channel-preview-pane">
        <div class="phone-mockup-frame">
          <div class="phone-mockup-header">
            📱 Mensagem de Texto (SMS Gateway) &bull; Claro/Vivo/TIM
          </div>
          <div class="sms-bubble">
            ${escapeHtml(text)}
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;">
            <span class="sms-char-badge">${count} / 160 caracteres</span>
            <span style="font-size:0.75rem;color:#00a884;font-weight:600;">✓ Entregue via SMS</span>
          </div>
        </div>
      </div>
    `;
  } else if (currentFormat === 'email') {
    const recsList = recommendations.length ? `
      <ul style="margin:10px 0;padding-left:20px;color:#d1d7db;">
        ${recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
      </ul>
    ` : '';

    container.innerHTML = `
      <div class="channel-preview-pane">
        <div class="email-mockup-frame">
          <div class="email-meta-header">
            <div><strong>De:</strong> InsureAlert Alertas &lt;alertas@insurealert.com.br&gt;</div>
            <div><strong>Para:</strong> ${escapeHtml(n.policyholder_name)} &lt;segurado@exemplo.com.br&gt;</div>
            <div><strong>Assunto:</strong> ${escapeHtml(n.subject || `Alerta Preventivo de ${eventName}`)}</div>
          </div>
          <div class="email-body-content">
            <p>${escapeHtml(n.message || '').replace(/\n/g, '<br>')}</p>
            ${recsList}
            <div style="margin-top:16px;padding:12px;background:rgba(59,130,246,0.1);border-left:3px solid #3b82f6;border-radius:4px;font-size:0.8rem;color:#93c5fd;">
              🚨 <strong>Central de Emergência da Seguradora:</strong> Ligue 0800 700 9000 ou acione o canal direto da Defesa Civil pelo 199.
            </div>
          </div>
        </div>
      </div>
    `;
  } else if (currentFormat === 'push') {
    container.innerHTML = `
      <div class="channel-preview-pane">
        <div style="background:#182229;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:16px;box-shadow:0 8px 24px rgba(0,0,0,0.5);">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <div style="width:24px;height:24px;background:var(--gradient-blue);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0.75rem;color:#fff;font-weight:700;">IA</div>
            <span style="font-size:0.78rem;font-weight:700;color:#e9edef;">INSUREALERT &bull; AGORA</span>
          </div>
          <div style="font-size:0.88rem;font-weight:700;color:#fff;margin-bottom:4px;">
            ${escapeHtml(n.subject || 'Alerta Meteorológico Preventivo')}
          </div>
          <div style="font-size:0.82rem;color:#8696a0;line-height:1.4;">
            ${escapeHtml(n.short_message || n.message || '').substring(0, 130)}...
          </div>
          <div style="margin-top:10px;font-size:0.75rem;color:#00a884;font-weight:600;">
            Toque para abrir medidas de proteção da apólice &rarr;
          </div>
        </div>
      </div>
    `;
  }
}

function copyActiveMessage() {
  const n = filteredNotifications[activeNotificationIndex] || allNotifications[0];
  if (!n) return;
  const text = currentFormat === 'sms' ? (n.short_message || n.message) : n.message;
  navigator.clipboard.writeText(text || '').then(() => {
    showToast('📋 Mensagem copiada para a área de transferência!');
  }).catch(() => {
    showToast('📋 Mensagem copiada!');
  });
}

function resendSimulation() {
  showToast('🔄 Notificação reenviada com sucesso para o segurado!');
}

function showToast(message) {
  const existing = document.querySelector('.wa-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'wa-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

function renderPolicyholders(policyholders) {
  const tbody = document.getElementById("policyholdersBody");

  if (!policyholders || policyholders.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); font-size: 0.9rem;">
          🔍 Nenhum segurado encontrado para o filtro atual.
        </td>
      </tr>
    `;
    return;
  }

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

function filterPolicyholders() {
  const input = document.getElementById("phSearchInput");
  const term = (input ? input.value : "").toLowerCase().trim();

  if (!term) {
    renderPolicyholders(allPolicyholders);
    const badge = document.getElementById("phBadge");
    if (badge) badge.textContent = allPolicyholders.length;
    return;
  }

  const filtered = allPolicyholders.filter((ph) => {
    const name = (ph.name || "").toLowerCase();
    const city = (ph.city || "").toLowerCase();
    const state = (ph.state || "").toLowerCase();
    const id = (ph.id || "").toLowerCase();
    const policies = (ph.policies || []).map((p) => (p.type || "").toLowerCase()).join(" ");
    return name.includes(term) || city.includes(term) || state.includes(term) || id.includes(term) || policies.includes(term);
  });

  renderPolicyholders(filtered);
  const badge = document.getElementById("phBadge");
  if (badge) badge.textContent = filtered.length;
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

// ═══════════════════════════════════════════════════════════
// THEME MANAGEMENT (DARK / LIGHT)
// ═══════════════════════════════════════════════════════════

function initTheme() {
  const savedTheme = localStorage.getItem("insureAlert_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeToggleUI(savedTheme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
  const newTheme = currentTheme === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("insureAlert_theme", newTheme);
  updateThemeToggleUI(newTheme);
  showToast(newTheme === "light" ? "☀️ Modo Claro ativado" : "🌙 Modo Escuro ativado");
}

function updateThemeToggleUI(theme) {
  const btn = document.getElementById("themeToggleBtn");
  if (!btn) return;
  const textEl = btn.querySelector(".theme-toggle-text");
  if (theme === "light") {
    btn.setAttribute("title", "Mudar para Tema Escuro");
    if (textEl) textEl.textContent = "Claro";
  } else {
    btn.setAttribute("title", "Mudar para Tema Claro");
    if (textEl) textEl.textContent = "Escuro";
  }
}

window.toggleTheme = toggleTheme;
window.initTheme = initTheme;

