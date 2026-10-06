"""Turn a picture into an ASCII-art SVG (run by hand when the picture changes).

Usage: python scripts/make_ascii.py <image>
Requires Pillow. Writes assets/ascii-{dark,light}.svg.
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
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(exist_ok=True)

    img = ImageOps.autocontrast(Image.open(src).convert("L"), cutoff=2)
    img = ImageOps.fit(img, (COLS, ROWS), Image.LANCZOS)
    px = img.load()

    pad = 24
    line_h = (HEIGHT - 2 * pad) / ROWS
    # dense glyphs are bright on dark and dark on light, so flip the ramp per theme
    for name, bg, border, ink, ramp in (
        ("dark", "#0d1117", "#30363d", "#c9d1d9", RAMP),
        ("light", "#ffffff", "#d0d7de", "#1f2328", RAMP[::-1]),
    ):
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
            f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}" font-size="{line_h:.1f}">',
            "<style>"
            "text{animation:scan 12s ease-in-out infinite backwards}"
            "@keyframes scan{0%,97%,100%{opacity:0}3%,90%{opacity:1}}"
            "</style>",
            f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" '
            f'fill="{bg}" stroke="{border}"/>',
        ]
        for y in range(ROWS):
            row = "".join(ramp[px[x, y] * (len(ramp) - 1) // 255] for x in range(COLS))
            parts.append(
                f'<text xml:space="preserve" style="animation-delay:{y * 0.04:.2f}s" '
                f'x="{pad}" y="{pad + (y + 0.8) * line_h:.1f}" '
                f'textLength="{WIDTH - 2 * pad}" lengthAdjust="spacingAndGlyphs" '
                f'fill="{ink}">{escape(row)}</text>'
            )
        parts.append("</svg>")
        out = out_dir / f"ascii-{name}.svg"
        out.write_text("\n".join(parts), encoding="utf-8")
        print(f"wrote {out}")

if __name__ == "__main__":
    main()
