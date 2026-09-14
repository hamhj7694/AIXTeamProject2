import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const VERSION = '1.0.0';
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultRoot = path.resolve(scriptDir, '..', '..');

const posix = (value) => value.split(path.sep).join('/');
const relative = (root, file) => {
  const value = posix(path.relative(root, path.resolve(file)));
  if (!value || value.startsWith('../') || path.isAbsolute(value) || /^[A-Za-z]:/.test(value)) throw new Error('Path must remain inside MVP_v3');
  return value;
};

export const createReader = (root) => {
  const reads = new Set();
  const record = (file) => {
    const rel = relative(root, file);
    const name = path.basename(file);
    if (name.startsWith('.env')) throw new Error(`Denied environment file: ${rel}`);
    reads.add(rel);
    return rel;
  };
  return {
    reads,
    text(file) { record(file); return fs.readFileSync(file, 'utf8'); },
    json(file) { return JSON.parse(this.text(file)); },
    hash(file) { record(file); return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); },
  };
};

const evidence = (source_path, reason, line) => ({ source_path, reason, ...(line ? { line } : {}) });
const lineOf = (text, needle) => {
  const index = text.split(/\r?\n/).findIndex((line) => line.includes(needle));
  return index < 0 ? undefined : index + 1;
};
const canonical = (value) => {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
};
const stableString = (value) => JSON.stringify(canonical(value));
const writeJson = (file, value) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(canonical(value), null, 2)}\n`, 'utf8');
};

const scanEndpoints = (root, reader, rel, componentId) => {
  const text = reader.text(path.join(root, rel));
  const endpoints = [];
  const regex = /^@app\.(get|post|put|patch|delete)\(["']([^"']+)["']([^\n]*)\)\s*\r?\n(?:async\s+)?def\s+([A-Za-z0-9_]+)/gm;
  for (const match of text.matchAll(regex)) {
    endpoints.push({
      component_id: componentId,
      method: match[1].toUpperCase(),
      path: match[2],
      handler: match[4],
      response_model: match[3].match(/response_model\s*=\s*([^,)]+)/)?.[1]?.trim() ?? null,
      status_code: Number(match[3].match(/status_code\s*=\s*(\d+)/)?.[1]) || null,
      source_path: rel,
      line: text.slice(0, match.index).split(/\r?\n/).length,
    });
  }
  return endpoints.sort((a, b) => a.path.localeCompare(b.path) || a.method.localeCompare(b.method));
};

const scanFrontend = (root, reader) => {
  const packageJson = reader.json(path.join(root, 'frontend/package.json'));
  const lock = reader.json(path.join(root, 'frontend/package-lock.json'));
  const vite = reader.text(path.join(root, 'frontend/vite.config.ts'));
  const app = reader.text(path.join(root, 'frontend/src/App.tsx'));
  const client = reader.text(path.join(root, 'frontend/src/api/client.ts'));
  const names = ['react', 'react-dom', 'react-router-dom', 'lucide-react', 'typescript', 'vite', '@vitejs/plugin-react'];
  const declared = { ...packageJson.dependencies, ...packageJson.devDependencies };
  const technologies = names.filter((name) => declared[name]).map((name) => ({
    name,
    declared_version: declared[name],
    resolved_version: lock.packages?.[`node_modules/${name}`]?.version ?? null,
    scope: 'frontend',
    source_paths: ['frontend/package.json', 'frontend/package-lock.json'],
  }));
  const pollingFiles = ['frontend/src/App.tsx', 'frontend/src/pages/CaseRoomPage.tsx', 'frontend/src/pages/CustomerCaseRoomPage.tsx', 'frontend/src/components/EditableContext.tsx'];
  const polling = pollingFiles.flatMap((rel) => {
    const text = rel.endsWith('App.tsx') ? app : reader.text(path.join(root, rel));
    return text.split(/\r?\n/).flatMap((line, index) => line.includes('setInterval') && line.match(/,\s*(\d+)\s*\)/)
      ? [{ interval_ms: Number(line.match(/,\s*(\d+)\s*\)/)[1]), source_path: rel, line: index + 1 }]
      : []);
  });
  return {
    technologies,
    routes: [...new Set([...app.matchAll(/<Route\s+path=["']([^"']+)/g)].map((item) => item[1]))].sort(),
    polling: polling.sort((a, b) => a.source_path.localeCompare(b.source_path) || a.line - b.line),
    build_command: packageJson.scripts?.build ?? null,
    dev_server: { port: Number(vite.match(/port:\s*(\d+)/)?.[1]) || null, api_proxy_target: vite.match(/target:\s*['"]([^'"]+)/)?.[1] ?? null },
    api_base: { environment_variable: client.includes('VITE_API_BASE_URL') ? 'VITE_API_BASE_URL' : null, default: client.includes("|| ''") ? 'same-origin' : 'unverified' },
    public_directory: 'frontend/public',
    evidence: [
      evidence('frontend/package.json', 'Frontend dependency and build scripts'),
      evidence('frontend/vite.config.ts', 'Vite development server and API proxy', lineOf(vite, 'server:')),
      evidence('frontend/src/App.tsx', 'React routes and polling', lineOf(app, '<Routes>')),
      evidence('frontend/src/api/client.ts', 'Same-origin API base with optional VITE_API_BASE_URL', lineOf(client, 'VITE_API_BASE_URL')),
    ],
  };
};

const scanDeployment = (root, reader) => {
  const compose = reader.text(path.join(root, 'docker-compose.yml'));
  const nginx = reader.text(path.join(root, 'frontend/nginx.conf'));
  const dockerfiles = ['frontend/Dockerfile', 'backend/Dockerfile.general-api', 'backend/Dockerfile.ai-api'].map((rel) => {
    const text = reader.text(path.join(root, rel));
    return {
      source_path: rel,
      images: [...text.matchAll(/^FROM\s+([^\s]+)(?:\s+AS\s+[^\s]+)?/gmi)].map((item) => item[1]),
      exposed_ports: [...text.matchAll(/^EXPOSE\s+(\d+)/gmi)].map((item) => Number(item[1])),
    };
  });
  const serviceNames = [...compose.matchAll(/^  ([A-Za-z0-9_-]+):$/gm)].map((item) => item[1]).filter((name) => !['volumes'].includes(name));
  const services = serviceNames.map((id, index) => {
    const start = compose.indexOf(`  ${id}:`);
    const end = index + 1 < serviceNames.length ? compose.indexOf(`  ${serviceNames[index + 1]}:`, start + 1) : compose.indexOf('\nvolumes:', start);
    const block = compose.slice(start, end < 0 ? undefined : end);
    return {
      id,
      image: block.match(/^    image:\s*([^\s]+)/m)?.[1] ?? null,
      dockerfile: block.match(/^      dockerfile:\s*([^\s]+)/m)?.[1] ?? null,
      ports: [...block.matchAll(/^      -\s*["']?([^\r\n"']+:[^\r\n"']+)["']?$/gm)].map((item) => item[1]).filter((item) => item.includes(':')),
      volumes: [...block.matchAll(/^      -\s*([^\r\n]+)$/gm)].map((item) => item[1].trim()).filter((item) => item.includes(':/')),
      healthcheck: block.includes('healthcheck:'),
      environment_variables: [...block.matchAll(/^      ([A-Z][A-Z0-9_]*):/gm)].map((item) => item[1]).sort(),
    };
  });
  return {
    services,
    dockerfiles,
    nginx: {
      listen_port: Number(nginx.match(/\blisten\s+(\d+)/)?.[1]) || null,
      static_root: nginx.match(/\broot\s+([^;]+);/)?.[1]?.trim() ?? null,
      api_proxy: nginx.match(/proxy_pass\s+([^;]+);/)?.[1]?.trim() ?? null,
      spa_fallback: nginx.match(/try_files\s+([^;]+);/)?.[1]?.trim() ?? null,
      source_path: 'frontend/nginx.conf',
    },
    evidence: [
      evidence('docker-compose.yml', 'Docker Compose services, ports, volumes and healthchecks'),
      evidence('frontend/nginx.conf', 'Production static root, API proxy and SPA fallback', lineOf(nginx, 'root ')),
      ...dockerfiles.map((item) => evidence(item.source_path, 'Container runtime image and exposed port')),
    ],
  };
};

const scanDatabase = (root, reader) => {
  const baseRel = 'database/01_mysql_csr_schema.sql';
  const base = reader.text(path.join(root, baseRel));
  const migrationDir = path.join(root, 'backend/migrations');
  const names = fs.readdirSync(migrationDir).filter((name) => name.endsWith('.sql')).sort();
  const tableRegex = /CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?([A-Za-z0-9_]+)`?/gi;
  const triggerRegex = /CREATE\s+TRIGGER\s+`?([A-Za-z0-9_]+)`?/gi;
  const tables = new Set([...base.matchAll(tableRegex)].map((item) => item[1]));
  const triggers = new Set([...base.matchAll(triggerRegex)].map((item) => item[1]));
  const migrations = names.map((name) => {
    const rel = `backend/migrations/${name}`;
    const text = reader.text(path.join(root, rel));
    const createdTables = [...text.matchAll(tableRegex)].map((item) => item[1]).sort();
    const createdTriggers = [...text.matchAll(triggerRegex)].map((item) => item[1]).sort();
    createdTables.forEach((item) => tables.add(item));
    createdTriggers.forEach((item) => triggers.add(item));
    return { name, source_path: rel, created_tables: createdTables, trigger_count: createdTriggers.length, has_alter_table: /\bALTER\s+TABLE\b/i.test(text) };
  });
  const markers = [...base.matchAll(/\('([^']+\.sql)'\)/g)].map((item) => item[1]).sort();
  return {
    engine: 'MySQL', base_schema: baseRel, tables: [...tables].sort(), table_count: tables.size,
    migrations, migration_count: migrations.length, base_schema_migration_markers: markers,
    marker_gaps: names.filter((name) => !markers.includes(name)), trigger_count: triggers.size,
    evidence: [evidence(baseRel, 'New database baseline schema and migration markers'), evidence('backend/migrations/', 'Additive migration files discovered by filename')],
  };
};

const scanAi = (root, reader, endpoints) => {
  const adapterRel = 'backend/ai_api/app/domains/diagnosis/model_adapter.py';
  const adapter = reader.text(path.join(root, adapterRel));
  const retrievalRel = 'backend/general_api/app/domains/cases/case_retrieval.py';
  const retrievalText = reader.text(path.join(root, retrievalRel));
  const workflowRel = 'backend/ai_api/app/domains/case_support/workflow.py';
  const workflow = reader.text(path.join(root, workflowRel));
  const snapshotRel = 'backend/ai_api/app/domains/case_support/case_snapshot_adapter.py';
  reader.text(path.join(root, snapshotRel));
  const snapshotKind = !reader.text(path.join(root, snapshotRel)).includes('AsyncOpenAI') && workflow.includes('사용하지 않는다')
    ? 'RULE_BASED_PROJECTION' : 'UNVERIFIED';
  const definitions = [
    ['text-analysis', 'Text Analysis', 'ai-api', '/ai/analyze/text', 'LLM_ML_HYBRID', 'backend/ai_api/app/domains/diagnosis/service.py'],
    ['window-analysis', 'Window Analysis', 'ai-api', '/ai/analyze/windows', 'LLM_ML_HYBRID', 'backend/ai_api/app/domains/diagnosis/window_ai/service.py'],
    ['feature-extraction', 'Feature Extraction', 'ai-api', '/ai/features/extract', 'STRUCTURED_FEATURE', 'backend/ai_api/app/domains/diagnosis/features.py'],
    ['risk-prediction', 'Risk Prediction', 'ai-api', '/ai/risk/predict', 'ML', adapterRel],
    ['case-support-snapshot', 'Case Support Snapshot', 'ai-api', '/ai/case-support/snapshot', snapshotKind, snapshotRel],
    ['case-copilot', 'Case Copilot', 'ai-api', '/ai/case-copilot/replies', 'LLM', 'backend/ai_api/app/domains/case_support/copilot_service.py'],
    ['work-card', 'Work Card', 'ai-api', '/ai/work-cards/generate', 'LLM', 'backend/ai_api/app/domains/case_support/work_card_service.py'],
    ['final-report', 'Final Report', 'ai-api', '/ai/final-reports/generate', 'LLM', 'backend/ai_api/app/domains/case_support/final_report_service.py'],
    ['customer-support', 'Customer Support', 'general-api', '/api/cases/{case_id}/ai/customer-replies', 'LLM_ORCHESTRATION', 'backend/ai_api/app/domains/case_support/copilot_service.py'],
  ];
  const services = definitions.flatMap(([id, name, component, endpointPath, kind, implementation]) => {
    const endpoint = endpoints.find((item) => item.component_id === component && item.path === endpointPath);
    if (!endpoint || !fs.existsSync(path.join(root, implementation))) return [];
    reader.text(path.join(root, implementation));
    return [{
      id, name, component_id: component, endpoint: endpointPath, method: endpoint.method, implementation_kind: kind,
      status: 'CURRENT', human_review: !['window-analysis', 'feature-extraction', 'risk-prediction'].includes(id),
      source_paths: [...new Set([endpoint.source_path, implementation])].sort(),
      evidence: [evidence(endpoint.source_path, `${endpoint.method} ${endpointPath}`, endpoint.line), evidence(implementation, `${kind} implementation`)],
    }];
  }).sort((a, b) => a.id.localeCompare(b.id));
  const filename = adapter.match(/MODEL_FILENAME\s*=\s*["']([^"']+)/)?.[1] ?? null;
  const expected = adapter.match(/EXPECTED_SHA256\s*=\s*["']([a-fA-F0-9]{64})/)?.[1]?.toLowerCase() ?? null;
  const artifactRel = filename ? `backend/ai_api/models/${filename}` : null;
  const actual = artifactRel && fs.existsSync(path.join(root, artifactRel)) ? reader.hash(path.join(root, artifactRel)) : null;
  return {
    services,
    retrieval: {
      id: 'case-lexical-retrieval', name: 'Case-scoped lexical retrieval', component_id: 'general-api',
      status: retrievalText.includes('class CaseRetriever') ? 'CURRENT' : 'UNVERIFIED', implementation_kind: 'TF_IDF_CHARACTER_NGRAM',
      consumer: 'ai-api', source_paths: [retrievalRel], evidence: [evidence(retrievalRel, 'Authorized Case-local character n-gram retrieval', lineOf(retrievalText, 'class CaseRetriever'))],
    },
    ml_artifact: {
      name: filename, source_path: artifactRel, sha256: actual, expected_sha256: expected, hash_matches_code: Boolean(actual && expected && actual === expected),
      required_sklearn_version: adapter.match(/sklearn\.__version__\s*!=\s*["']([^"']+)/)?.[1] ?? null,
      status: filename?.includes('EXPERIMENTAL') ? 'EXPERIMENTAL' : 'UNVERIFIED', inspection: 'FILE_METADATA_AND_SHA256_ONLY',
      evidence: [evidence(adapterRel, 'Artifact filename, expected hash and runtime guard'), ...(artifactRel ? [evidence(artifactRel, 'Artifact SHA-256 calculated without deserialization')] : [])],
    },
    unimplemented_domains: ['knowledge', 'voice'].filter((name) => !fs.readdirSync(path.join(root, `backend/ai_api/app/domains/${name}`)).some((file) => file.endsWith('.py')))
      .map((name) => ({ name, status: 'UNVERIFIED', reason: 'No Python implementation files' })),
    safety_facts: {
      case_support_snapshot: snapshotKind, lexical_retrieval_owner: 'general-api',
      raw_input_storage_detected: reader.text(path.join(root, 'database/01_mysql_csr_schema.sql')).includes('input_text'),
      inactive_case_brief_llm_path: workflow.includes('LLM 보강 경로') && workflow.includes('사용하지 않는다'),
    },
  };
};

const backendTechnologies = (root, reader, deployment) => {
  const rel = 'backend/requirements.txt';
  const requirements = reader.text(path.join(root, rel)).split(/\r?\n/).map((line) => line.trim()).filter((line) => line && !line.startsWith('#'))
    .map((line) => {
      const match = line.match(/^([A-Za-z0-9_.-]+)(.*)$/);
      return { name: match[1], declared_version: match[2] || null, resolved_version: null, scope: 'backend', source_paths: [rel] };
    });
  const runtimes = deployment.dockerfiles.flatMap((item) => item.images.map((image) => {
    const [name, version = null] = image.split(':');
    return { name, declared_version: version, resolved_version: version, scope: 'container-runtime', source_paths: [item.source_path] };
  }));
  const mysqlImage = deployment.services.find((item) => item.id === 'mysql')?.image;
  if (mysqlImage) {
    const [name, version = null] = mysqlImage.split(':');
    runtimes.push({ name, declared_version: version, resolved_version: version, scope: 'database-runtime', source_paths: ['docker-compose.yml'] });
  }
  if (deployment.services.length) {
    runtimes.push({ name: 'docker', declared_version: null, resolved_version: null, scope: 'container-orchestration', source_paths: ['docker-compose.yml'] });
  }
  return [...requirements, ...runtimes].sort((a, b) => a.scope.localeCompare(b.scope) || a.name.localeCompare(b.name));
};

const component = (id, friendly_name, layer, technologies, runtime, status, responsibilities, dependencies, source_paths, componentEvidence, port = null) => {
  if (status === 'CURRENT' && !componentEvidence.length) throw new Error(`CURRENT component lacks evidence: ${id}`);
  return { id, friendly_name, layer, technologies, runtime, port, status, responsibilities, dependencies, source_paths: [...new Set(source_paths)].sort(), evidence: componentEvidence };
};

const architecture = (frontend, ai, database, deployment) => {
  const dockerfile = (source) => deployment.dockerfiles.find((item) => item.source_path === source) ?? { images: [], exposed_ports: [] };
  const frontendDocker = dockerfile('frontend/Dockerfile');
  const generalDocker = dockerfile('backend/Dockerfile.general-api');
  const aiDocker = dockerfile('backend/Dockerfile.ai-api');
  const image = (item, prefix) => item.images.find((value) => value.startsWith(`${prefix}:`)) ?? `${prefix}:unverified`;
  const generalPort = generalDocker.exposed_ports[0] ?? null;
  const aiPort = aiDocker.exposed_ports[0] ?? null;
  const mysqlImage = deployment.services.find((item) => item.id === 'mysql')?.image ?? 'mysql:unverified';
  const versions = Object.fromEntries(frontend.technologies.map((item) => [item.name, item.resolved_version ?? item.declared_version]));
  return ({
  manifest_version: VERSION,
  manifest_type: 'architecture',
  components: [
    component('frontend', '사용자 화면', 'presentation', [`React ${versions.react ?? 'unverified'}`, `TypeScript ${versions.typescript ?? 'unverified'}`, `React Router ${versions['react-router-dom'] ?? 'unverified'}`], 'Browser', 'CURRENT', ['은행·고객 화면', 'Shared Case 상호작용'], ['nginx', 'general-api'], ['frontend/src/App.tsx', 'frontend/package.json'], [evidence('frontend/src/App.tsx', 'BrowserRouter routes and user workspaces'), evidence('frontend/package-lock.json', 'Resolved frontend versions')]),
    component('nginx', '웹 서비스 입구', 'web-entry', [image(frontendDocker, 'nginx')], image(frontendDocker, 'nginx'), 'CURRENT', ['정적 파일 제공', 'SPA fallback', '/api reverse proxy'], ['frontend', 'general-api'], ['frontend/nginx.conf', 'frontend/Dockerfile'], [evidence('frontend/nginx.conf', 'Production static root and API proxy')], deployment.nginx.listen_port),
    component('general-api', '서비스 제어', 'service', ['FastAPI', 'Uvicorn', 'Pydantic', 'HTTPX'], image(generalDocker, 'python'), 'CURRENT', ['공개 REST API', 'Case 상태·DB transaction', 'AI 호출 조정'], ['ai-api', 'mysql', 'lexical-retrieval'], ['backend/general_api/app/main.py', 'backend/general_api/app/domains/cases/mysql_repository.py'], [evidence('backend/general_api/app/main.py', 'General API FastAPI routes'), evidence('backend/general_api/app/domains/cases/mysql_repository.py', 'MySQL persistence and transactions')], generalPort),
    component('lexical-retrieval', '사건 근거 검색', 'service-module', ['TF-IDF character n-gram', 'Python'], 'General API process', ai.retrieval.status, ['같은 Case에서 허용된 근거 선별', '고객·은행 공개 범위 분리'], ['general-api', 'ai-api'], ai.retrieval.source_paths, ai.retrieval.evidence),
    component('ai-api', 'AI 지원', 'ai-service', ['FastAPI', 'OpenAI SDK', 'scikit-learn'], image(aiDocker, 'python'), 'CURRENT', ['통화 분석', 'Case Copilot', '업무 카드·보고서 생성'], ['ml-engine'], ['backend/ai_api/app/main.py', 'backend/ai_api/app/domains/'], [evidence('backend/ai_api/app/main.py', 'AI API routes backed by domain services')], aiPort),
    component('ml-engine', '위험 확률 계산', 'ml', ['scikit-learn', 'joblib', 'Logistic model'], `scikit-learn ${ai.ml_artifact.required_sklearn_version ?? 'unverified'}`, ai.ml_artifact.status, ['Window feature vector 추론', 'predict_proba 위험 확률'], ['ai-api'], [ai.ml_artifact.source_path, 'backend/ai_api/app/domains/diagnosis/model_adapter.py'].filter(Boolean), ai.ml_artifact.evidence),
    component('mysql', 'Shared Case Data', 'data', [mysqlImage], mysqlImage, 'CURRENT', ['Shared Case 영속 상태', '메시지·질문·검증·업무·보고 저장'], ['general-api'], [database.base_schema, 'backend/migrations/'], database.evidence, mysqlImage === 'mysql:unverified' ? null : 3306),
    component('docker-runtime', '서비스 실행환경', 'runtime', ['Docker Compose', 'Docker'], 'Containers', 'CURRENT', ['Frontend·General API·AI API·MySQL 실행', '내부 네트워크·volume 구성'], ['nginx', 'general-api', 'ai-api', 'mysql'], ['docker-compose.yml'], [evidence('docker-compose.yml', 'Four-service runtime')]),
  ].sort((a, b) => a.id.localeCompare(b.id)),
  edges: [
    ['frontend', 'nginx', 'HTTP', 'request', 'same-origin /api'],
    ['nginx', 'general-api', 'HTTP_PROXY', 'forward', generalPort ? `/api → :${generalPort}` : '/api → General API'],
    ['general-api', 'lexical-retrieval', 'IN_PROCESS', 'query', 'authorized Case records'],
    ['lexical-retrieval', 'ai-api', 'CONTEXT', 'input', 'selected retrieved_context'],
    ['general-api', 'ai-api', 'HTTP', 'request', aiPort ? `internal AI API :${aiPort}` : 'internal AI API'],
    ['ai-api', 'ml-engine', 'IN_PROCESS', 'inference', 'feature vector → predict_proba'],
    ['general-api', 'mysql', 'SQL', 'read_write', 'transactional persistence'],
  ].map(([source, target, type, direction, label]) => ({ source, target, type, direction, label })).sort((a, b) => a.source.localeCompare(b.source) || a.target.localeCompare(b.target)),
  });
};

const validate = (manifest, schema) => {
  for (const key of schema.required ?? []) if (!(key in manifest)) throw new Error(`Missing schema field: ${key}`);
  if (!schema.properties.manifest_type.enum.includes(manifest.manifest_type)) throw new Error(`Unknown manifest type: ${manifest.manifest_type}`);
  const rule = (schema.allOf ?? []).find((item) => item.if?.properties?.manifest_type?.const === manifest.manifest_type);
  for (const key of rule?.then?.required ?? []) if (!(key in manifest)) throw new Error(`${manifest.manifest_type} missing ${key}`);
};

export function generate({ root = defaultRoot, output, generatedAt } = {}) {
  root = path.resolve(root);
  const allowed = path.join(root, 'frontend/public/judge/data/auto');
  output = path.resolve(output ?? allowed);
  if (output !== path.resolve(allowed) && !posix(output).includes('judge-explorer-test-')) throw new Error('Output path is not allowed');
  const reader = createReader(root);
  const frontend = scanFrontend(root, reader);
  const generalEndpoints = scanEndpoints(root, reader, 'backend/general_api/app/main.py', 'general-api');
  const aiEndpoints = scanEndpoints(root, reader, 'backend/ai_api/app/main.py', 'ai-api');
  const endpoints = [...generalEndpoints, ...aiEndpoints];
  const deployment = scanDeployment(root, reader);
  const database = scanDatabase(root, reader);
  const ai = scanAi(root, reader, endpoints);
  const manifests = {
    'architecture.json': architecture(frontend, ai, database, deployment),
    'technologies.json': { manifest_version: VERSION, manifest_type: 'technologies', technologies: [...frontend.technologies, ...backendTechnologies(root, reader, deployment)].sort((a, b) => a.scope.localeCompare(b.scope) || a.name.localeCompare(b.name)), frontend_runtime: frontend },
    'api_manifest.json': { manifest_version: VERSION, manifest_type: 'api', services: [{ component_id: 'general-api', source_path: 'backend/general_api/app/main.py', endpoints: generalEndpoints }, { component_id: 'ai-api', source_path: 'backend/ai_api/app/main.py', endpoints: aiEndpoints }], endpoints: endpoints.sort((a, b) => a.component_id.localeCompare(b.component_id) || a.path.localeCompare(b.path) || a.method.localeCompare(b.method)) },
    'ai_manifest.json': { manifest_version: VERSION, manifest_type: 'ai', ...ai },
    'deployment.json': { manifest_version: VERSION, manifest_type: 'deployment', ...deployment },
    'db_manifest.json': { manifest_version: VERSION, manifest_type: 'database', ...database },
  };
  const schema = reader.json(path.join(root, 'tools/judge_explorer/schemas/manifest.schema.json'));
  Object.values(manifests).forEach((item) => validate(item, schema));
  let commit = 'unknown'; let dirty = null;
  try {
    commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
    dirty = Boolean(execFileSync('git', ['status', '--short', '--untracked-files=all'], { cwd: root, encoding: 'utf8' }).trim());
  } catch { /* Git metadata is optional and never promoted to CURRENT evidence. */ }
  const hash = crypto.createHash('sha256').update(stableString(manifests)).digest('hex');
  manifests['build_snapshot.json'] = {
    manifest_version: VERSION, manifest_type: 'build_snapshot', git_commit: commit,
    metadata_generated_at: generatedAt ?? new Date().toISOString(), manifest_hash: hash, hash_algorithm: 'sha256',
    hash_scope: Object.keys(manifests).sort(), volatile_fields_excluded_from_hash: ['metadata_generated_at', 'git_commit', 'working_tree_dirty'],
    working_tree_dirty: dirty, scanner_version: VERSION,
  };
  validate(manifests['build_snapshot.json'], schema);
  Object.entries(manifests).sort(([a], [b]) => a.localeCompare(b)).forEach(([name, value]) => writeJson(path.join(output, name), value));
  return { manifests, readPaths: [...reader.reads].sort() };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const { manifests, readPaths } = generate();
  process.stdout.write(`${JSON.stringify({
    output: 'frontend/public/judge/data/auto', files: Object.keys(manifests).sort(),
    read_file_count: readPaths.length, manifest_hash: manifests['build_snapshot.json'].manifest_hash,
  }, null, 2)}\n`);
}
