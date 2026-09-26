import { api } from '../api.js';
import { crumbs, refreshCount } from '../app.js';
import {
  $, alertBox, confirmDialog, date, dateTime, esc, icon, loading, moneyShort, overlay, pct, shortInsurer, table, tabs,
  toast, valor, vigencia, vigenciaStatus,
} from '../ui.js';

const CAT_CLS = { 'Lado A': 'blue', 'Lado B': 'violet', 'Lado C': 'green' };

export async function render(view, { id, query }) {
  crumbs([{ label: 'Carteira', href: '#/apolices' }, { label: `Apólice #${id}` }]);
  view.innerHTML = loading();
  const d = await api.policy(id);
  const ap = d.apolice, idt = ap.identificacao || {}, meta = d.meta;
  const title = idt.seguradora || meta.arquivo;
  crumbs([{ label: 'Carteira', href: '#/apolices' }, { label: shortInsurer(idt.seguradora) || meta.arquivo }]);
  const st = vigenciaStatus(idt.vigencia_inicio, idt.vigencia_fim);
  const lmg = ap.limite_maximo_garantia, pr = ap.premio_total;

  const alertas = (d.alertas || []).map((a) => alertBox(a.nivel === 'erro' ? 'error' : a.nivel === 'aviso' ? 'warn' : 'info', esc(a.mensagem))).join('');
  const kpi = (label, value, foot = '') => `<div class="card kpi"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-foot">${foot}</div></div>`;

  view.innerHTML = `
    <div class="page-head">
      <div>
        <div class="row" style="gap:8px;margin-bottom:6px"><span class="badge ${st.cls}">${st.label}</span>${idt.produto ? `<span class="badge">${esc(idt.produto)}</span>` : ''}</div>
        <h1 class="page-title">${esc(title)}</h1>
        <p class="page-sub">Apólice ${esc(idt.numero_apolice || '—')} · ${esc(idt.tomador || 'Tomador não identificado')} · ${vigencia(idt.vigencia_inicio, idt.vigencia_fim)}</p>
      </div>
      <div class="page-actions">
        ${d.tem_original ? `<button class="btn" id="origBtn">${icon('eye', 16)} Documento original</button>` : ''}
        <a class="btn" href="#/comparar?ids=${meta.id}">${icon('columns', 16)} Comparar</a>
        ${d.protegida ? '' : `<button class="btn btn-danger" id="delBtn">${icon('trash', 16)} Excluir</button>`}
      </div>
    </div>
    ${alertas ? `<div class="stack" style="gap:8px;margin-bottom:16px">${alertas}</div>` : ''}
    <div class="grid grid-4">
      ${kpi('Limite Máximo de Garantia', lmg?.valor != null ? moneyShort(lmg.valor, lmg.moeda) : esc(valor(lmg)), lmg?.texto ? esc(lmg.texto) : '')}
      ${kpi('Prêmio total', pr?.valor != null ? moneyShort(pr.valor, pr.moeda) : esc(valor(pr)))}
      ${kpi('Prêmio / LMG', lmg?.valor && pr?.valor ? pct((pr.valor / lmg.valor) * 100) : '—', 'custo relativo da cobertura')}
      ${kpi('Coberturas · Exclusões', `${(ap.coberturas || []).length} · ${(ap.exclusoes || []).length}`, `${(ap.franquias || []).length} franquias`)}
    </div>
    <div class="card mt-16">
      <div class="tabs" id="tabs">
        <button class="tab active" data-tab="geral">Visão geral</button>
        <button class="tab" data-tab="cob">Coberturas <span class="badge">${(ap.coberturas || []).length}</span></button>
        <button class="tab" data-tab="exc">Exclusões <span class="badge">${(ap.exclusoes || []).length}</span></button>
        <button class="tab" data-tab="fra">Franquias <span class="badge">${(ap.franquias || []).length}</span></button>
        <button class="tab" data-tab="idx">${icon('layers', 14)} Índice</button>
        <button class="tab" data-tab="txt">Texto extraído</button>
        <button class="tab" data-tab="rev">${icon('edit', 14)} Revisão</button>
      </div>
      <div id="tabBody"></div>
    </div>
    <p class="subtle mt-16">Arquivo <span class="mono">${esc(meta.arquivo)}</span> · processado em ${dateTime(meta.criado_em)} · extraído por ${esc(meta.provedor_llm || '—')}${d.triagem?.tipo_documento ? ` · triagem: ${esc(d.triagem.tipo_documento)}` : ''}</p>`;

  const list = (items) => (items?.length ? `<ul style="padding-left:18px">${items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : '<span class="subtle">—</span>');
  const kv = (pairs) => `<div class="kv">${pairs.map(([k, v]) => `<div>${esc(k)}</div><div>${v}</div>`).join('')}</div>`;

  const panes = {
    geral: () => `<div class="grid grid-2" style="gap:0">
      <div style="border-right:1px solid var(--border)">${kv([
        ['Seguradora', esc(idt.seguradora || '—')], ['Nº da apólice', esc(idt.numero_apolice || '—')],
        ['Processo SUSEP', esc(idt.processo_susep || '—')], ['Tomador', esc(idt.tomador || '—')],
        ['CNPJ', esc(idt.cnpj_tomador || '—')], ['Corretor', esc(idt.corretor || '—')],
        ['Vigência', vigencia(idt.vigencia_inicio, idt.vigencia_fim)],
      ])}</div>
      <div>${kv([
        ['Base de cobertura', esc(ap.base_cobertura || '—')], ['Retroatividade', esc(date(ap.data_retroatividade))],
        ['Prazo complementar', esc(ap.prazo_complementar || '—')], ['Territorialidade', esc(ap.territorialidade || '—')],
        ['Custos de defesa', esc(ap.custos_defesa || '—')],
      ])}</div></div>
      <div class="grid grid-2" style="border-top:1px solid var(--border);gap:0">
        <div class="card-body" style="border-right:1px solid var(--border)"><div class="label" style="margin-bottom:8px">Segurados</div>${list(ap.segurados)}</div>
        <div class="card-body"><div class="label" style="margin-bottom:8px">Cláusulas relevantes</div>${list(ap.clausulas_relevantes)}</div>
      </div>
      ${ap.observacoes ? `<div class="card-body" style="border-top:1px solid var(--border)"><div class="label" style="margin-bottom:6px">Observações</div><p class="muted">${esc(ap.observacoes)}</p></div>` : ''}`,
    cob: () => table(ap.coberturas || [], [
      { key: 'nome', label: 'Cobertura', fmt: (v, r) => `<div class="cell-title">${esc(v)}</div>${r.descricao ? `<div class="cell-sub">${esc(r.descricao)}</div>` : ''}` },
      { key: 'categoria', label: 'Categoria', fmt: (v) => `<span class="badge ${CAT_CLS[v] || ''}">${esc(v || '—')}</span>` },
      { key: 'limite', label: 'Limite', cls: 'num', fmt: (v) => esc(valor(v)) },
      { key: 'franquia', label: 'Franquia', cls: 'num', fmt: (v) => esc(valor(v)) },
      { key: 'trecho_fonte', label: 'Trecho-fonte', fmt: (v) => (v ? `<span class="cell-sub">“${esc(v)}”</span>` : '—') },
    ], { empty: 'Nenhuma cobertura extraída.' }),
    exc: () => table(ap.exclusoes || [], [
      { key: 'titulo', label: 'Exclusão', fmt: (v) => `<span class="cell-title">${esc(v)}</span>` },
      { key: 'categoria', label: 'Categoria', fmt: (v) => `<span class="badge">${esc(v || '—')}</span>` },
      { key: 'descricao', label: 'Descrição' },
    ], { empty: 'Nenhuma exclusão extraída.' }),
    fra: () => table(ap.franquias || [], [
      { key: 'aplicacao', label: 'Aplicação', fmt: (v) => `<span class="cell-title">${esc(v)}</span>` },
      { key: 'valor', label: 'Valor', cls: 'num', fmt: (v) => esc(valor(v)) },
    ], { empty: 'Nenhuma franquia extraída.' }),
    idx: async (el) => {
      el.innerHTML = loading('Carregando índice…');
      const t = await api.index(meta.id);
      const metodo = { estrutura: 'estrutura do documento', 'estrutura+llm': 'estrutura + resumos pela IA', paginas: 'uma seção por página', 'paginas+llm': 'páginas + resumos pela IA' }[t.metodo] || t.metodo;
      const node = (n) => `
        <details class="tnode" ${n.nivel === 1 && n.filhos.length ? 'open' : ''}>
          <summary><span class="tid mono">${esc(n.id)}</span><span class="ttitle">${esc(n.titulo)}</span>
            <span class="badge">pág. ${n.pagina_inicio}${n.pagina_fim !== n.pagina_inicio ? `–${n.pagina_fim}` : ''}</span></summary>
          ${n.resumo ? `<p class="tsum">${esc(n.resumo)}</p>` : ''}
          ${n.filhos.length ? `<div class="tkids">${n.filhos.map(node).join('')}</div>` : `<pre class="ttext">${esc(n.texto)}</pre>`}
        </details>`;
      el.innerHTML = `<div class="card-body stack">
        ${alertBox('info', `Sumário que a IA percorre para decidir o que ler numa consulta (abordagem PageIndex). Montado por: <strong>${esc(metodo)}</strong>.`)}
        <div class="tree">${t.nos.map(node).join('')}</div></div>`;
    },
    txt: async (el) => {
      el.innerHTML = loading('Carregando páginas…');
      const pages = await api.pages(meta.id);
      el.innerHTML = pages.map((p) => `
        <details class="cite" style="margin:12px 16px" ${p.numero === 1 ? 'open' : ''}>
          <summary>${icon('file', 14)} Página ${p.numero} <span class="badge ${p.metodo === 'ocr' ? 'amber' : ''}">${esc(p.metodo === 'ocr' ? 'OCR' : 'texto nativo')}</span></summary>
          <pre>${esc(p.texto)}</pre>
        </details>`).join('') || '<div class="empty">Sem texto.</div>';
    },
    rev: (el) => {
      if (d.protegida) {
        el.innerHTML = `<div class="card-body">${alertBox('info', 'Esta é uma apólice de demonstração e não pode ser editada. Envie seus próprios documentos para testar a revisão humana.')}</div>`;
        return;
      }
      el.innerHTML = `<div class="card-body stack">
        ${alertBox('info', 'Corrija os dados extraídos editando o JSON abaixo. Ao salvar, a correção substitui a extração e passa a valer nas comparações e consultas.')}
        <textarea id="json" class="textarea code" style="min-height:420px" spellcheck="false">${esc(JSON.stringify(ap, null, 2))}</textarea>
        <div id="jsonMsg"></div>
        <div class="row" style="justify-content:flex-end">
          <button class="btn" id="fmt">${icon('code', 16)} Formatar</button>
          <button class="btn btn-primary" id="save">${icon('check', 16)} Salvar correções</button>
        </div></div>`;
      const ta = $('#json', el), msg = $('#jsonMsg', el);
      const parse = () => { try { msg.innerHTML = ''; return JSON.parse(ta.value); } catch (e) { msg.innerHTML = alertBox('error', `JSON inválido: ${esc(e.message)}`); return null; } };
      $('#fmt', el).addEventListener('click', () => { const j = parse(); if (j) ta.value = JSON.stringify(j, null, 2); });
      $('#save', el).addEventListener('click', async (e) => {
        const j = parse(); if (!j) return;
        e.currentTarget.disabled = true;
        try {
          const r = await api.updatePolicy(meta.id, j);
          toast('Correções salvas.', 'success');
          location.hash = `#/apolices/${r.id}`;
          if (r.id === meta.id) render(view, { id: r.id });
        } catch (err) {
          msg.innerHTML = alertBox('error', esc(err.message));
          e.currentTarget.disabled = false;
        }
      });
    },
  };

  const body = $('#tabBody', view);
  const show = async (t) => {
    const out = panes[t](body);
    if (typeof out === 'string') body.innerHTML = out;
    else await out;
  };
  tabs($('#tabs', view), show);
  const aba = query?.get('tab');
  const btn = aba && $(`.tab[data-tab="${aba}"]`, view);
  if (btn) btn.click(); else show('geral');

  $('#delBtn', view)?.addEventListener('click', async () => {
    if (!await confirmDialog({ title: 'Excluir apólice?', message: `“${title}” e todo o texto extraído serão removidos. Esta ação não pode ser desfeita.`, confirm: 'Excluir', danger: true })) return;
    try {
      await api.deletePolicy(meta.id);
      toast('Apólice excluída.', 'success');
      refreshCount();
      location.hash = '#/apolices';
    } catch (e) { toast(e.message, 'error'); }
  });

  $('#origBtn', view)?.addEventListener('click', () => {
    const url = `/api/policies/${meta.id}/file`;
    const isPdf = /\.pdf$/i.test(meta.arquivo);
    overlay(`<div class="modal wide" role="dialog" aria-modal="true">
      <div class="drawer-head"><div class="card-title" style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(meta.arquivo)}</div>
        <a class="btn btn-sm" style="margin-left:auto" href="${url}" target="_blank" rel="noopener">${icon('external', 14)} Abrir em nova aba</a>
        <button class="btn btn-ghost btn-icon btn-sm" data-close aria-label="Fechar">${icon('x', 16)}</button></div>
      ${isPdf ? `<iframe src="${url}" title="Documento original"></iframe>` : `<img class="doc" src="${url}" alt="Documento original">`}
    </div>`);
  });
}
