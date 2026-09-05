"""공식 포스터에서 PWA 아이콘(192/512)을 생성한다.

포스터는 세로로 길어 그대로 줄이면 제목이 뭉개진다.
상단 키아트 위주로 정사각 크롭한 뒤 리사이즈한다.
"""

from pathlib import Path

from PIL import Image

SRC = Path(r"d:\workspace\x-collector\data\raw\_LIVECONNECTION\2089864959727682046_1.jpg")
OUT = Path(r"d:\workspace\ikkisup2026")

# 세로 기준 크롭 시작 위치 (0.0=최상단, 1.0=최하단). 제목이 살도록 조정.
VERTICAL_ANCHOR = 0.30


def main() -> None:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    print(f"원본 {SRC.name} {w}x{h}")

    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * VERTICAL_ANCHOR)
    square = im.crop((left, top, left + side, top + side))

    for size in (192, 512):
        icon = square.resize((size, size), Image.LANCZOS)
        # sw.js 가 아이콘을 프리캐시하므로 용량을 줄인다.
        # 사진 원본이라 팔레트로 양자화해도 아이콘 크기에서는 차이가 보이지 않는다.
        icon = icon.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        path = OUT / f"icon-{size}.png"
        icon.save(path, "PNG", optimize=True)
        print(f"  {path.name}  {size}x{size}  {path.stat().st_size / 1024:.1f}KB")


if __name__ == "__main__":
    main()
