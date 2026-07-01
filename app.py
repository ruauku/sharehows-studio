
import io
import json
import zipfile
import urllib.parse
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
APP_DIR = Path(__file__).parent
DEFAULT_LOGO_PATH = APP_DIR / "sharehows_logo.png"

LEFT_X = 78
LOGO_Y = 835
TITLE_Y = 970
SUBTITLE_GAP = 34
LOGO_WIDTH_FIXED = 300

def first_existing(paths):
    for p in paths:
        if Path(p).expanduser().exists():
            return str(Path(p).expanduser())
    return None

def font_path(bold=True):
    if bold:
        return first_existing([
            "~/Library/Fonts/Pretendard-Bold.otf",
            "~/Library/Fonts/Pretendard-Bold.ttf",
            "/Library/Fonts/Pretendard-Bold.otf",
            "/Library/Fonts/Pretendard-Bold.ttf",
            "~/Library/Fonts/Pretendard-SemiBold.otf",
            "/Library/Fonts/Pretendard-SemiBold.otf",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        ])
    return first_existing([
        "~/Library/Fonts/Pretendard-Regular.otf",
        "~/Library/Fonts/Pretendard-Regular.ttf",
        "/Library/Fonts/Pretendard-Regular.otf",
        "/Library/Fonts/Pretendard-Regular.ttf",
        "~/Library/Fonts/Pretendard-Medium.otf",
        "/Library/Fonts/Pretendard-Medium.otf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ])

BOLD_FONT = font_path(True)
REG_FONT = font_path(False)

def get_font(size, bold=True):
    try:
        return ImageFont.truetype(BOLD_FONT if bold else REG_FONT, size)
    except Exception:
        return ImageFont.load_default()

def smart_query(issue):
    title = issue.get("title") or issue.get("thumbnail_title") or issue.get("card_title") or ""
    tags = issue.get("tags", [])
    tag_text = " ".join(tags) if isinstance(tags, list) else str(tags)
    if "BTS" in title or "BTS" in tag_text:
        return "BTS official press photo Billboard 2026"
    if "청룡" in title:
        return "Blue Dragon Series Awards official photo"
    if "김무열" in title or "참교육" in title:
        return "Kim Moo Yul Netflix official press photo"
    if "문채원" in title:
        return "Moon Chae Won official press photo"
    if "류준열" in title:
        return "Ryu Jun Yeol Galaxy Corporation official press photo"
    return f"{title} official press photo"

def google_images_url(query):
    return "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(query)

def naver_images_url(query):
    return "https://search.naver.com/search.naver?where=image&query=" + urllib.parse.quote(query)

def cover_crop_manual(img, zoom=1.0, offset_x=0, offset_y=0, size=(W, H)):
    img = img.convert("RGB")
    sw, sh = img.size
    tw, th = size
    base_scale = max(tw / sw, th / sh)
    scale = base_scale * zoom
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)

    max_x = max(0, (nw - tw) // 2)
    max_y = max(0, (nh - th) // 2)
    center_left = (nw - tw) // 2
    center_top = (nh - th) // 2

    left = int(center_left - (offset_x / 100) * max_x)
    top = int(center_top - (offset_y / 100) * max_y)
    left = max(0, min(left, nw - tw))
    top = max(0, min(top, nh - th))
    return img.crop((left, top, left + tw, top + th))

def wrap_by_pixel(text, font, max_width):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, cur = [], ""
    for ch in str(text):
        test = cur + ch
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines

def draw_wrapped(draw, xy, text, font, fill, max_width, line_spacing=8, max_lines=2):
    x, y = xy
    lines = []
    for block in str(text).split("\n"):
        lines.extend(wrap_by_pixel(block, font, max_width))
    lines = lines[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        box = draw.textbbox((x, y), line, font=font)
        y += (box[3] - box[1]) + line_spacing
    return y

def fit_logo(logo, target_w=LOGO_WIDTH_FIXED):
    logo = logo.convert("RGBA")
    w, h = logo.size
    scale = target_w / w
    nw, nh = int(w * scale), int(h * scale)
    return logo.resize((nw, nh), Image.LANCZOS)

def add_text_zone_gradient(img, strength=0.35):
    """
    글씨가 들어가는 하단 영역에만 최대 35% 검은 그라데이션.
    위는 자연스럽게 투명, 글자 주변으로 내려갈수록 어두워짐.
    """
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = grad.load()
    start_y = 760
    end_y = H
    max_alpha = int(255 * strength)
    for y in range(start_y, end_y):
        t = (y - start_y) / (end_y - start_y)
        # 부드럽게 하단으로 갈수록 진해짐
        alpha = int(max_alpha * (t ** 1.35))
        for x in range(W):
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(img, grad)

def make_card(
    bg_img,
    title,
    subtitle,
    logo_img=None,
    title_size=70,
    subtitle_size=38,
    zoom=1.0,
    offset_x=0,
    offset_y=0,
    text_gradient=True,
    gradient_strength=35,
):
    img = cover_crop_manual(bg_img, zoom=zoom, offset_x=offset_x, offset_y=offset_y).convert("RGBA")

    # 전체 이미지에는 아주 약한 기본 딤만 적용
    base_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 18))
    img = Image.alpha_composite(img, base_overlay)

    if text_gradient:
        img = add_text_zone_gradient(img, strength=gradient_strength / 100)

    # 텍스트 영역 부드러운 음영
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((0, 770, W, H), fill=(0, 0, 0, 38))
    shadow = shadow.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img, shadow)

    draw = ImageDraw.Draw(img)

    if logo_img is not None:
        logo = fit_logo(logo_img, target_w=LOGO_WIDTH_FIXED)
        img.alpha_composite(logo, (LEFT_X, LOGO_Y))
    else:
        draw.text((LEFT_X, LOGO_Y), "ShareHows", font=get_font(48, True), fill=(255, 255, 255, 245))

    y = TITLE_Y
    y = draw_wrapped(
        draw, (LEFT_X, y), title, get_font(title_size, True),
        (255, 255, 255, 255), 930, line_spacing=4, max_lines=2
    )
    y += SUBTITLE_GAP
    draw_wrapped(
        draw, (LEFT_X, y), subtitle, get_font(subtitle_size, False),
        (255, 255, 255, 240), 930, line_spacing=10, max_lines=2
    )
    return img.convert("RGB")

def clean_issue(issue):
    return {
        "title": issue.get("thumbnail_title") or issue.get("title") or issue.get("card_title", ""),
        "subtitle": issue.get("subtitle") or issue.get("body_text", "")[:80],
        "query": issue.get("image_query") or smart_query(issue),
    }

st.set_page_config(page_title="ShareHows Studio v11", layout="wide")
st.title("ShareHows Studio v11")
st.caption("글씨 영역 검은 그라데이션 0~70% 조절 버전")

with st.sidebar:
    st.subheader("디자인 설정")
    title_size = st.slider("주제목 크기", 54, 86, 70, 1)
    subtitle_size = st.slider("소제목 크기", 28, 48, 38, 1)
    gradient_strength = st.slider("글씨 영역 검은 그라데이션", 0, 70, 35, 5)
    text_gradient = gradient_strength > 0
    st.write("로고:", "자동 적용됨 · 300px 고정")
    st.write("폰트:", "Pretendard 감지됨" if "Pretendard" in str(BOLD_FONT) else "Pretendard 미감지 → Apple SD Gothic 대체")

logo_img = Image.open(DEFAULT_LOGO_PATH) if DEFAULT_LOGO_PATH.exists() else None

sample_json = {
  "date": "2026년 7월 2일 (목)",
  "issues": [
    {"rank": 1, "category": "K-POP / 글로벌", "thumbnail_title": "BTS, 롤링스톤스 기록 넘고 역대 최고 월 수익 달성", "subtitle": "12회 공연으로 약 1,278억 원을 기록하며 빌보드 그룹 최고 기록을 새로 썼다.", "tags":["BTS","빌보드"]},
    {"rank": 2, "category": "드라마 / 시상식", "thumbnail_title": "청룡시리즈어워드 후보 공개, 남우주연상 경쟁 본격화", "subtitle": "현빈·김우빈·박해수·김선호 등 7월 31일 시상식에서 맞붙는다."}
  ]
}

json_text = st.text_area("뉴스 JSON 붙여넣기", value=json.dumps(sample_json, ensure_ascii=False, indent=2), height=260)

try:
    parsed = json.loads(json_text)
    issues = [clean_issue(x) for x in parsed.get("issues", [])]
except Exception as e:
    st.error(f"JSON 파싱 오류: {e}")
    issues = []

st.divider()

if issues:
    st.subheader("카드별 실제 사진 업로드 / 위치 조정")
    uploaded = []
    settings = []

    for idx, issue in enumerate(issues):
        with st.expander(f"{idx+1}. {issue['title']}", expanded=True):
            st.markdown(f"**추천 이미지 검색어:** `{issue['query']}`")
            st.markdown(f"[Google 이미지 검색]({google_images_url(issue['query'])})  ·  [Naver 이미지 검색]({naver_images_url(issue['query'])})")

            c1, c2 = st.columns([1, 2])
            with c1:
                file = st.file_uploader(f"사진 업로드 #{idx+1}", type=["jpg", "jpeg", "png", "webp"], key=f"up_{idx}")
                uploaded.append(file)
                zoom = st.slider("확대/축소", 1.0, 2.5, 1.0, 0.05, key=f"zoom_{idx}")
                ox = st.slider("사진 좌우 위치", -100, 100, 0, 1, key=f"ox_{idx}")
                oy = st.slider("사진 상하 위치", -100, 100, 0, 1, key=f"oy_{idx}")
                settings.append((zoom, ox, oy))

            with c2:
                issue["title"] = st.text_input("주제목", issue["title"], key=f"title_{idx}")
                issue["subtitle"] = st.text_area("소제목", issue["subtitle"], key=f"sub_{idx}", height=80)
                if file is not None:
                    preview = make_card(
                        Image.open(file), issue["title"], issue["subtitle"],
                        logo_img=logo_img, title_size=title_size, subtitle_size=subtitle_size,
                        zoom=zoom, offset_x=ox, offset_y=oy, text_gradient=text_gradient, gradient_strength=gradient_strength
                    )
                    st.image(preview, caption="실시간 미리보기", use_container_width=True)

    if st.button("카드뉴스 생성", type="primary"):
        if any(f is None for f in uploaded):
            st.warning("모든 카드에 사진을 업로드해주세요.")
        else:
            zip_buffer = io.BytesIO()
            cards = []
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
                for idx, (issue, file, setting) in enumerate(zip(issues, uploaded, settings), start=1):
                    zoom, ox, oy = setting
                    card = make_card(
                        Image.open(file), issue["title"], issue["subtitle"],
                        logo_img=logo_img, title_size=title_size, subtitle_size=subtitle_size,
                        zoom=zoom, offset_x=ox, offset_y=oy, text_gradient=text_gradient, gradient_strength=gradient_strength
                    )
                    img_buf = io.BytesIO()
                    card.save(img_buf, format="PNG")
                    img_bytes = img_buf.getvalue()
                    filename = f"sharehows_{idx:02d}.png"
                    z.writestr(filename, img_bytes)
                    cards.append((filename, img_bytes))
                z.writestr("caption.txt", "오늘의 ShareHows 카드뉴스입니다.\n")
                z.writestr("hashtags.txt", "#ShareHows #카드뉴스 #오늘의뉴스\n")

            st.success("생성 완료")
            st.download_button("ZIP 다운로드", zip_buffer.getvalue(), "sharehows_cards.zip", "application/zip")
            cols = st.columns(2)
            for i, (filename, img_bytes) in enumerate(cards):
                with cols[i % 2]:
                    st.image(img_bytes, caption=filename, use_container_width=True)
else:
    st.info("JSON에 issues 배열이 필요합니다.")
