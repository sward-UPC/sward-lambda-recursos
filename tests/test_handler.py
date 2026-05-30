from unittest.mock import patch
from handler import handle_s3_event, _estimar_tiempo, EXTENSION_TIPO_MAP


def _make_s3_event(key: str, size: int = 1024) -> dict:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "sward-recursos-educativos"},
                    "object": {"key": key, "size": size},
                }
            }
        ]
    }


@patch("handler._actualizar_metadata")
def test_procesa_evento_pdf(mock_act):
    result = handle_s3_event(_make_s3_event("cursos/cs101/intro.pdf", 512000), None)
    assert result["procesados"] == 1
    mock_act.assert_called_once_with(
        "sward-recursos-educativos", "cursos/cs101/intro.pdf", 512000
    )


@patch("handler._actualizar_metadata")
def test_procesa_evento_video(mock_act):
    result = handle_s3_event(_make_s3_event("cursos/cs101/clase1.mp4", 10485760), None)
    assert result["procesados"] == 1


@patch("handler._actualizar_metadata")
def test_error_no_bloquea_otros(mock_act):
    mock_act.side_effect = [Exception("db error"), None]
    event = {
        "Records": [
            {"s3": {"bucket": {"name": "b"}, "object": {"key": "a.pdf", "size": 100}}},
            {"s3": {"bucket": {"name": "b"}, "object": {"key": "b.mp4", "size": 200}}},
        ]
    }
    result = handle_s3_event(event, None)
    assert result["procesados"] == 1


def test_sin_records():
    result = handle_s3_event({}, None)
    assert result["procesados"] == 0


def test_tipo_por_extension():
    assert EXTENSION_TIPO_MAP[".mp4"] == "video"
    assert EXTENSION_TIPO_MAP[".pdf"] == "lectura"
    assert EXTENSION_TIPO_MAP[".py"] == "ejercicio"


def test_estimar_tiempo_video():
    t = _estimar_tiempo("video", 100 * 1024 * 1024)  # 100 MB
    assert t >= 5


def test_estimar_tiempo_minimo():
    assert _estimar_tiempo("video", 0) == 5
    assert _estimar_tiempo("lectura", 0) == 3
