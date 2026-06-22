import json
import os
from contextlib import contextmanager


def _get_db_kwargs() -> dict:
    """Construye los kwargs de conexion psycopg2 en runtime leyendo las
    credenciales desde AWS Secrets Manager."""
    host = os.environ.get("DATABASE_HOST", "")
    port = int(os.environ.get("DATABASE_PORT", "5432"))
    name = os.environ.get("DATABASE_NAME", "")
    secret_arn = os.environ.get("DB_SECRET_ARN", "")

    if not (host and secret_arn):
        raise RuntimeError(
            f"Variables de entorno DB incompletas: DATABASE_HOST={host!r}, DB_SECRET_ARN={secret_arn!r}"
        )

    import boto3

    client = boto3.client(
        "secretsmanager",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    secret = json.loads(client.get_secret_value(SecretId=secret_arn)["SecretString"])

    return {
        "host": host,
        "port": port,
        "dbname": name,
        "user": secret["username"],
        "password": secret["password"],
        "connect_timeout": 10,
    }


@contextmanager
def get_connection():
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError("psycopg2 no disponible.")

    kwargs = _get_db_kwargs()
    conn = psycopg2.connect(**kwargs)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
