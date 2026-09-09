import { initIntro } from './intro.js';
import {
  renderApplication,
  renderArchitecture,
  renderDemo,
} from './explorer.js';

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
    renderArchitecture(data.architecture, data.curated, data.api);
    renderApplication(data.curated);
    renderDemo(data.curated);
  } catch (error) {
    console.error(error);
    showStatus('일부 안내 정보를 불러오지 못했습니다. CSR MVP 체험은 계속 사용할 수 있습니다.');
  }
}

start();
