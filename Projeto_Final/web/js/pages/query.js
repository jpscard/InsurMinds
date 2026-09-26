import { api } from '../api.js';
import { crumbs, llmLabel } from '../app.js';
import { $, $$, alertBox, empty, esc, icon, loading, markdown, shortInsurer, table } from '../ui.js';

const history = []; // conversa mantida ao navegar
let mode = 'ask';

const SUGGESTIONS = [
  'Qual apólice tem o maior prazo complementar?',
  'Alguma apólice cobre multas administrativas?',
  'Quais exclusões aparecem em só uma das apólices?',
  'Como cada apólice trata os custos de defesa?',
];

export async function render(view, { query } = {}) {
  crumbs([{ label: 'Consultar' }]);
  view.innerHTML = loading();
  const rows = await api.policies();

  view.innerHTML = `
    <div class="page-head">
      <div><h1 class="page-title">Consultar a carteira</h1>
      <p class="page-sub">Pergunte em linguagem natural (a resposta cita a página de origem) ou faça consultas estruturadas em SQL.</p></div>
      <div class="seg" id="mode"><button data-m="ask">${icon('chat', 14)} Pergunta</button><button data-m="sql">${icon('database', 14)} SQL</button></div>
    </div>
    <div id="pane"></div>`;

  if (!rows.length) {
    $('#pane', view).innerHTML = `<div class="card">${empty({ ic: 'chat', title: 'Nenhuma apólice para consultar',
      action: `<a class="btn btn-primary" href="#/enviar">${icon('upload', 16)} Enviar documentos</a>` })}</div>`;
    $('#mode', view).remove();
    return;
  }

  const paintMode = () => {
    $$('#mode button', view).forEach((b) => b.classList.toggle('active', b.dataset.m === mode));
    mode === 'ask' ? ask() : sql();
  };
  $('#mode', view).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { mode = b.dataset.m; paintMode(); } });
  const pergunta = query?.get('q');  // link direto para uma pergunta
  if (pergunta) mode = 'ask';
  paintMode();
  if (pergunta && !history.some((h) => h.q === pergunta)) {
    $('#q', view).value = pergunta;
    $('#send', view).click();
  }

  // ─── Pergunta ───────────────────────────────────────────
  function ask() {
    const sel = new Set(rows.map((r) => r.id));
    $('#pane', view).innerHTML = `
      <div class="grid grid-main">
        <div class="card" style="display:flex;flex-direction:column;min-height:480px">
          <div class="card-body chat" id="chat" style="flex:1"></div>
          <div class="card-foot" style="display:block">
            <div class="composer">
              <textarea id="q" class="textarea" placeholder="Pergunte algo sobre as apólices selecionadas…" rows="1"></textarea>
              <button class="btn btn-primary btn-icon" id="send" style="height:44px;width:44px" aria-label="Enviar">${icon('send', 16)}</button>
            </div>
            <div class="subtle mt-8">Enter envia · Shift+Enter quebra linha · respondendo com ${esc(llmLabel())}</div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div class="card-title">Apólices consideradas</div></div>
          <div class="card-body stack" style="gap:10px" id="scope">
            ${rows.map((r) => `<label class="check"><input type="checkbox" data-id="${r.id}" checked>
              <span><strong style="font-size:13px">${esc(shortInsurer(r.seguradora) || r.arquivo)}</strong> <span class="subtle">${esc(r.numero_apolice || '')}</span></span></label>`).join('')}
          </div>
        </div>
      </div>`;

    const chat = $('#chat', view), q = $('#q', view), send = $('#send', view);
    const paintChat = () => {
      if (!history.length) {
        chat.innerHTML = `<div class="empty" style="padding:24px 8px"><div class="empty-icon">${icon('sparkles', 24)}</div>
          <h3>O que você quer saber?</h3><p>A IA percorre o índice de cada apólice, abre as seções relevantes e responde citando seção e página.</p>
          <div class="suggestions" style="justify-content:center">${SUGGESTIONS.map((s) => `<button class="suggestion">${esc(s)}</button>`).join('')}</div></div>`;
        return;
      }
      chat.innerHTML = history.map((h) => `
        <div class="msg"><span class="avatar user">${icon('chat', 14)}</span><div class="bubble user">${esc(h.q)}</div></div>
        <div class="msg"><span class="avatar ai">${icon('sparkles', 14)}</span><div class="bubble">
          ${h.pending ? '<span class="spinner"></span> <span class="subtle">Percorrendo o índice das apólices…</span>'
            : h.error ? alertBox('error', esc(h.error))
            : `<div class="md">${markdown(h.a.resposta)}</div>
               ${h.a.trechos?.length ? `<div class="cites">${h.a.trechos.map((t) => `
                 <details class="cite"><summary>${icon('file', 14)} ${esc(t.rotulo)}${t.secao ? ` · ${esc(t.secao)}` : ''} · pág. ${esc(t.paginas || t.pagina)}</summary>
                 ${t.motivo ? `<p class="subtle" style="padding:0 12px 6px">Aberta porque: ${esc(t.motivo)}</p>` : ''}<pre>${esc(t.texto)}</pre></details>`).join('')}</div>` : ''}
               ${h.a.caminho?.length ? `<details class="cite mt-8"><summary>${icon('layers', 14)} Caminho da consulta · ${h.a.caminho.length} etapa(s)</summary>
                 <div class="route">${h.a.caminho.map((c) => `<div class="route-step"><i></i><b>${esc(c.etapa)}</b><span>${esc(c.detalhe)}</span></div>`).join('')}</div></details>` : ''}`}
        </div></div>`).join('');
      chat.lastElementChild?.scrollIntoView({ block: 'nearest' });
    };
    paintChat();

    const submit = async (text) => {
      const pergunta = (text ?? q.value).trim();
      const ids = [...sel];
      if (pergunta.length < 3 || !ids.length) return;
      q.value = '';
      const h = { q: pergunta, pending: true };
      history.push(h);
      paintChat();
      send.disabled = true;
      try { h.a = await api.ask(pergunta, ids); } catch (e) { h.error = e.message; }
      h.pending = false;
      send.disabled = false;
      if (document.body.contains(chat)) paintChat();
    };
    send.addEventListener('click', () => submit());
    q.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } });
    q.addEventListener('input', () => { q.style.height = 'auto'; q.style.height = `${Math.min(q.scrollHeight, 160)}px`; });
    chat.addEventListener('click', (e) => { const s = e.target.closest('.suggestion'); if (s) submit(s.textContent); });
    $('#scope', view).addEventListener('change', (e) => {
      const id = Number(e.target.dataset.id);
      e.target.checked ? sel.add(id) : sel.delete(id);
      send.disabled = !sel.size;
    });
  }

  // ─── SQL ────────────────────────────────────────────────
  async function sql() {
    const ex = await api.sqlExamples();
    const names = Object.keys(ex);
    $('#pane', view).innerHTML = `
      <div class="card">
        <div class="card-head"><div class="card-title">Consulta estruturada</div>
          <select class="select" id="ex" style="max-width:280px;margin-left:auto">${names.map((n) => `<option>${esc(n)}</option>`).join('')}</select></div>
        <div class="card-body stack">
          <textarea id="sql" class="textarea code" rows="6" spellcheck="false">${esc(ex[names[0]])}</textarea>
          <div class="row"><span class="subtle">Somente leitura (SELECT). Tabelas: <span class="mono">apolices, coberturas, exclusoes, paginas, comparacoes</span> · Ctrl+Enter executa</span>
            <span class="spacer"></span><button class="btn btn-primary" id="run">${icon('play', 14)} Executar</button></div>
        </div>
        <div id="out" style="border-top:1px solid var(--border)"></div>
      </div>`;
    const ta = $('#sql', view), out = $('#out', view);
    $('#ex', view).addEventListener('change', (e) => { ta.value = ex[e.target.value]; });
    const run = async () => {
      out.innerHTML = loading('Executando…');
      try {
        const r = await api.sql(ta.value);
        out.innerHTML = `<div class="card-head subtle" style="border-bottom:1px solid var(--border)">${r.total} linha(s)${r.total > r.rows.length ? ` · exibindo ${r.rows.length}` : ''}</div>`
          + table(r.rows, r.columns.map((c) => ({ key: c, label: c, cls: typeof r.rows[0]?.[c] === 'number' ? 'num' : '',
            fmt: (v) => (typeof v === 'number' ? v.toLocaleString('pt-BR') : esc(v ?? '—')) })), { empty: 'A consulta não retornou linhas.' });
      } catch (e) { out.innerHTML = `<div class="card-body">${alertBox('error', esc(e.message))}</div>`; }
    };
    $('#run', view).addEventListener('click', run);
    ta.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); } });
    run();
  }
}
