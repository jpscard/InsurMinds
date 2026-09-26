import { api } from '../api.js';
import { crumbs } from '../app.js';
import { $, $$, dateTime, docTipo, empty, esc, icon, loading, moneyShort, pct, shortInsurer, vigencia, vigenciaStatus } from '../ui.js';

export async function render(view) {
  crumbs([{ label: 'Carteira' }]);
  view.innerHTML = loading();
  const rows = await api.policies();
  const selected = new Set();

  view.innerHTML = `
    <div class="page-head">
      <div><h1 class="page-title">Carteira de apólices</h1><p class="page-sub">${rows.length} ${rows.length === 1 ? 'apólice armazenada' : 'apólices armazenadas'}. Clique em uma linha para ver os detalhes.</p></div>
      <div class="page-actions">
        <button class="btn" id="cmpBtn" disabled>${icon('columns', 16)} Comparar selecionadas</button>
        <a class="btn btn-primary" href="#/enviar">${icon('upload', 16)} Enviar documentos</a>
      </div>
    </div>
    <div class="card">
      <div class="card-head">
        <div class="input-wrap" style="flex:1;max-width:380px">${icon('search', 16)}<input id="q" class="input" placeholder="Buscar por seguradora, número, tomador ou arquivo"></div>
        <div class="seg" id="flt" style="margin-left:auto">
          <button class="active" data-f="">Todas</button><button data-f="Vigente">Vigentes</button><button data-f="Vencida">Vencidas</button>
        </div>
      </div>
      <div id="tbl"></div>
    </div>`;

  if (!rows.length) {
    $('#tbl', view).innerHTML = empty({ title: 'Nenhuma apólice ainda', text: 'Envie documentos para começar.',
      action: `<a class="btn btn-primary" href="#/enviar">${icon('upload', 16)} Enviar documentos</a>` });
    return;
  }

  let filter = '';
  function paint() {
    const q = $('#q', view).value.trim().toLowerCase();
    const list = rows.filter((r) => {
      const hay = [r.seguradora, r.numero_apolice, r.tomador, r.arquivo].join(' ').toLowerCase();
      return (!q || hay.includes(q)) && (!filter || vigenciaStatus(r.vigencia_inicio, r.vigencia_fim).label === filter);
    });
    if (!list.length) { $('#tbl', view).innerHTML = empty({ ic: 'search', title: 'Nada encontrado', text: 'Ajuste a busca ou o filtro.' }); return; }
    $('#tbl', view).innerHTML = `<div class="table-wrap"><table class="table hover">
      <thead><tr><th style="width:36px"></th><th>Seguradora</th><th>Tomador</th><th>Vigência</th><th class="num">LMG</th><th class="num">Prêmio</th><th class="num">Prêmio/LMG</th><th class="num">Cob. / Excl.</th><th>Processado</th></tr></thead>
      <tbody>${list.map((r) => {
        const st = vigenciaStatus(r.vigencia_inicio, r.vigencia_fim);
        const tipo = docTipo(r.tipo_documento, r.numero_apolice);
        return `<tr data-id="${r.id}">
          <td><input type="checkbox" class="sel" data-id="${r.id}" ${selected.has(r.id) ? 'checked' : ''} aria-label="Selecionar"></td>
          <td><div class="cell-title">${esc(shortInsurer(r.seguradora) || r.arquivo)}</div><div class="cell-sub">${esc(r.numero_apolice || r.arquivo)}</div></td>
          <td>${esc(r.tomador || '—')}</td>
          <td class="nowrap">${tipo ? `<span class="badge amber" title="A triagem identificou que não é uma apólice: serve de consulta, não entra bem em comparações">${tipo}</span><div class="cell-sub">não é apólice</div>`
            : `${vigencia(r.vigencia_inicio, r.vigencia_fim)}<br><span class="badge ${st.cls}">${st.label}</span>`}</td>
          <td class="num">${moneyShort(r.lmg, r.moeda)}</td>
          <td class="num">${moneyShort(r.premio, r.moeda)}</td>
          <td class="num">${r.lmg && r.premio ? pct((r.premio / r.lmg) * 100) : '—'}</td>
          <td class="num">${r.n_coberturas} / ${r.n_exclusoes}</td>
          <td><div>${dateTime(r.criado_em)}</div><div class="cell-sub">${esc(r.provedor_llm || '')}</div></td>
        </tr>`;
      }).join('')}</tbody></table></div>`;
  }

  function paintSel() {
    const b = $('#cmpBtn', view);
    b.disabled = selected.size < 2;
    b.innerHTML = `${icon('columns', 16)} Comparar selecionadas${selected.size ? ` (${selected.size})` : ''}`;
  }

  $('#q', view).addEventListener('input', paint);
  $('#flt', view).addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    $$('#flt button', view).forEach((x) => x.classList.toggle('active', x === b));
    filter = b.dataset.f; paint();
  });
  $('#tbl', view).addEventListener('click', (e) => {
    const cb = e.target.closest('.sel');
    if (cb) {
      const id = Number(cb.dataset.id);
      cb.checked ? selected.add(id) : selected.delete(id);
      paintSel();
      return;
    }
    const tr = e.target.closest('tr[data-id]');
    if (tr) location.hash = `#/apolices/${tr.dataset.id}`;
  });
  $('#cmpBtn', view).addEventListener('click', () => { location.hash = `#/comparar?ids=${[...selected].join(',')}`; });
  paint();
}
