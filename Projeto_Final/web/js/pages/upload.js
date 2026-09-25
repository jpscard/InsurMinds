import { api } from '../api.js';
import { crumbs, llmLabel, llmReady, openSettings, refreshCount } from '../app.js';
import { $, alertBox, bytes, esc, icon, moneyShort, toast, traceSteps } from '../ui.js';

const EXT = ['.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'];
let queue = []; // sobrevive à navegação entre páginas enquanto processa
let running = false;
let repaint = () => {};

export async function render(view, { query }) {
  crumbs([{ label: 'Carteira', href: '#/apolices' }, { label: 'Enviar documentos' }]);
  view.innerHTML = `
    <div class="page-head">
      <div><h1 class="page-title">Enviar documentos</h1>
      <p class="page-sub">Cada documento passa por leitura (OCR quando preciso), triagem, extração, validação e armazenamento.</p></div>
    </div>
    <div class="grid grid-main">
      <div class="stack">
        <div class="card"><div class="card-body stack">
          <label class="dropzone" id="drop" tabindex="0">
            <input type="file" id="file" multiple accept="${EXT.join(',')}" hidden>
            <span class="empty-icon">${icon('upload', 24)}</span>
            <strong>Arraste os arquivos para cá ou clique para escolher</strong>
            <span class="subtle">PDF digital, PDF digitalizado ou imagem (PNG, JPG, TIFF, WEBP) · vários arquivos por vez</span>
          </label>
          <div class="row">
            <label class="switch"><input type="checkbox" id="force"> Reprocessar arquivos que já estão na carteira</label>
            <span class="spacer"></span>
            <span class="subtle" id="llmInfo"></span>
          </div>
        </div></div>
        <div class="card" id="queueCard" style="display:none">
          <div class="card-head"><div class="card-title">Processamento</div><span class="card-sub" id="qSummary"></span>
            <button class="btn btn-sm btn-ghost" id="clearBtn" style="margin-left:auto">Limpar concluídos</button></div>
          <div class="file-list" id="queue"></div>
        </div>
      </div>
      <div class="stack">
        <div class="card" id="samplesCard">
          <div class="card-head"><div><div class="card-title">Apólices de exemplo</div><div class="card-sub">Três apólices fictícias do mesmo tomador</div></div></div>
          <div class="card-body stack" id="samples"><span class="subtle">Carregando…</span></div>
        </div>
        <div class="card"><div class="card-body stack" style="gap:10px">
          <div class="card-title">Como funciona</div>
          ${['Ingestão: texto nativo do PDF; páginas sem texto vão para OCR.', 'Triagem: confirma se é uma apólice D&O.',
             'Extração: a IA estrutura coberturas, limites, franquias, exclusões e vigência.', 'Validação: checa consistência e aponta alertas.',
             'Armazenamento: dados estruturados + texto original para consultas.'].map((t, i) => `<div class="row" style="flex-wrap:nowrap;align-items:flex-start"><span class="badge blue">${i + 1}</span><span class="muted" style="font-size:13px">${t}</span></div>`).join('')}
        </div></div>
      </div>
    </div>`;

  const paintLlm = () => {
    $('#llmInfo', view).innerHTML = llmReady()
      ? `Processará com <strong>${esc(llmLabel())}</strong> · <a href="#" id="chg">alterar</a>`
      : `<span style="color:var(--danger)">Sem chave de API</span> · <a href="#" id="chg">configurar IA</a>`;
    $('#chg', view).addEventListener('click', (e) => { e.preventDefault(); openSettings(); });
  };
  paintLlm();
  const chip = document.getElementById('llmChip');
  const obs = new MutationObserver(paintLlm);
  obs.observe(chip, { subtree: true, childList: true, attributes: true });

  const drop = $('#drop', view), input = $('#file', view);
  const add = (files) => {
    const ok = [...files].filter((f) => EXT.some((e) => f.name.toLowerCase().endsWith(e)));
    if (ok.length < files.length) toast('Alguns arquivos foram ignorados: formato não suportado.', 'error');
    ok.forEach((f) => queue.push({ kind: 'file', file: f, name: f.name, size: f.size, status: 'queued' }));
    run();
  };
  input.addEventListener('change', () => { add(input.files); input.value = ''; });
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
  ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', (e) => add(e.dataTransfer.files));
  $('#clearBtn', view).addEventListener('click', () => { queue = queue.filter((q) => q.status === 'queued' || q.status === 'running'); repaint(); });

  repaint = () => {
    const box = $('#queue', view);
    if (!box) return;
    $('#queueCard', view).style.display = queue.length ? '' : 'none';
    const done = queue.filter((q) => q.status === 'done').length, err = queue.filter((q) => q.status === 'error').length;
    $('#qSummary', view).textContent = `${done} concluído(s)${err ? ` · ${err} com erro` : ''} · ${queue.length} no total`;
    box.innerHTML = queue.map((q) => {
      const ico = { queued: ['clock', ''], running: [null, 'run'], done: ['checkCircle', 'ok'], error: ['alertCircle', 'err'] }[q.status];
      const r = q.result;
      let detail = '';
      if (q.status === 'running') detail = '<div class="subtle">Lendo, estruturando e validando… pode levar até um minuto com IA.</div>';
      if (q.status === 'error') detail = `<div class="mt-8">${alertBox('error', esc(q.error))}</div>`;
      if (q.status === 'done') {
        const ap = r.apolice, lmg = ap.limite_maximo_garantia;
        detail = `<div class="subtle">${esc(ap.identificacao?.seguradora || '—')} · LMG ${lmg?.valor != null ? moneyShort(lmg.valor, lmg.moeda) : '—'} · ${ap.coberturas.length} coberturas · ${ap.exclusoes.length} exclusões
          ${r.reaproveitado ? ' · <span class="badge">já estava na carteira</span>' : ''}${r.alertas.length ? ` · <span class="badge amber">${r.alertas.length} alerta(s)</span>` : ''}</div>
          ${r.avisos.map((a) => `<div class="mt-8">${alertBox('warn', esc(a))}</div>`).join('')}
          ${traceSteps(r.trace)}`;
      }
      return `<div class="file-item">
        <div class="file-ico ${ico[1]}">${ico[0] ? icon(ico[0], 18) : '<span class="spinner"></span>'}</div>
        <div style="min-width:0"><div class="file-name">${esc(q.name)}</div><div class="file-meta">${q.size ? bytes(q.size) : 'amostra'}${q.status === 'queued' ? ' · na fila' : ''}</div></div>
        <div>${q.status === 'done' ? `<a class="btn btn-sm" href="#/apolices/${r.id}">Ver apólice ${icon('arrowRight', 14)}</a>` : ''}</div>
        ${detail ? `<div class="file-detail">${detail}</div>` : ''}
      </div>`;
    }).join('');
  };
  repaint();

  // Amostras
  const samples = await api.samples().catch(() => []);
  const sEl = $('#samples', view);
  if (!sEl) return () => obs.disconnect();
  sEl.innerHTML = samples.length ? `
    ${samples.map((s) => `<div class="row" style="flex-wrap:nowrap"><span class="file-ico">${icon('file', 16)}</span>
      <div style="min-width:0;flex:1"><div class="file-name" style="font-size:13px">${esc(s.name)}</div><div class="file-meta">${bytes(s.size)}${/digitalizada/.test(s.name) ? ' · exige OCR' : ''}</div></div></div>`).join('')}
    <button class="btn btn-primary" id="runSamples">${icon('play', 14)} Processar as ${samples.length} amostras</button>` : '<span class="subtle">Nenhuma amostra disponível.</span>';
  $('#runSamples', view)?.addEventListener('click', () => {
    samples.forEach((s) => queue.push({ kind: 'sample', name: s.name, size: s.size, status: 'queued' }));
    run();
  });
  if (query.get('amostras')) {
    $('#samplesCard', view).style.boxShadow = 'var(--focus)';
    $('#samplesCard', view).scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  return () => { obs.disconnect(); repaint = () => {}; };

  async function run() {
    repaint();
    if (running) return;
    running = true;
    const force = () => document.getElementById('force')?.checked;
    let item;
    while ((item = queue.find((q) => q.status === 'queued'))) {
      item.status = 'running'; repaint();
      try {
        item.result = item.kind === 'sample' ? await api.processSample(item.name, force()) : await api.upload(item.file, force());
        item.status = 'done';
        refreshCount();
      } catch (e) {
        item.status = 'error'; item.error = e.message;
      }
      repaint();
    }
    running = false;
    const errs = queue.filter((q) => q.status === 'error').length;
    toast(errs ? `Processamento concluído com ${errs} erro(s).` : 'Processamento concluído.', errs ? 'error' : 'success');
  }
}
