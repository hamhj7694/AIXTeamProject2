"""Executed in a copied application with its own freshly installed environment."""
import argparse
import json
import os
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forbidden-root", required=True)
    args = parser.parse_args()
    allowed = Path(__file__).resolve().parents[2]
    forbidden = Path(args.forbidden_root).resolve()
    blocked_reads, blocked_network = [], []

    def audit(event, arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            blocked_network.append(event)
            raise PermissionError("Network disabled during isolated inference")
        if event in {"open", "os.listdir", "os.scandir", "os.chdir"} and arguments:
            raw = arguments[0]
            if isinstance(raw, (str, bytes, os.PathLike)):
                candidate = Path(os.fsdecode(raw)).resolve()
                if candidate.is_relative_to(forbidden) and not candidate.is_relative_to(allowed):
                    blocked_reads.append(event)
                    raise PermissionError("Original workspace reads disabled during isolated inference")

    sys.addaudithook(audit)
    # Prove the guards with synthetic audit events, without opening an external file.
    for event, arguments in (("open", (str(forbidden / "audit-probe"), "r", 0)),
                             ("socket.connect", (None, ("127.0.0.1", 1)))):
        try:
            sys.audit(event, *arguments)
        except PermissionError:
            pass
        else:
            raise RuntimeError("Isolation guard did not reject the probe")
    blocked_reads.clear()
    blocked_network.clear()

    from backend.config import ROOT
    from backend.ai_api.app.domains.diagnosis import model_adapter
    from backend.ai_api.app.domains.diagnosis.preflight import model_preflight
    import sklearn
    import pandas
    import joblib

    assert ROOT == allowed
    assert Path(sys.prefix).resolve() == allowed / ".venv"
    for module in (model_adapter, sklearn, pandas, joblib):
        assert Path(module.__file__).resolve().is_relative_to(allowed)
    result = model_preflight()
    assert not blocked_reads and not blocked_network
    print(json.dumps({"passed": True, "guard_self_test": "PASS", "fresh_venv": True,
                      "blocked_external_reads": len(blocked_reads), "blocked_network_attempts": len(blocked_network),
                      "ml": result.model_dump(mode="json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
