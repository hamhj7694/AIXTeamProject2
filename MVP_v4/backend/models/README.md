# Approved local ML artifact · P0-006

File: WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl (6658 bytes).
SHA-256: 662db2a9351dc4ca2c453776ae6f45750e465234cc9abcecc65b58a6b047c5fc.
Model status: EXPERIMENTAL_SAMPLE; version: 12_07_recall_first_v1.0.
Runtime: scikit-learn 1.6.1, pinned dependencies in backend/requirements.txt.
The 23 model features, 0.95 threshold and guardrail settings come from the unchanged bundle.

The adapter loads only this internal artifact. It verifies the hash on every load request,
then deserializes those exact verified bytes (cached). No path override is accepted.
Provenance: docs/evidence/model-port-manifest.json; actual inference: docs/evidence/model_preflight.json.
Synthetic probes verify execution and guardrails, not model accuracy or operational approval.
