// Shell da aplicação: roteamento por hash, tema, menu e configuração do modelo de IA.
import { api, llm } from './api.js';
import { $, $$, esc, hydrateIcons, icon, overlay, toast } from './ui.js';
import * as dashboard from './pages/dashboard.js';
import * as policies from './pages/policies.js';
import * as policy from './pages/policy.js';
import * as upload from './pages/upload.js';
import * as compare from './pages/compare.js';
import * as query from './pages/query.js';
import * as about from './pages/about.js';

const PROVIDER_INFO = {
  anthropic: { label: 'Anthropic', desc: 'Modelos Claude' },
  openai: { label: 'OpenAI', desc: 'Modelos GPT e o-series' },
  gemini: { label: 'Google', desc: 'Modelos Gemini' },
  offline: { label: 'Offline', desc: 'Regras, sem IA generativa' },
};

const ROUTES = [
  { re: /^$/, page: dashboard, nav: 'dashboard' },
  { re: /^apolices$/, page: policies, nav: 'policies' },
  { re: /^apolices\/(\d+)$/, page: policy, nav: 'policies', params: (m) => ({ id: Number(m[1]) }) },
  { re: /^enviar$/, page: upload, nav: 'upload' },
  { re: /^comparar$/, page: compare, nav: 'compare' },
  { re: /^consultar$/, page: query, nav: 'query' },
  { re: /^sobre$/, page: about, nav: 'about' },
];

export const state = { providers: [], defaultProvider: 'offline' };

// ─── Contexto passado às páginas ──────────────────────────
export function crumbs(items) {
  $('#crumbs').innerHTML = items.map((c, i) => (i === items.length - 1
    ? `<strong>${esc(c.label)}</strong>`
    : `<a href="${c.href}">${esc(c.label)}</a>${icon('chevronRight', 14)}`)).join('');
  document.title = `${items[items.length - 1].label} · D&O Insight`;
}

export function currentProvider() {
  const p = llm.provider;
  return state.providers.some((x) => x.name === p) ? p : state.defaultProvider;
}

export function llmReady() {
  const p = currentProvider();
  const info = state.providers.find((x) => x.name === p);
  return p === 'offline' || !!llm.key(p) || !!info?.has_env_key;
}

export function llmLabel() {
  const p = currentProvider();
  const info = state.providers.find((x) => x.name === p);
  return p === 'offline' ? 'modo offline (regras)' : `${PROVIDER_INFO[p].label} · ${llm.model(p) || info?.default_model || ''}`;
}

export async function refreshCount() {
  try {
    const rows = await api.policies();
    $('#navCount').textContent = rows.length || '';
  } catch { /* contagem é só decorativa */ }
}

// ─── Roteamento ───────────────────────────────────────────
let cleanup = null;
async function route() {
  const [path, qs] = location.hash.replace(/^#\/?/, '').split('?');
  const match = ROUTES.map((r) => ({ r, m: r.re.exec(path) })).find((x) => x.m);
  if (!match) { location.hash = '#/'; return; }
  const { r, m } = match;
  $$('.nav-item[data-route]').forEach((a) => a.classList.toggle('active', a.dataset.route === r.nav));
  $('#app').classList.remove('mobile-open');
  if (typeof cleanup === 'function') cleanup();
  const view = $('#view');
  view.innerHTML = '';
  window.scrollTo(0, 0);
  const params = { ...(r.params ? r.params(m) : {}), query: new URLSearchParams(qs || '') };
  try {
    cleanup = await r.page.render(view, params);
  } catch (e) {
    console.error(e);
    view.innerHTML = `<div class="card"><div class="card-body">${icon('alertCircle')} Não foi possível abrir esta página: ${esc(e.message)}</div></div>`;
  }
}

// ─── Chip de status do modelo ─────────────────────────────
function paintChip() {
  const p = currentProvider();
  $('#llmProvider').textContent = PROVIDER_INFO[p]?.label || p;
  const info = state.providers.find((x) => x.name === p);
  $('#llmModel').textContent = p === 'offline' ? 'sem IA' : (llm.model(p) || info?.default_model || '');
  const dot = $('#llmDot');
  dot.className = `dot ${p === 'offline' ? 'warn' : llmReady() ? 'ok' : 'err'}`;
  $('#llmChip').title = p === 'offline' ? 'Modo offline: extração por regras. Clique para configurar a IA.'
    : llmReady() ? 'Modelo configurado. Clique para alterar.' : 'Falta a chave de API. Clique para configurar.';
}

// ─── Drawer de configuração do modelo ─────────────────────
export function openSettings() {
  let prov = currentProvider();
  const { el, close } = overlay(`
    <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="stTitle">
      <div class="drawer-head">
        <div class="kpi-icon">${icon('sparkles', 16)}</div>
        <div><div class="card-title" id="stTitle">Modelo de IA</div><div class="card-sub">Usado na extração, comparação e consultas</div></div>
        <button class="btn btn-ghost btn-icon btn-sm" style="margin-left:auto" data-close aria-label="Fechar">${icon('x', 16)}</button>
      </div>
      <div class="drawer-body">
        <div class="field"><span class="label">Provedor</span><div class="provider-grid" id="stProv"></div></div>
        <div id="stKeyWrap" class="field">
          <label for="stKey">Chave de API</label>
          <div class="row" style="flex-wrap:nowrap">
            <div class="input-wrap" style="flex:1">${icon('key', 16)}<input id="stKey" class="input" type="password" autocomplete="off" spellcheck="false"></div>
            <button class="btn btn-icon" id="stShow" title="Mostrar/ocultar">${icon('eye', 16)}</button>
          </div>
          <span class="hint">Fica só nesta aba do navegador e vai direto ao provedor; não é gravada no servidor.</span>
        </div>
        <div id="stModelWrap" class="field">
          <label for="stModel">Modelo</label>
          <select id="stModel" class="select"></select>
          <input id="stModelTxt" class="input" placeholder="Nome exato do modelo" style="display:none">
          <span class="hint" id="stModelHint"></span>
        </div>
        <div id="stMsg"></div>
      </div>
      <div class="drawer-foot">
        <button class="btn" data-close>Cancelar</button>
        <button class="btn btn-primary" id="stSave">${icon('check', 16)} Salvar</button>
      </div>
    </aside>`, { center: false });

  const keyIn = $('#stKey', el), sel = $('#stModel', el), txt = $('#stModelTxt', el), hint = $('#stModelHint', el), msg = $('#stMsg', el);
  let loadSeq = 0;

  function paintProviders() {
    $('#stProv', el).innerHTML = state.providers.map((p) => `
      <button class="provider ${p.name === prov ? 'on' : ''}" data-p="${p.name}">
        <strong>${PROVIDER_INFO[p.name].label}</strong><span>${PROVIDER_INFO[p.name].desc}</span>
      </button>`).join('');
  }

  async function loadModels() {
    const info = state.providers.find((x) => x.name === prov);
    const seq = ++loadSeq;
    msg.innerHTML = '';
    const current = llm.model(prov) || info.default_model;
    const key = keyIn.value.trim();
    if (prov !== 'offline' && !key && !info.has_env_key) {
      sel.innerHTML = `<option>${esc(info.default_model)}</option>`;
      sel.disabled = true;
      hint.textContent = 'Informe a chave para ver os modelos disponíveis.';
      return;
    }
    sel.disabled = true;
    hint.innerHTML = '<span class="spinner"></span> Buscando modelos…';
    try {
      const { models } = await api.models(prov, key);
      if (seq !== loadSeq) return;
      const ids = models.map((m) => m.id);
      const opts = [...(ids.includes(current) ? [] : [{ id: current, name: current }]), ...models];
      sel.innerHTML = opts.map((m) => `<option value="${esc(m.id)}" ${m.id === current ? 'selected' : ''}>${esc(m.name && m.name !== m.id ? `${m.name} (${m.id})` : m.id)}</option>`).join('')
        + (prov === 'offline' ? '' : '<option value="__other">Outro (digitar)…</option>');
      sel.disabled = prov === 'offline';
      hint.textContent = prov === 'offline' ? 'Extração por regras, sem chamar nenhum modelo.' : `${models.length} modelos disponíveis para esta chave.`;
    } catch (e) {
      if (seq !== loadSeq) return;
      sel.innerHTML = `<option value="${esc(current)}">${esc(current)}</option><option value="__other">Outro (digitar)…</option>`;
      sel.disabled = false;
      hint.textContent = '';
      msg.innerHTML = `<div class="alert ${e.status === 502 && /inválida/.test(e.message) ? 'error' : 'warn'}">${icon('alert', 18)}<div>${esc(e.message)}</div></div>`;
    }
    txt.style.display = sel.value === '__other' ? '' : 'none';
  }

  function paint() {
    paintProviders();
    const info = state.providers.find((x) => x.name === prov);
    $('#stKeyWrap', el).style.display = prov === 'offline' ? 'none' : '';
    keyIn.value = llm.key(prov) || '';
    keyIn.placeholder = info.has_env_key ? 'Usando a chave do servidor (.env)' : 'Cole a chave aqui';
    txt.value = '';
    loadModels();
  }

  $('#stProv', el).addEventListener('click', (e) => {
    const b = e.target.closest('[data-p]');
    if (b && b.dataset.p !== prov) { prov = b.dataset.p; paint(); }
  });
  let t;
  keyIn.addEventListener('input', () => { clearTimeout(t); t = setTimeout(loadModels, 600); });
  $('#stShow', el).addEventListener('click', () => { keyIn.type = keyIn.type === 'password' ? 'text' : 'password'; });
  sel.addEventListener('change', () => { txt.style.display = sel.value === '__other' ? '' : 'none'; if (sel.value === '__other') txt.focus(); });
  $('#stSave', el).addEventListener('click', () => {
    const info = state.providers.find((x) => x.name === prov);
    const model = sel.value === '__other' ? txt.value.trim() : sel.value;
    if (prov !== 'offline' && !keyIn.value.trim() && !info.has_env_key) {
      msg.innerHTML = `<div class="alert error">${icon('alertCircle', 18)}<div>Informe a chave de API para usar ${PROVIDER_INFO[prov].label}.</div></div>`;
      keyIn.focus();
      return;
    }
    llm.provider = prov;
    if (prov !== 'offline') {
      llm.setKey(prov, keyIn.value.trim());
      llm.setModel(prov, model && model !== info.default_model ? model : '');
    }
    paintChip();
    close();
    toast(`Usando ${llmLabel()}`, 'success');
  });
  paint();
}

// ─── Inicialização ────────────────────────────────────────
function setTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem('doi.theme', t); } catch { /* ok */ }
  $('#themeBtn').innerHTML = icon(t === 'dark' ? 'sun' : 'moon');
}

async function init() {
  hydrateIcons();
  setTheme(document.documentElement.getAttribute('data-theme') || 'dark');
  $('#themeBtn').addEventListener('click', () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'));
  $('#collapseBtn').addEventListener('click', () => {
    const on = $('#app').classList.toggle('collapsed');
    try { localStorage.setItem('doi.collapsed', on ? '1' : ''); } catch { /* ok */ }
  });
  try { if (localStorage.getItem('doi.collapsed')) $('#app').classList.add('collapsed'); } catch { /* ok */ }
  $('#menuBtn').addEventListener('click', () => $('#app').classList.toggle('mobile-open'));
  $('#settingsBtn').addEventListener('click', openSettings);
  $('#llmChip').addEventListener('click', openSettings);
  document.addEventListener('click', (e) => {
    if ($('#app').classList.contains('mobile-open') && !e.target.closest('.sidebar') && !e.target.closest('#menuBtn')) $('#app').classList.remove('mobile-open');
  });

  try {
    const p = await api.providers();
    state.providers = p.providers;
    state.defaultProvider = p.default;
  } catch (e) {
    toast(e.message, 'error', 8000);
  }
  paintChip();
  refreshCount();
  window.addEventListener('hashchange', route);
  route();
}

init();
