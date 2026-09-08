const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const badgeClass = (status) => ({
  CURRENT: 'badge-current', PARTIAL: 'badge-partial', EXPERIMENTAL: 'badge-experimental', FUTURE: 'badge-future',
}[status] ?? 'badge-partial');

const cleanTechnology = (value) => String(value ?? '').replace(/\s+/g, ' ').trim();

const detailRows = (component) => {
  const dependencies = component.dependencies?.join(', ') || '없음';
  const sources = (component.source_paths ?? []).map((path) => `<li>${escapeHtml(path)}</li>`).join('');
  return `
    <dl>
      <dt>Runtime</dt><dd>${escapeHtml(component.runtime || '확인되지 않음')}</dd>
      <dt>Port</dt><dd>${component.port ? escapeHtml(component.port) : '내부 module / 해당 없음'}</dd>
      <dt>연결</dt><dd>${escapeHtml(dependencies)}</dd>
      <dt>Source</dt><dd><ul class="source-list">${sources}</ul></dd>
    </dl>`;
};

export function renderArchitecture(manifest, curated) {
  const flow = document.querySelector('#architecture-flow');
  const grid = document.querySelector('#architecture-grid');
  const descriptions = curated.components ?? {};
  const components = manifest.components ?? [];
  const flowOrder = ['frontend', 'nginx', 'general-api', 'ai-api', 'mysql'];
  const byId = Object.fromEntries(components.map((item) => [item.id, item]));
  flow.innerHTML = flowOrder.filter((id) => byId[id]).map((id, index, selected) => {
    const item = byId[id];
    return `${index ? '<span class="flow-arrow" aria-hidden="true">→</span>' : ''}<div class="flow-node"><strong>${escapeHtml(item.friendly_name)}</strong><small>${escapeHtml(item.technologies.join(' · '))}</small></div>`;
  }).join('');

  grid.innerHTML = components.map((component) => {
    const copy = descriptions[component.id] ?? {};
    return `<article class="node-card">
      <button class="node-toggle" type="button" aria-expanded="false">
        <span class="node-topline"><span class="badge ${badgeClass(component.status)}">${escapeHtml(component.status)}</span><span class="node-chevron" aria-hidden="true">⌄</span></span>
        <strong class="node-role">${escapeHtml(component.friendly_name)}</strong>
        <span class="node-tech">${escapeHtml(component.technologies.join(' · '))}</span>
      </button>
      <div class="node-summary" hidden>
        <p>${escapeHtml(copy.simple_description || component.responsibilities?.[0] || '')}</p>
        <p class="node-why">${escapeHtml(copy.why_it_exists || '')}</p>
        <button class="technical-toggle" type="button" aria-expanded="false">기술 상세 보기</button>
        <div class="node-technical" hidden>${detailRows(component)}</div>
      </div>
    </article>`;
  }).join('');

  grid.addEventListener('click', (event) => {
    const nodeButton = event.target.closest('.node-toggle');
    if (nodeButton) {
      const expanded = nodeButton.getAttribute('aria-expanded') === 'true';
      nodeButton.setAttribute('aria-expanded', String(!expanded));
      nodeButton.nextElementSibling.hidden = expanded;
      return;
    }
    const detailButton = event.target.closest('.technical-toggle');
    if (detailButton) {
      const expanded = detailButton.getAttribute('aria-expanded') === 'true';
      detailButton.setAttribute('aria-expanded', String(!expanded));
      detailButton.textContent = expanded ? '기술 상세 보기' : '기술 상세 닫기';
      detailButton.nextElementSibling.hidden = expanded;
    }
  });
}

export function renderTechnologies(manifest, curated) {
  const list = document.querySelector('#technology-list');
  const roles = curated.technology_roles ?? {};
  const aliases = { 'react-dom': 'react', 'react-router-dom': 'react', '@vitejs/plugin-react': 'vite', 'python': 'python', 'nginx': 'nginx' };
  const preferred = ['react', 'typescript', 'vite', 'nginx', 'fastapi', 'uvicorn', 'pydantic', 'httpx', 'openai', 'scikit-learn', 'joblib', 'mysql', 'docker'];
  const all = manifest.technologies ?? [];
  const rows = preferred.flatMap((name) => {
    const match = all.find((item) => item.name.toLowerCase() === name || aliases[item.name.toLowerCase()] === name);
    if (!match || !roles[name]) return [];
    return [{ name, item: match, copy: roles[name] }];
  });
  list.innerHTML = rows.map(({ name, item, copy }) => `
    <div class="technology-row">
      <strong>${escapeHtml(name === 'openai' ? 'OpenAI' : name === 'mysql' ? 'MySQL' : name.charAt(0).toUpperCase() + name.slice(1))}</strong>
      <span class="tech-where">${escapeHtml(copy.where)}</span>
      <span class="tech-role">${escapeHtml(copy.role)}</span>
      <span class="tech-version">${escapeHtml(item.resolved_version || item.declared_version || 'version unverified')}</span>
    </div>`).join('');
}

export function renderAi(aiManifest) {
  const list = document.querySelector('#ai-service-list');
  list.innerHTML = (aiManifest.services ?? []).map((service) => `
    <span class="service-chip">${escapeHtml(service.name)}<small>${escapeHtml(service.implementation_kind)}</small></span>
  `).join('');
  const artifact = aiManifest.ml_artifact ?? {};
  document.querySelector('#artifact-summary').textContent = artifact.hash_matches_code
    ? `${artifact.name} · SHA-256 코드 기대값 일치 · 역직렬화 없이 확인`
    : 'Artifact 상태를 정적 분석만으로 확정하지 못했습니다.';
}

export function renderComparison(curated) {
  const comparison = document.querySelector('#comparison');
  const entries = [curated.comparison.current, curated.comparison.target];
  comparison.innerHTML = entries.map((item, index) => `
    <article class="comparison-card ${index ? 'target' : ''}">
      <span class="badge ${index ? 'badge-target' : 'badge-current'}">${escapeHtml(item.badge)}</span>
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.description)}</p>
      <ol class="comparison-steps">${item.steps.map((step, stepIndex) => `<li data-step="${stepIndex + 1}">${escapeHtml(step)}</li>`).join('')}</ol>
      ${index ? '<p class="comparison-warning">현재 외부 시스템과 연동된 기능이 아닙니다. 실제 서비스 적용 방향으로만 제시합니다.</p>' : ''}
    </article>`).join('');
}

export function renderCodeFacts(api, database, deployment) {
  const facts = [
    { value: api.services?.find((item) => item.component_id === 'general-api')?.endpoints?.length ?? '—', label: 'General API endpoint' },
    { value: api.services?.find((item) => item.component_id === 'ai-api')?.endpoints?.length ?? '—', label: 'AI API endpoint' },
    { value: database.table_count ?? '—', label: '코드에서 확인된 DB table' },
  ];
  document.querySelector('#code-facts').innerHTML = facts.map((item) => `<div class="fact-card"><strong>${escapeHtml(item.value)}</strong><span>${escapeHtml(item.label)}</span></div>`).join('');
}

export function renderSnapshot(snapshot) {
  const commit = snapshot.git_commit === 'unknown' ? 'commit 확인 불가' : snapshot.git_commit.slice(0, 10);
  const generated = snapshot.metadata_generated_at ? new Date(snapshot.metadata_generated_at).toLocaleString('ko-KR') : '생성 시각 확인 불가';
  document.querySelector('#snapshot-line').textContent = `코드 기준 ${commit} · metadata generated at ${generated}`;
}
