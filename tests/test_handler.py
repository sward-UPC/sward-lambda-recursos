"""Tests unitarios para sward-lambda-recursos.

Trigger: S3 ObjectCreated event → actualiza MetadataRecurso
"""
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


def test_estimar_tiempo_lectura():
    """Tipo lectura: 3 min base + 2 min/MB."""
    t = _estimar_tiempo("lectura", 50 * 1024 * 1024)  # 50 MB
    assert t >= 3


def test_estimar_tiempo_presentacion():
    """Tipo presentacion: 3 min base + 2 min/MB."""
    t = _estimar_tiempo("presentacion", 25 * 1024 * 1024)  # 25 MB
    assert t >= 3


def test_estimar_tiempo_ejercicio():
    """Tipo ejercicio: 10 min base + 1.5 min/MB."""
    t = _estimar_tiempo("ejercicio", 100 * 1024 * 1024)  # 100 MB
    assert t >= 10


def test_estimar_tiempo_tipo_desconocido():
    """Tipo desconocido: 5 min base + 1 min/MB."""
    t = _estimar_tiempo("unknown", 50 * 1024 * 1024)
    assert t >= 5


def test_maneja_nombres_con_espacios_y_simbolos():
    """Verifica que se manejen nombres URL-encoded correctamente."""
    key = "cursos/cs101/archivo%20con%20espacios.pdf"
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "bucket"},
                    "object": {"key": key, "size": 1000},
                }
            }
        ]
    }
    with patch("handler._actualizar_metadata") as mock_act:
        result = handle_s3_event(event, None)
        assert result["procesados"] == 1
        # El key debe estar URL-decodificado
        call_args = mock_act.call_args[0]
        assert "con espacios.pdf" in call_args[1]


def test_extension_no_encontrada_usa_default():
    """Sin extensión reconocida, se usa 'lectura' como default."""
    with patch("handler._actualizar_metadata") as mock_act:
        event = _make_s3_event("archivo_sin_extension", 1000)
        handle_s3_event(event, None)
        assert mock_act.called


def test_evento_s3_con_errores_multiples():
    """Si hay errores en múltiples records, se cuenta solo los exitosos."""
    with patch("handler._actualizar_metadata") as mock_act:
        mock_act.side_effect = [
            Exception("error1"),
            None,
            Exception("error2"),
            None,
        ]
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "b"},
                        "object": {"key": f"archivo{i}.pdf", "size": 100},
                    }
                }
                for i in range(4)
            ]
        }
        result = handle_s3_event(event, None)
        # Debería procesar los que no fallaron (2 de 4)
        assert result["procesados"] == 2


class TestActualizarMetadata:
    """Tests para la función _actualizar_metadata."""

    @patch("handler._actualizar_metadata")
    def test_actualiza_metadata_pdf(self, mock_act):
        """Happy path: actualiza metadata para un PDF."""
        result = handle_s3_event(_make_s3_event("curso/file.pdf", 500000), None)
        assert result["procesados"] == 1
        mock_act.assert_called_once()
        call_args = mock_act.call_args[0]
        assert call_args[0] == "sward-recursos-educativos"
        assert call_args[1] == "curso/file.pdf"
        assert call_args[2] == 500000

    @patch("handler._actualizar_metadata")
    def test_actualiza_metadata_video(self, mock_act):
        """Actualiza metadata para un video."""
        result = handle_s3_event(_make_s3_event("videos/lecture.mp4", 500000000), None)
        assert result["procesados"] == 1
        call_args = mock_act.call_args[0]
        assert call_args[2] == 500000000

    @patch("handler._actualizar_metadata")
    def test_actualiza_metadata_ejercicio(self, mock_act):
        """Actualiza metadata para un archivo de ejercicio."""
        result = handle_s3_event(_make_s3_event("ejercicios/tarea.py", 10000), None)
        assert result["procesados"] == 1
        call_args = mock_act.call_args[0]
        assert "tarea.py" in call_args[1]

    @patch("handler._actualizar_metadata")
    def test_actualiza_metadata_presentacion(self, mock_act):
        """Actualiza metadata para una presentación."""
        result = handle_s3_event(_make_s3_event("slides/clase.pptx", 50000000), None)
        assert result["procesados"] == 1
