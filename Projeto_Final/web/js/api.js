// Cliente da API. Envia a configuração de LLM em cabeçalhos a cada chamada.
import { progress } from './ui.js';

const store = {
  get(k, session = false) { try { return (session ? sessionStorage : localStorage).getItem(k); } catch { return null; } },
  set(k, v, session = false) {
    try {
      const s = session ? sessionStorage : localStorage;
      v === null || v === '' ? s.removeItem(k) : s.setItem(k, v);
    } catch { /* armazenamento indisponível: segue só em memória */ }
  },
};

const memKeys = {};

export const llm = {
  get provider() { return store.get('doi.provider'); },
  set provider(v) { store.set('doi.provider', v); },
  model(p = this.provider) { return store.get(`doi.model.${p}`); },
  setModel(p, v) { store.set(`doi.model.${p}`, v); },
  // A chave fica só nesta aba (sessionStorage) e nunca é gravada no servidor.
  key(p = this.provider) { return memKeys[p] ?? store.get(`doi.key.${p}`, true); },
  setKey(p, v) { memKeys[p] = v || undefined; store.set(`doi.key.${p}`, v || null, true); },
  headers(p = this.provider) {
    const h = {};
    if (p) h['X-LLM-Provider'] = p;
    const m = this.model(p); if (m) h['X-LLM-Model'] = m;
    const k = this.key(p); if (k) h['X-LLM-Key'] = k;
    return h;
  },
};

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function request(method, path, { body, form, blob, quiet, headers = {} } = {}) {
  const opts = { method, headers: { ...llm.headers(), ...headers } };
  if (form) opts.body = form;
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers['Content-Type'] = 'application/json'; }
  if (!quiet) progress(true);
  try {
    const res = await fetch(path, opts);
    if (!res.ok) {
      let msg = `${res.status} ${res.statusText}`;
      try {
        const j = await res.json();
        msg = typeof j.detail === 'string' ? j.detail : Array.isArray(j.detail) ? j.detail.map((d) => d.msg).join('; ') : msg;
      } catch { /* resposta sem JSON */ }
      throw new ApiError(msg, res.status);
    }
    if (res.status === 204) return null;
    return blob ? res.blob() : res.json();
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError('Não foi possível falar com o servidor. Ele está rodando?', 0);
  } finally {
    if (!quiet) progress(false);
  }
}

/** Requisição com progresso ao vivo: a API responde NDJSON, uma linha por etapa concluída
 *  ({type: "step"}) e, no fim, {type: "result"} ou {type: "error"}. `onStep` recebe cada etapa. */
async function stream(method, path, { body, form, onStep = () => {} } = {}) {
  const opts = { method, headers: { ...llm.headers() } };
  if (form) opts.body = form;
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers['Content-Type'] = 'application/json'; }
  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new ApiError('Não foi possível falar com o servidor. Ele está rodando?', 0);
  }
  if (!res.ok) {  // validação antes do processamento: erro HTTP comum
    let msg = `${res.status} ${res.statusText}`;
    try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : msg; } catch { /* sem JSON */ }
    throw new ApiError(msg, res.status);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { value, done } = await reader.read();
    buf += decoder.decode(value || new Uint8Array(), { stream: !done });
    let nl;
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      const ev = JSON.parse(line);
      if (ev.type === 'step') onStep(ev);
      else if (ev.type === 'result') return ev.data;
      else if (ev.type === 'error') throw new ApiError(ev.detail, ev.status);
    }
    if (done) throw new ApiError('A conexão terminou antes do resultado.', 0);
  }
}

export const api = {
  config: () => request('GET', '/api/config', { quiet: true }),
  providers: () => request('GET', '/api/llm/providers', { quiet: true }),
  models: (provider, key) => request('GET', '/api/llm/models', {
    quiet: true, headers: { 'X-LLM-Provider': provider, ...(key ? { 'X-LLM-Key': key } : { 'X-LLM-Key': '' }) },
  }),
  stats: () => request('GET', '/api/stats'),
  policies: () => request('GET', '/api/policies'),
  policy: (id) => request('GET', `/api/policies/${id}`),
  pages: (id) => request('GET', `/api/policies/${id}/pages`),
  index: (id) => request('GET', `/api/policies/${id}/index`),
  updatePolicy: (id, data) => request('PUT', `/api/policies/${id}`, { body: data }),
  deletePolicy: (id) => request('DELETE', `/api/policies/${id}`),
  upload(file, force) {
    const f = new FormData();
    f.append('file', file);
    f.append('force', force ? 'true' : 'false');
    return request('POST', '/api/policies', { form: f, quiet: true });
  },
  uploadStream(file, force, onStep) {
    const f = new FormData();
    f.append('file', file);
    f.append('force', force ? 'true' : 'false');
    return stream('POST', '/api/policies/stream', { form: f, onStep });
  },
  processSampleStream: (name, force, onStep) => stream('POST', `/api/samples/${encodeURIComponent(name)}/stream?force=${!!force}`, { onStep }),
  compareStream: (ids, onStep) => stream('POST', '/api/compare/stream', { body: { ids }, onStep }),
  askStream: (pergunta, ids, onStep) => stream('POST', '/api/ask/stream', { body: { pergunta, ids }, onStep }),
  samples: () => request('GET', '/api/samples', { quiet: true }),
  processSample: (name, force) => request('POST', `/api/samples/${encodeURIComponent(name)}?force=${!!force}`, { quiet: true }),
  compare: (ids) => request('POST', '/api/compare', { body: { ids } }),
  exportComparison: (fmt, data) => request('POST', `/api/compare/export/${fmt}`, { body: data, blob: true }),
  ask: (pergunta, ids) => request('POST', '/api/ask', { body: { pergunta, ids } }),
  sqlExamples: () => request('GET', '/api/sql/examples', { quiet: true }),
  sql: (sql) => request('POST', '/api/sql', { body: { sql } }),
};
