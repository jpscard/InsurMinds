import { api } from '../api.js';
import { crumbs } from '../app.js';
import { loading, markdown } from '../ui.js';

export async function render(view) {
  crumbs([{ label: 'Sobre a solução' }]);
  view.innerHTML = loading();
  const { markdown: md } = await api.about();
  view.innerHTML = `<div class="card"><div class="card-body md" style="padding:32px;max-width:900px">${markdown(md || 'Veja o README.md.')}</div></div>`;
}
