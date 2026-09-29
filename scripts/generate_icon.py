"""Genera el ícono de MetaVerificador (resources/icon.png + icon.ico).

Diseño: lupa (inspección de metadatos) con las iniciales "MV" en el lente y una
insignia verde de "verificado" (check) que alude a la verificación.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

S = 512
FONT_BOLD = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"

# --- Fondo: cuadrado redondeado con gradiente azul -> verde oscuro ------------
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=112, fill=255)

top = (31, 78, 121)      # #1F4E79
bottom = (17, 82, 49)    # #115231
grad = Image.new("RGBA", (S, S))
gd = ImageDraw.Draw(grad)
for y in range(S):
    t = y / (S - 1)
    gd.line([(0, y), (S, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)) + (255,))
img.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(img)

# --- Lupa ---------------------------------------------------------------------
lens_c = (206, 210)
lens_r = 118

# Lente blanco
d.ellipse(
    [lens_c[0] - lens_r, lens_c[1] - lens_r, lens_c[0] + lens_r, lens_c[1] + lens_r],
    fill=(255, 255, 255, 255),
)

# Mango (línea gruesa redondeada) desde el borde del lente hacia abajo-derecha
ang = math.radians(42)
hx0 = lens_c[0] + (lens_r - 6) * math.cos(ang)
hy0 = lens_c[1] + (lens_r - 6) * math.sin(ang)
hx1, hy1 = 424, 436
hw = 32
d.line([(hx0, hy0), (hx1, hy1)], fill=(255, 255, 255, 255), width=hw)
d.ellipse([hx1 - hw // 2, hy1 - hw // 2, hx1 + hw // 2, hy1 + hw // 2], fill=(255, 255, 255, 255))

# "MV" dentro del lente
for size in (120, 116, 112, 108):
    font = ImageFont.truetype(FONT_BOLD, size)
    bbox = d.textbbox((0, 0), "MV", font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if w <= lens_r * 2 - 36:
        break
d.text(
    (lens_c[0] - w / 2 - bbox[0], lens_c[1] - h / 2 - bbox[1]),
    "MV",
    font=font,
    fill=(31, 78, 121, 255),
)

# --- Insignia verde "verificado" (check) en la esquina inferior derecha -------
bc = (452, 452)
br = 52
d.ellipse([bc[0] - br, bc[1] - br, bc[0] + br, bc[1] + br], fill=(34, 197, 94, 255))
d.ellipse(
    [bc[0] - br, bc[1] - br, bc[0] + br, bc[1] + br],
    outline=(255, 255, 255, 255),
    width=5,
)
# check blanco
cx, cy = bc
pts = [(cx - 22, cy - 2), (cx - 6, cy + 15), (cx + 24, cy - 16)]
d.line(pts, fill=(255, 255, 255, 255), width=12, joint="curve")
d.ellipse([cx - 22 - 6, cy - 2 - 6, cx - 22 + 6, cy - 2 + 6], fill=(255, 255, 255, 255))
d.ellipse([cx + 24 - 6, cy - 16 - 6, cx + 24 + 6, cy - 16 + 6], fill=(255, 255, 255, 255))

# --- Exportar ----------------------------------------------------------------
img.save("resources/icon.png")

# .ico multi-tamaño (para Windows)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save("resources/icon.ico", sizes=sizes)

print("icon.png e icon.ico generados")
