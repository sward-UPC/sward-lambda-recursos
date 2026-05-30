# PROGRESS — sward-lambda-recursos

## Sprint 4 — 2026-05-29

### Implementado
- [x] handler.py — detecta tipo por extensión, estima tiempo, actualiza resource_metadata en cursos_db
- [x] lib/db_client.py — psycopg2 con context manager
- [x] lib/logger.py — JSON logger CloudWatch
- [x] Tests: 7 casos (PDF, video, error no bloquea, sin records, extensiones, tiempos)
- [x] template.yaml — AWS SAM con S3 trigger + S3ReadPolicy
- [x] GitHub Actions CI
