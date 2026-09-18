"""Run the current v3.1 diagnosis pipeline against benchmark_v1.0.

The artifact is a privacy-safe structured replay: source turns, evidence text,
and free-text summaries are removed before writing. Provider usage and latency
are retained. API keys are loaded from the local MVP_v3/.env and never logged.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "replay_benchmark").is_dir()), Path.cwd())
BACKEND = ROOT / "MVP_v3/backend"
BENCHMARK = ROOT / "replay_benchmark/fact_context_cases.json"
ENV_FILE = ROOT / "MVP_v3/.env"


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


USAGE: list[dict[str, Any]] = []
RAW_PROVIDER_OUTPUTS: list[dict[str, Any]] = []


def usage_dict(value: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        number = getattr(value, key, None)
        if number is not None:
            result[key] = int(number)
    return result


class TraceResponses:
    def __init__(self, owner: "TraceClient") -> None:
        self.owner = owner

    async def create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        response = await self.owner.client.responses.create(**kwargs)
        call_index = len(USAGE) + 1
        USAGE.append({"call_index": call_index, "model": kwargs.get("model"),
                      "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                      "usage": usage_dict(getattr(response, "usage", None))})
        if hasattr(response, "model_dump"):
            raw = response.model_dump(mode="json")
        elif hasattr(response, "to_dict"):
            raw = response.to_dict()
        else:
            raw = str(response)
        RAW_PROVIDER_OUTPUTS.append({"call_index": call_index, "model": kwargs.get("model"),
                                     "response": raw})
        return response


class TraceClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(*args, **kwargs)
        self.responses = TraceResponses(self)

    async def __aenter__(self) -> "TraceClient":
        await self.client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> Any:
        return await self.client.__aexit__(*args)


def sanitize(value: Any, key: str = "") -> Any:
    blocked = {"text", "evidence_text", "source_text", "quote", "summary", "claims", "demands",
               "manipulation_tactics", "recommended_next_steps", "turns", "observations"}
    if key in blocked:
        return "<REDACTED>" if not isinstance(value, list) else []
    if isinstance(value, dict):
        return {k: sanitize(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item, key) for item in value]
    return value


async def run(args: argparse.Namespace) -> dict[str, Any]:
    USAGE.clear()
    RAW_PROVIDER_OUTPUTS.clear()
    load_local_env()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured in the environment or MVP_v3/.env")
    sys.path.insert(0, str(BACKEND))
    from ai_api.app.domains.diagnosis import audit_agent, context_features, extractor
    from ai_api.app.domains.diagnosis.service import DiagnosisService

    extractor.AsyncOpenAI = TraceClient
    context_features.AsyncOpenAI = TraceClient
    audit_agent.AsyncOpenAI = TraceClient
    cases = json.loads(BENCHMARK.read_text(encoding="utf-8"))["cases"]
    if args.limit:
        cases = cases[: args.limit]
    results = []
    service = DiagnosisService()
    for case in cases:
        case_id = case["case_id"]
        text = "\n".join(turn["text"] for turn in case["turns"])
        before = len(USAGE)
        started = time.perf_counter()
        try:
            diagnosis = await service.analyze(text, case_id=case_id)
            structured = sanitize(diagnosis.model_dump(mode="json"))
            status = "LIVE"
            error = None
        except Exception as exc:
            structured = None
            status = "ERROR"
            error = {"type": type(exc).__name__, "message": str(exc)[:300]}
        calls = USAGE[before:]
        results.append({"case_id": case_id, "status": status, "error": error,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "llm_call_count": len(calls),
                        "usage": {key: sum(item.get("usage", {}).get(key, 0) for item in calls)
                                  for key in ("input_tokens", "output_tokens", "total_tokens")},
                        "structured_output": structured})
        if args.stop_on_error and status == "ERROR":
            break
    return {"schema_version": "v3.1-live-replay.v2", "status": "LIVE_AI_REPLAY",
            "executed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "benchmark": "benchmark_v1.0", "case_count": len(results),
            "api_key_logged": False, "raw_transcript_logged": False,
            "raw_provider_outputs_logged": True,
            "cases": results, "provider_calls": USAGE,
            "raw_provider_outputs": RAW_PROVIDER_OUTPUTS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--raw-output", type=Path, help="Optional separate copy of the provider-raw JSON artifact")
    args = parser.parse_args()
    payload = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.raw_output:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(json.dumps({"schema_version": "v3.1-provider-raw.v1",
                                               "source_output": str(args.output),
                                               "benchmark": payload["benchmark"],
                                               "executed_at": payload["executed_at"],
                                               "provider_calls": payload["provider_calls"],
                                               "raw_provider_outputs": payload["raw_provider_outputs"]},
                                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "case_count": payload["case_count"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
