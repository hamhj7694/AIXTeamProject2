from typing import Literal

from pydantic import BaseModel, ConfigDict


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: Literal["csr-general-api", "csr-ai-api"]
    status: Literal["ok"] = "ok"
    contract_version: Literal["v4.health.1"] = "v4.health.1"


class Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: Literal["csr-general-api", "csr-ai-api"]
    ready: bool
    checks: dict[str, str]
