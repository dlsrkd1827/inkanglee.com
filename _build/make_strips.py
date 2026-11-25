"""메인 페이지 가로 썸네일(10:3) 만들기.
usage: python make_strips.py [preview_out.jpg]
   - 인자 없이 실행하면 assets/img/home/<작품>.jpg 저장
   - 인자를 주면 저장 대신 미리보기 한 장으로 모아 그 파일에 저장

mode
  "cover": 사진을 띠에 꽉 채워 자름 (fy: 0=위쪽, 1=아래쪽 기준)
  "fit"  : 사진(또는 region 비율로 자른 부분)을 통째로 가운데 넣고,
           양옆은 같은 사진을 흐리게 늘린 배경으로 자연스럽게 이어 붙임 → 대상이 잘리지 않음
"""
import os, sys
from PIL import Image, ImageFilter, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
W, H = 1600, 480

STRIPS = [
    # (작품, 원본 사진, mode, 옵션)
    ("highway-to-hell",    "assets/img/highway-to-hell/14.jpg",    "fit",   {"region": 2.0, "fy": .35}),
    ("lightgrass-01",      "assets/img/lightgrass-01/01.jpg",      "fit",   {}),
    ("susu-sangseung",     "assets/img/home/susu-sangseung.jpg",   "keep",  {}),
    ("sensory-relay-01",   "assets/img/sensory-relay-01/01.jpg",   "fit",   {}),
    ("drawing-suit-01-02", "assets/img/home/drawing-suit-01-02.jpg", "keep", {}),
    ("performing-suit-02", "assets/img/performing-suit-02/06.jpg", "solid",   {"feather": 24}),
    ("performing-suit-01", "assets/img/performing-suit-01/01.jpg", "solid",   {}),
    ("drawing-suit-02",    "assets/img/drawing-suit-02/03.jpg",    "solid",   {}),
    ("drawing-suit-01",    "assets/img/home/drawing-suit-01.jpg",  "keep",  {}),
    ("memory",             "assets/img/home/memory.jpg",           "keep",  {}),
]


def cover(im, fy=.5, w=W, h=H):
    tr = w / h
    iw, ih = im.size
    if iw / ih > tr:
        nw = int(ih * tr); x = (iw - nw) // 2; box = (x, 0, x + nw, ih)
    else:
        nh = int(iw / tr); y = int((ih - nh) * fy); box = (0, y, iw, y + nh)
    return im.crop(box).resize((w, h), Image.LANCZOS)


def fit(im, region=None, fy=.5):
    if region:  # 먼저 region 비율로 잘라서 덜 확대
        im = cover(im, fy, w=int(1000 * region), h=1000) if im.width / im.height > region or True else im
    # 배경: 같은 사진을 꽉 채운 뒤 크게 흐림 + 살짝 밝게
    bg = cover(im, .5).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (255, 255, 255)), .25)
    # 앞: 사진 전체를 높이에 맞춰 가운데
    fg = im.copy(); fg.thumbnail((W, H), Image.LANCZOS)
    if fg.height < H:
        fg = im.resize((int(im.width * H / im.height), H), Image.LANCZOS)
    x = (W - fg.width) // 2
    # 가장자리를 부드럽게 (좌우 40px 페이드)
    mask = Image.new("L", fg.size, 255); d = ImageDraw.Draw(mask)
    f = min(40, fg.width // 10)
    for i in range(f):
        a = int(255 * (i + 1) / f)
        d.line([(i, 0), (i, fg.height)], fill=a)
        d.line([(fg.width - 1 - i, 0), (fg.width - 1 - i, fg.height)], fill=a)
    bg.paste(fg, (x, 0), mask)
    return bg


def extend(im):
    """사진 전체를 가운데 넣고, 양옆은 사진 가장자리 색을 그대로 옆으로 늘려 이어 붙임 (단색 배경 사진용)"""
    fg = im.resize((int(im.width * H / im.height), H), Image.LANCZOS)
    if fg.width >= W:
        return cover(im)
    x = (W - fg.width) // 2
    canvas = Image.new("RGB", (W, H), "white")
    k = max(3, fg.width // 100)  # 가장자리 몇 px 평균
    left = fg.crop((0, 0, k, H)).resize((1, H), Image.BOX).resize((x + 2, H))
    right = fg.crop((fg.width - k, 0, fg.width, H)).resize((1, H), Image.BOX).resize((W - x - fg.width + 2, H))
    canvas.paste(left.filter(ImageFilter.GaussianBlur(6)), (0, 0))
    canvas.paste(right.filter(ImageFilter.GaussianBlur(6)), (x + fg.width - 2, 0))
    mask = Image.new("L", fg.size, 255); d = ImageDraw.Draw(mask)
    f = min(24, fg.width // 12)
    for i in range(f):
        a = int(255 * (i + 1) / f)
        d.line([(i, 0), (i, H)], fill=a); d.line([(fg.width - 1 - i, 0), (fg.width - 1 - i, H)], fill=a)
    canvas.paste(fg, (x, 0), mask)
    return canvas


def solid(im, feather=120):
    """사진 전체를 가운데 넣고, 배경은 사진 좌우 가장자리의 평균 한 색으로. 사진 테두리는 넓게 녹여서 이음매가 안 보이게."""
    fg = im.resize((int(im.width * H / im.height), H), Image.LANCZOS)
    if fg.width >= W:
        return cover(im)
    k = max(4, fg.width // 30)
    edge = Image.new("RGB", (2 * k, H))
    edge.paste(fg.crop((0, 0, k, H)), (0, 0)); edge.paste(fg.crop((fg.width - k, 0, fg.width, H)), (k, 0))
    px = sorted(edge.resize((2 * k, 60)).getdata(), key=sum)
    color = px[len(px) // 2]  # 중간값 색 (전선 같은 어두운 점은 무시)
    canvas = Image.new("RGB", (W, H), color)
    x = (W - fg.width) // 2
    mask = Image.new("L", fg.size, 255); d = ImageDraw.Draw(mask)
    f = min(feather, fg.width // 5)
    for i in range(f):
        a = int(255 * ((i + 1) / f) ** 1.5)
        d.line([(i, 0), (i, H)], fill=a); d.line([(fg.width - 1 - i, 0), (fg.width - 1 - i, H)], fill=a)
    canvas.paste(fg, (x, 0), mask)
    return canvas


def make(entry):
    name, src, mode, opt = entry
    im = Image.open(os.path.join(ROOT, src)).convert("RGB")
    if mode == "keep":
        return im if im.size[0] / im.size[1] > 3.2 else cover(im)
    if mode == "solid":
        return solid(im, opt.get("feather", 120))
    if mode == "extend":
        return extend(im)
    if mode == "cover":
        return cover(im, opt.get("fy", .5))
    return fit(im, opt.get("region"), opt.get("fy", .5))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        tw, th = 800, 240
        sheet = Image.new("RGB", (tw * 2 + 30, (th + 30) * ((len(STRIPS) + 1) // 2)), "white")
        dr = ImageDraw.Draw(sheet)
        for i, e in enumerate(STRIPS):
            t = make(e).resize((tw, th), Image.LANCZOS)
            x = (i % 2) * (tw + 30); y = (i // 2) * (th + 30)
            sheet.paste(t, (x, y)); dr.text((x + 4, y + th + 4), f"{e[0]}  ({e[2]})", fill="black")
        sheet.save(sys.argv[1], quality=82)
    else:
        for e in STRIPS:
            if e[2] == "keep":
                continue
            out = make(e)
            p = os.path.join(ROOT, "assets/img/home", e[0] + ".jpg")
            out.save(p, quality=82, optimize=True, progressive=True)
            print(e[0], out.size, os.path.getsize(p) // 1024, "KB")
