import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const mvpRoot = path.resolve(path.dirname(currentFile), "../../..");
const judgeRoot = path.join(mvpRoot, "frontend/public/judge");
const autoRoot = path.join(judgeRoot, "data/auto");

const read = (relativePath) => fs.readFileSync(path.join(judgeRoot, relativePath), "utf8");
const readJson = (name) => JSON.parse(fs.readFileSync(path.join(autoRoot, name), "utf8"));

test("Judge entry uses hash navigation and the required external MVP CTA", () => {
  const html = read("index.html");
  assert.match(html, /href="#architecture"/);
  assert.match(html, /href="#technology"/);
  assert.match(html, /href="#workflow"/);
  assert.match(html, /id="replay-intro"/);
  assert.match(read("js/intro.js"), /location\.hash === '#intro'/);
  assert.doesNotMatch(html, /href="\/judge\/(?:architecture|technology|workflow)/);
  assert.match(html, /href="\/"[^>]*target="_blank"[^>]*rel="noopener noreferrer"/);
});

test("Every local static dependency referenced by index exists", () => {
  const html = read("index.html");
  const references = [...html.matchAll(/(?:src|href)="\.\/([^"#]+)"/g)].map((match) => match[1]);
  assert.ok(references.length >= 4);
  for (const reference of references) {
    assert.equal(fs.existsSync(path.join(judgeRoot, reference)), true, `missing ${reference}`);
  }
});

test("All seven AUTO manifests parse and expose required evidence", () => {
  const names = [
    "architecture.json",
    "technologies.json",
    "api_manifest.json",
    "ai_manifest.json",
    "deployment.json",
    "db_manifest.json",
    "build_snapshot.json",
  ];
  for (const name of names) assert.doesNotThrow(() => readJson(name), name);

  const architecture = readJson("architecture.json");
  for (const component of architecture.components.filter((item) => item.status === "CURRENT")) {
    assert.ok(component.evidence?.length > 0, `${component.id} lacks evidence`);
  }

  const snapshot = readJson("build_snapshot.json");
  assert.match(snapshot.git_commit, /^[0-9a-f]{40}$/);
  assert.match(snapshot.manifest_hash, /^[0-9a-f]{64}$/);
  assert.ok(snapshot.metadata_generated_at);
});

test("Published Judge files contain no Windows absolute paths or external CDN resources", () => {
  const publishedFiles = [];
  const visit = (directory) => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) visit(absolute);
      else if (/\.(?:html|css|js|json|md)$/.test(entry.name)) publishedFiles.push(absolute);
    }
  };
  visit(judgeRoot);

  for (const file of publishedFiles) {
    const content = fs.readFileSync(file, "utf8");
    assert.doesNotMatch(content, /[A-Za-z]:[\\/](?:Users|Documents|Downloads)[\\/]/, file);
    if (/\.html$/.test(file)) {
      assert.doesNotMatch(content, /<(?:script|link)[^>]+(?:src|href)="https?:\/\//i, file);
    }
  }
});

test("Curated data cannot redefine AUTO technical facts", () => {
  const curated = JSON.parse(read("data/curated/content.json"));
  const forbidden = new Set([
    "version",
    "endpoint",
    "port",
    "dependencies",
    "runtime",
    "source_path",
    "source_paths",
    "artifact",
    "status",
  ]);

  const inspect = (value) => {
    if (Array.isArray(value)) return value.forEach(inspect);
    if (!value || typeof value !== "object") return;
    for (const [key, child] of Object.entries(value)) {
      assert.equal(forbidden.has(key), false, `curated field ${key} overrides AUTO scope`);
      inspect(child);
    }
  };
  inspect(curated);
});
