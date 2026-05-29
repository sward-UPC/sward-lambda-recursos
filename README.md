# sward-lambda-recursos

AWS Lambda del sistema **SWARD** que procesa los metadatos de recursos educativos subidos al almacenamiento.

## Trigger

**Amazon S3** event `ObjectCreated` — se activa cuando un nuevo archivo educativo es subido al bucket de recursos.

## Acción

Extrae y actualiza los metadatos del recurso educativo (tipo, tamaño, duración estimada, etiquetas) en la base de datos de cursos (`cursos_db`).

## Estructura

```
handler.py          # LambdaRecursosHandler.handle_s3_event()
lib/
  db_client.py      # psycopg3 directo (sin ORM)
  logger.py         # Structured JSON logger para CloudWatch
requirements.txt
template.yaml       # AWS SAM template
Makefile            # make deploy | make test | make invoke
```

## Stack

- Python 3.11 · psycopg3 · boto3 · AWS SAM

## Despliegue

```bash
make deploy ENV=staging
```

## Tests

```bash
make test
```

## Proyecto

**TP202610051** — Universidad Peruana de Ciencias Aplicadas (UPC)  
Taller de Proyecto 1 / 2026
