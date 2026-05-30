import logging
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EXTENSION_TIPO_MAP = {
    ".mp4": "video",
    ".avi": "video",
    ".mov": "video",
    ".webm": "video",
    ".pdf": "lectura",
    ".docx": "lectura",
    ".doc": "lectura",
    ".txt": "lectura",
    ".pptx": "presentacion",
    ".ppt": "presentacion",
    ".py": "ejercicio",
    ".ipynb": "ejercicio",
    ".zip": "ejercicio",
    ".html": "lectura",
    ".md": "lectura",
}


def handle_s3_event(event: dict, context) -> dict:
    """Trigger: S3 ObjectCreated — actualiza metadatos del recurso en cursos_db."""
    records = event.get("Records", [])
    procesados = 0

    for record in records:
        try:
            s3_info = record.get("s3", {})
            bucket = s3_info.get("bucket", {}).get("name", "")
            key = urllib.parse.unquote_plus(s3_info.get("object", {}).get("key", ""))
            size_bytes = s3_info.get("object", {}).get("size", 0)

            logger.info(
                "Procesando recurso | bucket=%s | key=%s | size=%d",
                bucket,
                key,
                size_bytes,
            )
            _actualizar_metadata(bucket, key, size_bytes)
            procesados += 1
        except Exception as e:
            logger.error("Error procesando evento S3 | error=%s", e)

    return {"procesados": procesados}


def _actualizar_metadata(bucket: str, key: str, size_bytes: int) -> None:
    from lib.db_client import get_connection

    nombre_archivo = key.split("/")[-1]
    extension = (
        "." + nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    )
    tipo = EXTENSION_TIPO_MAP.get(extension, "lectura")
    tiempo_estimado = _estimar_tiempo(tipo, size_bytes)
    s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE resource_metadata
                SET competencia = COALESCE(NULLIF(competencia, ''), %s),
                    tiempo_estimado_min = GREATEST(tiempo_estimado_min, %s)
                WHERE recurso_id IN (
                    SELECT id FROM resources WHERE s3_key = %s
                )
            """,
                (tipo, tiempo_estimado, key),
            )

            if cur.rowcount == 0:
                cur.execute(
                    """
                    UPDATE resources SET url = %s WHERE s3_key = %s
                """,
                    (s3_url, key),
                )

        conn.commit()
    logger.info(
        "Metadata actualizada | key=%s | tipo=%s | tiempo=%d min",
        key,
        tipo,
        tiempo_estimado,
    )


def _estimar_tiempo(tipo: str, size_bytes: int) -> int:
    """Estima tiempo de estudio en minutos según tipo y tamaño."""
    mb = size_bytes / (1024 * 1024)
    if tipo == "video":
        return max(5, int(mb * 0.5))
    if tipo in ("lectura", "presentacion"):
        return max(3, int(mb * 2))
    if tipo == "ejercicio":
        return max(10, int(mb * 1.5))
    return max(5, int(mb))


lambda_handler = handle_s3_event
