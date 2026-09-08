import { initIntro } from './intro.js';
import { renderAi, renderArchitecture, renderCodeFacts, renderComparison, renderSnapshot, renderTechnologies } from './explorer.js';

const DATA_ROOT = './data';
const files = {
  architecture: `${DATA_ROOT}/auto/architecture.json`,
  technologies: `${DATA_ROOT}/auto/technologies.json`,
  api: `${DATA_ROOT}/auto/api_manifest.json`,
  ai: `${DATA_ROOT}/auto/ai_manifest.json`,
  deployment: `${DATA_ROOT}/auto/deployment.json`,
  database: `${DATA_ROOT}/auto/db_manifest.json`,
  snapshot: `${DATA_ROOT}/auto/build_snapshot.json`,
  curated: `${DATA_ROOT}/curated/content.json`,
};

const loadJson = async (url) => {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`metadata request failed: ${response.status}`);
  return response.json();
};

const status = document.querySelector('#load-status');
const showStatus = (message) => {
  status.textContent = message;
  status.classList.add('show');
  window.setTimeout(() => status.classList.remove('show'), 4200);
};

async function start() {
  try {
    const keys = Object.keys(files);
    const values = await Promise.all(keys.map((key) => loadJson(files[key])));
    const data = Object.fromEntries(keys.map((key, index) => [key, values[index]]));
    initIntro(data.curated.intro_steps);
    renderArchitecture(data.architecture, data.curated);
    renderTechnologies(data.technologies, data.curated);
    renderAi(data.ai);
    renderComparison(data.curated);
    renderCodeFacts(data.api, data.database, data.deployment);
    renderSnapshot(data.snapshot);
  } catch (error) {
    console.error(error);
    document.querySelector('#snapshot-line').textContent = '기술 metadata를 불러오지 못했습니다. CSR 서비스 체험은 계속 사용할 수 있습니다.';
    showStatus('일부 기술 정보를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.');
  }
}

start();
