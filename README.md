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
- Exporta informes a **CSV**, **JSON**, **HTML** y **Excel (.xlsx)** (autocontenido, sin CDN).
- **Plantilla opcional**: carga un `.xlsx` o `.html` cuyos encabezados definen qué
  columnas y en qué orden salen en el informe (CSV/HTML/Excel).
- **Mapeo con IA local opcional**: un modelo pequeño (Qwen2.5-1.5B en GGUF) resuelve
  encabezados ambiguos; si no hay modelo, se usa el mapeo determinístico.
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
│   ├── report.py           # Exportación CSV/JSON/HTML/Excel
│   ├── template.py         # Plantillas opcionales (columnas del informe)
│   ├── llm.py              # Mapeo con IA local (opcional, Qwen GGUF)
│   ├── cli.py              # Modo terminal
│   └── ui.py               # Interfaz gráfica (PySide6)
├── resources/exiftool/     # Binario de exiftool (empaquetado en el .exe)
├── scripts/download_exiftool.py   # Descarga el binario oficial
├── scripts/download_model.py      # Descarga el modelo GGUF (opcional)
├── tests/                  # Tests unitarios (pytest)
├── requirements.txt        # Dependencias de ejecución
├── requirements-ai.txt     # Dependencias opcionales (IA local)
├── requirements-dev.txt    # Dependencias de desarrollo (pytest)
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

Si además está instalado `llama-cpp-python` (vía `requirements-ai.txt`), el
`.exe` incluye la librería de IA local. El modelo GGUF (~1.1 GB) **no** se
incluye: se descarga en primer uso con `scripts/download_model.py`. En la GUI,
la primera vez que una plantilla tiene encabezados ambiguos se ofrece descargar
el modelo (con confirmación); el CLI nunca descarga, solo usa el modelo si ya
existe. Sin IA, el `.exe` funciona igual con el mapeo determinístico de
plantillas.

## Uso

**GUI:** arrastra archivos o carpetas a la ventana, o usa "Agregar
archivos/carpeta". La tabla muestra por archivo si tiene autor, los valores
encontrados, título, fecha y software. El panel inferior muestra todos los
campos. Exporta con los botones CSV / JSON / HTML / XLSX.

**CLI:**

```bash
python main.py --cli archivo1.pdf archivo2.docx --csv reporte.csv --xlsx reporte.xlsx
```

Flags de exportación: `--csv`, `--json`, `--html` y `--xlsx` (se pueden combinar).

### Plantillas (opcional)

Puedes pasar una plantilla `.xlsx` o `.html` para definir las columnas del informe:

```bash
python main.py --cli *.pdf --template plantilla.xlsx --xlsx reporte.xlsx
```

Cada encabezado de la plantilla se resuelve así:

- Si es una etiqueta ExifTool (`EXIF:Model`, `File:FileSize`, …), se lee ese campo.
- Si es un nombre conocido (Autor, Título, Fecha, Software, Tipo, Ruta…), se usa
  ese campo lógico.
- Los encabezados ambiguos se resuelven con el modelo local de IA si está
  disponible; si no, esa columna queda vacía en el informe.

**Sin plantilla** el informe sale exactamente como antes (columnas por defecto).

Para activar el mapeo con IA local (opcional):

```bash
pip install -r requirements-ai.txt
python scripts/download_model.py    # descarga ~1.1 GB una sola vez
```

La app detecta el modelo automáticamente (`~/.metaverificador/models` o la
carpeta `models` junto al ejecutable) y, si no está, sigue funcionando con el
mapeo determinístico.

Puedes forzar la ubicación con las variables de entorno `METAVERIFICADOR_MODEL`
(ruta al `.gguf`) o `METAVERIFICADOR_MODELS_DIR` (carpeta de modelos).

El Excel se genera siempre con dos hojas. Sin plantilla: **Resumen** (una fila
por archivo, autor SÍ/NO, filas rojas para los sin autor, autofiltro y
encabezados congelados) y **Metadatos** (volcado completo campo por campo). Con
plantilla: **Datos** (las columnas que pide la plantilla) y **Metadatos**.

Ejemplo de salida:

```
Backend: ExifToolBackend
ARCHIVO                                  AUTOR TIPO   TITULO
Esbozo_de_la_Composición_Escenica.pdf    NO    PDF
Horario_estudiantes.pdf                  SÍ    PDF    (SAPPORTAL)
--------------------------------------------------------------------
Total: 2 | Sin autor: 1
```

## Seguridad

- **Sin red en tiempo de análisis.** Los archivos nunca se copian, suben ni
  envían a ningún servidor.
- La descarga de ExifTool ocurre en el **momento del build**, no al usar la app.
- La **única** descarga en tiempo de uso es el modelo de IA local (opcional,
  ~1.1 GB), que solo se hace con tu confirmación (GUI) o manualmente con
  `scripts/download_model.py`. El análisis de metadatos nunca usa red.
- Los terceros son ExifTool (software libre, licencia Artistic/Perl, ejecutado
  localmente como subproceso) y, solo si activas la IA, el modelo Qwen GGUF de
  Hugging Face. Ambos corren 100 % en tu máquina.
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

## Desarrollo (tests)

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Apoyar el proyecto

¿MetaVerificador te ahorra tiempo? Puedes invitarme un café en
[ko-fi.com/daneryarriagada](https://ko-fi.com/daneryarriagada).

## Licencia

Código de la aplicación: MIT. ExifTool es una herramienta independiente de
Phil Harvey, distribuida bajo licencia Artistic/Perl.
