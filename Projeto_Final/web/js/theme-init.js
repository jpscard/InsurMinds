// Aplica o tema salvo antes da página desenhar (evita piscar claro/escuro).
(function () {
  var t = null;
  try { t = localStorage.getItem('doi.theme'); } catch (e) { /* armazenamento indisponível */ }
  if (!t) t = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();
