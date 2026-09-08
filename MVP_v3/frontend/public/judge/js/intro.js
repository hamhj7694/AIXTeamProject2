const STORAGE_KEY = 'csr_judge_intro_seen';

const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const introVisual = (step) => {
  const items = step.items ?? [];
  const separator = step.visual === 'sequence' || step.visual === 'relationship';
  return `<div class="intro-visual ${escapeHtml(step.visual)}">${items.map((item, index) => `
    ${index && separator ? '<span class="intro-arrow" aria-hidden="true">→</span>' : ''}
    <span class="intro-item">${escapeHtml(item)}</span>
  `).join('')}</div>`;
};

export function initIntro(steps) {
  const dialog = document.querySelector('#intro-dialog');
  const content = document.querySelector('#intro-content');
  const progress = document.querySelector('#intro-progress');
  const back = document.querySelector('#intro-back');
  const next = document.querySelector('#intro-next');
  const start = document.querySelector('#intro-start');
  const skip = document.querySelector('#skip-intro');
  const replay = document.querySelector('#replay-intro');
  if (!dialog || !content || !progress || !Array.isArray(steps) || !steps.length) return;

  let current = 0;
  progress.innerHTML = steps.map((step, index) => `
    <button class="progress-dot" type="button" data-step="${index}" aria-label="${index + 1}단계 ${escapeHtml(step.purpose)}"></button>
  `).join('');

  const render = () => {
    const step = steps[current];
    content.innerHTML = `
      ${step.badge ? `<span class="badge badge-target intro-badge">${escapeHtml(step.badge)}</span>` : ''}
      <p class="eyebrow">${escapeHtml(step.label)}</p>
      <p class="intro-purpose">${escapeHtml(step.purpose)}</p>
      <h2 id="intro-title">${escapeHtml(step.title)}</h2>
      <p class="intro-description">${escapeHtml(step.description)}</p>
      ${introVisual(step)}
    `;
    progress.querySelectorAll('.progress-dot').forEach((dot, index) => {
      dot.classList.toggle('active', index <= current);
      dot.setAttribute('aria-current', index === current ? 'step' : 'false');
    });
    back.hidden = current === 0;
    next.hidden = current === steps.length - 1;
    start.hidden = current !== steps.length - 1;
    (current === steps.length - 1 ? start : next).focus({ preventScroll: true });
  };

  const rememberAndClose = () => {
    try { localStorage.setItem(STORAGE_KEY, '1'); } catch { /* device-local preference is optional */ }
    dialog.close();
    document.body.classList.remove('dialog-open');
    if (location.hash === '#intro') history.replaceState(null, '', `${location.pathname}${location.search}`);
  };
  const open = (reset = true) => {
    if (reset) current = 0;
    render();
    if (!dialog.open) dialog.showModal();
    document.body.classList.add('dialog-open');
  };

  progress.addEventListener('click', (event) => {
    const button = event.target.closest('[data-step]');
    if (!button) return;
    current = Number(button.dataset.step);
    render();
  });
  back.addEventListener('click', () => { current = Math.max(0, current - 1); render(); });
  next.addEventListener('click', () => { current = Math.min(steps.length - 1, current + 1); render(); });
  skip.addEventListener('click', rememberAndClose);
  start.addEventListener('click', rememberAndClose);
  replay?.addEventListener('click', () => open(true));
  dialog.addEventListener('cancel', (event) => { event.preventDefault(); rememberAndClose(); });
  window.addEventListener('hashchange', () => { if (location.hash === '#intro') open(true); });

  let seen = false;
  try { seen = localStorage.getItem(STORAGE_KEY) === '1'; } catch { seen = false; }
  if (!seen || location.hash === '#intro') open(true);
}
