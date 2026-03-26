# ╔══════════════════════════════════════════════════════════════════════╗
# ║    베베노리 (BebeNori) v3.0 — 서울형 키즈카페 AI 큐레이터 최종판       ║
# ║    팀: 2모3촌  |  Google Colab + cloudflared 완전 통코드            ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# ═══════════════════════════════════════════════════════════════════
#  [Colab 실행 가이드]
# ═══════════════════════════════════════════════════════════════════
# # ── 패키지 설치 (최초 1회) ─────────────────────────────────────
# !pip install streamlit chromadb sentence-transformers openai pandas -q
#
# # ── 파일 업로드 (/content/ 폴더에 아래 파일 필요) ───────────────
# #   places.csv, place_features.csv, review_docs.csv,
# #   baby_development_final.csv, bebenori_mascot.png,
# #   grid_pattern_png.png, moon_balloon.png,
# #   icon_geometry.png, icon_zigzag.png,
# #   icon_spiral_arrow.png, icon_cactus.png
#
# # ── HuggingFace 토큰 설정 ──────────────────────────────────────
# import os; os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN_HERE"
#
# # ── 앱 실행 ──────────────────────────────────────────────────────
# !streamlit run app.py --server.port 8501 &>/content/st.log &
# import time; time.sleep(5)
#
# # ── cloudflared 터널 (비밀번호 없이 접속 가능) ─────────────────
# !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
# !dpkg -i cloudflared-linux-amd64.deb
# !cloudflared tunnel --url http://localhost:8501 &
# import time; time.sleep(6)
# # 출력된 https://xxxx.trycloudflare.com 주소로 바로 접속!
#
# # ── (대안) localtunnel ─────────────────────────────────────────
# !npm install localtunnel -q
# import subprocess; p = subprocess.Popen(['npx','lt','--port','8501'],stdout=subprocess.PIPE)
# print(p.stdout.readline().decode())
# ═══════════════════════════════════════════════════════════════════

import os, base64
from pathlib import Path
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────
# 0. 페이지 설정
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="베베노리",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# 1. 파일 경로 상수
# ─────────────────────────────────────────────────────────────────
PLACES_CSV      = "places.csv"
FEATURES_CSV    = "place_features.csv"
REVIEWS_CSV     = "review_docs.csv"
DEV_CSV         = "baby_development_final.csv"
MASCOT_FILE     = "bebenori_mascot.png"
GRID_FILE       = "grid_pattern_png.png"
MOON_FILE       = "moon_balloon.png"
GEO_FILE        = "icon_geometry.png"
ZIGZAG_FILE     = "icon_zigzag.png"
SPIRAL_FILE     = "icon_spiral_arrow.png"
CACTUS_FILE     = "icon_cactus.png"
CHROMA_DIR      = "./bebenori_db"
FALLBACK_IMG    = "https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&w=800&q=80"
PUBLIC_BOOKING  = "https://yeyak.seoul.go.kr"

HF_TOKEN = os.environ.get("HF_TOKEN", "hf_YOUR_TOKEN_HERE")

# ─────────────────────────────────────────────────────────────────
# 2. 이미지 → base64
# ─────────────────────────────────────────────────────────────────
def img_b64(path: str, fallback: str = "") -> str:
    if Path(path).exists():
        ext = "jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "png"
        with open(path, "rb") as f:
            return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
    return fallback

def img_tag(path: str, cls: str = "", style: str = "", fallback: str = "") -> str:
    src = img_b64(path, fallback)
    if not src:
        return ""
    return f'<img src="{src}" class="{cls}" style="{style}" alt="">'

# ─────────────────────────────────────────────────────────────────
# 3. 에셋 로드
# ─────────────────────────────────────────────────────────────────
GRID_B64    = img_b64(GRID_FILE)
MASCOT_B64  = img_b64(MASCOT_FILE, FALLBACK_IMG)
MOON_B64    = img_b64(MOON_FILE)
GEO_B64     = img_b64(GEO_FILE)
ZIGZAG_B64  = img_b64(ZIGZAG_FILE)
SPIRAL_B64  = img_b64(SPIRAL_FILE)
CACTUS_B64  = img_b64(CACTUS_FILE)

GRID_CSS = f"url('{GRID_B64}')" if GRID_B64 else "none"

# ─────────────────────────────────────────────────────────────────
# 4. 전역 CSS
# ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Nanum+Square+Round:wght@400;700;800&display=swap');

/* ── 기반 ────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
    font-family: 'Nanum Square Round', 'Apple SD Gothic Neo', sans-serif;
}}

/* ── 전체 배경: 그리드 패턴 ──────────────────────────────────── */
.stApp {{
    background-color: #FEFCF3 !important;
    background-image: {GRID_CSS} !important;
    background-repeat: repeat !important;
    background-size: 480px !important;
    background-attachment: fixed !important;
}}
[data-testid="stAppViewContainer"] {{
    background: transparent !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container   {{ padding-top: 0 !important; max-width: 1160px; }}

/* ── 사이드바 ────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(175deg, #EBF4FF 0%, #FFF9E6 100%) !important;
    border-right: 2px solid #D6E8FF !important;
}}
[data-testid="stSidebar"] * {{ color: #2C4A7C !important; }}
[data-testid="stSidebar"] .stButton > button {{
    background: #6B9DD4 !important;
    color: #fff !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 14px !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: #5188C0 !important;
}}

/* ── 헤더 ────────────────────────────────────────────────────── */
.bebe-header {{
    background: linear-gradient(130deg, #6B9DD4 0%, #5188C0 40%, #3B6FAE 100%);
    border-radius: 0 0 40px 40px;
    padding: 32px 40px 40px;
    margin: -1rem -1rem 0;
    position: relative; overflow: hidden;
    display: flex; align-items: center; gap: 28px;
    box-shadow: 0 8px 32px rgba(107, 157, 212, .35);
    border-bottom: 3px solid rgba(255,255,255,.2);
}}
.header-bg-deco {{
    position: absolute; inset: 0; pointer-events: none;
    background: radial-gradient(circle at 80% 20%, rgba(255,255,255,.12) 0%, transparent 60%),
                radial-gradient(circle at 10% 80%, rgba(242,183,5,.15) 0%, transparent 40%);
}}
.header-mascot {{
    width: 110px; height: 110px; object-fit: contain;
    flex-shrink: 0; position: relative; z-index: 2;
    filter: drop-shadow(0 6px 18px rgba(0,0,0,.25));
    animation: float 3.5s ease-in-out infinite;
}}
@keyframes float {{
    0%,100% {{ transform: translateY(0); }}
    50%      {{ transform: translateY(-8px); }}
}}
.header-content {{ position: relative; z-index: 2; flex: 1; }}
.header-brand {{
    font-family: 'Jua', cursive;
    font-size: 3em; color: #FFFFFF;
    line-height: 1; margin-bottom: 6px;
    text-shadow: 0 3px 12px rgba(0,0,0,.3), 0 1px 0 rgba(0,0,0,.2);
}}
.header-tagline {{
    font-size: .95em; color: rgba(255,255,255,.95);
    font-weight: 700; line-height: 1.65;
    text-shadow: 0 1px 6px rgba(0,0,0,.2);
}}
.header-pills {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
.header-pill {{
    background: rgba(255,255,255,.22);
    backdrop-filter: blur(6px);
    color: #ffffff; font-size: .73em; font-weight: 800;
    padding: 5px 13px; border-radius: 20px;
    border: 1px solid rgba(255,255,255,.35);
    text-shadow: 0 1px 3px rgba(0,0,0,.15);
}}
.header-deco-moon {{
    position: absolute; right: 120px; top: 10px;
    width: 80px; opacity: .55; z-index: 1;
    animation: float 4s ease-in-out infinite 1s;
}}
.header-deco-zigzag {{
    position: absolute; right: 28px; bottom: 16px;
    width: 52px; opacity: .45; z-index: 1;
    animation: float 5s ease-in-out infinite .5s;
}}

/* ── 통계 바 ─────────────────────────────────────────────────── */
.stat-bar {{
    display: flex; gap: 12px; margin: 22px 0 0; flex-wrap: wrap;
}}
.stat-card {{
    background: rgba(255,255,255,.85);
    backdrop-filter: blur(8px);
    border: 1.5px solid #D6E8FF;
    border-radius: 20px; padding: 12px 18px;
    text-align: center; flex: 1; min-width: 100px;
    box-shadow: 0 3px 12px rgba(107,157,212,.1);
    transition: transform .2s;
}}
.stat-card:hover {{ transform: translateY(-3px); }}
.stat-num {{ display:block; font-size:1.55em; font-weight:800; color:#6B9DD4; }}
.stat-lbl {{ font-size:.7em; color:#A8C4E8; font-weight:700; margin-top:2px; }}

/* ── 섹션 구분 라벨 ──────────────────────────────────────────── */
.section-label {{
    display: flex; align-items: center; gap: 10px;
    font-family: 'Jua', cursive;
    font-size: 1.2em; color: #2C4A7C;
    margin: 28px 0 14px; padding: 12px 18px;
    background: rgba(255,255,255,.8);
    border-radius: 16px; border-left: 5px solid #F2B705;
    box-shadow: 0 3px 12px rgba(107,157,212,.08);
}}
.section-label-icon {{
    width: 32px; height: 32px; object-fit: contain;
}}

/* ── 채팅 래퍼 ───────────────────────────────────────────────── */
.chat-outer {{
    background: rgba(255,255,255,.88);
    backdrop-filter: blur(8px);
    border-radius: 28px; padding: 24px 28px;
    margin: 20px 0 18px;
    border: 1.5px solid #D6E8FF;
    box-shadow: 0 6px 24px rgba(107,157,212,.1);
}}
.chat-label {{
    font-family: 'Jua', cursive;
    font-size: 1.05em; color: #2C4A7C; margin-bottom: 6px;
    display: flex; align-items: center; gap: 8px;
}}
.chat-hint {{
    font-size: .78em; color: #A8C4E8; line-height: 1.7; margin-bottom: 14px;
}}

/* ── 대화 버블 ───────────────────────────────────────────────── */
.bubble-user {{
    background: #6B9DD4;
    color: #ffffff;
    border-radius: 22px 4px 22px 22px;
    padding: 13px 18px; margin: 8px 0 4px;
    font-size: .9em; max-width: 75%; margin-left: auto;
    box-shadow: 0 4px 14px rgba(107,157,212,.35);
    line-height: 1.65; font-weight: 700;
}}
.bubble-ai {{
    background: linear-gradient(135deg, #FFFDE7 0%, #FFF8CC 100%);
    border: 1.5px solid #F2B705;
    border-radius: 4px 22px 22px 22px;
    padding: 16px 20px; margin: 4px 0 16px;
    font-size: .9em; color: #3D2B00; line-height: 1.8;
    box-shadow: 0 4px 18px rgba(242,183,5,.15);
    max-width: 88%;
}}
.bubble-ai-label {{
    font-family: 'Jua', cursive;
    font-size: .8em; color: #C17F00; margin-bottom: 8px;
    display: flex; align-items: center; gap: 5px; font-weight: 800;
}}

/* ── 장소 카드 ───────────────────────────────────────────────── */
.place-card {{
    background: rgba(255,255,255,.92);
    border-radius: 26px; overflow: hidden;
    border: 1.5px solid #D6E8FF;
    box-shadow: 0 6px 24px rgba(107,157,212,.1);
    transition: transform .22s, box-shadow .22s;
    height: 100%;
}}
.place-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 16px 40px rgba(107,157,212,.22);
}}
.card-img-wrap {{ position: relative; height: 196px; overflow: hidden; }}
.card-img {{
    width: 100%; height: 100%; object-fit: cover;
    transition: transform .4s;
}}
.place-card:hover .card-img {{ transform: scale(1.05); }}
.card-badge-row {{
    position: absolute; top: 12px; left: 12px;
    display: flex; gap: 6px; flex-wrap: wrap;
}}
.cbdg {{
    padding: 4px 10px; border-radius: 20px;
    font-size: .68em; font-weight: 800;
    backdrop-filter: blur(6px);
}}
.cbdg-blue   {{ background: rgba(107,157,212,.92); color:#fff; }}
.cbdg-yellow {{ background: rgba(242,183,5,.92);   color:#fff; }}
.cbdg-green  {{ background: rgba(56,142,60,.88);   color:#fff; }}
.cbdg-dark   {{ background: rgba(0,0,0,.55);        color:#fff; }}
.card-rev {{
    position: absolute; bottom: 10px; right: 10px;
    background: rgba(255,255,255,.92); color: #6B9DD4;
    border-radius: 14px; padding: 3px 10px;
    font-size: .7em; font-weight: 800;
}}
.card-body {{ padding: 18px 20px 20px; }}
.card-name {{
    font-family: 'Jua', cursive;
    font-size: 1.1em; color: #1A3A6B; margin-bottom: 4px; line-height: 1.3;
}}
.card-loc  {{ font-size: .76em; color: #BDBDBD; margin-bottom: 10px; }}
.chip-row  {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }}
.chip {{ padding: 3px 10px; border-radius: 12px; font-size: .7em; font-weight: 700; }}
.chip-b {{ background:#EBF4FF; color:#2C4A7C; border:1px solid #D6E8FF; }}
.chip-y {{ background:#FFF8CC; color:#7A5700; border:1px solid #F2B705; }}
.chip-g {{ background:#E8F5E9; color:#1B5E20; border:1px solid #A5D6A7; }}
.chip-p {{ background:#F3E5F5; color:#6A1B9A; border:1px solid #CE93D8; }}

/* ── AI 추천 박스 ────────────────────────────────────────────── */
.rec-box {{
    background: linear-gradient(135deg,#FFFDE7,#FFF8CC);
    border-left: 4px solid #F2B705;
    border-radius: 0 16px 16px 0;
    padding: 12px 15px; margin: 10px 0;
}}
.rec-lbl {{ font-size:.72em; font-weight:800; color:#C17F00; margin-bottom:4px; }}
.rec-txt  {{ font-size:.82em; color:#5D4000; line-height:1.75; }}

/* ── 액션 버튼 ───────────────────────────────────────────────── */
.act-row {{ display: flex; gap: 8px; margin-top: 12px; }}
.btn-main {{
    flex: 1; text-align: center; background: #6B9DD4;
    color: #fff !important; padding: 11px 8px;
    border-radius: 14px; font-weight: 800; font-size: .8em;
    text-decoration: none; display: block;
    box-shadow: 0 4px 12px rgba(107,157,212,.35);
    transition: background .2s;
}}
.btn-main:hover {{ background: #5188C0; text-decoration: none; }}
.btn-sub {{
    text-align: center; background: #FFF8CC;
    color: #7A5700 !important; padding: 11px 13px;
    border-radius: 14px; font-weight: 800; font-size: .8em;
    text-decoration: none; display: block;
    border: 1.5px solid #F2B705; transition: background .2s;
}}
.btn-sub:hover {{ background: #FFF0A0; text-decoration: none; }}

/* ── 발달 대시보드 ───────────────────────────────────────────── */
.dev-wrap {{
    background: rgba(255,255,255,.9);
    border-radius: 28px; padding: 28px 30px;
    margin: 24px 0;
    border: 1.5px solid #D6E8FF;
    box-shadow: 0 6px 24px rgba(107,157,212,.09);
}}
.dev-title-row {{
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 18px; margin-bottom: 22px;
    border-bottom: 2px dashed #D6E8FF;
}}
.dev-title-main {{
    font-family: 'Jua', cursive; font-size: 1.25em; color: #1A3A6B; margin: 0;
}}
.dev-title-sub {{ font-size: .78em; color: #A8C4E8; font-weight: 700; margin-top: 3px; }}
.dev-age-pill {{
    margin-left: auto;
    background: linear-gradient(135deg,#6B9DD4,#5188C0);
    color: #fff; font-family:'Jua',cursive; font-size:1em;
    padding: 8px 20px; border-radius: 20px; white-space: nowrap;
    box-shadow: 0 3px 10px rgba(107,157,212,.3);
}}

.dom-grid {{
    display: grid; gap: 14px;
    grid-template-columns: repeat(auto-fill, minmax(260px,1fr));
}}
.dom-card {{
    border-radius: 20px; padding: 18px 18px 16px;
    border: 1.5px solid transparent;
    transition: transform .2s, box-shadow .2s;
    position: relative; overflow: hidden;
}}
.dom-card::after {{
    content: ''; position: absolute;
    top: -24px; right: -24px;
    width: 70px; height: 70px; border-radius: 50%;
    background: rgba(255,255,255,.25);
}}
.dom-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 26px rgba(0,0,0,.1); }}

.dom-gross  {{ background: linear-gradient(135deg,#E3F2FD,#BBDEFB); border-color:#90CAF9; }}
.dom-fine   {{ background: linear-gradient(135deg,#E8EAF6,#C5CAE9); border-color:#9FA8DA; }}
.dom-lang   {{ background: linear-gradient(135deg,#FFF9C4,#FFF176); border-color:#FDD835; }}
.dom-cog    {{ background: linear-gradient(135deg,#E8F5E9,#C8E6C9); border-color:#A5D6A7; }}
.dom-social {{ background: linear-gradient(135deg,#FCE4EC,#F8BBD0); border-color:#F48FB1; }}
.dom-motor  {{ background: linear-gradient(135deg,#FFF3E0,#FFE0B2); border-color:#FFCC80; }}

.dom-icon    {{ font-size:2em; display:block; margin-bottom:8px; }}
.dom-title   {{ font-family:'Jua',cursive; font-size:.95em; margin-bottom:8px; }}
.dom-gross  .dom-title {{ color:#1565C0; }}
.dom-fine   .dom-title {{ color:#283593; }}
.dom-lang   .dom-title {{ color:#F57F17; }}
.dom-cog    .dom-title {{ color:#2E7D32; }}
.dom-social .dom-title {{ color:#880E4F; }}
.dom-motor  .dom-title {{ color:#E65100; }}
.dom-text {{ font-size:.76em; line-height:1.75; color:#424242; }}

.dom-bar {{ height:5px; border-radius:3px; margin-top:12px;
    background:rgba(255,255,255,.45); overflow:hidden; }}
.dom-fill {{
    height:100%; border-radius:3px;
    background:rgba(255,255,255,.75);
    animation: barfill 1.4s ease-out forwards;
}}
@keyframes barfill {{ from{{width:0}} }}

/* 감각 칩 */
.sense-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; }}
.sense-chip {{
    flex:1; min-width:110px;
    background:rgba(255,255,255,.85); border-radius:14px;
    padding:12px 14px; border:1.5px solid #D6E8FF;
    box-shadow:0 2px 8px rgba(107,157,212,.07);
}}
.sense-icon  {{ font-size:1.4em; display:block; margin-bottom:3px; }}
.sense-title {{ font-size:.7em; font-weight:800; color:#2C4A7C; margin-bottom:2px; }}
.sense-text  {{ font-size:.67em; color:#757575; line-height:1.55; }}

/* ── 빈 결과 ─────────────────────────────────────────────────── */
.empty-box {{
    text-align:center; padding:52px 24px;
    background:rgba(255,255,255,.85); border-radius:24px;
    border:1.5px dashed #D6E8FF; margin:20px 0;
}}
.empty-ico {{ font-size:3.5em; display:block; margin-bottom:12px; }}
.empty-msg {{ font-size:1.05em; font-weight:800; color:#6B9DD4; margin-bottom:8px; }}
.empty-sub {{ font-size:.85em; color:#BDBDBD; line-height:1.75; }}

/* ── 결과 헤더 ───────────────────────────────────────────────── */
.result-header {{
    display:flex; align-items:center; gap:10px;
    background:rgba(255,255,255,.85); border-radius:16px;
    padding:14px 20px; margin-bottom:18px;
    border-left:5px solid #6B9DD4;
    border-top:1.5px solid #D6E8FF;
    border-right:1.5px solid #D6E8FF;
    border-bottom:1.5px solid #D6E8FF;
    font-family:'Jua',cursive; font-size:1.1em; color:#1A3A6B;
    box-shadow:0 3px 12px rgba(107,157,212,.08);
}}
.result-cnt {{ margin-left:auto; color:#6B9DD4; font-size:1.15em; }}

/* ── Streamlit 위젯 오버라이드 ──────────────────────────────── */
.stButton > button {{
    background: #6B9DD4 !important; color: #fff !important;
    font-weight: 800 !important; border: none !important;
    border-radius: 14px !important;
    font-family: 'Nanum Square Round', sans-serif !important;
    box-shadow: 0 4px 12px rgba(107,157,212,.28) !important;
    transition: background .2s !important;
}}
.stButton > button:hover {{ background: #5188C0 !important; }}
.stTextInput > div > div > input {{
    border-radius: 14px !important;
    border: 1.5px solid #6B9DD4 !important;
    background: rgba(255,255,255,.9) !important;
    color: #1A3A6B !important;
    font-family: 'Nanum Square Round', sans-serif !important;
}}
.stSelectbox > div > div {{ border-radius:14px !important; }}
.stSlider > div {{ color: #2C4A7C !important; }}
div[data-testid="stExpander"] {{
    border: 1.5px solid #D6E8FF !important;
    border-radius: 18px !important;
    background: rgba(255,255,255,.85) !important;
}}
hr {{ border:none; border-top:2px dashed #D6E8FF !important; margin:26px 0; }}

/* ── 푸터 ────────────────────────────────────────────────────── */
.bebe-footer {{
    text-align:center; padding:28px 0 22px;
    color:#A8C4E8; font-size:.76em; line-height:2.1;
}}
.bebe-footer strong {{ color:#6B9DD4; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 5. 상수 및 매핑
# ─────────────────────────────────────────────────────────────────

# 개월수 슬라이더 눈금 → 레이블 / dev_csv age 컬럼 / 연나이(세) 범위
AGE_MARKS = [0, 3, 6, 9, 12, 18, 24, 30, 36, 48]
AGE_LABEL_MAP = {
    0: "0개월", 3: "3개월", 6: "6개월", 9: "9개월",
    12: "12개월", 18: "18개월", 24: "24개월",
    30: "30개월", 36: "36개월", 48: "48개월+",
}

def months_to_dev_age(m: int) -> str:
    """개월수 → baby_development_final.csv age 컬럼 매핑."""
    if m <= 1:   return "0~1"
    if m <= 3:   return "1~3"
    if m <= 6:   return "4~6"
    if m <= 9:   return "7~9"
    if m <= 12:  return "10~12"
    if m <= 24:  return "13~24"
    return "25~36"

def months_to_year_range(m: int) -> tuple:
    """개월수 → 장소 age_min/age_max(연나이) 필터 범위."""
    yr = m / 12
    return (max(0, yr - 0.5), yr + 0.5)

# feature → (아이콘, 레이블)
FEAT_LABEL = {
    "parking_available":         ("🅿", "주차 가능"),
    "reservation_available":     ("📋", "예약 가능"),
    "weekend_operation":         ("📅", "주말 운영"),
    "toddler_friendly":          ("👶", "영유아 친화"),
    "toddler_positive":          ("⭐", "영유아 칭찬"),
    "preschool_friendly":        ("🧒", "유아 적합"),
    "lower_elementary_friendly": ("🎒", "초등 저학년"),
    "program_info_available":    ("🎨", "프로그램"),
    "group_visit_available":     ("👨‍👩‍👧", "단체 가능"),
    "spacious_positive":         ("🏟", "넓어요"),
    "safety_positive":           ("🛡", "안전"),
    "cleanliness_positive":      ("✨", "깨끗해요"),
    "active_play_positive":      ("🏃", "놀이 풍부"),
}
FEAT_SKIP = {
    "district", "has_phone", "guardian_rule_mentioned",
    "socks_rule_mentioned", "cleanliness_negative", "crowded_warning",
}

DISTRICTS = ["전체"] + sorted([
    "강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구",
    "노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구",
    "성동구","성북구","송파구","양천구","영등포구","용산구","은평구",
    "종로구","중구","중랑구",
])

# 발달 도메인 설정
DOMAINS = [
    ("gross_motor_skills",   "🦵", "대근육 발달", "dom-gross",  82),
    ("fine_motor_skills",    "✋", "소근육 발달", "dom-fine",   74),
    ("language_development", "🗣", "언어 발달",   "dom-lang",   70),
    ("cognitive_development","🧠", "인지 발달",   "dom-cog",    78),
    ("social_development",   "👫", "사회성 발달", "dom-social", 67),
    ("motor_development",    "🏃", "전반 운동",   "dom-motor",  85),
]
SENSES = [
    ("vision",  "👁", "시각"),
    ("hearing", "👂", "청각"),
    ("smell",   "👃", "후각"),
    ("taste",   "👅", "미각"),
    ("touch",   "🤚", "촉각"),
]

# ─────────────────────────────────────────────────────────────────
# 6. 시스템 프롬프트 (요구사항 그대로)
# ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Role
너는 서울시 공공 데이터를 기반으로 부모님들에게 아이와 방문하기 좋은 키즈카페를 추천하는 AI 이모삼촌 '베베노리(BebeNori)'야. 너의 정체성은 아이를 진심으로 아끼는 '2모3촌(이모 2명, 삼촌 3명)'으로, 전문적이면서도 아주 다정하고 친절한 말투를 사용해야 해.

Task
사용자의 입력(지역, 아이 연령, 특징 등)을 바탕으로 제공된 [Context] 내에서 가장 적합한 서울형 키즈카페를 추천해줘. 단순한 정보 나열이 아니라, 해당 시설이 아이의 발달 단계에 어떤 긍정적인 영향을 주는지 반드시 포함해야 해.

RAG
1. [Place_DB]: 장소명, 주소, 주요 시설, 이용료, 예약 링크 정보가 포함됨.
2. [Development_DB]: 연령별(개월수) 발달 특징 및 추천 활동 가이드가 포함됨.
3. 답변 구성 시: [Place_DB]의 '주요 시설'과 [Development_DB]의 '발달 특징'을 논리적으로 연결해. (예: "이곳의 트램펄린 시설은 24개월 아이의 균형 감각과 대근육 발달에 큰 도움을 줍니다.")

Constraints (반드시 지킬 것)
1. Hallucination 방지: 제공된 [Context]에 없는 장소는 절대 추천하지 마. 모르는 정보라면 정직하게 모른다고 답하고 서울시 공공서비스 예약 사이트를 안내해.
2. 정확도: 추천하는 장소가 사용자가 언급한 지역 및 연령 기준에 부합하는지 최종 확인해.
3. 페르소나: "조카를 생각하는 마음으로 엄선했어요", "부모님, 오늘 고생 많으셨죠?" 같은 다정한 문구를 섞어서 답변해.
4. 답변 형식:
   * 추천 장소 이름 및 위치
   * 추천 이유 (아동 발달 근거 포함)
   * 이용 정보 (요금, 연령 등)
   * 예약 바로가기 링크"""

# ─────────────────────────────────────────────────────────────────
# 7. 데이터 로딩 (st.cache_data)
# ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_places() -> pd.DataFrame:
    places = pd.read_csv(PLACES_CSV)
    places["age_min"] = pd.to_numeric(places["age_min"], errors="coerce").fillna(0)
    places["age_max"] = pd.to_numeric(places["age_max"], errors="coerce").fillna(13)
    places["image_url"] = places["image_url"].fillna(FALLBACK_IMG)

    feats = pd.read_csv(FEATURES_CSV)
    feats["confidence"] = pd.to_numeric(feats["confidence"], errors="coerce").fillna(0)
    high = feats[
        (feats["confidence"] >= 0.7) & (~feats["feature_name"].isin(FEAT_SKIP))
    ]
    feat_map: dict = {}
    for _, r in high.iterrows():
        pid = r["place_id"]
        fn  = r["feature_name"]
        if pid not in feat_map:
            feat_map[pid] = []
        if fn not in feat_map[pid]:
            feat_map[pid].append(fn)

    revs = pd.read_csv(REVIEWS_CSV)
    agg = (
        revs.groupby("place_id")
        .agg(
            review_count=("doc_id", "count"),
            review_text=("content", lambda x: " ".join(
                x.dropna().astype(str).tolist()[:6]
            )),
        )
        .reset_index()
    )
    df = places.merge(agg, on="place_id", how="left")
    df["review_count"] = df["review_count"].fillna(0).astype(int)
    df["review_text"]  = df["review_text"].fillna("")
    df["features"]     = df["place_id"].map(feat_map).apply(
        lambda x: x if isinstance(x, list) else []
    )
    return df


@st.cache_data(show_spinner=False)
def load_dev() -> pd.DataFrame:
    return pd.read_csv(DEV_CSV)


# ─────────────────────────────────────────────────────────────────
# 8. ChromaDB PersistentClient (속도 최적화)
# ─────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_chroma(df: pd.DataFrame):
    try:
        import chromadb
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction,
        )
        ef = SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        existing = [c.name for c in client.list_collections()]

        if "bebenori_v3" in existing:
            col = client.get_collection("bebenori_v3", embedding_function=ef)
            if col.count() == len(df):
                return col          # ← 캐시 히트
            client.delete_collection("bebenori_v3")

        col = client.create_collection("bebenori_v3", embedding_function=ef)
        docs, ids, metas = [], [], []
        for _, r in df.iterrows():
            pid  = str(r["place_id"])
            prog = str(r.get("program_info_text", ""))[:200]
            feat = ", ".join(r["features"][:6])
            rev  = str(r["review_text"])[:480]
            text = (
                f"{r['place_name']} {r['district']} {r['address']} "
                f"{r['age_text']} {prog} {feat} {rev}"
            )
            docs.append(text)
            ids.append(pid)
            metas.append({
                "place_id":   pid,
                "place_name": str(r["place_name"]),
                "district":   str(r["district"]),
            })
        for i in range(0, len(docs), 64):
            col.add(
                documents=docs[i:i+64],
                ids=ids[i:i+64],
                metadatas=metas[i:i+64],
            )
        return col
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# 9. LLM 클라이언트 (openai → HuggingFace base_url)
# ─────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_llm():
    try:
        from openai import OpenAI
        return OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=HF_TOKEN,
        )
    except Exception:
        return None


def llm_chat(client, messages: list, max_tokens: int = 420) -> str:
    if client is None:
        return f"AI 클라이언트 초기화 실패. HF_TOKEN을 확인해 주세요! 자세한 정보는 서울시 공공서비스 예약 사이트({PUBLIC_BOOKING})를 이용해 주세요 🌸"
    try:
        r = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.72,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return (
            f"이모삼촌이 잠깐 쉬고 있어요 😅 잠시 후 다시 시도해 주세요!\n"
            f"지금 당장 정보가 필요하시다면 서울시 공공서비스 예약 사이트를 확인해 주세요: {PUBLIC_BOOKING}\n"
            f"(오류: {str(e)[:80]})"
        )


# ─────────────────────────────────────────────────────────────────
# 10. RAG 파이프라인
# ─────────────────────────────────────────────────────────────────

def rag_retrieve(col, query: str, district: str, n: int = 5) -> list:
    if col is None:
        return []
    where = {"district": {"$eq": district}} if district and district != "전체" else None
    try:
        res = col.query(query_texts=[query], n_results=n, where=where)
        return res["ids"][0] if res["ids"] else []
    except Exception:
        return []


def build_rag_context(df: pd.DataFrame, dev_df: pd.DataFrame,
                      pids: list, months: int) -> str:
    """[Place_DB] + [Development_DB] 결합 컨텍스트."""
    place_rows = df[df["place_id"].isin(pids)]
    place_parts = []
    for _, r in place_rows.iterrows():
        feat_str  = ", ".join(r["features"][:5]) if r["features"] else "정보 없음"
        price_str = str(r.get("price_info_text",""))[:60] or "정보 없음"
        res_url   = str(r.get("reservation_url","")) or PUBLIC_BOOKING
        place_parts.append(
            f"- 장소명: {r['place_name']}\n"
            f"  위치: {r['district']} {r['address']}\n"
            f"  이용 연령: {r['age_text']} | 이용료: {price_str}\n"
            f"  주요 특징(confidence≥0.7): {feat_str}\n"
            f"  예약: {res_url}"
        )

    dev_age  = months_to_dev_age(months)
    dev_rows = dev_df[dev_df["age"] == dev_age]
    dev_text = ""
    if not dev_rows.empty:
        row = dev_rows.iloc[0]
        dev_text = (
            f"\n[Development_DB] — {dev_age}개월 발달 정보\n"
            f"  대근육: {str(row.get('gross_motor_skills',''))[:120]}\n"
            f"  소근육: {str(row.get('fine_motor_skills',''))[:120]}\n"
            f"  언어:   {str(row.get('language_development',''))[:120]}\n"
            f"  인지:   {str(row.get('cognitive_development',''))[:120]}\n"
            f"  사회성: {str(row.get('social_development',''))[:120]}"
        )

    context = "[Place_DB]\n" + "\n\n".join(place_parts) + dev_text
    return context


def gen_answer(client, query: str, context: str, months: int) -> str:
    user_msg = (
        f"사용자 질문: {query}\n"
        f"아이 개월 수: {months}개월\n\n"
        f"[Context]\n{context}\n\n"
        "위 Context 데이터만을 바탕으로 추천해 주세요."
    )
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ], max_tokens=450)


def gen_card_rec(client, name: str, addr: str,
                 feats: list, review: str, months: int) -> str:
    feat_str = ", ".join(feats[:5]) if feats else "다양한 놀이 시설"
    prompt = (
        f"장소명: {name} | 위치: {addr}\n"
        f"아이 개월 수: {months}개월\n"
        f"주요 특징: {feat_str}\n"
        f"방문 리뷰 요약: {review[:320]}\n\n"
        "이 키즈카페를 2~3문장(100자 이내)으로 따뜻하게 추천해 주세요. "
        "아동 발달 효과를 한 가지 포함하고, 마크다운 기호는 사용하지 마세요."
    )
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ], max_tokens=180)


# ─────────────────────────────────────────────────────────────────
# 11. 발달 대시보드 렌더러
# ─────────────────────────────────────────────────────────────────

def render_dev_dashboard(dev_df: pd.DataFrame, months: int):
    dev_age = months_to_dev_age(months)
    row_df  = dev_df[dev_df["age"] == dev_age]
    if row_df.empty:
        return
    row = row_df.iloc[0]

    spiral_tag = img_tag(SPIRAL_FILE, style="width:28px;height:28px;object-fit:contain")

    st.markdown(f"""
    <div class="dev-wrap">
      <div class="dev-title-row">
        <span style="font-size:1.8em">🌱</span>
        <div>
          <div class="dev-title-main">우리 아이, 지금 이런 것들이 쑥쑥 자라나요!</div>
          <div class="dev-title-sub">경기도육아종합지원센터 영유아 발달지원 가이드북 기반 · 데이터: 지연님 조사</div>
        </div>
        <div class="dev-age-pill">{months}개월 ({dev_age}개월)</div>
      </div>
      <div class="dom-grid">
    """, unsafe_allow_html=True)

    for col_name, icon, title, cls, prog in DOMAINS:
        raw  = str(row.get(col_name, "데이터 준비 중..."))
        pts  = [b.strip() for b in raw.split(";") if b.strip()][:3]
        disp = " · ".join(pts) if pts else raw[:130]
        st.markdown(f"""
        <div class="dom-card {cls}">
          <span class="dom-icon">{icon}</span>
          <div class="dom-title">{title}</div>
          <div class="dom-text">{disp}</div>
          <div class="dom-bar">
            <div class="dom-fill" style="width:{prog}%"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 감각 발달
    st.markdown('<div class="sense-row">', unsafe_allow_html=True)
    for col_name, icon, title in SENSES:
        txt   = str(row.get(col_name, ""))
        short = txt[:55] + "…" if len(txt) > 55 else txt
        st.markdown(f"""
        <div class="sense-chip">
          <span class="sense-icon">{icon}</span>
          <div class="sense-title">{title} 발달</div>
          <div class="sense-text">{short}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# 12. 장소 카드 렌더러
# ─────────────────────────────────────────────────────────────────

def render_place_card(row: pd.Series, client, months: int, key_pfx: str = ""):
    pid     = str(row["place_id"])
    name    = str(row["place_name"])
    dist    = str(row["district"])
    addr    = str(row["address"])
    img_url = str(row["image_url"])
    r_cnt   = int(row["review_count"])
    r_text  = str(row["review_text"])
    feats   = row["features"] if isinstance(row["features"], list) else []
    age_txt = str(row.get("age_text", ""))
    parking = str(row.get("parking_info", ""))
    res_url = str(row.get("reservation_url","")) or ""
    det_url = str(row.get("detail_url",""))     or ""

    # 뱃지
    badges = '<span class="cbdg cbdg-blue">★ 이모삼촌 추천</span>'
    if "toddler_friendly" in feats or "toddler_positive" in feats:
        badges += '<span class="cbdg cbdg-green">👶 영유아</span>'
    if any(k in pid for k in ("2025","2026")):
        badges += '<span class="cbdg cbdg-yellow">NEW</span>'

    # 특징 칩
    feat_chips = "".join(
        f"<span class='chip chip-b'>{FEAT_LABEL[fn][0]} {FEAT_LABEL[fn][1]}</span>"
        for fn in feats[:5] if fn in FEAT_LABEL
    )
    age_chip  = f"<span class='chip chip-y'>👶 {age_txt}</span>" if age_txt else ""
    park_chip = (
        f"<span class='chip chip-g'>🅿 {str(parking)[:22]}</span>"
        if parking and parking.lower() not in ("nan","none","") else ""
    )

    link = res_url if res_url.startswith("http") else (
        det_url if det_url.startswith("http") else PUBLIC_BOOKING
    )
    map_link = f"https://map.naver.com/p/search/{name}"

    # st.container 카드
    with st.container():
        st.markdown(f"""
        <div class="place-card">
          <div class="card-img-wrap">
            <img class="card-img" src="{img_url}"
                 alt="{name}" onerror="this.src='{FALLBACK_IMG}'">
            <div class="card-badge-row">{badges}</div>
            <div class="card-rev">💬 {r_cnt}건</div>
          </div>
          <div class="card-body">
            <div class="card-name">{name}</div>
            <div class="card-loc">📍 {dist} · {addr[:34]}{"…" if len(addr)>34 else ""}</div>
            <div class="chip-row">{feat_chips}</div>
            <div class="chip-row">{age_chip}{park_chip}</div>
        """, unsafe_allow_html=True)

        # AI 추천 이유
        rec_key = f"rec_{pid}"
        if rec_key in st.session_state.ai_recs:
            txt = st.session_state.ai_recs[rec_key]
            st.markdown(f"""
            <div class="rec-box">
              <div class="rec-lbl">💡 이모삼촌의 추천 이유 (AI · 발달 근거)</div>
              <div class="rec-txt">{txt}</div>
            </div>""", unsafe_allow_html=True)
        else:
            if st.button("💡 추천 이유 보기", key=f"{key_pfx}r_{pid}"):
                with st.spinner(f"'{name}' 분석 중... 🔍"):
                    st.session_state.ai_recs[rec_key] = gen_card_rec(
                        client, name, addr, feats, r_text, months
                    )
                st.rerun()

        st.markdown(f"""
            <div class="act-row">
              <a href="{link}" target="_blank" class="btn-main">📋 예약 바로가기</a>
              <a href="{map_link}" target="_blank" class="btn-sub">🗺 지도</a>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# 13. 세션 상태 초기화
# ─────────────────────────────────────────────────────────────────
for _k, _v in [
    ("ai_recs",   {}),
    ("chat_hist", []),
    ("ai_ans",    ""),
    ("last_pids", []),
    ("card_page", 0),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────
# 14. 리소스 로드
# ─────────────────────────────────────────────────────────────────
with st.spinner("📂 데이터 불러오는 중..."):
    try:
        df     = load_places()
        dev_df = load_dev()
    except FileNotFoundError as e:
        st.error(
            f"⚠️ CSV 파일을 찾을 수 없어요: {e}\n\n"
            "places.csv, place_features.csv, review_docs.csv, "
            "baby_development_final.csv 를 앱 폴더에 넣어 주세요."
        )
        st.stop()

with st.spinner("🗄 벡터 DB 준비 중 (최초 1회만 인덱싱)..."):
    chroma = get_chroma(df)

llm = get_llm()

# ─────────────────────────────────────────────────────────────────
# 15. 사이드바 (지역구 + 개월수 슬라이더)
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    mascot_tag = img_tag(MASCOT_FILE,
        style="width:80px;height:80px;object-fit:contain;"
              "border-radius:50%;box-shadow:0 4px 16px rgba(107,157,212,.28);"
              "border:3px solid rgba(255,255,255,.85)")
    cactus_tag = img_tag(CACTUS_FILE, style="width:38px;object-fit:contain")

    st.markdown(f"""
    <div style="text-align:center;padding:18px 0 14px">
      {mascot_tag}
      <div style="font-family:'Jua',cursive;font-size:1.5em;
                  color:#1A3A6B;margin-top:9px">베베노리</div>
      <div style="font-size:.72em;color:#6B9DD4;font-weight:700;margin-top:4px">
        이모삼촌이 엄선한 서울형 키즈카페
      </div>
    </div>
    <hr style="border:none;border-top:1.5px dashed #D6E8FF;margin:10px 0">
    <div style="display:flex;align-items:center;gap:8px;
                font-family:'Jua',cursive;font-size:.95em;
                color:#1A3A6B;margin-bottom:12px">
      {cactus_tag} 조건 필터
    </div>
    """, unsafe_allow_html=True)

    dist_sel = st.selectbox("📍 지역구", DISTRICTS, index=0, key="dist_sel")

    months_sel = st.slider(
        "👶 아이 개월 수",
        min_value=0, max_value=48,
        value=12, step=1,
        key="months_sel",
        help="슬라이더를 드래그해 아이의 개월 수를 선택하세요",
    )
    st.markdown(
        f"<div style='text-align:center;font-family:Jua,cursive;"
        f"font-size:1.1em;color:#6B9DD4;margin:-6px 0 10px'>"
        f"현재: <b>{months_sel}개월</b> ({months_to_dev_age(months_sel)}개월 구간)"
        f"</div>",
        unsafe_allow_html=True,
    )

    sort_sel = st.selectbox("📊 정렬 기준",
        ["리뷰 많은 순", "이름 순", "연령 낮은 순"],
        index=0, key="sort_sel"
    )

    st.markdown("""
    <hr style="border:none;border-top:1.5px dashed #D6E8FF;margin:14px 0">
    <div style="font-family:'Jua',cursive;font-size:.9em;
                color:#1A3A6B;margin-bottom:10px">💬 샘플 질문</div>
    """, unsafe_allow_html=True)

    SAMPLE_QS = [
        "주말에 16개월 아이랑 마곡 키즈카페 추천",
        "비 오는 날 18개월 아이 실내 놀이공간",
        "부모도 쉴 수 있는 영유아 키즈카페",
        "수유실 있는 아기 친화 키즈카페",
        "예약 없이 바로 갈 수 있는 키즈카페",
    ]
    for sq in SAMPLE_QS:
        if st.button(sq, key=f"sq_{sq}", use_container_width=True):
            st.session_state["preset_q"] = sq
            st.rerun()

    st.markdown(f"""
    <hr style="border:none;border-top:1.5px dashed #D6E8FF;margin:14px 0">
    <div style="font-size:.68em;color:#A8C4E8;line-height:2">
      🤖 Qwen/Qwen2.5-72B (HuggingFace)<br>
      🗄 ChromaDB Persistent · MiniLM-L12<br>
      📊 {len(df)}개 장소 · {int(df['review_count'].sum()):,}건 리뷰<br>
      📗 경기도 발달 가이드북 연동<br>
      ♥ 광고 없이 진심만 담았어요
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 16. 헤더 (흰색 텍스트 + text-shadow)
# ─────────────────────────────────────────────────────────────────
total_rev = int(df["review_count"].sum())

moon_tag   = img_tag(MOON_FILE,   cls="header-deco-moon")
zigzag_tag = img_tag(ZIGZAG_FILE, cls="header-deco-zigzag")
mascot_src = img_b64(MASCOT_FILE, FALLBACK_IMG)

st.markdown(f"""
<div class="bebe-header">
  <div class="header-bg-deco"></div>
  {moon_tag}
  {zigzag_tag}
  <img class="header-mascot" src="{mascot_src}" alt="베베노리 마스코트">
  <div class="header-content">
    <div class="header-brand">🌙 베베노리</div>
    <div class="header-tagline">
      이모삼촌이 직접 검증한 서울형 키즈카페 AI 큐레이션<br>
      광고 없이 진심만 담았어요 · 팀 2모3촌
    </div>
    <div class="header-pills">
      <span class="header-pill">📍 서울 {df['district'].nunique()}개 자치구</span>
      <span class="header-pill">🏠 {len(df)}개 키즈카페</span>
      <span class="header-pill">💬 리뷰 {total_rev:,}건</span>
      <span class="header-pill">🌱 발달 가이드북 연동</span>
      <span class="header-pill">🗄 ChromaDB RAG</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# 통계 바
st.markdown(f"""
<div class="stat-bar">
  <div class="stat-card">
    <span class="stat-num">{len(df)}</span>
    <div class="stat-lbl">서울형 키즈카페</div>
  </div>
  <div class="stat-card">
    <span class="stat-num">{total_rev:,}</span>
    <div class="stat-lbl">네이버 실제 리뷰</div>
  </div>
  <div class="stat-card">
    <span class="stat-num">25</span>
    <div class="stat-lbl">서울 자치구 커버</div>
  </div>
  <div class="stat-card">
    <span class="stat-num">100%</span>
    <div class="stat-lbl">광고 없음</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 17. 발달 대시보드 (개월수 선택 시 표시)
# ─────────────────────────────────────────────────────────────────
spiral_tag2 = img_tag(SPIRAL_FILE, style="width:26px;object-fit:contain")
geo_tag     = img_tag(GEO_FILE,    style="width:26px;object-fit:contain")

st.markdown(f"""
<div class="section-label">
  {spiral_tag2} 우리 아이 발달 현황 — {months_sel}개월
</div>
""", unsafe_allow_html=True)

render_dev_dashboard(dev_df, months_sel)

# ─────────────────────────────────────────────────────────────────
# 18. 채팅 인터페이스 (STEP 1 + 4)
# ─────────────────────────────────────────────────────────────────
preset = st.session_state.pop("preset_q", "")

moon_tag2 = img_tag(MOON_FILE, style="width:24px;object-fit:contain")

st.markdown(f"""
<div class="chat-outer">
  <div class="chat-label">
    {moon_tag2} 베베노리에게 물어보세요!
  </div>
  <div class="chat-hint">
    예: "주말에 {months_sel}개월 아이랑 {dist_sel if dist_sel!="전체" else "강남"} 키즈카페 추천해줘" ·
    "비 오는 날 갈 영유아 친화 카페" · "수유실 있는 곳 알려줘"
  </div>
</div>
""", unsafe_allow_html=True)

c_inp, c_btn = st.columns([5, 1])
with c_inp:
    query_input = st.text_input(
        label="질문",
        value=preset,
        placeholder="예) 18개월 아이랑 주말에 갈 수 있는 송파구 키즈카페 추천해줘",
        label_visibility="collapsed",
        key="query_input",
    )
with c_btn:
    ask_clicked = st.button("🔍 검색", key="ask_btn", use_container_width=True)

# 대화 이력 (최근 4턴)
if st.session_state.chat_hist:
    for role, msg in st.session_state.chat_hist[-8:]:
        if role == "user":
            st.markdown(
                f"<div class='bubble-user'>{msg}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='bubble-ai'>"
                f"<div class='bubble-ai-label'>🌙 베베노리 이모삼촌</div>"
                f"{msg}</div>",
                unsafe_allow_html=True,
            )

# 질문 처리
if ask_clicked and query_input.strip():
    q = query_input.strip()

    # 자치구 자동 감지 (사이드바 선택 우선)
    auto_dist = dist_sel if dist_sel != "전체" else ""
    for d in DISTRICTS[1:]:
        if d in q or d.replace("구","") in q:
            auto_dist = d
            break

    with st.spinner("이모삼촌이 최적의 장소를 찾는 중... 🔍"):
        top_pids = rag_retrieve(chroma, q, auto_dist, n=4)
        if not top_pids:
            sub = df[df["district"] == auto_dist] if auto_dist else df
            top_pids = (
                sub.sort_values("review_count", ascending=False)
                .head(4)["place_id"].tolist()
            )
        ctx = build_rag_context(df, dev_df, top_pids, months_sel)
        ans = gen_answer(llm, q, ctx, months_sel)

    st.session_state.chat_hist.append(("user", q))
    st.session_state.chat_hist.append(("ai",   ans))
    st.session_state.ai_ans    = ans
    st.session_state.last_pids = top_pids
    st.session_state.card_page = 0
    st.rerun()

# 최신 답변
if st.session_state.ai_ans:
    st.markdown(
        f"<div class='bubble-ai'>"
        f"<div class='bubble-ai-label'>🌙 베베노리 이모삼촌 (AI 추천)</div>"
        f"{st.session_state.ai_ans}"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 19. 필터링 + 카드 목록 (STEP 5)
# ─────────────────────────────────────────────────────────────────
filtered = df.copy()

# 자치구 필터
if dist_sel != "전체":
    filtered = filtered[filtered["district"] == dist_sel]

# 연령 필터 (슬라이더 기반 연나이 범위)
lo, hi = months_to_year_range(months_sel)
filtered = filtered[
    (filtered["age_min"] <= hi) & (filtered["age_max"] >= lo)
]

# 정렬
if sort_sel == "리뷰 많은 순":
    filtered = filtered.sort_values("review_count", ascending=False)
elif sort_sel == "이름 순":
    filtered = filtered.sort_values("place_name")
elif sort_sel == "연령 낮은 순":
    filtered = filtered.sort_values("age_min")

# AI 검색 결과 상단 고정
if st.session_state.last_pids:
    top_rows = filtered[filtered["place_id"].isin(st.session_state.last_pids)]
    rest     = filtered[~filtered["place_id"].isin(st.session_state.last_pids)]
    filtered = pd.concat([top_rows, rest]).reset_index(drop=True)
else:
    filtered = filtered.reset_index(drop=True)

# 결과 헤더
region_lbl = dist_sel if dist_sel != "전체" else "서울 전체"
geo_tag2   = img_tag(GEO_FILE, style="width:24px;object-fit:contain")

st.markdown(f"""
<div class="result-header">
  {geo_tag2}
  <b>{region_lbl}</b> · <b>{months_sel}개월</b> 기준 맞춤 키즈카페
  <span class="result-cnt">🏠 {len(filtered)}개</span>
</div>
""", unsafe_allow_html=True)

# 카드 그리드 (st.container 2열 + 페이지네이션)
PER_PAGE = 6

if filtered.empty:
    st.markdown(f"""
    <div class="empty-box">
      <span class="empty-ico">🌙</span>
      <div class="empty-msg">해당 조건의 키즈카페를 찾지 못했어요!</div>
      <div class="empty-sub">
        이모삼촌이 아직 공부 중이에요 🌸<br>
        지역 또는 개월 수 조건을 바꿔보거나,
        <a href="{PUBLIC_BOOKING}" target="_blank"
           style="color:#6B9DD4;font-weight:800">
          서울시 공공서비스 예약 사이트
        </a>에서 직접 검색해 보세요.
      </div>
    </div>""", unsafe_allow_html=True)
else:
    total_pages = max(1, (len(filtered) - 1) // PER_PAGE + 1)
    if st.session_state.card_page >= total_pages:
        st.session_state.card_page = 0

    p_start = st.session_state.card_page * PER_PAGE
    page_df = filtered.iloc[p_start: p_start + PER_PAGE]

    cols = st.columns(2, gap="medium")
    for i, (_, row) in enumerate(page_df.iterrows()):
        with cols[i % 2]:
            render_place_card(
                row, llm, months_sel,
                key_pfx=f"pg{st.session_state.card_page}_",
            )
            # 발달 연계 expander
            with st.expander(
                f"🌱 {row['place_name']} — 이 공간에서 기대되는 발달 효과"
            ):
                render_dev_dashboard(dev_df, months_sel)

    # 페이지네이션
    if total_pages > 1:
        pc = st.columns([1, 2, 1])
        with pc[0]:
            if st.session_state.card_page > 0:
                if st.button("◀ 이전", use_container_width=True, key="prev"):
                    st.session_state.card_page -= 1
                    st.rerun()
        with pc[1]:
            st.markdown(
                f"<div style='text-align:center;font-family:Jua,cursive;"
                f"color:#6B9DD4;padding:10px;font-size:1em;font-weight:800'>"
                f"{st.session_state.card_page + 1} / {total_pages} 페이지</div>",
                unsafe_allow_html=True,
            )
        with pc[2]:
            if st.session_state.card_page < total_pages - 1:
                if st.button("다음 ▶", use_container_width=True, key="nxt"):
                    st.session_state.card_page += 1
                    st.rerun()

# ─────────────────────────────────────────────────────────────────
# 20. 전체 AI 추천 일괄 생성
# ─────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
c_l, c_r = st.columns([3, 1])
with c_l:
    st.markdown(
        "**💡 이모삼촌 추천 이유**를 아직 확인 안 한 카드에 대해 한 번에 생성해드려요!"
    )
with c_r:
    if st.button("✨ 전체 AI 추천", key="gen_all", use_container_width=True):
        cur_pids = [
            str(r["place_id"])
            for _, r in filtered.iloc[:PER_PAGE].iterrows()
            if f"rec_{r['place_id']}" not in st.session_state.ai_recs
        ]
        if not cur_pids:
            st.success("이미 모든 추천 이유가 생성됐어요! 🎉")
        else:
            bar = st.progress(0)
            msg = st.empty()
            for i, pid in enumerate(cur_pids):
                rr = df[df["place_id"] == pid].iloc[0]
                msg.markdown(
                    f"🌙 **{rr['place_name']}** 분석 중... ({i+1}/{len(cur_pids)})"
                )
                try:
                    st.session_state.ai_recs[f"rec_{pid}"] = gen_card_rec(
                        llm,
                        str(rr["place_name"]),
                        str(rr["address"]),
                        rr["features"] if isinstance(rr["features"], list) else [],
                        str(rr["review_text"]),
                        months_sel,
                    )
                except Exception:
                    st.session_state.ai_recs[f"rec_{pid}"] = (
                        "이모삼촌이 잠시 쉬고 있어요. 다시 시도해 주세요! 🌸"
                    )
                bar.progress((i + 1) / len(cur_pids))
            msg.empty()
            st.success("✅ 완료! 카드에서 이모삼촌 추천 이유를 확인하세요 🎉")
            st.rerun()

# ─────────────────────────────────────────────────────────────────
# 21. 푸터
# ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<hr>
<div class="bebe-footer">
  <strong>🌙 베베노리 (BebeNori) v3.0</strong><br>
  이모삼촌이 만든 서울형 키즈카페 AI 큐레이션 · 팀 2모3촌<br>
  📊 places.csv ({len(df)}개) · review_docs.csv ({total_rev:,}건) ·
     place_features.csv · baby_development_final.csv<br>
  📗 경기도육아종합지원센터 영유아 발달지원 가이드북 2023-13호 (지연님 데이터)<br>
  📘 초보아빠를위한육아가이드(배포용)_.pdf (Colab 업로드 후 RAG 확장 가능)<br>
  🗄 ChromaDB PersistentClient ({CHROMA_DIR}) + paraphrase-multilingual-MiniLM-L12-v2<br>
  🤖 LLM: Qwen/Qwen2.5-72B-Instruct via HuggingFace Inference API (openai 라이브러리)<br>
  🔗 데이터 없는 장소 문의: <a href="{PUBLIC_BOOKING}"
       style="color:#6B9DD4">{PUBLIC_BOOKING}</a><br>
  <span style="color:#90CAF9">♥ 광고 없이 진심만 담았어요</span>
</div>
""", unsafe_allow_html=True)
