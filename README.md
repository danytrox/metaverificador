# MetaVerificador

Analiza y verifica los metadatos de muchos archivos de forma **100 % local**.
Ningún archivo sale de tu equipo: no se sube nada a páginas web ni a servicios
externos. El motor de extracción es [ExifTool](https://exiftool.org) —el mismo
que usan los sitios web de metadatos— pero ejecutado en tu propia máquina.

Nació para responder una pregunta concreta: **¿quién es el autor de este
documento?** Muchos archivos (sobre todo PDFs) no registran autor, y las webs
de metadatos no lo muestran porque el dato simplemente no existe. Esta
herramienta lo detecta y te lo explica, sin exponer tus archivos.

## Características

- Extrae **todos** los metadatos: Info del PDF, XMP, EXIF, IPTC, etc.
- Detecta el **autor** (Author, `dc:creator`, Artist, By-line…) y avisa
  claramente cuando un archivo **no tiene autor**.
- Muestra título, fecha de creación y software de origen.
- Procesa **carpetas enteras** (recursivo) y admite **arrastrar y soltar**.
- Exporta informes a **CSV**, **JSON** y **HTML** (autocontenido, sin CDN).
- Resalta en rojo los archivos sin autor.
- Doble motor: ExifTool (completo) y respaldo en Python puro (pypdf/Pillow).

## Stack tecnológico

| Componente | Tecnología | Por qué |
|------------|------------|---------|
| Interfaz   | Python + PySide6 | GUI de escritorio nativa, drag & drop |
| Metadatos  | ExifTool 13.x | El estándar de facto; soporta +200 formatos |
| Respaldo   | pypdf + Pillow | Funciona aunque falte ExifTool |
| Empaquetado| PyInstaller | Genera un único `.exe` portátil |

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
├── resources/exiftool/     # Binario de exiftool (empaquetado en el .exe)
├── scripts/download_exiftool.py   # Descarga el binario oficial
├── metaverificador.spec    # Configuración de PyInstaller
├── build_windows.ps1/.bat  # Build del .exe
└── .github/workflows/build.yml  # Build automático del .exe (CI)
```

## Ejecutar desde el código fuente

Requisito: Python 3.11 o 3.12 (también funciona en 3.14).

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py              # interfaz gráfica
python main.py --cli *.pdf  # terminal

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Empaquetar como ejecutable de Windows (.exe)

El `.exe` se compila **en Windows** (PyInstaller no compila en cruzado). Dos vías:

1. **En tu PC con Windows** (requiere Python 3.11/3.12):
   doble clic en `build_windows.bat`. Genera `dist\MetaVerificador.exe`.

2. **Automático por GitHub Actions**: cada `push` a este repo compila el `.exe`
   y lo deja como artefacto descargable (pestaña *Actions*).

El build descarga el paquete Windows de ExifTool (launcher + Perl portátil)
desde el mirror de Oliver Betz —el mismo sistema que exiftool.org usa para su
paquete oficial de Windows— y lo empaqueta dentro del ejecutable. Se usa ese
mirror porque el enlace directo de SourceForge está detrás de un challenge de
Cloudflare que bloquea las descargas automáticas. El resultado es un único
`.exe` portátil que no requiere instalación.

## Uso

**GUI:** arrastra archivos o carpetas a la ventana, o usa "Agregar
archivos/carpeta". La tabla muestra por archivo si tiene autor, los valores
encontrados, título, fecha y software. El panel inferior muestra todos los
campos. Exporta con los botones CSV / JSON / HTML.

**CLI:**

```bash
python main.py --cli archivo1.pdf archivo2.docx --csv reporte.csv --html reporte.html
```

Ejemplo de salida:

```
Backend: ExifToolBackend
ARCHIVO                                  AUTOR TIPO   TITULO
Esbozo_de_la_Composición_Escenica.pdf    NO    PDF
Horario_estudiantes.pdf                  SI    PDF    (SAPPORTAL)
--------------------------------------------------------------------
Total: 2 | Sin autor: 1
```

## Seguridad

- **Sin red en tiempo de análisis.** Los archivos nunca se copian, suben ni
  envían a ningún servidor.
- La única descarga (ExifTool) ocurre en el **momento del build**, no al usar
  la app.
- El único tercero es ExifTool (software libre, licencia Artistic/Perl),
  ejecutado localmente como subproceso.
- Se recomienda auditar el `.exe` compilado (por ejemplo, verificando su hash
  o compilándolo tú mismo desde este código fuente).

## Por qué algunos archivos "no tienen autor"

Un PDF exportado desde InDesign solo lleva autor si quien lo exportó completó
el campo *Autor* (que se guarda como `/Author` y `dc:creator`). Si lo dejó
vacío, **no hay nada que extraer**: no es un fallo de la herramienta, es que el
dato no existe. La app lo detecta y lo avisa con una explicación específica
(por ejemplo: *"PDF exportado desde InDesign sin autor: probablemente el campo
/Author y dc:creator nunca se completaron"*).

En ese caso, el autor real hay que rastrearlo por otras vías (contenido,
número de folio, remitente, archivo `.indd` original), no por los metadatos.

## Licencia

Código de la aplicación: MIT. ExifTool es una herramienta independiente de
Phil Harvey, distribuida bajo licencia Artistic/Perl.
