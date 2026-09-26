// Landing page: ícones, tema, barra de navegação e aviso de demonstração.
import { icon } from './ui.js';

document.querySelectorAll('[data-icon]').forEach((el) => {
  const big = el.classList.contains('brand-mark') && !el.classList.contains('sm');
  el.outerHTML = el.classList.contains('brand-mark')
    ? `<span class="${el.className}">${icon(el.dataset.icon, big ? 20 : 16)}</span>`
    : icon(el.dataset.icon, el.closest('.ficon, .picon, .aicon') ? 20 : 16, el.className);
});

const themeBtn = document.getElementById('themeBtn');
function setTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem('doi.theme', t); } catch { /* ok */ }
  themeBtn.innerHTML = icon(t === 'dark' ? 'sun' : 'moon');
}
setTheme(document.documentElement.getAttribute('data-theme') || 'dark');
themeBtn.addEventListener('click', () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'));

const nav = document.getElementById('lnav');
const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 8);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

fetch('/api/config').then((r) => (r.ok ? r.json() : null)).then((cfg) => {
  if (cfg?.demo_mode) document.getElementById('demoNote').hidden = false;
}).catch(() => {});
