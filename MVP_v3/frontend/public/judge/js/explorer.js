const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const statusLabel = (status) => ({
  CURRENT: '현재 구현', PARTIAL: '일부 구현', EXPERIMENTAL: '실험 구현', FUTURE: '향후 연동',
}[status] ?? '확인 필요');

const badgeClass = (status) => ({
  CURRENT: 'badge-current', PARTIAL: 'badge-partial', EXPERIMENTAL: 'badge-experimental', FUTURE: 'badge-future',
}[status] ?? 'badge-partial');

const plainTechnology = (value) => String(value ?? '')
  .replace(/:[0-9].*$/, '')
  .replace(/\s+[0-9].*$/, '')
  .trim();

const displayTechnologies = (component) => {
  const names = (component.technologies ?? []).map(plainTechnology);
  if (component.id === 'frontend') return names.filter((name) => !name.includes('Router')).slice(0, 2).join(' · ');
  if (component.id === 'general-api') return names.filter((name) => ['FastAPI', 'Uvicorn'].includes(name)).join(' · ');
  if (component.id === 'ai-api') return names.filter((name) => name.includes('OpenAI') || name.includes('scikit')).join(' · ');
  return names.slice(0, 2).join(' · ');
};

const routeSummary = (component, api) => {
  const service = (api.services ?? []).find((item) => item.component_id === component.id);
  if (!service) return '별도 공개 route 없음';
  const routes = service.endpoints ?? [];
  const examples = routes.slice(0, 3).map((item) => `${item.method} ${item.path}`).join(', ');
  return `${routes.length}개 route${examples ? ` · 예: ${examples}` : ''}`;
};

const technicalRows = (component, api) => {
  const sources = (component.source_paths ?? []).map((source) => `<li>${escapeHtml(source)}</li>`).join('');
  const evidence = (component.evidence ?? []).map((item) => `<li>${escapeHtml(item.reason)}${item.line ? ` · line ${item.line}` : ''}</li>`).join('');
  return `<dl>
    <dt>정확한 기술</dt><dd>${escapeHtml((component.technologies ?? []).join(' · '))}</dd>
    <dt>Runtime</dt><dd>${escapeHtml(component.runtime || '확인되지 않음')}</dd>
    <dt>내부 Port</dt><dd>${component.port ? escapeHtml(component.port) : '해당 없음'}</dd>
    <dt>연결 대상</dt><dd>${escapeHtml(component.dependencies?.join(', ') || '없음')}</dd>
    <dt>Endpoint</dt><dd>${escapeHtml(routeSummary(component, api))}</dd>
    <dt>Source</dt><dd><ul class="source-list">${sources}</ul></dd>
    <dt>Code evidence</dt><dd><ul class="evidence-list">${evidence}</ul></dd>
  </dl>`;
};

const nodeButton = (component, className = '') => `<button class="architecture-node ${className}" type="button" data-component-id="${escapeHtml(component.id)}" aria-pressed="false">
  <strong>${escapeHtml(component.friendly_name)}</strong>
  <small>${escapeHtml(displayTechnologies(component))}</small>
</button>`;

export function renderArchitecture(manifest, curated, api) {
  const flow = document.querySelector('#architecture-flow');
  const detail = document.querySelector('#architecture-detail');
  const byId = Object.fromEntries((manifest.components ?? []).map((item) => [item.id, item]));
  const main = ['frontend', 'nginx', 'general-api'].map((id) => byId[id]).filter(Boolean);
  const branches = ['ai-api', 'mysql'].map((id) => byId[id]).filter(Boolean);

  flow.innerHTML = `<div class="diagram-main">${main.map((component, index) => `${index ? '<span class="diagram-arrow" aria-hidden="true"><span>→</span></span>' : ''}${nodeButton(component)}`).join('')}</div>
    <div class="diagram-connector" aria-hidden="true"></div>
    <div class="diagram-branches">${branches.map((component) => nodeButton(component)).join('')}</div>`;

  const select = (id) => {
    const component = byId[id];
    if (!component) return;
    flow.querySelectorAll('[data-component-id]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.componentId === id)));
    const copy = curated.components?.[id] ?? {};
    detail.innerHTML = `<article class="role-detail">
      <div class="role-detail-top"><div><h3>${escapeHtml(component.friendly_name)}</h3><p>${escapeHtml(copy.simple_description || component.responsibilities?.[0] || '')}</p></div><span class="badge ${badgeClass(component.status)}">${escapeHtml(statusLabel(component.status))}</span></div>
      <div class="role-meta"><span><strong>작동 위치</strong> ${escapeHtml(copy.where || component.layer)}</span><span><strong>담당 역할</strong> ${escapeHtml(copy.role || component.responsibilities?.join(' · ') || '')}</span><span><strong>주요 기술</strong> ${escapeHtml(displayTechnologies(component))}</span></div>
      <button class="technical-toggle" type="button" aria-expanded="false">기술 상세 보기</button>
      <div class="node-technical" hidden>${technicalRows(component, api)}</div>
    </article>`;
  };

  flow.addEventListener('click', (event) => {
    const button = event.target.closest('[data-component-id]');
    if (button) select(button.dataset.componentId);
  });
  detail.addEventListener('click', (event) => {
    const button = event.target.closest('.technical-toggle');
    if (!button) return;
    const expanded = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!expanded));
    button.textContent = expanded ? '기술 상세 보기' : '기술 상세 닫기';
    button.nextElementSibling.hidden = expanded;
  });
  if (main[0]) select(main[0].id);
}

export function renderApplication(curated) {
  const root = document.querySelector('#application-map');
  const target = curated.target_service;
  const lane = (item) => `<article class="application-lane">
    <div class="lane-heading"><span>${escapeHtml(item.label)}</span><span class="badge badge-target">TARGET SERVICE</span></div>
    <h3>${escapeHtml(item.title)}</h3>
    <div class="flow-stack">${item.steps.map((step, index) => `${index ? '<span class="flow-down" aria-hidden="true">↓</span>' : ''}<div class="flow-step">${escapeHtml(step)}</div>`).join('')}</div>
    <p>${escapeHtml(item.description)}</p>
  </article>`;
  root.innerHTML = `${lane(target.bank)}<div class="shared-bridge" aria-label="두 접점을 연결하는 Shared Case"><strong>Shared Case</strong></div>${lane(target.customer)}
    <p class="target-notice"><span class="badge badge-target">TARGET SERVICE</span><span>${escapeHtml(target.notice)}</span></p>`;
}

export function renderDemo(curated) {
  const root = document.querySelector('#demo-flow');
  root.innerHTML = (curated.demo_flow ?? []).map((step, index) => `<li class="demo-card">
    <div class="demo-image"><img src="./assets/screenshots/${escapeHtml(step.image)}" alt="${escapeHtml(step.alt)}" loading="lazy" /></div>
    <div class="demo-copy"><span>STEP ${index + 1}</span><h3>${escapeHtml(step.title)}</h3><p>${escapeHtml(step.description)}</p></div>
  </li>`).join('');
}

const findTechnology = (all, names) => all.find((item) => names.includes(item.name.toLowerCase()));

export function renderTechnologies(manifest, curated, architecture) {
  const all = manifest.technologies ?? [];
  const roles = curated.technology_roles ?? {};
  const definitions = [
    ['React', 'react', ['react']],
    ['Nginx', 'nginx', ['nginx']],
    ['FastAPI + Uvicorn', 'fastapi', ['fastapi']],
    ['OpenAI', 'openai', ['openai']],
    ['Logistic Regression', 'scikit-learn', ['scikit-learn']],
    ['TF-IDF', 'tf-idf', []],
    ['MySQL', 'mysql', ['mysql']],
    ['Docker', 'docker', ['docker']],
  ];
  const lexicalExists = (architecture.components ?? []).some((item) => item.id === 'lexical-retrieval');
  const rows = definitions.filter(([, key, names]) => (key === 'tf-idf' ? lexicalExists : findTechnology(all, names)) && roles[key]);
  document.querySelector('#technology-list').innerHTML = rows.map(([label, key]) => `<div class="technology-row"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(roles[key].where)}</span><span>${escapeHtml(roles[key].role)}</span></div>`).join('');
}

export function renderDeveloperDetails(architecture, api) {
  const root = document.querySelector('#developer-detail');
  root.innerHTML = (architecture.components ?? []).map((component) => `<details class="component-developer"><summary>${escapeHtml(component.friendly_name)} · ${escapeHtml(statusLabel(component.status))}</summary><div class="node-technical">${technicalRows(component, api)}</div></details>`).join('');
}

export function renderImplementationBoundary(curated, ai, api, database) {
  const root = document.querySelector('#implementation-boundary');
  const classByLabel = { '현재 구현': 'badge-current', '일부 구현': 'badge-partial', '실험 구현': 'badge-experimental', '향후 연동': 'badge-future' };
  const generalRoutes = api.services?.find((item) => item.component_id === 'general-api')?.endpoints?.length ?? '—';
  const aiRoutes = api.services?.find((item) => item.component_id === 'ai-api')?.endpoints?.length ?? '—';
  const cards = (curated.implementation_boundaries ?? []).map((item) => `<article class="boundary-card"><span class="badge ${classByLabel[item.badge] ?? 'badge-partial'}">${escapeHtml(item.badge)}</span><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.description)}</p></article>`);
  cards.push(`<article class="boundary-card"><span class="badge badge-current">코드 기준 상세</span><h3>현재 수집된 구현 정보</h3><ul><li>General API route ${escapeHtml(generalRoutes)}개</li><li>AI API route ${escapeHtml(aiRoutes)}개</li><li>DB table ${escapeHtml(database.table_count ?? '—')}개</li><li>ML artifact: ${escapeHtml(ai.ml_artifact?.status ?? 'UNVERIFIED')}</li></ul></article>`);
  root.innerHTML = cards.join('');
}
