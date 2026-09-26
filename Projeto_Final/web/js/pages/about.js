// "Sobre a solução": arquitetura apresentada visualmente (diagramas no tema do app).
import { crumbs } from '../app.js';
import { $, icon, tabs } from '../ui.js';

const REPO = 'https://github.com/jpscard/InsurMinds/tree/main/Projeto_Final';

const FLUXO = [
  { ic: 'file', nome: 'Documento', det: 'PDF digital, digitalizado ou imagem', tipo: 'in' },
  { ic: 'eye', nome: 'Ingestão / OCR', det: 'texto nativo ou Tesseract (português)', tipo: 'det' },
  { ic: 'search', nome: 'Triagem', det: 'é uma apólice D&O?', tipo: 'ia' },
  { ic: 'sparkles', nome: 'Extração', det: 'JSON no esquema ApoliceDO', tipo: 'ia' },
  { ic: 'checkCircle', nome: 'Validação', det: 'consistência e alertas', tipo: 'det' },
  { ic: 'database', nome: 'Armazenamento', det: 'SQLite: dados, texto e páginas', tipo: 'det' },
  { ic: 'layers', nome: 'Indexação', det: 'sumário em árvore (PageIndex)', tipo: 'ia' },
];

const CAMADAS = [
  { nome: 'Apresentação', onde: 'web/', itens: ['Landing page', 'Plataforma (/app)', 'Modelo de IA no navegador', 'Linha de comando (cli.py)'] },
  { nome: 'API', onde: 'api/main.py · FastAPI', itens: ['Apólices, índice e original', 'Comparação e exportação', 'Consulta por IA e SQL', 'Modelos de cada provedor'] },
  { nome: 'Núcleo', onde: 'do_platform/', itens: ['Pipeline', '6 agentes', 'Comparação determinística', 'Índice hierárquico'] },
  { nome: 'Infraestrutura', onde: 'LLM · SQLite · Docker', itens: ['Anthropic, OpenAI, Gemini ou offline', 'SQLite relacional + JSON', 'Render com deploy automático'] },
];

const AGENTES = [
  { n: 1, nome: 'Triagem', ia: 'ia', entrada: 'início do texto', saida: 'tipo do documento e se é D&O',
    txt: 'Evita processar documentos errados e avisa quando o arquivo não parece uma apólice D&O. Lê só o começo do documento, para ser barato.' },
  { n: 2, nome: 'Extração', ia: 'ia', entrada: 'texto completo', saida: 'JSON ApoliceDO',
    txt: 'Núcleo da solução: estrutura coberturas (Lados A, B e C), limites, franquias, exclusões e vigência, guardando o trecho de origem. Documentos longos são extraídos em blocos e consolidados.' },
  { n: 3, nome: 'Validação', ia: 'det', entrada: 'ApoliceDO', saida: 'dados normalizados + alertas',
    txt: 'Revisor determinístico: normaliza datas e valores e aponta sublimite maior que o LMG, vigência invertida e campos ausentes. Não corrige em silêncio.' },
  { n: 4, nome: 'Indexação', ia: 'resumo', entrada: 'páginas', saida: 'árvore de seções',
    txt: 'Monta o sumário do documento pelo layout (títulos em maiúsculas e cláusulas numeradas). A IA só escreve um resumo curto das seções principais.' },
  { n: 5, nome: 'Comparação', ia: 'ia', entrada: 'N apólices', saida: 'diferenças + análise executiva',
    txt: 'As diferenças são calculadas por código, exatas e reprodutíveis; a IA entra depois para avaliar impacto e redigir a recomendação.' },
  { n: 6, nome: 'Consulta', ia: 'ia', entrada: 'pergunta + apólices', saida: 'resposta com seção e página',
    txt: 'Grafo LangGraph que navega o índice das apólices, lê as seções certas e responde citando a fonte. Sem IA, usa busca por palavras.' },
];

const NOS = [
  ['roteador', 'Decide se os dados extraídos bastam ("qual tem o maior LMG?") ou se é preciso ler o documento.'],
  ['navegador', 'Lê só o sumário de cada apólice (títulos, páginas e resumos) e escolhe até 6 seções, com o motivo.'],
  ['leitor', 'Traz o texto das seções escolhidas, com as subseções.'],
  ['avaliador', 'Confere se o que foi lido basta; se não, o grafo navega de novo (no máximo 2 rodadas).'],
  ['busca_lexical', 'BM25 nas seções: caminho do modo offline e reserva quando a navegação falha.'],
  ['respondedor', 'Responde só com o que foi lido, citando apólice, seção e página.'],
];

const DECISOES = [
  ['scale', 'Comparação híbrida', 'Números e presença de cláusulas são calculados por código; a IA só interpreta. Valores nunca são inventados e o resultado é reprodutível.'],
  ['code', 'Esquema canônico', 'O modelo ApoliceDO (Pydantic) é o contrato entre os agentes: valida a saída da IA e gera o esquema enviado no prompt.'],
  ['layers', 'IA plugável', 'Anthropic, OpenAI e Gemini atrás de uma interface única. O modo offline permite demonstrar e testar sem chave.'],
  ['eye', 'OCR só onde precisa', 'Páginas com texto usam o texto nativo, rápido e exato; só as digitalizadas passam pelo Tesseract.'],
  ['database', 'SQLite híbrido', 'Colunas relacionais para filtrar e consultar em SQL, mais o JSON completo para não perder detalhe. Zero infraestrutura.'],
  ['refresh', 'Sem retrabalho', 'O hash SHA-256 reconhece arquivos já processados: reenviar não gasta chamadas à IA.'],
  ['edit', 'Revisão humana', 'Qualquer dado extraído pode ser corrigido na tela; a correção vale nas comparações e consultas.'],
  ['shield', 'Erros em camadas', 'Configuração errada para cedo com mensagem clara; falhas temporárias têm nova tentativa; triagem, comparação e consulta têm caminho alternativo sem IA.'],
];

const TABELAS = [
  ['apolices', 'identificação, vigência, LMG, prêmio, triagem, alertas e o JSON completo'],
  ['coberturas', 'nome, categoria (Lado A/B/C...), limite e franquia'],
  ['exclusoes', 'título, categoria e descrição'],
  ['paginas', 'texto original de cada página e o método (texto ou OCR)'],
  ['indices', 'árvore de seções de cada documento, navegada pela consulta'],
  ['comparacoes', 'histórico das análises geradas'],
];

const LIMITES = [
  'Muitas exclusões ficam nas Condições Gerais; enviando só a apólice, a comparação de exclusões fica incompleta.',
  'O índice depende do layout: documentos sem títulos nem cláusulas numeradas viram uma seção por página.',
  'Coberturas são alinhadas por similaridade de palavras; nomes muito diferentes podem não ser pareados.',
  'O OCR depende da qualidade da digitalização; tabelas complexas podem perder a estrutura.',
  'Uma consulta sobre cláusulas usa até 5 chamadas à IA: mais precisa, porém mais lenta que uma busca direta.',
];

const PROXIMOS = [
  'Gabarito das apólices de exemplo e taxa de acerto por campo com cada provedor.',
  'Memória de conversa na consulta ("e na Boreal?").',
  'Embeddings para alinhar cláusulas entre seguradoras.',
  'Login com carteira por usuário e fila de processamento para lotes grandes.',
];

const iaBadge = (t) => ({ ia: '<span class="badge blue">Usa IA</span>', det: '<span class="badge green">Determinístico</span>',
  resumo: '<span class="badge violet">IA só nos resumos</span>' }[t] || '');

function visaoGeral() {
  const passos = FLUXO.map((f, i) => `
    ${i ? `<div class="flow-arrow">${icon('chevronRight', 18)}</div>` : ''}
    <div class="flow-step ${f.tipo}"><span class="flow-ic">${icon(f.ic, 18)}</span><b>${f.nome}</b><span>${f.det}</span></div>`).join('');
  return `
    <div class="card"><div class="card-head"><div><div class="card-title">Do documento à resposta</div>
      <div class="card-sub">O que acontece com cada apólice enviada</div></div>
      <div class="legend-inline"><span><i class="lg ia"></i>usa IA</span><span><i class="lg det"></i>determinístico</span></div></div>
      <div class="card-body">
        <div class="flow">${passos}</div>
        <div class="flow-branch">
          <div class="branch-line"></div>
          <div class="grid grid-2">
            <div class="flow-step ia wide"><span class="flow-ic">${icon('scale', 18)}</span><b>Comparação</b><span>diferenças calculadas por código + análise executiva pela IA · exporta PDF, Excel e Markdown</span></div>
            <div class="flow-step ia wide"><span class="flow-ic">${icon('chat', 18)}</span><b>Consulta</b><span>grafo LangGraph que navega o índice e cita seção e página · SQL somente leitura</span></div>
          </div>
        </div>
      </div></div>

    <div class="card mt-16"><div class="card-head"><div><div class="card-title">Camadas da arquitetura</div>
      <div class="card-sub">A interface e a API usam só o pipeline, nunca os agentes diretamente</div></div></div>
      <div class="card-body layers">
        ${CAMADAS.map((c, i) => `
          <div class="layer-row l${i}"><div class="layer-name"><b>${c.nome}</b><span class="mono">${c.onde}</span></div>
            <div class="layer-items">${c.itens.map((x) => `<span>${x}</span>`).join('')}</div></div>`).join('')}
      </div></div>

    <div class="grid grid-4 mt-16">
      ${[['6', 'agentes especializados'], ['3', 'provedores de IA + modo offline'], ['3', 'formatos de entrada'], ['3', 'formatos de relatório (PDF, Excel, Markdown)']]
        .map(([n, t]) => `<div class="card kpi" style="text-align:center"><div class="kpi-value grad-num">${n}</div><div class="kpi-foot" style="font-size:13px">${t}</div></div>`).join('')}
    </div>`;
}

function agentes() {
  return `<div class="grid grid-3">${AGENTES.map((a) => `
    <div class="card agent-card"><div class="card-body stack" style="gap:10px">
      <div class="row" style="flex-wrap:nowrap"><span class="agent-num">${a.n}</span><b style="font-size:15.5px">${a.nome}</b><span class="spacer"></span>${iaBadge(a.ia)}</div>
      <div class="io"><span>${a.entrada}</span>${icon('arrowRight', 14)}<span>${a.saida}</span></div>
      <p class="muted" style="font-size:13.5px">${a.txt}</p>
    </div></div>`).join('')}</div>`;
}

function grafo() {
  const svg = `
  <svg class="graph" viewBox="0 0 1144 440" role="img" aria-label="Grafo da consulta">
    <defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="g-head"/></marker></defs>
    <g class="g-start"><rect x="20" y="185" width="120" height="50" rx="25"/><text class="h" x="80" y="215" text-anchor="middle">pergunta</text></g>
    <g class="g-ia"><rect x="185" y="175" width="175" height="70" rx="12"/><text class="h" x="272" y="204" text-anchor="middle">roteador</text><text class="s" x="272" y="224" text-anchor="middle">dados ou documento?</text></g>
    <g class="g-ia"><rect x="415" y="80" width="210" height="70" rx="12"/><text class="h" x="520" y="109" text-anchor="middle">navegador</text><text class="s" x="520" y="129" text-anchor="middle">lê o sumário, escolhe seções</text></g>
    <g class="g-det"><rect x="680" y="80" width="160" height="70" rx="12"/><text class="h" x="760" y="109" text-anchor="middle">leitor</text><text class="s" x="760" y="129" text-anchor="middle">texto das seções</text></g>
    <g class="g-ia"><rect x="680" y="230" width="160" height="70" rx="12"/><text class="h" x="760" y="259" text-anchor="middle">avaliador</text><text class="s" x="760" y="279" text-anchor="middle">já basta?</text></g>
    <g class="g-det"><rect x="430" y="340" width="180" height="70" rx="12"/><text class="h" x="520" y="369" text-anchor="middle">busca_lexical</text><text class="s" x="520" y="389" text-anchor="middle">BM25 nas seções</text></g>
    <g class="g-ia"><rect x="900" y="175" width="220" height="70" rx="12"/><text class="h" x="1010" y="204" text-anchor="middle">respondedor</text><text class="s" x="1010" y="224" text-anchor="middle">cita apólice · seção · pág.</text></g>
    <g class="g-edges">
      <line x1="140" y1="210" x2="183" y2="210"/>
      <path d="M360 200 C 395 185, 395 115, 413 115"/><text x="386" y="140" text-anchor="end">documento</text>
      <path d="M360 230 C 400 255, 400 375, 428 375"/><text x="388" y="322" text-anchor="end">offline</text>
      <path d="M272 175 C 272 18, 1010 18, 1010 173"/><text x="610" y="44">estruturado</text>
      <line x1="625" y1="115" x2="678" y2="115"/><text x="628" y="105">seções</text>
      <path d="M520 150 L 520 338"/><text x="528" y="250">nada novo</text>
      <line x1="760" y1="150" x2="760" y2="228"/>
      <path d="M680 275 C 630 275, 590 225, 575 152"/><text x="600" y="322">falta algo (máx. 2)</text>
      <path d="M840 265 C 875 265, 875 225, 898 220"/><text x="850" y="287">suficiente</text>
      <path d="M610 375 C 850 375, 1000 325, 1010 247"/>
    </g>
  </svg>`;
  return `
    <div class="card"><div class="card-head"><div><div class="card-title">RAG por raciocínio sobre o índice (PageIndex) em LangGraph</div>
      <div class="card-sub">Em vez de picotar o texto e buscar por similaridade, a IA lê o sumário da apólice e decide o que abrir, como um especialista folheando o documento</div></div></div>
      <div class="card-body"><div class="graph-wrap">${svg}</div>
      <div class="legend-inline" style="justify-content:center;margin-top:6px"><span><i class="lg ia"></i>usa IA</span><span><i class="lg det"></i>determinístico</span></div></div></div>
    <div class="grid grid-main mt-16">
      <div class="card"><div class="card-head"><div class="card-title">O que cada nó faz</div></div>
        <div class="card-body flush">${NOS.map(([n, t]) => `<div class="node-row"><span class="mono node-name">${n}</span><span>${t}</span></div>`).join('')}</div></div>
      <div class="stack">
        ${[['layers', 'Multiprovedor', 'Os nós usam a camada de IA do projeto: funciona com Claude, GPT ou Gemini. A biblioteca oficial do PageIndex só aceita OpenAI.'],
           ['eye', 'Transparente', 'Cada nó registra o que fez; o "caminho da consulta" aparece junto da resposta.'],
           ['shield', 'Resiliente', 'Se a IA devolver algo inválido, o grafo segue pela busca por palavras em vez de falhar.']]
          .map(([ic, t, d]) => `<div class="card"><div class="card-body row" style="flex-wrap:nowrap;align-items:flex-start"><span class="kpi-icon">${icon(ic, 16)}</span>
            <div><b>${t}</b><p class="muted" style="font-size:13px;margin-top:2px">${d}</p></div></div></div>`).join('')}
      </div>
    </div>`;
}

function decisoes() {
  return `<div class="grid grid-2">${DECISOES.map(([ic, t, d], i) => `
    <div class="card"><div class="card-body row" style="flex-wrap:nowrap;align-items:flex-start;gap:14px">
      <span class="kpi-icon" style="width:36px;height:36px">${icon(ic, 18)}</span>
      <div><div class="subtle" style="font-weight:600">Decisão ${i + 1}</div><b style="font-size:15px">${t}</b><p class="muted" style="font-size:13.5px;margin-top:4px">${d}</p></div>
    </div></div>`).join('')}</div>`;
}

function dados() {
  return `
    <div class="card"><div class="card-head"><div><div class="card-title">Modelo de dados (SQLite)</div>
      <div class="card-sub">Relacional para filtrar e consultar em SQL, com o JSON completo de cada apólice</div></div></div>
      <div class="card-body"><div class="tables-grid">${TABELAS.map(([t, d]) => `
        <div class="db-table"><div class="db-head">${icon('database', 14)}<span class="mono">${t}</span></div><p>${d}</p></div>`).join('')}</div></div></div>
    <div class="grid grid-2 mt-16">
      <div class="card"><div class="card-head"><span class="kpi-icon" style="background:var(--warning-soft);color:var(--warning)">${icon('alert', 16)}</span><div class="card-title">Limitações conhecidas</div></div>
        <div class="card-body" style="padding-top:6px;padding-bottom:6px">${LIMITES.map((l) => `<div class="point">${icon('alert', 16)}<span>${l}</span></div>`).join('')}</div></div>
      <div class="card"><div class="card-head"><span class="kpi-icon">${icon('arrowRight', 16)}</span><div class="card-title">Próximos passos</div></div>
        <div class="card-body" style="padding-top:6px;padding-bottom:6px">${PROXIMOS.map((l) => `<div class="point next">${icon('chevronRight', 16)}<span>${l}</span></div>`).join('')}</div></div>
    </div>`;
}

const PANES = { geral: visaoGeral, agentes, consulta: grafo, decisoes, dados };

export async function render(view, { query } = {}) {
  crumbs([{ label: 'Sobre a solução' }]);
  view.innerHTML = `
    <div class="page-head">
      <div><h1 class="page-title">Como o Apólis funciona</h1>
      <p class="page-sub">Arquitetura, agentes e decisões de projeto da plataforma de análise e comparação de apólices D&O.</p></div>
      <div class="page-actions">
        <a class="btn" href="/docs" target="_blank" rel="noopener">${icon('code', 16)} API</a>
        <a class="btn" href="${REPO}" target="_blank" rel="noopener">${icon('external', 16)} Código no GitHub</a>
      </div>
    </div>
    <div class="card" style="margin-bottom:16px"><div class="tabs" id="atabs">
      <button class="tab active" data-tab="geral">Visão geral</button>
      <button class="tab" data-tab="agentes">Agentes <span class="badge">6</span></button>
      <button class="tab" data-tab="consulta">Consulta (RAG)</button>
      <button class="tab" data-tab="decisoes">Decisões</button>
      <button class="tab" data-tab="dados">Dados e limites</button>
    </div></div>
    <div id="abody"></div>`;
  const body = $('#abody', view);
  tabs($('#atabs', view), (t) => { body.innerHTML = PANES[t](); });
  const aba = query?.get('tab');
  const btn = aba && $(`#atabs .tab[data-tab="${aba}"]`, view);
  if (btn) btn.click(); else body.innerHTML = PANES.geral();
}
