param(
  [string]$V30Worktree = "..\AIXTeamProject2_v3_0_baseline",
  [string]$OutputDirectory = "replay_benchmark\results\v3_0_live_ai_external"
)

$ErrorActionPreference = "Stop"
$repo = (Get-Location).Path
$v30 = (Resolve-Path $V30Worktree).Path
$benchmark = Join-Path $repo "replay_benchmark"
$expectedCommit = "071fb512ce42a570b0bcf585041eac6f31c2fb1c"
$python = Join-Path $repo "MVP_v3\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$head = (& git -c "safe.directory=$v30" -C $v30 rev-parse HEAD).Trim()
if ($head -ne $expectedCommit) { throw "STOP: v3.0 worktree HEAD mismatch: $head" }
if (-not $env:OPENAI_API_KEY) { throw "LIVE_AI_BLOCKED: OPENAI_API_KEY is not present in the process environment." }

$hashes = @{
  "fact_context_cases.json" = "ef6ffeadb23d688074d6b5a2edbbb2a5aca8976bd7968c813eb9659ab9b05166"
  "chat_prompts.json" = "2f35e3de88fe669a0953d365b8214e784af9b3743510074a3819bd6c08339ba1"
  "question_states.json" = "9e41ec3c016d3ccf9fe2abee44793340e7052eb0baff7fce6e6bea6334d8aa3e"
  "rag_queries.json" = "f1d0c7b8f5392b3b33671a2c37b96b78b0ec3cc4aa9bb6fd3d48ac829cf372f4"
  "e2e_cases.json" = "b916a2e44795144e04c31d9aff120d6b3fc670973c02157c0b83ee09c287913d"
}
foreach ($name in $hashes.Keys) {
  $actual = (Get-FileHash (Join-Path $benchmark $name) -Algorithm SHA256).Hash.ToLower()
  if ($actual -ne $hashes[$name]) { throw "BENCHMARK_HASH_MISMATCH: $name" }
}
$evaluator = (Get-FileHash (Join-Path $benchmark "evaluator.py") -Algorithm SHA256).Hash.ToLower()
if ($evaluator -ne "ffff15e820aa6dd3668552bd8799d2deecc996101c9e5806adfc80186d744afc") { throw "BENCHMARK_HASH_MISMATCH: evaluator.py" }

$out = Join-Path $repo $OutputDirectory
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:PYTHONPATH = Join-Path $v30 "MVP_v3\backend"
$env:CSR_REPLAY_OUTPUT = $out
$env:CSR_REPLAY_BENCHMARK = $benchmark

& $python (Join-Path $benchmark "run_v3_0_live_ai.py") --v30 $v30 --benchmark $benchmark --output $out
if ($LASTEXITCODE -ne 0) { throw "Live AI replay failed with exit code $LASTEXITCODE" }
Write-Output "Replay output: $out"
