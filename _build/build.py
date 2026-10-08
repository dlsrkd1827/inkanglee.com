"""Wix(inkanglee.com) 스냅샷 -> 정적 HTML 사이트 변환기.
usage: python -I build.py <pages_dir> <out_dir> [--no-download]
"""
import re, json, os, sys, html as H, urllib.request, urllib.parse, concurrent.futures as cf

sys.stdout.reconfigure(encoding="utf8")
PAGES_DIR, OUT = sys.argv[1], sys.argv[2]
DOWNLOAD = "--no-download" not in sys.argv
# 원본 Wix 모바일 스냅샷 (fetch_mobile.py 로 받음). 없으면 모바일 전용 레이아웃 생략
MOBILE_DIR = sys.argv[sys.argv.index("--mobile") + 1] if "--mobile" in sys.argv else None

# (출력 파일명, 원본 슬러그, 메뉴 라벨) — 메뉴 순서 그대로
WORKS = [
    ("lightgrass-01", "%EB%B3%B5%EC%A0%9C-motorized-wheelchair-sensory-rel-1", "Lightgrass 01 2025"),
    ("susu-sangseung", "%EB%B3%B5%EC%A0%9C-motorized-wheelchair-sensory-rel", "수수상승 흑환재생 手手相承 黑環再生 2025"),
    ("sensory-relay-01", "sensoryrelay01", "Sensory Relay 01 2024"),
    ("drawing-suit-01-02", "drawingsuit01-02", "Drawing Suit 01_02 2024"),
    ("performing-suit-02", "performing-suit-02-2023", "Performing Suit 02 2023"),
    ("performing-suit-01", "%ED%8D%BC%ED%8F%AC%EB%B0%8D-%EC%88%98%ED%8A%B8-01-2022-12", "Performing Suit 01 2022"),
    ("drawing-suit-02", "%EB%93%9C%EB%A1%9C%EC%9E%89-%EC%88%98%ED%8A%B8-02-2022", "Drawing Suit 02 2022"),
    ("drawing-suit-01", "drawing-suit-01", "Drawing Suit 01 2021"),
]
ARCHIVE = [
    ("undead-weight", "undead-weight", "Undead Weight 2020"),
    ("tinker-ball", "tinker-ball", "Tinker Ball 2020"),
    ("perfect-posture", "perfectposture", "Perfect Posture 2019"),
    ("hack-the-boxing-2", "hack-the-boxing-2", "Hack the boxing 2"),
    ("hack-the-boxing", "hack-the-box", "Hack the boxing"),
    ("1997-11-22-1", "1997-11-22-1", "1997.11.22"),
    ("windows-diary", "untitled1", "일기창 Windows diary"),
    ("wood-diary", "wood-diary", "일기목 Wood diary"),
    ("reddish-brothers", "reddish-brothers", "붉은 형들 Reddish brothers"),
    ("jangsaengpo-people", "untitled2", "장생포 사람들 Jangsaengpo people"),
    ("eyes-2017", "eyes-2017", "눈 The Eyes 2017"),
    ("1997-11-22", "1997-11-22", "1997.11.22"),
    ("the-boxer", "the-boxer", "복서 The Boxer"),
    ("light-of-memory", "light-of-memory", "기억빛 Light of Memory"),
    ("coated-memory", "coated-memory", "기억코팅 Coated Memory"),
    ("coated-memory-2", "coated-memory-2", "기억코팅 Coated Memory 2"),
    ("the-flying-arrow", "the-flying-arrow-is-therefore-motio", "The Flying Arrow is Therefore Motionless"),
    ("hello-nice-to-meet-you", "hello-nice-to-meet-you", "안녕하세요 반갑습니다 Hello, Nice to Meet You"),
    ("prepper", "prepper", "재난대비 The Prepper"),
    ("eyes-2013", "eyes-2013", "눈 The Eyes 2013"),
]
TAIL = [("reviews", "critic", "Reviews"), ("cv", "cv", "CV"), ("contact", "contact", "Contact")]
MEMORY = ("memory", "memory", "2013-2020")
ALL = WORKS + [MEMORY] + ARCHIVE + TAIL
SLUG2FILE = {urllib.parse.unquote(s).lower(): f for f, s, _ in ALL}
SLUG2FILE[""] = "index"

def local_href(href):
    m = re.match(r"https?://(?:www\.)?inkanglee\.com/?([^?#]*)(.*)$", href)
    if not m:
        return href
    slug = urllib.parse.unquote(m.group(1)).strip("/").lower()
    return SLUG2FILE.get(slug, "index") + ".html" + m.group(2) if slug in SLUG2FILE else href

# ---------- 글꼴 매핑 (Wix 전용 라이선스 폰트 -> 무료 대체) ----------
def map_fonts(s):
    def rep(m):
        fam = m.group(1).lower()
        if "helvetica" in fam:
            w = "700" if "bold" in fam else "300" if "light" in fam else "400"
            return f"font-family:var(--sans);font-weight:{w}"
        if "garamond" in fam:
            return "font-family:var(--serif)"
        if "open sans" in fam:
            return "font-family:'Open Sans',var(--sans)"
        if "neogothic" in fam:
            return "font-family:var(--sans)"
        return "font-family:var(--sans)"
    return re.sub(r"font-family:([^;\"]*)", rep, s)

def clean_rich(h):
    h = re.sub(r'<span class="wixGuard[^"]*">​</span>', "", h)
    h = re.sub(r'\s*class="wixui-rich-text__text"', "", h)
    h = re.sub(r'\s*(wixui-rich-text__text)', "", h)
    h = re.sub(r'<a href="mailto:[^"]*"[^>]*>(.*?)</a>', lambda m: m.group(1), h)
    # 원본 CV에 복사·붙여넣기로 딸려 온 네이버 사전 링크 제거 (글자는 유지)
    h = re.sub(r'<a href="https?://[^"]*dict\.naver\.com[^"]*"[^>]*>(.*?)</a>', lambda m: m.group(1), h, flags=re.S)
    h = re.sub(r'href="([^"]+)"', lambda m: 'href="%s"' % H.escape(local_href(H.unescape(m.group(1)))), h)
    return map_fonts(h)

# ---------- 다운로드 ----------
jobs = {}  # url -> local path
def want(url, rel):
    if url in jobs:
        return jobs[url]
    jobs[url] = rel
    return rel

def img_url(p):
    uri = p["uri"]
    cw, ch = p.get("containerWidth") or p["width"], p.get("containerHeight") or p["height"]
    crop = p.get("crop")
    sw, sh = (crop["width"], crop["height"]) if crop else (p["width"], p["height"])
    # 레티나 2배, 단 원본보다 크게는 안 함, 최대 2400px
    scale = min(2.0, sw / cw, sh / ch, 2400 / max(cw, ch))
    w, h = max(1, round(cw * scale)), max(1, round(ch * scale))
    mode = "fit" if p.get("displayMode") in ("fit", "fitWidth", "full") else "fill"
    parts = f"v1/crop/x_{crop['x']},y_{crop['y']},w_{crop['width']},h_{crop['height']}/" if crop else "v1/"
    ext = uri.rsplit(".", 1)[-1].lower()
    return f"https://static.wixstatic.com/media/{uri}/{parts}{mode}/w_{w},h_{h},al_c,q_90/file.{ext}", ext

def download_all():
    def one(item):
        url, rel = item
        dst = os.path.join(OUT, rel)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return rel, "skip"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=300).read()
        open(dst, "wb").write(data)
        return rel, len(data)
    with cf.ThreadPoolExecutor(8) as ex:
        for rel, r in ex.map(one, jobs.items()):
            pass
    print("downloaded", len(jobs), "files")

# ---------- 레이아웃 파싱 ----------
KEEP_CHILD = ["position", "margin", "left", "top", "grid-area", "justify-self", "align-self"]
KEEP_SELF = ["width", "height", "min-height"]
KEEP_GRID = ["display", "grid-template-rows", "grid-template-columns", "min-height", "padding-bottom", "padding-top", "margin-top", "margin-bottom", "height"]

def decls(body, keep):
    out = {}
    for d in body.split(";"):
        if ":" in d:
            k, v = d.split(":", 1)
            k = k.strip()
            if k in keep and k not in out:
                out[k] = v.strip()
    return out

def parse_layout(html):
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    child, grid, selfc = {}, {}, {}
    for m in re.finditer(r'\[data-mesh-id=([\w-]+?)inlineContent-gridContainer\] > \[id="([\w-]+)"\][^{]*\{([^}]*)\}', css):
        parent, cid, body = m.groups()
        child.setdefault(cid, {"parent": parent, **decls(body, KEEP_CHILD)})
    for m in re.finditer(r'\[data-mesh-id=([\w-]+?)inlineContent-gridContainer\]\{([^}]*)\}', css):
        grid.setdefault(m.group(1), {}).update(decls(m.group(2), KEEP_GRID))
    for m in re.finditer(r'\[data-mesh-id=([\w-]+?)inlineContent\]\{([^}]*)\}', css):
        mh = decls(m.group(2), ["min-height"]).get("min-height")
        if mh and mh != "auto":
            g = grid.setdefault(m.group(1), {})
            if g.get("min-height", "auto") == "auto":
                g["min-height"] = mh
    for m in re.finditer(r'(?<![\w-])#([\w-]+)\{([^}]*)\}', css):
        d = decls(m.group(2), KEEP_SELF)
        if d:
            selfc.setdefault(m.group(1), {}).update({k: v for k, v in d.items() if k not in selfc.get(m.group(1), {})})
    wedges = {}
    for m in re.finditer(r'\[data-mesh-id=([\w-]+?)inlineContent-wedge-(\d+)\]\{([^}]*)\}', css):
        d = decls(m.group(3), ["height", "grid-area"])
        if "height" in d and "grid-area" in d:
            wedges.setdefault(m.group(1), {})[m.group(2)] = d
    return child, grid, selfc, wedges

def row_of(c):
    return int(c.get("grid-area", "1").split("/")[0])

def left_of(c):
    try:
        return float(c.get("left", "0").replace("px", ""))
    except ValueError:
        return 0

def style(d):
    return ";".join(f"{k}:{v}" for k, v in d.items())

# ---------- 컴포넌트 렌더 ----------
def yt_id(src):
    m = re.search(r"(?:youtu\.be/|v=|embed/)([\w-]{11})", src or "")
    return m.group(1) if m else None

def yt_iframe(vid, title=""):
    return (f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}?rel=0" title="{H.escape(title or "YouTube video")}" '
            'loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen" '
            'allowfullscreen></iframe>')

class Page:
    def __init__(self, name, label, pdir=None, pfx="", imgmap=None):
        """pfx: 모바일 레이아웃용 id 접두사('m-'). imgmap: 데스크톱에서 받은 이미지 재사용."""
        self.name, self.label, self.pfx = name, label, pfx
        self.imgmap = {} if imgmap is None else imgmap
        pdir = pdir or os.path.join(PAGES_DIR, name)
        self.html = open(os.path.join(pdir, "ssr.html"), encoding="utf8").read()
        d = json.load(open(os.path.join(pdir, "data.json"), encoding="utf8"))
        self.types, self.props, self.seo = d["types"], d["props"], d.get("seo") or {}
        self.child, self.grid, self.selfc, self.wedges = parse_layout(self.html)
        self.css = []
        self.nimg = 0
        self.nvid = 0

    def children(self, parent):
        """DOM 순서 = 모바일에서 보이는 순서. (데스크톱은 grid-area로 배치되므로 순서 무관)
        여러 열로 된 '캡션 줄 + 사진 줄' 쌍은 열 단위로 묶어 캡션-사진이 붙어 나오게 한다."""
        ks = [k for k, c in self.child.items() if c["parent"] == parent]
        rows = {}
        for k in ks:
            rows.setdefault(row_of(self.child[k]), []).append(k)
        order, rs, i = [], sorted(rows), 0
        is_txt = lambda k: self.types.get(k) == "WRichText"
        while i < len(rs):
            a = sorted(rows[rs[i]], key=lambda k: left_of(self.child[k]))
            if i + 1 < len(rs) and len(a) > 1:
                b = sorted(rows[rs[i + 1]], key=lambda k: left_of(self.child[k]))
                same_cols = len(a) == len(b) and all(
                    abs(left_of(self.child[x]) - left_of(self.child[y])) < 40 for x, y in zip(a, b))
                pair = all(map(is_txt, a)) != all(map(is_txt, b))
                if same_cols and pair:
                    for x, y in zip(a, b):
                        order += [x, y]
                    i += 2
                    continue
            order += a
            i += 1
        return order

    def mesh(self, cid):
        g = self.grid.get(cid, {})
        kids = self.children(cid)
        if not kids and not g:
            return ""
        i = self.pfx + cid
        self.css.append(f"#{i}-mesh{{{style(g)}}}")
        # Wix 웨지: 보이지 않는 간격용 요소 (원본의 세로 여백 재현)
        wedge = ""
        for n, w in self.wedges.get(cid, {}).items():
            self.css.append(f"#{i}-w{n}{{height:{w['height']};grid-area:{w['grid-area']}}}")
            wedge += f'<div class="wedge" id="{i}-w{n}"></div>'
        return f'<div class="mesh" id="{i}-mesh">' + "".join(self.render(k) for k in kids) + wedge + "</div>"

    def render(self, cid):
        t = self.types.get(cid)
        p = self.props.get(cid, {})
        lay = dict(self.child.get(cid, {}))
        lay.pop("parent", None)
        own = self.selfc.get(cid, {})
        if t in ("ClassicSection",):
            own = {"left": "0", "margin-left": "0", "width": "100%"}
        iid = self.pfx + cid
        self.css.append(f"#{iid}{{{style({**lay, **own})}}}")
        cls = "cell"
        inner = ""
        tag = "div"
        if t == "WRichText" and "메시지가 발송" in p.get("html", ""):
            return ""  # Wix 폼 전송 완료 문구 (정적 사이트에서는 메일 앱으로 보냄)
        if t == "AppWidget":
            return ""  # Contact 문의 폼은 쓰지 않음 (인스타그램 링크만 남김)
        if t in ("AppWidget", "FormContainer"):
            cls += " sec"
            if t == "FormContainer":
                tag = "form"
                cls += " contact-form"
            inner = self.mesh(cid)
        elif t == "TextInput":
            cls += " field"
            req = " required" if p.get("required") else ""
            nm = re.sub(r"[^a-z]", "", (p.get("name") or "").lower()) or "field"
            inner = (f'<input type="{p.get("inputType", "text")}" name="{nm}" '
                     f'placeholder="{H.escape(p.get("placeholder", ""))}" aria-label="{H.escape(p.get("placeholder", ""))}"{req}>')
        elif t == "TextAreaInput":
            cls += " field"
            inner = f'<textarea name="message" placeholder="{H.escape(p.get("placeholder", ""))}" aria-label="Message"></textarea>'
        elif t == "SiteButton":
            cls += " btn"
            inner = f'<button type="submit">{H.escape(p.get("label", "Send"))}</button>'
        elif t in ("ClassicSection", "Group", "Container", "HeaderSection", "FooterSection"):
            cls += " box" if t == "Container" else " sec"
            inner = self.mesh(cid)
            if t == "Container":
                bg = re.search(r"#%s\{--bg:var\(--color_(\d+)\);--alpha-bg:([\d.]+)" % re.escape(cid), self.html)
                if bg:
                    self.css.append(f"#{iid}{{background:rgba(var(--color_{bg.group(1)}),{bg.group(2)})}}")
        elif t == "WRichText":
            cls += " txt"
            inner = clean_rich(p.get("html", ""))
        elif t == "WPhoto":
            cls += " pic"
            key = (p["uri"], json.dumps(p.get("crop"), sort_keys=True))
            if key in self.imgmap:
                rel = self.imgmap[key]
            else:
                self.nimg += 1
                url, ext = img_url(p)
                rel = want(url, f"assets/img/{self.name}/{self.pfx}{self.nimg:02d}.{ext}")
                self.imgmap[key] = rel
            cw, ch = p.get("containerWidth") or p["width"], p.get("containerHeight") or p["height"]
            alt = H.escape(self.label)
            img = f'<img src="{rel}" width="{cw}" height="{ch}" alt="{alt}" loading="lazy" decoding="async">'
            link = p.get("link") or {}
            if link.get("href"):
                img = f'<a href="{H.escape(local_href(link["href"]))}">{img}</a>'
            inner = img
            # 좁은 화면(한 줄 레이아웃)에서 원래 크기보다 커지지 않게
            return f'<div class="{cls}" id="{iid}" style="max-width:{cw}px">{inner}</div>'
        elif t == "VideoPlayer":
            cls += " vid"
            src = p.get("src", "")
            vid = yt_id(src)
            if vid:
                inner = yt_iframe(vid, self.label)
            elif "video.wixstatic.com" in src:
                self.nvid += 1
                rel = want(src, f"assets/video/{self.name}-{self.nvid:02d}.mp4")
                inner = f'<video src="{rel}" controls playsinline preload="metadata"></video>'
        elif t == "Video":
            cls += " vid"
            if p.get("videoType") == "YOUTUBE" and p.get("videoId"):
                inner = yt_iframe(p["videoId"], self.label)
        elif t == "VectorImage":
            cls += " vec"
            m = re.search(r'id="%s".*?(<svg.*?</svg>)' % re.escape(cid), self.html, re.S)
            if m:
                inner = m.group(1)
            fill = re.search(r"#%s\{[^}]*--fill:([^;}]*)" % re.escape(cid), self.html)
            if fill:
                self.css.append(f"#{iid} svg{{fill:{fill.group(1)};width:100%;height:100%}}")
        elif t == "LinkBar":
            cls += " links"
            for i, im in enumerate(p.get("images", []), 1):
                href = im.get("link", {}).get("href", "#")
                label = "Instagram" if "instagram" in href else im.get("title", "")
                rel = want(f"https://static.wixstatic.com/media/{im['uri']}/v1/fill/w_120,h_120,q_90/icon.png",
                           f"assets/img/icon-{i}.png")
                inner += (f'<a href="{H.escape(href)}" target="_blank" rel="noopener" aria-label="{H.escape(label)}">'
                          f'<img src="{rel}" width="30" height="30" alt="{H.escape(label)}"></a>')
        else:
            return ""  # 폼 등 정적 사이트에서 동작하지 않는 요소는 제외
        return f'<{tag} class="{cls}" id="{iid}">{inner}</{tag}>'

    def body(self):
        roots = sorted({c["parent"] for c in self.child.values() if c["parent"].startswith("Container")})
        out = []
        for r in roots:
            out.append(self.mesh(r))
        return "\n".join(out)

# ---------- 공통 템플릿 ----------
def nav_html(current):
    def li(f, label, extra=""):
        cur = ' aria-current="page"' if f == current else ""
        return f'<li{extra}><a href="{f}.html"{cur}>{H.escape(label)}</a>'
    items = ['<li class="home"><a href="index.html">LEE IN KANG</a></li>']
    items += [li(f, l) + "</li>" for f, _, l in WORKS]
    sub = "".join(li(f, l) + "</li>" for f, _, l in ARCHIVE)
    open_cls = " open" if current in [a[0] for a in ARCHIVE] + ["memory"] else ""
    items.append(li("memory", "2013-2020", f' class="has-sub{open_cls}"') + f'<ul class="sub">{sub}</ul></li>')
    items += [li(f, l) + "</li>" for f, _, l in TAIL]
    return ('<button class="menu-btn" aria-expanded="false" aria-controls="site-nav">Menu</button>\n'
            '<nav id="site-nav"><ul>' + "".join(items) + "</ul></nav>")

def mobile_nav(current):
    """원본 Wix 모바일 메뉴: 왼쪽 위 햄버거 -> 전체 화면 메뉴(드로잉 배경 23%), 2013-2020 접기/펼치기."""
    def li(f, label):
        cur = ' aria-current="page"' if f == current else ""
        return f'<li><a href="{f}.html"{cur}>{H.escape(label)}</a></li>'
    open_ = current in [a[0] for a in ARCHIVE] + ["memory"]
    items = '<li><a href="index.html">LEE IN KANG</a></li>'
    items += "".join(li(f, l) for f, _, l in WORKS)
    items += ('<li class="m-has-sub' + (' open' if open_ else '') + '">'
              '<a href="memory.html"' + (' aria-current="page"' if current == "memory" else '') + '>2013-2020</a>'
              '<button class="m-chev" aria-label="2013-2020 펼치기" aria-expanded="' + ('true' if open_ else 'false') + '">'
              '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 6l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>'
              '</button><ul>' + "".join(li(f, l) for f, _, l in ARCHIVE) + '</ul></li>')
    items += "".join(li(f, l) for f, _, l in TAIL)
    return ('<button class="m-burger" aria-label="메뉴 열기" aria-expanded="false" aria-controls="m-menu"><span></span><span></span><span></span></button>\n'
            '<div class="m-menu" id="m-menu" hidden>'
            f'<div class="m-menu-bg" style="background-image:url({MENU_BG})"></div>'
            '<button class="m-close" aria-label="메뉴 닫기"></button>'
            '<nav aria-label="사이트 메뉴"><ul>' + items + '</ul></nav></div>\n'
            '<button class="m-top" aria-label="맨 위로">'
            '<svg viewBox="0 0 44 44" aria-hidden="true"><path d="M44 0H0v44h44" style="stroke-width:1"/>'
            '<path d="M30.588 27.233L22 18.366l-8.588 8.867-1.078-1.043L22 16.21l9.666 9.98-1.078 1.043z" style="stroke-width:1.5"/></svg></button>\n')

HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>/* 폰: 원본 Wix 모바일처럼 320px 화면을 기기 폭에 맞춰 확대 */
if (screen.width < 768) document.querySelector('meta[name=viewport]').setAttribute('content', 'width=320, user-scalable=yes');</script>
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter+Tight:wght@300;400;700&family=Noto+Sans+KR:wght@300;400;700&family=Open+Sans:wght@300;400&display=swap">
<link rel="stylesheet" href="assets/css/style.css">
{extra}</head>
<body class="{bodycls}">
"""
FOOT = """<script src="assets/js/site.js"></script>
</body>
</html>
"""

def write(name, title, desc, body, bodycls="", extra=""):
    path = os.path.join(OUT, name + ".html")
    with open(path, "w", encoding="utf8", newline="\n") as f:
        f.write(HEAD.format(title=H.escape(title), desc=H.escape(desc), bodycls=bodycls, extra=extra))
        f.write(body)
        f.write(FOOT)

MENU_BG = ""
MOBILE_HOME_BG = ""

def build():
    global MENU_BG, MOBILE_HOME_BG
    os.makedirs(OUT, exist_ok=True)
    MENU_BG = want("https://static.wixstatic.com/media/39d245_1ab8baeb1130480fa1d2cc92e23613b9~mv2.jpg/v1/fill/w_960,h_2076,al_c,q_85/file.jpg",
                   "assets/img/menu-bg.jpg")
    MOBILE_HOME_BG = want("https://static.wixstatic.com/media/39d245_c5a8ff504fdb4971bb7f904e9648e186~mv2.jpg/v1/fit/w_1280,h_2000,q_90/file.jpg",
                          "assets/img/home-bg-mobile.jpg")
    # 홈
    bg = want("https://static.wixstatic.com/media/39d245_d19da722e3264161a05c61fe3c4d73b9~mv2.jpg/v1/fit/w_2560,h_2560,q_90/file.jpg",
              "assets/img/home-bg.jpg")
    write("index", "leeinkang 이인강", "LEE IN KANG 이인강 — artist portfolio",
          f'<div class="home-bg home-bg-d" style="background-image:url({bg})"></div>'
          f'<div class="home-bg home-bg-m" style="background-image:url({MOBILE_HOME_BG})"></div>\n'
          + nav_html("index") + "\n" + mobile_nav("index"),
          bodycls="is-home")
    for name, _, label in ALL:
        pg = Page(name, label)
        main = pg.body()
        mmain, mcss = "", []
        if MOBILE_DIR:
            mp = Page(name, label, pdir=os.path.join(MOBILE_DIR, name), pfx="m-", imgmap=pg.imgmap)
            mmain = mp.body()
            mcss = mp.css
        title = pg.seo.get("title") or f"{label} | leeinkang"
        if "|" not in title:
            title = f"{title.strip()} | leeinkang"
        extra = ("<style>\n@media (min-width:1340px){\n" + "\n".join(dict.fromkeys(pg.css)) + "\n}\n"
                 + ("@media (max-width:767px){\n" + "\n".join(dict.fromkeys(mcss)) + "\n}\n" if mcss else "")
                 + "</style>\n")
        body = nav_html(name) + "\n" + mobile_nav(name) + f'<main id="main" class="d">\n{main}\n</main>\n'
        if mmain:
            body += f'<main class="m">\n{mmain}\n</main>\n'
        write(name, title, f"LEE IN KANG 이인강 — {label}", body,
              bodycls=f"page-{name}" + (" has-m" if mmain else ""), extra=extra)
        print(name, "img", pg.nimg, "vid", pg.nvid)
    if DOWNLOAD:
        download_all()

build()
