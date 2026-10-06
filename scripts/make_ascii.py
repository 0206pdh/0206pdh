"""Turn a picture into an ASCII-art SVG (run by hand when the picture changes).

Usage: python scripts/make_ascii.py <image> [assets/ascii.svg]
Requires Pillow.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps

RAMP = " .:-=+*#%@"
COLS, ROWS = 100, 56
WIDTH, HEIGHT = 840, 720
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else (
        Path(__file__).resolve().parent.parent / "assets" / "ascii.svg")

    img = ImageOps.autocontrast(Image.open(src).convert("L"), cutoff=2)
    img = ImageOps.fit(img, (COLS, ROWS), Image.LANCZOS)
    px = img.load()

    pad = 24
    line_h = (HEIGHT - 2 * pad) / ROWS
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}" font-size="{line_h:.1f}">',
        "<style>"
        "text{animation:scan .4s ease-out backwards}"
        "@keyframes scan{from{opacity:0}}"
        "</style>",
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>',
    ]
    for y in range(ROWS):
        row = "".join(RAMP[px[x, y] * (len(RAMP) - 1) // 255] for x in range(COLS))
        parts.append(
            f'<text xml:space="preserve" style="animation-delay:{y * 0.03:.2f}s" '
            f'x="{pad}" y="{pad + (y + 0.8) * line_h:.1f}" textLength="{WIDTH - 2 * pad}" '
            f'lengthAdjust="spacingAndGlyphs" fill="#c9d1d9">{escape(row)}</text>'
        )
    parts.append("</svg>")
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
