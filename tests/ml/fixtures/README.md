# API contract fixture

backend_pair.json contains actual HTTP 200 JSON responses from FastAPI TestClient on backend commit acc136ab70b895430ce3e66293df836c66c1b31c, captured 2026-10-11. Requests: GET /api/v1/badan-usaha/BU-0001 and GET /api/v1/badan-usaha/BU-0001/evidence/2025-01. The application used the hash-verified source snapshot and a disposable SQLite database. No auth tokens, review writes, or personal data are included. The ML test verifies these payloads produce the same features as training, and rejects mismatched dataset/company identities.
