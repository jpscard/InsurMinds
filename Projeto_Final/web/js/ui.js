// Utilitários de interface: ícones, formatação, toasts, modais e markdown.

const P = {
  shield: '<path d="M12 3l8 3.2v6.3c0 4.9-3.4 8.8-8 10-4.6-1.2-8-5.1-8-10V6.2z"/><path d="M8.5 12.3l2.5 2.5 4.5-5"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  files: '<path d="M15 2H8a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V6z"/><path d="M15 2v4h4"/><path d="M4 7v13a2 2 0 0 0 2 2h9"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/>',
  columns: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 3v18"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8M8 13h5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
  settings: '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  sidebar: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  alert: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  alertCircle: '<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/>',
  trash: '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
  eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  arrowRight: '<path d="M5 12h14M13 5l7 7-7 7"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  sparkles: '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  send: '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
  key: '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3L21 2M16 7l3 3M18.5 4.5l2 2"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
  cash: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h.01M18 12h.01"/>',
  percent: '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
  layers: '<path d="M12 2L2 7l10 5 10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
  external: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6M10 14L21 3"/>',
  chevronRight: '<path d="M9 18l6-6-6-6"/>',
  play: '<path d="M6 4l14 8-14 8z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  scale: '<path d="M12 3v18M5 21h14M3 7h18"/><path d="M6 7l-3 7a3 3 0 0 0 6 0zM18 7l-3 7a3 3 0 0 0 6 0z"/>',
  code: '<path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
};

export function icon(name, size = 18, cls = '') {
  return `<svg class="${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || ''}</svg>`;
}

/** Substitui <i data-icon="x"> pelos SVGs (usado no HTML estático). */
export function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach((el) => {
    el.innerHTML = icon(el.dataset.icon, 18);
    el.removeAttribute('data-icon');
    el.style.display = 'inline-flex';
  });
}

// ─── HTML seguro ───────────────────────────────────────────
export function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** Template literal que escapa as interpolações; use raw() para HTML confiável. */
export function html(strings, ...vals) {
  return strings.reduce((out, s, i) => {
    if (i === 0) return s;
    const v = vals[i - 1];
    const str = Array.isArray(v) ? v.map((x) => (x && x.__raw !== undefined ? x.__raw : esc(x))).join('')
      : v && v.__raw !== undefined ? v.__raw : esc(v);
    return out + str + s;
  }, '');
}
export const raw = (s) => ({ __raw: s ?? '' });

export function $(sel, root = document) { return root.querySelector(sel); }
export function $$(sel, root = document) { return [...root.querySelectorAll(sel)]; }

// ─── Formatação ────────────────────────────────────────────
// Estas funções devolvem HTML seguro: tudo que vem dos dados (extraídos de documentos enviados
// por qualquer pessoa) é escapado. `valor` e `shortInsurer` devolvem texto cru: escape ao usar.
const CUR = { BRL: 'R$', USD: 'US$', EUR: '€' };
export function money(v, moeda = 'BRL') {
  if (v === null || v === undefined) return '—';
  return `${esc(CUR[moeda || 'BRL'] || moeda)} ${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
export function moneyShort(v, moeda = 'BRL') {
  if (v === null || v === undefined) return '—';
  const p = esc(CUR[moeda || 'BRL'] || moeda);
  const a = Math.abs(v);
  const f = (n) => n.toLocaleString('pt-BR', { maximumFractionDigits: 1 });
  if (a >= 1e9) return `${p} ${f(v / 1e9)} bi`;
  if (a >= 1e6) return `${p} ${f(v / 1e6)} mi`;
  if (a >= 1e3) return `${p} ${f(v / 1e3)} mil`;
  return money(v, moeda);
}
export function valor(v) {
  if (!v) return '—';
  return v.valor !== null && v.valor !== undefined ? money(v.valor, v.moeda) : (v.texto || '—');
}
export function pct(v, digits = 3) {
  return v === null || v === undefined ? '—' : `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
}
export function date(iso) {
  if (!iso) return '—';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : esc(iso);
}
export function dateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? esc(iso) : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}
export function bytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}
export function vigencia(ini, fim) {
  if (!ini && !fim) return '—';
  return `${date(ini)} – ${date(fim)}`;
}
/** Situação da vigência hoje: vigente / vencida / futura. */
export function vigenciaStatus(ini, fim) {
  const today = new Date().toISOString().slice(0, 10);
  if (fim && /^\d{4}-/.test(fim) && fim < today) return { label: 'Vencida', cls: 'red' };
  if (ini && /^\d{4}-/.test(ini) && ini > today) return { label: 'Futura', cls: 'blue' };
  if (ini || fim) return { label: 'Vigente', cls: 'green' };
  return { label: 'Sem vigência', cls: '' };
}
export function shortInsurer(name) {
  if (!name) return '—';
  const skip = new Set(['seguros', 'seguradora', 'companhia', 'cia', 'de', 'do', 's.a.', 'sa', '(fictícia)', 'brasil']);
  const words = name.split(/\s+/).filter((w) => !skip.has(w.toLowerCase()));
  return words.slice(0, 2).join(' ') || name;
}

// ─── Feedback ──────────────────────────────────────────────
export function toast(msg, type = 'info', ms = 4200) {
  const box = $('#toasts');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = icon(type === 'success' ? 'checkCircle' : type === 'error' ? 'alertCircle' : 'info', 18) + `<div>${esc(msg)}</div>`;
  box.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, ms);
}

export function alertBox(type, content) {
  const ic = { info: 'info', warn: 'alert', error: 'alertCircle', success: 'checkCircle' }[type];
  return `<div class="alert ${type}">${icon(ic, 18)}<div>${content}</div></div>`;
}

let pending = 0;
export function progress(on) {
  pending = Math.max(0, pending + (on ? 1 : -1));
  const bar = $('#progress');
  if (pending > 0) {
    bar.classList.add('on');
    bar.style.width = '70%';
  } else {
    bar.style.width = '100%';
    setTimeout(() => { if (!pending) { bar.classList.remove('on'); bar.style.width = '0'; } }, 250);
  }
}

// ─── Overlays ──────────────────────────────────────────────
export function overlay(inner, { center = true, onClose } = {}) {
  const ov = document.createElement('div');
  ov.className = `overlay${center ? ' center' : ''}`;
  ov.innerHTML = inner;
  const close = () => { ov.remove(); document.removeEventListener('keydown', onKey); onClose && onClose(); };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  ov.addEventListener('mousedown', (e) => { if (e.target === ov) close(); });
  ov.addEventListener('click', (e) => { if (e.target.closest('[data-close]')) close(); });
  document.addEventListener('keydown', onKey);
  document.body.appendChild(ov);
  return { el: ov, close };
}

export function confirmDialog({ title, message, confirm = 'Confirmar', danger = false }) {
  return new Promise((resolve) => {
    let ok = false;
    const { el, close } = overlay(`
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-body"><h3>${esc(title)}</h3><p class="muted">${esc(message)}</p></div>
        <div class="modal-foot">
          <button class="btn" data-close>Cancelar</button>
          <button class="btn ${danger ? 'btn-danger-solid' : 'btn-primary'}" data-ok>${esc(confirm)}</button>
        </div>
      </div>`, { onClose: () => resolve(ok) });
    el.querySelector('[data-ok]').addEventListener('click', () => { ok = true; close(); });
    el.querySelector('[data-ok]').focus();
  });
}

// ─── Componentes ───────────────────────────────────────────
export function empty({ ic = 'files', title, text = '', action = '' }) {
  return `<div class="empty"><div class="empty-icon">${icon(ic, 24)}</div><h3>${esc(title)}</h3>${text ? `<p>${text}</p>` : ''}${action}</div>`;
}
export function loading(text = 'Carregando…') {
  return `<div class="loading-block"><span class="spinner lg"></span><span>${esc(text)}</span></div>`;
}

/** Tabela simples a partir de linhas (objetos). `cols`: [{key,label,cls,fmt}] */
export function table(rows, cols, { rowCls, empty: emptyText = 'Nenhum registro.' } = {}) {
  if (!rows.length) return `<div class="empty" style="padding:28px">${esc(emptyText)}</div>`;
  const head = cols.map((c) => `<th class="${c.cls || ''}">${esc(c.label)}</th>`).join('');
  const body = rows.map((r) => `<tr class="${rowCls ? rowCls(r) : ''}">${cols.map((c) => {
    const v = c.fmt ? c.fmt(r[c.key], r) : esc(r[c.key] ?? '—');
    return `<td class="${c.cls || ''}">${v}</td>`;
  }).join('')}</tr>`).join('');
  return `<div class="table-wrap"><table class="table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function tabs(el, onChange) {
  el.addEventListener('click', (e) => {
    const t = e.target.closest('.tab');
    if (!t) return;
    $$('.tab', el).forEach((x) => x.classList.toggle('active', x === t));
    onChange(t.dataset.tab);
  });
}

export function traceSteps(trace = []) {
  return `<div class="steps">${trace.map((s) => `<span class="step"><b>${esc(s.agente)}</b> ${esc(s.acao)} · ${Number(s.duracao_s).toLocaleString('pt-BR')}s</span>`).join('')}</div>`;
}

export function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ─── Markdown (subconjunto: títulos, listas, tabelas, código, ênfase) ──
function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|#[^)\s]*)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
export function markdown(src = '') {
  const lines = src.replace(/\r/g, '').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++;
      out.push(`<pre><code>${esc(buf.join('\n'))}</code></pre>`);
      continue;
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(l);
    if (h) { out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const cells = (r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const head = cells(l);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(cells(lines[i++]));
      out.push(`<table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
      continue;
    }
    if (/^\s*([-*+]|\d+[.)])\s+/.test(l)) {
      const ordered = /^\s*\d/.test(l);
      const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+[.)])\s+/, ''));
        i++;
      }
      const tag = ordered ? 'ol' : 'ul';
      out.push(`<${tag}>${items.map((x) => `<li>${inline(x)}</li>`).join('')}</${tag}>`);
      continue;
    }
    if (/^>\s?/.test(l)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ''));
      out.push(`<blockquote>${inline(buf.join(' '))}</blockquote>`);
      continue;
    }
    if (/^(-{3,}|\*{3,})\s*$/.test(l)) { out.push('<hr>'); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*([-*+]|\d+[.)])\s+|>\s?|\s*\|)/.test(lines[i])) buf.push(lines[i++]);
    if (buf.length) out.push(`<p>${inline(buf.join(' '))}</p>`);
    else { out.push(`<p>${inline(l)}</p>`); i++; }
  }
  return out.join('\n');
}
