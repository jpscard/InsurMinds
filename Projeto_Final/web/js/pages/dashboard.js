import { api } from '../api.js';
import { crumbs, llmLabel, llmReady, openSettings } from '../app.js';
import { $, empty, esc, icon, loading, moneyShort, pct, shortInsurer, vigencia, vigenciaStatus } from '../ui.js';

export async function render(view) {
  crumbs([{ label: 'Painel' }]);
  view.innerHTML = loading();
  const [stats, rows] = await Promise.all([api.stats(), api.policies()]);

  const head = `
    <div class="page-head">
      <div><h1 class="page-title">Painel</h1><p class="page-sub">Visão geral da carteira de apólices D&O analisadas.</p></div>
      <div class="page-actions">
        <a class="btn" href="#/comparar">${icon('columns', 16)} Comparar</a>
        <a class="btn btn-primary" href="#/enviar">${icon('upload', 16)} Enviar documentos</a>
      </div>
    </div>`;

  const llmAlert = llmReady() ? '' : `
    <div class="alert warn" style="margin-bottom:20px">${icon('alert', 18)}
      <div class="row" style="flex:1"><span>Nenhuma chave de API configurada para o provedor escolhido. A extração e a análise precisam de um modelo.</span>
      <span class="spacer"></span><button class="btn btn-sm" id="cfgLlm">${icon('settings', 14)} Configurar IA</button></div>
    </div>`;

  if (!rows.length) {
    view.innerHTML = head + llmAlert + `<div class="card">${empty({
      ic: 'shield', title: 'Sua carteira está vazia',
      text: 'Envie apólices em PDF ou imagem. Cada documento é lido (com OCR quando preciso), estruturado pela IA, validado e guardado para comparação e consulta.',
      action: `<div class="row" style="justify-content:center;margin-top:8px">
        <a class="btn btn-primary" href="#/enviar">${icon('upload', 16)} Enviar documentos</a>
        <a class="btn" href="#/enviar?amostras=1">${icon('play', 14)} Usar apólices de exemplo</a></div>`,
    })}</div>`;
    $('#cfgLlm', view)?.addEventListener('click', openSettings);
    return;
  }

  const kpi = (ic, cls, label, value, foot) => `
    <div class="card kpi"><div class="kpi-label"><span class="kpi-icon ${cls}">${icon(ic, 16)}</span>${label}</div>
    <div class="kpi-value">${value}</div><div class="kpi-foot">${foot}</div></div>`;

  const recent = rows.slice(0, 6).map((r) => {
    const st = vigenciaStatus(r.vigencia_inicio, r.vigencia_fim);
    return `<tr data-id="${r.id}">
      <td><div class="cell-title">${esc(shortInsurer(r.seguradora) || r.arquivo)}</div><div class="cell-sub">${esc(r.numero_apolice || r.arquivo)}</div></td>
      <td>${esc(r.tomador || '—')}</td>
      <td class="nowrap">${vigencia(r.vigencia_inicio, r.vigencia_fim)} <span class="badge ${st.cls}">${st.label}</span></td>
      <td class="num">${moneyShort(r.lmg, r.moeda)}</td>
    </tr>`;
  }).join('');

  const action = (href, ic, title, text) => `
    <a class="pick" href="${href}" style="text-decoration:none;color:inherit">
      <span class="kpi-icon">${icon(ic, 16)}</span>
      <span><strong style="display:block">${title}</strong><span class="subtle">${text}</span></span>
    </a>`;

  view.innerHTML = head + llmAlert + `
    <div class="grid grid-4">
      ${kpi('files', '', 'Apólices na carteira', stats.apolices, `${stats.coberturas} coberturas mapeadas`)}
      ${kpi('building', 'cyan', 'Seguradoras', stats.seguradoras, 'distintas na carteira')}
      ${kpi('shield', 'violet', 'LMG total', moneyShort(stats.lmg_total), 'soma dos limites máximos')}
      ${kpi('percent', 'green', 'Prêmio / LMG médio', pct(stats.taxa_media), `${stats.comparacoes} comparações realizadas`)}
    </div>
    <div class="grid grid-main mt-16">
      <div class="card">
        <div class="card-head"><div><div class="card-title">Apólices recentes</div><div class="card-sub">Últimos documentos processados</div></div>
          <a class="btn btn-sm btn-ghost" style="margin-left:auto" href="#/apolices">Ver todas ${icon('arrowRight', 14)}</a></div>
        <div class="table-wrap"><table class="table hover"><thead><tr><th>Seguradora</th><th>Tomador</th><th>Vigência</th><th class="num">LMG</th></tr></thead>
        <tbody id="recent">${recent}</tbody></table></div>
      </div>
      <div class="stack">
        <div class="card"><div class="card-head"><div class="card-title">Ações rápidas</div></div>
          <div class="card-body stack" style="gap:10px">
            ${action('#/enviar', 'upload', 'Enviar documentos', 'PDF digital, digitalizado ou imagem')}
            ${action('#/comparar', 'columns', 'Comparar apólices', 'Coberturas, exclusões e custos lado a lado')}
            ${action('#/consultar', 'chat', 'Perguntar à carteira', 'Respostas com citação da página')}
          </div></div>
        <div class="card"><div class="card-body row">
          <span class="dot ${llmReady() ? 'ok' : 'err'}"></span>
          <div style="flex:1;min-width:0"><div class="subtle">Modelo de IA</div><strong style="font-size:13px">${esc(llmLabel())}</strong></div>
          <button class="btn btn-sm" id="cfgLlm2">Alterar</button></div></div>
      </div>
    </div>`;

  $('#recent', view).addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-id]');
    if (tr) location.hash = `#/apolices/${tr.dataset.id}`;
  });
  $('#cfgLlm', view)?.addEventListener('click', openSettings);
  $('#cfgLlm2', view).addEventListener('click', openSettings);
}
