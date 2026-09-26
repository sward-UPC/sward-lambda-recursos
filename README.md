# sward-lambda-recursos

AWS Lambda del sistema **SWARD** que registra y enriquece los metadatos de los
recursos educativos a medida que se suben al almacenamiento de cursos.

## Qué hace

Cada vez que se sube un archivo al bucket de recursos, la Lambda:

1. Decodifica la ruta (`key`) del objeto S3.
2. Infiere el **tipo pedagógico** del recurso a partir de su extensión:
   - `video` — `.mp4`, `.avi`, `.mov`, `.webm`
   - `lectura` — `.pdf`, `.docx`, `.doc`, `.txt`, `.html`, `.md`
   - `presentacion` — `.pptx`, `.ppt`
   - `ejercicio` — `.py`, `.ipynb`, `.zip`
   - (sin extensión reconocida → `lectura` por defecto)
3. **Estima el tiempo de estudio** en minutos según el tipo y el tamaño del
   archivo.
4. Actualiza la tabla `resource_metadata` en la base de datos de cursos
   (`competencia` y `tiempo_estimado_min`). Si no hay fila de metadata aún,
   actualiza la `url` del recurso en `resources` como fallback.

El procesamiento es **idempotente** (`COALESCE` + `GREATEST`): reprocesar el
mismo objeto no degrada los datos existentes, lo cual es importante porque las
entregas de eventos S3 son *at-least-once*.

## Trigger

**Amazon S3 → `s3:ObjectCreated:*`** sobre el bucket
`sward-recursos-educativos`. El handler procesa todos los `Records` del evento;
un fallo en un record no bloquea el resto del lote.

Handler: `handler.lambda_handler` (alias de `handle_s3_event`).

## Variables de entorno y secretos

Las credenciales de base de datos se resuelven en runtime desde **AWS Secrets
Manager** (nunca se almacenan en el repo).

| Variable          | Requerida | Descripción                                                  |
|-------------------|-----------|--------------------------------------------------------------|
| `DATABASE_HOST`   | Sí        | Host del Postgres de cursos                                  |
| `DATABASE_PORT`   | No        | Puerto (por defecto `5432`)                                  |
| `DATABASE_NAME`   | Sí        | Nombre de la base de datos                                   |
| `DB_SECRET_ARN`   | Sí        | ARN del secreto con `{ "username", "password" }`            |
| `AWS_REGION`      | No        | Región para el cliente de Secrets Manager (def. `us-east-1`)|
| `LOG_LEVEL`       | No        | Nivel de log (`INFO` por defecto)                           |

Ver `.env.example` para un ejemplo local.

## Estructura

```
handler.py              # Adaptador de ENTRADA: traduce el evento S3 → caso de uso
lib/
  db_client.py          # Adaptador de SALIDA: conexión psycopg2 + Secrets Manager
  logger.py             # Logger JSON para CloudWatch
tests/test_handler.py   # Tests unitarios (lógica pura + cableado del handler)
requirements.txt        # Dependencias de runtime (psycopg2-binary)
requirements-dev.txt    # Dependencias de test (pytest, ruff, moto)
Dockerfile              # Imagen de Lambda basada en public.ecr.aws/lambda/python:3.11
template.yaml           # AWS SAM (trigger S3 + permisos S3/Secrets Manager)
Makefile                # make test | make lint
```

## Stack

Python 3.11 · psycopg2 · boto3 · AWS SAM · empaquetado como imagen de contenedor.

## Build y despliegue (ECR)

La Lambda se empaqueta como **imagen de contenedor**. El pipeline
(`.github/workflows/build-push.yml`, rama `deploy`) construye la imagen y la
publica al registro de la organización.

Build local de la imagen:

```bash
docker build -t sward-lambda-recursos .
```

Despliegue de infraestructura con SAM (parámetros alineados con las variables
de entorno que el código consume):

```bash
sam deploy \
  --parameter-overrides \
    DatabaseHost=<host> \
    DatabaseName=cursos_db \
    DbSecretArn=<arn-del-secreto>
```

## Testear

```bash
make test          # instala requirements-dev y ejecuta pytest
make lint          # ruff check + ruff format --check
```

O directamente:

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Proyecto

**TP202610051** — Universidad Peruana de Ciencias Aplicadas (UPC)
Taller de Proyecto 1 / 2026
