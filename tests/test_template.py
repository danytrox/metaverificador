import pytest

from app.template import classify_header, load_template


def test_clasifica_nombre_conocido():
    assert classify_header("Autor").kind == "author_bool"
    assert classify_header("Título").kind == "title"
    assert classify_header("Fecha").kind == "date"
    assert classify_header("Software").kind == "software"
    assert classify_header("Tipo").kind == "filetype"
    assert classify_header("Ruta").kind == "path"


def test_clasifica_etiqueta_exiftool():
    c = classify_header("EXIF:Model")
    assert c.kind == "tag"
    assert c.source == "EXIF:Model"


def test_clasifica_desconocido():
    assert classify_header("QuéSeYo").kind == "unknown"


def test_autor_valores_tiene_prioridad():
    assert classify_header("Autor (valores)").kind == "author_values"


def test_parsea_encabezados_html(tmp_path):
    p = tmp_path / "t.html"
    p.write_text(
        "<html><table><tr><th>Archivo</th><th>Autor</th></tr></table></html>",
        encoding="utf-8",
    )
    spec = load_template(str(p))
    assert [c.header for c in spec.columns] == ["Archivo", "Autor"]


def test_plantilla_vacia_lanza_error(tmp_path):
    p = tmp_path / "e.html"
    p.write_text("<html><body>sin tabla</body></html>", encoding="utf-8")
    with pytest.raises(ValueError):
        load_template(str(p))
