import { api } from '../api.js';
import { crumbs, currentProvider, llmLabel, openSettings } from '../app.js';
import { $, $$, alertBox, download, empty, esc, icon, liveSteps, loading, moneyShort, pct, shortInsurer, tabs, toast, traceSteps } from '../ui.js';

let last = null; // última comparação, mantida ao navegar

const ORDEM = { alto: 0, medio: 1, 'médio': 1, baixo: 2 };
const VISIVEIS = 6;  // diferenças-chave mostradas antes de "Ver todas"
const IMPACT = { alto: ['red', 'Alto'], medio: ['amber', 'Médio'], 'médio': ['amber', 'Médio'], baixo: ['green', 'Baixo'] };

export async function render(view, { query }) {
  crumbs([{ label: 'Comparar apólices' }]);
  view.innerHTML = loading();
  const rows = await api.policies();

  view.innerHTML = `
    <div class="page-head">
      <div><h1 class="page-title">Comparar apólices</h1>
      <p class="page-sub">Diferenças objetivas calculadas de forma determinística e interpretadas pela IA: coberturas, exclusões, franquias e custo relativo.</p></div>
    </div>
    <div class="card">
      <div class="card-head"><div><div class="card-title">Selecione as apólices</div><div class="card-sub">Duas ou mais</div></div>
        <button class="btn btn-primary" id="goBtn" style="margin-left:auto">${icon('scale', 16)} Comparar</button></div>
      <div class="card-body" id="picks"></div>
    </div>
    <div id="result" class="mt-24"></div>`;

  if (rows.length < 2) {
    $('#picks', view).innerHTML = empty({ ic: 'columns', title: 'São necessárias ao menos duas apólices',
      text: 'Envie mais documentos para comparar.', action: `<a class="btn btn-primary" href="#/enviar">${icon('upload', 16)} Enviar documentos</a>` });
    $('#goBtn', view).remove();
    return;
  }

  const fromQuery = (query.get('ids') || '').split(',').map(Number).filter((id) => rows.some((r) => r.id === id));
  const sel = new Set(fromQuery.length ? fromQuery : last ? last.ids.filter((id) => rows.some((r) => r.id === id)) : rows.slice(0, 2).map((r) => r.id));

  const paintPicks = () => {
    $('#picks', view).innerHTML = `<div class="pick-list">${rows.map((r) => `
      <label class="pick ${sel.has(r.id) ? 'on' : ''}">
        <input type="checkbox" data-id="${r.id}" ${sel.has(r.id) ? 'checked' : ''}>
        <span style="min-width:0"><strong style="display:block">${esc(shortInsurer(r.seguradora) || r.arquivo)}</strong>
        <span class="subtle">${esc(r.numero_apolice || r.arquivo)} · LMG ${moneyShort(r.lmg, r.moeda)}</span></span>
      </label>`).join('')}</div>`;
    const b = $('#goBtn', view);
    b.disabled = sel.size < 2;
    b.innerHTML = `${icon('scale', 16)} Comparar${sel.size ? ` ${sel.size} apólices` : ''}`;
  };
  $('#picks', view).addEventListener('change', (e) => {
    const id = Number(e.target.dataset.id);
    e.target.checked ? sel.add(id) : sel.delete(id);
    paintPicks();
  });
  paintPicks();

  const compararAgora = async (rolar = true) => {
    const ids = rows.filter((r) => sel.has(r.id)).map((r) => r.id);
    const btn = $('#goBtn', view);
    btn.disabled = true;
    const steps = [];
    const paintLoading = () => {
      const label = !steps.length ? 'Calculando as diferenças entre as apólices…'
        : currentProvider() === 'offline' ? 'Classificando as diferenças por impacto…' : `Redigindo a análise executiva com ${llmLabel()}…`;
      $('#result', view).innerHTML = `<div class="card"><div class="card-body"><div class="card-title">Comparando ${ids.length} apólices</div>${liveSteps(steps, { label })}</div></div>`;
    };
    paintLoading();
    try {
      last = await api.compareStream(ids, (st) => { steps.push(st); paintLoading(); });
      paintResult();
      if (rolar) $('#result', view).scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
      $('#result', view).innerHTML = alertBox('error', `Falha na comparação: ${esc(e.message)}`);
    } finally { btn.disabled = sel.size < 2; }
  };
  $('#goBtn', view).addEventListener('click', () => compararAgora());

  if (query.get('run') && sel.size >= 2) compararAgora(false);  // link direto para um resultado
  else if (last && !fromQuery.length) paintResult();

  function paintResult() {
    const { resultado: res, analise, trace } = last;
    const labels = res.labels, M = res.metricas;
    const vals = (k) => labels.map((l) => M[l][k]).filter((v) => v !== null && v !== undefined);
    const best = { lmg: Math.max(...vals('lmg')), taxa_pct: Math.min(...vals('taxa_pct')), coberturas: Math.max(...vals('coberturas')), exclusoes: Math.min(...vals('exclusoes')) };
    const maxCob = Math.max(1, ...vals('coberturas')), maxExc = Math.max(1, ...vals('exclusoes'));
    const mark = (k, v) => (v !== null && v === best[k] && labels.length > 1 ? 'best' : '');

    const cols = labels.map((l) => {
      const m = M[l];
      return `<div class="card policy-col">
        <h4>${esc(l)}</h4>
        <div class="metric-row"><span>LMG</span><span class="${mark('lmg', m.lmg)}">${moneyShort(m.lmg)}</span></div>
        <div class="metric-row"><span>Prêmio</span><span>${moneyShort(m.premio)}</span></div>
        <div class="metric-row"><span>Prêmio / LMG</span><span class="${mark('taxa_pct', m.taxa_pct)}">${pct(m.taxa_pct)}</span></div>
        <div class="bars">
          <div class="metric-row"><span>Coberturas</span><span class="${mark('coberturas', m.coberturas)}">${m.coberturas}</span></div>
          <div class="bar"><i style="width:${(m.coberturas / maxCob) * 100}%"></i></div>
          <div class="metric-row"><span>Exclusões</span><span class="${mark('exclusoes', m.exclusoes)}">${m.exclusoes}</span></div>
          <div class="bar red"><i style="width:${(m.exclusoes / maxExc) * 100}%"></i></div>
        </div>
      </div>`;
    }).join('');

    const dk = [...(analise.diferencas_chave || [])].sort((a, b) => (ORDEM[String(a.impacto).toLowerCase()] ?? 3) - (ORDEM[String(b.impacto).toLowerCase()] ?? 3));
    const porRegras = analise.modo === 'regras';
    const pts = analise.pontos_de_atencao || [];

    $('#result', view).innerHTML = `
      <div class="page-head" style="margin-bottom:16px">
        <div><h2 class="page-title" style="font-size:20px">Resultado</h2><p class="page-sub">${res.diferencas.length} diferenças objetivas identificadas. Valores em verde são os mais favoráveis de cada métrica.</p></div>
        <div class="page-actions">
          <button class="btn" data-exp="xlsx">${icon('download', 16)} Planilha (.xlsx)</button>
          <button class="btn" data-exp="md">${icon('download', 16)} Relatório (.md)</button>
        </div>
      </div>
      <div class="grid" style="grid-template-columns:repeat(${Math.min(labels.length, 4)},minmax(0,1fr))">${cols}</div>
      <div class="grid grid-main mt-16">
        <div class="card">
          <div class="card-head"><span class="kpi-icon">${icon('sparkles', 16)}</span><div class="card-title">Análise executiva</div></div>
          <div class="card-body stack">
            ${porRegras ? alertBox('info', `<div class="row" style="flex-wrap:wrap"><span style="flex:1;min-width:220px"><strong>Análise por regras (modo offline).</strong> As diferenças foram classificadas automaticamente pelo impacto. Com um modelo de IA, você recebe o resumo executivo redigido e uma recomendação.</span><button class="btn btn-sm" id="cfgCmp">${icon('settings', 14)} Configurar IA</button></div>`) : ''}
            <p class="summary">${esc(analise.resumo_executivo || '—')}</p>
            ${analise.recomendacao && !porRegras ? `<div><div class="label" style="margin-bottom:6px">Recomendação</div><p class="muted">${esc(analise.recomendacao)}</p></div>` : ''}
          </div>
          ${dk.length ? `<div style="border-top:1px solid var(--border)"><div class="table-wrap"><table class="table">
            <thead><tr><th>Tema</th><th>Impacto</th><th>Favorece</th><th>Descrição</th></tr></thead>
            <tbody id="dkBody">${dk.map((d, i) => { const im = IMPACT[String(d.impacto).toLowerCase()] || ['', d.impacto || '—'];
              return `<tr ${i >= VISIVEIS ? 'hidden' : ''}><td class="strong">${esc(d.tema)}</td><td><span class="badge ${im[0]}">${esc(im[1])}</span></td><td>${esc(d.favorece || '—')}</td><td>${esc(d.descricao)}</td></tr>`; }).join('')}</tbody>
          </table></div>${dk.length > VISIVEIS ? `<div class="card-foot" style="justify-content:center"><button class="btn btn-sm btn-ghost" id="dkMais">Ver todas as ${dk.length} diferenças ${icon('chevronRight', 14)}</button></div>` : ''}</div>` : ''}
        </div>
        <div class="card">
          <div class="card-head"><span class="kpi-icon" style="background:var(--warning-soft);color:var(--warning)">${icon('alert', 16)}</span><div class="card-title">Pontos de atenção</div></div>
          <div class="card-body" style="padding-top:6px;padding-bottom:6px">${pts.length ? pts.map((p) => `<div class="point">${icon('alert', 16)}<span>${esc(p)}</span></div>`).join('') : '<p class="subtle" style="padding:12px 0">Nenhum ponto de atenção.</p>'}</div>
        </div>
      </div>
      <div class="card mt-16">
        <div class="tabs" id="ctabs">
          <button class="tab active" data-tab="geral">Dados gerais</button>
          <button class="tab" data-tab="cob">Coberturas <span class="badge">${res.coberturas.length}</span></button>
          <button class="tab" data-tab="exc">Exclusões <span class="badge">${res.exclusoes.length}</span></button>
          <button class="tab" data-tab="fra">Franquias <span class="badge">${res.franquias.length}</span></button>
        </div>
        <div id="cbody"></div>
      </div>
      <details class="cite mt-16"><summary>${icon('layers', 14)} Etapas executadas</summary><div style="padding:0 12px 12px">${traceSteps(trace)}</div></details>`;

    const grid = (rowsIn, first, extra = [], rowCls = () => '') => {
      const cols2 = [...first, ...labels, ...extra];
      return `<div class="table-wrap"><table class="table"><thead><tr>${cols2.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead>
        <tbody>${rowsIn.map((r) => `<tr class="${rowCls(r)}">${cols2.map((c, i) => {
          const v = r[c] ?? '—';
          const txt = esc(v).replace(/^✓/, `<span style="color:var(--success)">✓</span>`).replace(/^✗/, `<span style="color:var(--danger)">✗</span>`);
          return `<td class="${i === 0 ? 'strong' : ''}">${txt}</td>`;
        }).join('')}</tr>`).join('')}</tbody></table></div>`;
    };
    const sit = (r) => (/^(Ausente|Só em)/.test(r['Situação'] || '') ? 'missing' : /^Limites/.test(r['Situação'] || '') ? 'diff' : '');
    const panes = {
      geral: () => grid(res.geral, ['Campo'], [], (r) => (r.Diferente ? 'diff' : '')) + '<p class="subtle" style="padding:10px 16px">Linhas destacadas diferem entre as apólices.</p>',
      cob: () => grid(res.coberturas, ['Cobertura', 'Categoria'], ['Situação'], sit),
      exc: () => grid(res.exclusoes, ['Exclusão', 'Categoria'], ['Situação'], sit),
      fra: () => grid(res.franquias, ['Aplicação']),
    };
    $('#cfgCmp', view)?.addEventListener('click', openSettings);
    $('#dkMais', view)?.addEventListener('click', (e) => {
      $$('#dkBody tr[hidden]', view).forEach((tr) => { tr.hidden = false; });
      e.currentTarget.parentElement.remove();
    });
    const cbody = $('#cbody', view);
    cbody.innerHTML = panes.geral();
    tabs($('#ctabs', view), (t) => { cbody.innerHTML = panes[t](); });

    $$('[data-exp]', view).forEach((b) => b.addEventListener('click', async () => {
      const fmt = b.dataset.exp;
      try {
        const blob = await api.exportComparison(fmt, { resultado: res, analise });
        download(blob, `comparacao_do.${fmt}`);
      } catch (e) { toast(e.message, 'error'); }
    }));
  }
}
