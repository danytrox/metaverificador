# MetaVerificador

Analiza y verifica los metadatos de muchos archivos de forma **100% local**.
Ningún archivo sale de tu equipo: no se sube nada a páginas web ni a servicios
externos. El motor de extracción es [ExifTool](https://exiftool.org), el mismo
que usan los sitios web de metadatos, pero ejecutado en tu máquina.

Ideal para responder la pregunta que motivó este proyecto: **¿quién es el
autor de este documento?** — detectando cuándo el campo de autor está vacío o
nunca fue completado (por ejemplo, PDFs exportados desde InDesign sin autor).

## Qué hace

- Extrae **todos** los metadatos (Info del PDF, XMP, EXIF, IPTC, etc.).
- Detecta el **autor** (Author, dc:creator, Artist, By-line, etc.) y avisa
  cuando un archivo **no tiene autor**.
- Muestra título, fecha de creación y software de origen.
- Procesa **carpetas enteras** (recursivo) y arrastra/suelta archivos.
- Exporta informes a **CSV**, **JSON** y **HTML** (autocontenido, sin CDN).
- Resalta en rojo los archivos sin autor.

## Estructura

```
metaverificador/
├── main.py                 # Punto de entrada (GUI o --cli)
├── app/
│   ├── extractor.py        # Motor ExifTool + respaldo pypdf/Pillow
│   ├── analyzer.py         # Localiza autor/título/fecha/software
│   ├── report.py           # Exportación CSV/JSON/HTML
│   ├── cli.py              # Modo terminal
│   └── ui.py               # Interfaz gráfica (PySide6)
├── resources/exiftool/     # Binario de exiftool (empaquetado)
├── scripts/download_exiftool.py
├── metaverificador.spec    # Configuración de PyInstaller
├── build_windows.ps1/.bat  # Build del .exe
└── .github/workflows/build.yml  # Build automático del .exe (CI)
```

## Ejecutar desde el código fuente

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py              # interfaz gráfica
python main.py --cli *.pdf  # terminal
```

## Empaquetar como ejecutable de Windows (.exe)

El `.exe` debe compilarse **en Windows** (PyInstaller no hace compilación
cruzada). Dos opciones:

1. **En tu PC con Windows** (doble clic en `build_windows.bat`).
   Requiere Python 3.11 o 3.12 instalado.
2. **Automático por GitHub Actions**: sube el repo a GitHub y cada push
   generará `MetaVerificador.exe` como artefacto descargable.

El build descarga el binario oficial de ExifTool desde exiftool.org y lo
empaqueta dentro del ejecutable. El resultado es un único
`dist/MetaVerificador.exe` portátil.

## Modo terminal (CLI)

```bash
python main.py --cli archivo1.pdf archivo2.docx --csv reporte.csv --html reporte.html
```

## Seguridad

- Sin conexión de red en tiempo de análisis (solo se descarga ExifTool en el
  momento del *build*, no al usar la app).
- Los archivos analizados nunca se copian ni se envían a ningún servidor.
- El único tercero involucrado es ExifTool (software libre, licencia
  Artistic/Perl), ejecutado localmente.

## Nota sobre el autor ausente

Muchos archivos (sobre todo PDFs) no registran autor. La app lo detecta y lo
avisa con una explicación: por ejemplo, un PDF de InDesign sin `/Author` ni
`dc:creator` indica que el campo nunca se completó al exportar. En ese caso el
autor real hay que rastrearlo por otras vías (contenido, folio, remitente,
archivo `.indd` original), no por los metadatos.
