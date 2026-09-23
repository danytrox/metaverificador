from app.analyzer import summarize
from app.extractor import FileResult


def _sum(tags):
    return summarize(FileResult(path="/tmp/x.pdf", tags=tags))


def test_autor_xmp_dc_creator():
    s = _sum({"XMP-dc:Creator": "Juan", "File:FileType": "PDF"})
    assert s.author_found is True
    assert any("Juan" in v for v in s.author_values)


def test_pdf_creator_es_software_no_autor():
    s = _sum({"PDF:Creator": "Adobe InDesign 18.0", "File:FileType": "PDF"})
    assert s.author_found is False
    assert any("InDesign" in v for v in s.software)


def test_aviso_sin_autor():
    s = _sum({"File:FileType": "PDF"})
    assert s.author_found is False
    assert any("Sin autor" in w for w in s.warnings)


def test_aviso_indesign():
    s = _sum({"File:FileType": "PDF", "PDF:Creator": "Adobe InDesign 18.0"})
    assert any("InDesign" in w for w in s.warnings)
