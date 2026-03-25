# ╔══════════════════════════════════════════════════════════════════════╗
# ║         베베노리 (BebeNori) v2.0 — 서울형 키즈카페 AI 큐레이터          ║
# ║         팀: 2모3촌  |  Google Colab + cloudflared 완전판              ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# ════════════════════════════════════════════════════════════════
#  [Colab 실행 가이드] 새 코드 셀에 아래 명령어를 순서대로 실행하세요
# ════════════════════════════════════════════════════════════════
#
# ── STEP 0: 패키지 설치 (최초 1회) ──────────────────────────────
#   !pip install streamlit chromadb sentence-transformers openai pandas -q
#
# ── STEP 1: 파일 업로드 (왼쪽 파일 패널 또는 코드) ──────────────
#   필수 파일을 /content/ 에 업로드:
#     places.csv, place_features.csv, review_docs.csv,
#     baby_development_final.csv,
#     bebenori_crayon.png.jpg, bebenori_pattern.png.jpg
#     (선택) 초보아빠를위한육아가이드(배포용)_.pdf
#     (선택) _경기도육아종합지원센터_부모를위한_한눈에보는_영유아발달지원가이드북.pdf
#
# ── STEP 2: HuggingFace 토큰 설정 ───────────────────────────────
#   import os
#   os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN_HERE"
#
# ── STEP 3: app.py 업로드 후 실행 ───────────────────────────────
#   !streamlit run app.py --server.port 8501 &>/content/st.log &
#   import time; time.sleep(5)
#
# ── STEP 4: cloudflared 터널 (비밀번호 없이 접속) ────────────────
#   # cloudflared 설치 (최초 1회)
#   !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
#   !dpkg -i cloudflared-linux-amd64.deb
#
#   # 터널 실행 → 출력되는 https://xxxx.trycloudflare.com URL로 접속
#   !cloudflared tunnel --url http://localhost:8501 &
#   import time; time.sleep(5)
#   !grep -o 'https://.*\.trycloudflare\.com' /proc/$(pgrep cloudflared)/fd/1 2>/dev/null \
#     || print("터널 URL: 위 cloudflared 출력 확인")
#
# ── (대안) localtunnel ───────────────────────────────────────────
#   !npm install -g localtunnel -q
#   import subprocess; p = subprocess.Popen(['lt','--port','8501'],stdout=subprocess.PIPE)
#   print(p.stdout.readline().decode())
#
# ── 앱 재시작 (코드 수정 후) ────────────────────────────────────
#   !pkill -f streamlit; sleep 1
#   !streamlit run app.py --server.port 8501 &>/content/st.log &

# ════════════════════════════════════════════════════════════════
#  IMPORTS
# ════════════════════════════════════════════════════════════════
import os, base64, json
from pathlib import Path
import pandas as pd
import streamlit as st

# ════════════════════════════════════════════════════════════════
#  0. 페이지 설정 — 반드시 첫 번째 Streamlit 호출
# ════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="베베노리 🖍",
    page_icon="🖍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════
#  1. 파일 경로 상수
# ════════════════════════════════════════════════════════════════
PLACES_CSV   = "places.csv"
FEATURES_CSV = "place_features.csv"
REVIEWS_CSV  = "review_docs.csv"
DEV_CSV      = "baby_development_final.csv"
LOGO_FILE    = "logo.jpg.png"
PATTERN_FILE = "pattern.png.png"
CHROMA_DIR   = "./bebenori_db"
FALLBACK_IMG = "https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&w=800&q=80"

HF_TOKEN = os.environ.get("HF_TOKEN", "hf_YOUR_TOKEN_HERE")

# ════════════════════════════════════════════════════════════════
#  2. 유틸: 이미지 → base64
# ════════════════════════════════════════════════════════════════
def img_b64(path: str, fallback_url: str = "") -> str:
    if Path(path).exists():
        ext = "jpeg" if path.lower().endswith((".jpg",".jpeg")) else "png"
        with open(path, "rb") as f:
            return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
    return fallback_url

# ════════════════════════════════════════════════════════════════
#  3. 전역 CSS — 크레파스 파스텔 옐로우 × 민트 테마
# ════════════════════════════════════════════════════════════════
PATTERN_B64 = img_b64(PATTERN_FILE)
LOGO_B64    = img_b64(LOGO_FILE, FALLBACK_IMG)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Nanum+Square+Round:wght@400;700;800&display=swap');

/* ── 기반 ─────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
    font-family: 'Nanum Square Round', 'Apple SD Gothic Neo', sans-serif;
}}
.stApp                          {{ background: #FDFBF0 !important; }}
[data-testid="stAppViewContainer"] {{ background: #FDFBF0 !important; }}
[data-testid="stHeader"]        {{ background: transparent !important; }}
.block-container                {{ padding-top: 0 !important; max-width: 1200px; }}

/* ── 사이드바 ──────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(175deg,#FFF9C4 0%,#F0FFF4 100%) !important;
    border-right: 2px dashed #A5D6A7 !important;
    position: relative;
}}
[data-testid="stSidebar"]::after {{
    content: '';
    position: absolute; inset: 0; pointer-events: none; z-index: 0;
    background-image: url('{PATTERN_B64}');
    background-size: 180px; background-repeat: repeat;
    opacity: 0.07;
}}
[data-testid="stSidebar"] > div {{ position: relative; z-index: 1; }}
[data-testid="stSidebar"] * {{ color: #33691E !important; }}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {{ font-weight: 800 !important; }}

/* ── 히어로 헤더 ───────────────────────────────────────── */
.bebe-hero {
    /* 이미지를 배경으로 넣고, 글씨가 잘 보이게 하얀색 필터를 살짝 깔았어요 */
    background-image: linear-gradient(rgba(255,255,255,0.4), rgba(255,255,255,0.4)), url('{LOGO_B64}');
    background-size: cover;      /* 이미지가 칸에 꽉 차게 */
    background-position: center; /* 이미지 중앙 맞춤 */
    border-radius: 0 0 52px 52px;
    padding: 50px 36px;
    margin: -1rem -1rem 0;
    box-shadow: 0 8px 28px rgba(100,150,80,.15);
    display: flex; align-items: center; justify-content: center; gap: 26px;
    border-bottom: 2px dashed #C5E1A5;
    position: relative; overflow: hidden;
}
.bebe-hero::before {{
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background-image: url('{PATTERN_B64}');
    background-size: 140px; background-repeat: repeat; opacity: 0.05;
}}
.hero-logo {{
    width: 92px; height: 92px; object-fit: contain;
    border-radius: 26px; flex-shrink: 0; position: relative; z-index: 1;
    box-shadow: 0 6px 20px rgba(0,0,0,.12);
    border: 3px solid rgba(255,255,255,.8);
}}
.hero-text {{ position: relative; z-index: 1; flex: 1; }}
.hero-title {{
    font-family: 'Jua', cursive; font-size: 2.8em;
    color: #33691E; line-height: 1; margin-bottom: 6px;
    text-shadow: 2px 3px 0 rgba(255,255,255,.6);
}}
.hero-sub {{ font-size: .9em; color: #558B2F; font-weight: 700; line-height: 1.7; }}
.hero-pills {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
.hero-pill {{
    background: rgba(255,255,255,.75); backdrop-filter: blur(4px);
    color: #33691E; font-size: .72em; font-weight: 800;
    padding: 5px 13px; border-radius: 20px; border: 1px solid #C5E1A5;
}}

/* ── 통계 바 ────────────────────────────────────────────── */
.stat-bar {{ display:flex; gap:10px; margin:18px 0; flex-wrap:wrap; }}
.stat-chip {{
    background: #fff; border: 1.5px solid #C5E1A5;
    border-radius: 18px; padding: 10px 16px; text-align: center;
    box-shadow: 0 3px 10px rgba(100,150,80,.1); flex: 1; min-width: 90px;
}}
.stat-num {{ display:block; font-size:1.55em; font-weight:800; color:#2E7D32; }}
.stat-lbl {{ font-size:.7em; color:#81C784; font-weight:700; margin-top:2px; }}

/* ── 채팅 래퍼 ──────────────────────────────────────────── */
.chat-wrap {{
    background: #fff; border-radius: 24px;
    padding: 20px 24px; margin: 20px 0 16px;
    border: 1.5px solid #C5E1A5;
    box-shadow: 0 6px 22px rgba(100,150,80,.09);
}}
.chat-lbl {{ font-size: 1em; font-weight: 800; color: #33691E; margin-bottom: 6px; }}
.chat-hint {{ font-size: .78em; color: #A5D6A7; line-height: 1.65; margin-bottom: 12px; }}
.user-bubble {{
    background: #33691E; color: #fff;
    border-radius: 20px 4px 20px 20px;
    padding: 11px 16px; margin: 8px 0 4px;
    font-size: .88em; max-width: 78%; margin-left: auto;
    box-shadow: 0 3px 12px rgba(0,0,0,.15); line-height: 1.6;
}}
.ai-bubble {{
    background: linear-gradient(135deg,#FFFDE7,#F1F8E9);
    border: 1.5px solid #C5E1A5;
    border-radius: 4px 20px 20px 20px;
    padding: 14px 18px; margin: 4px 0 14px;
    font-size: .9em; color: #33691E; line-height: 1.8;
    box-shadow: 0 4px 16px rgba(100,150,80,.12);
}}
.ai-label {{
    font-weight: 800; font-size: .75em; color: #2E7D32; margin-bottom: 7px;
    display: flex; align-items: center; gap: 5px;
}}

/* ── 장소 카드 ──────────────────────────────────────────── */
.place-card {{
    background: #fff; border-radius: 24px; overflow: hidden;
    border: 1.5px solid #E8F5E9;
    box-shadow: 0 6px 22px rgba(100,150,80,.09);
    transition: transform .22s, box-shadow .22s; height: 100%;
}}
.place-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 16px 40px rgba(100,150,80,.18);
}}
.card-img-wrap {{ position:relative; height: 200px; overflow: hidden; }}
.card-img {{
    width:100%; height:100%; object-fit:cover;
    transition: transform .4s;
}}
.place-card:hover .card-img {{ transform: scale(1.05); }}
.card-badges {{ position:absolute; top:12px; left:12px; display:flex; gap:5px; flex-wrap:wrap; }}
.cbdg {{
    padding: 4px 10px; border-radius: 20px;
    font-size: .68em; font-weight: 800;
    backdrop-filter: blur(5px);
}}
.cbdg-star {{ background: rgba(255,179,0,.92); color: #fff; }}
.cbdg-green{{ background: rgba(56,142,60,.90); color: #fff; }}
.cbdg-blue {{ background: rgba(21,101,192,.88); color: #fff; }}
.cbdg-gray {{ background: rgba(0,0,0,.55);       color: #fff; }}
.rev-cnt {{
    position:absolute; bottom:12px; right:12px;
    background: rgba(255,255,255,.92); color: #33691E;
    border-radius: 14px; padding: 4px 10px;
    font-size: .7em; font-weight: 800;
    box-shadow: 0 2px 8px rgba(0,0,0,.1);
}}
.card-body {{ padding: 18px 20px 20px; }}
.card-name {{ font-size: 1.1em; font-weight: 800; color: #1B5E20; margin-bottom: 4px; line-height:1.3; }}
.card-addr {{ font-size: .78em; color: #BDBDBD; margin-bottom: 10px; }}
.chip-row  {{ display:flex; flex-wrap:wrap; gap:5px; margin-bottom:7px; }}
.chip {{ padding: 3px 9px; border-radius: 12px; font-size: .7em; font-weight: 700; }}
.chip-y {{ background:#FFFDE7; color:#F9A825; border:1px solid #FFE082; }}
.chip-g {{ background:#E8F5E9; color:#2E7D32; border:1px solid #A5D6A7; }}
.chip-b {{ background:#E3F2FD; color:#1565C0; border:1px solid #90CAF9; }}
.chip-p {{ background:#F3E5F5; color:#6A1B9A; border:1px solid #CE93D8; }}
.chip-m {{ background:#FCE4EC; color:#880E4F; border:1px solid #F48FB1; }}

/* ── AI 추천 박스 ────────────────────────────────────────── */
.rec-box {{
    background: linear-gradient(135deg,#FFFDE7,#F1F8E9);
    border-left: 4px solid #66BB6A;
    border-radius: 0 16px 16px 0;
    padding: 12px 15px; margin: 10px 0;
}}
.rec-lbl {{ font-size:.73em; font-weight:800; color:#2E7D32; margin-bottom:5px; }}
.rec-txt  {{ font-size:.83em; color:#388E3C; line-height:1.75; }}

/* ── 발달 대시보드 ──────────────────────────────────────── */
.dev-wrap {{
    background: #fff; border-radius: 28px;
    padding: 26px 28px; margin: 24px 0;
    border: 1.5px solid #C5E1A5;
    box-shadow: 0 6px 24px rgba(100,150,80,.08);
}}
.dev-header {{
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 18px; margin-bottom: 20px;
    border-bottom: 2px dashed #C5E1A5;
}}
.dev-header-icon {{ font-size: 2.2em; }}
.dev-header-text h3 {{
    font-family: 'Jua', cursive; font-size: 1.3em;
    color: #2E7D32; margin: 0 0 4px;
}}
.dev-header-text p {{ font-size: .8em; color: #81C784; margin: 0; font-weight: 700; }}
.dev-age-badge {{
    margin-left: auto; background: linear-gradient(135deg,#FFFDE7,#F1F8E9);
    border: 1.5px solid #C5E1A5; border-radius: 20px;
    padding: 8px 18px; font-family:'Jua',cursive;
    font-size: 1.1em; color: #33691E; white-space: nowrap;
}}

/* ── 발달 도메인 카드 ──────────────────────────────────── */
.dom-grid {{ display:grid; gap:14px;
    grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); }}
.dom-card {{
    border-radius: 20px; padding: 18px 18px 16px;
    border: 1.5px solid transparent;
    transition: transform .2s, box-shadow .2s;
    position: relative; overflow: hidden;
}}
.dom-card::before {{
    content: ''; position: absolute; top:-20px; right:-20px;
    width: 80px; height: 80px; border-radius: 50%;
    background: rgba(255,255,255,.3);
}}
.dom-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 28px rgba(0,0,0,.1); }}

.dom-motor   {{ background: linear-gradient(135deg,#E8F5E9,#DCEDC8); border-color:#A5D6A7; }}
.dom-cog     {{ background: linear-gradient(135deg,#FFF9C4,#FFFDE7); border-color:#FFE082; }}
.dom-lang    {{ background: linear-gradient(135deg,#E3F2FD,#E1F5FE); border-color:#90CAF9; }}
.dom-social  {{ background: linear-gradient(135deg,#FCE4EC,#F8BBD0); border-color:#F48FB1; }}
.dom-fine    {{ background: linear-gradient(135deg,#EDE7F6,#E8EAF6); border-color:#B39DDB; }}
.dom-gross   {{ background: linear-gradient(135deg,#E0F7FA,#E0F2F1); border-color:#80DEEA; }}

.dom-icon  {{ font-size: 1.9em; display:block; margin-bottom: 8px; }}
.dom-title {{ font-family:'Jua',cursive; font-size: 1em; font-weight:800;
    margin-bottom: 8px; }}
.dom-motor  .dom-title {{ color:#2E7D32; }}
.dom-cog    .dom-title {{ color:#F57F17; }}
.dom-lang   .dom-title {{ color:#1565C0; }}
.dom-social .dom-title {{ color:#880E4F; }}
.dom-fine   .dom-title {{ color:#6A1B9A; }}
.dom-gross  .dom-title {{ color:#00695C; }}

.dom-text {{
    font-size: .78em; line-height: 1.75; color: #424242;
    display: -webkit-box; -webkit-line-clamp: 5;
    -webkit-box-orient: vertical; overflow: hidden;
}}
.dom-progress-bar {{
    height: 6px; border-radius: 3px; margin-top: 12px;
    background: rgba(255,255,255,.5);
    position: relative; overflow: hidden;
}}
.dom-progress-fill {{
    height: 100%; border-radius: 3px;
    background: linear-gradient(90deg,rgba(255,255,255,.4),rgba(255,255,255,.9));
    animation: prog 1.5s ease-out forwards;
}}
@keyframes prog {{ from {{ width:0 }} }}

/* ── 감각 발달 미니 카드 ────────────────────────────────── */
.sense-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; }}
.sense-chip {{
    flex: 1; min-width: 120px; background:#fff;
    border-radius:14px; padding:12px 14px;
    border:1.5px solid #E8F5E9;
    box-shadow:0 2px 8px rgba(0,0,0,.05);
}}
.sense-icon {{ font-size:1.4em; display:block; margin-bottom:4px; }}
.sense-title {{ font-size:.72em; font-weight:800; color:#33691E; margin-bottom:3px; }}
.sense-text  {{ font-size:.68em; color:#757575; line-height:1.55; }}

/* ── 액션 버튼 ──────────────────────────────────────────── */
.act-row {{ display:flex; gap:8px; margin-top:12px; }}
.btn-main {{
    flex:1; text-align:center; background: #43A047; color:#fff !important;
    padding:11px; border-radius:14px; font-weight:800; font-size:.8em;
    text-decoration:none; box-shadow:0 4px 12px rgba(56,142,60,.3);
    transition:background .2s;
}}
.btn-main:hover {{ background:#388E3C; text-decoration:none; }}
.btn-sub {{
    text-align:center; background:#F1F8E9; color:#33691E !important;
    padding:11px 14px; border-radius:14px; font-weight:800; font-size:.8em;
    text-decoration:none; border:1.5px solid #C5E1A5; transition:background .2s;
}}
.btn-sub:hover {{ background:#DCEDC8; text-decoration:none; }}

/* ── 빈 결과 ────────────────────────────────────────────── */
.empty-box {{
    text-align:center; padding:52px 24px; background:#fff;
    border-radius:24px; border:1.5px dashed #C5E1A5; margin:20px 0;
}}
.empty-ico {{ font-size:3.6em; display:block; margin-bottom:14px; }}
.empty-msg {{ font-size:1.1em; font-weight:800; color:#43A047; margin-bottom:8px; }}
.empty-sub {{ font-size:.85em; color:#BDBDBD; line-height:1.75; }}

/* ── 결과 헤더 ──────────────────────────────────────────── */
.result-header {{
    font-family:'Jua',cursive; font-size:1.25em; color:#33691E;
    margin:4px 0 18px; display:flex; align-items:center; gap:10px;
    padding: 14px 20px; background:#fff;
    border-radius:16px; border:1.5px solid #E8F5E9;
    box-shadow:0 3px 12px rgba(100,150,80,.07);
}}
.result-count {{ color:#43A047; font-size:1.2em; margin-left:auto; }}

/* ── Streamlit 위젯 오버라이드 ─────────────────────────── */
.stButton > button {{
    background: #43A047 !important; color: #fff !important;
    font-weight: 800 !important; border: none !important;
    border-radius: 14px !important;
    font-family: 'Nanum Square Round', sans-serif !important;
    box-shadow: 0 4px 12px rgba(56,142,60,.25) !important;
    transition: background .2s !important;
}}
.stButton > button:hover {{ background: #388E3C !important; }}
.stTextInput > div > div > input {{
    border-radius: 14px !important; border: 1.5px solid #A5D6A7 !important;
    background: #F9FBF5 !important; color: #33691E !important;
    font-family: 'Nanum Square Round', sans-serif !important;
}}
.stSelectbox > div > div {{
    border-radius: 14px !important; border-color: #A5D6A7 !important;
}}
div[data-testid="stExpander"] {{
    border: 1.5px solid #C5E1A5 !important;
    border-radius: 18px !important; background: #fff !important;
    overflow: hidden;
}}
div[data-testid="stExpander"] summary {{
    font-weight: 800 !important; color: #33691E !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 800 !important;
    font-family: 'Nanum Square Round', sans-serif !important;
}}
.stTabs [aria-selected="true"] {{
    color: #2E7D32 !important;
    border-bottom-color: #43A047 !important;
}}
hr {{ border:none; border-top:2px dashed #C5E1A5 !important; margin:24px 0; }}

/* ── 푸터 ───────────────────────────────────────────────── */
.bebe-footer {{
    text-align:center; padding:28px 0 24px;
    color:#A5D6A7; font-size:.77em; line-height:2.1;
}}
.bebe-footer strong {{ color:#43A047; }}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  4. 상수 / 매핑 테이블
# ════════════════════════════════════════════════════════════════

# 사용자 개월 수 선택지
AGE_OPTIONS = [
    "전체", "0~6개월", "6~12개월", "12~18개월",
    "18~24개월", "24~30개월", "30~36개월", "36개월 이상",
]

# 사용자 선택 → baby_development_final.csv 의 age 컬럼 값 매핑
# CSV age: '0~1', '1~3', '4~6', '7~9', '10~12', '13~24', '25~36' (단위: 개월)
AGE_TO_DEV: dict[str, str] = {
    "0~6개월":  "4~6",    # 4~6개월 기준이 중간
    "6~12개월": "7~9",
    "12~18개월":"13~24",
    "18~24개월":"13~24",
    "24~30개월":"25~36",
    "30~36개월":"25~36",
    "36개월 이상":"25~36",
}

# 사용자 개월 수 → place age_min/max 필터 (연나이 = year, 연령 기준)
# places.csv 의 age_min/age_max 는 연나이(세) 기준
AGE_TO_YEAR: dict[str, tuple] = {
    "0~6개월":  (0, 0),
    "6~12개월": (0, 1),
    "12~18개월":(0, 1),
    "18~24개월":(0, 2),
    "24~30개월":(0, 2),
    "30~36개월":(2, 3),
    "36개월 이상":(3, 99),
}

# feature_name → (아이콘, 한글 레이블) — confidence >= 0.7 뱃지
FEAT_LABEL: dict[str, tuple] = {
    "parking_available":          ("🅿", "주차 가능"),
    "reservation_available":      ("📋", "예약 가능"),
    "weekend_operation":          ("📅", "주말 운영"),
    "toddler_friendly":           ("👶", "영유아 친화"),
    "toddler_positive":           ("⭐", "영유아 칭찬"),
    "preschool_friendly":         ("🧒", "유아 적합"),
    "lower_elementary_friendly":  ("🎒", "초등 저학년"),
    "program_info_available":     ("🎨", "프로그램"),
    "group_visit_available":      ("👨‍👩‍👧", "단체 가능"),
    "spacious_positive":          ("🏟", "넓어요"),
    "safety_positive":            ("🛡", "안전"),
    "cleanliness_positive":       ("✨", "깨끗해요"),
    "active_play_positive":       ("🏃", "놀이 풍부"),
}
FEAT_SKIP = {
    "district","has_phone","guardian_rule_mentioned",
    "socks_rule_mentioned","cleanliness_negative","crowded_warning",
}

# 서울 자치구 목록
DISTRICTS = ["전체"] + sorted([
    "강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구",
    "노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구",
    "성동구","성북구","송파구","양천구","영등포구","용산구","은평구",
    "종로구","중구","중랑구",
])

# 시스템 프롬프트 (베베노리 페르소나)
SYSTEM_PROMPT = """당신은 '2모3촌'이 만든 따뜻한 육아 비서 '베베노리(BebeNori)'입니다.
조카를 아끼는 이모·삼촌처럼 따뜻하고 구체적으로 답변하세요.

[답변 규칙]
- 존댓말, 다정하고 친근한 말투
- 키즈카페 추천 시: 장소명·위치·주차·예약·연령 정보를 반드시 언급
- 실제 리뷰/특징 데이터를 반영한 구체적 추천 이유
- 데이터에 없는 지역/조건: "이모삼촌이 아직 공부 중이에요! 🌸"
- 답변 마지막에 예약 링크 또는 공식 사이트 안내
- 마크다운 기호(##, **, ---)는 금지, 이모지와 줄바꿈으로 구조화
- 180~280자 내외로 간결하게"""

# ════════════════════════════════════════════════════════════════
#  5. 데이터 로딩 (@st.cache_data)
# ════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def load_places() -> pd.DataFrame:
    places = pd.read_csv(PLACES_CSV)
    places["age_min"] = pd.to_numeric(places["age_min"], errors="coerce").fillna(0)
    places["age_max"] = pd.to_numeric(places["age_max"], errors="coerce").fillna(13)
    places["image_url"] = places["image_url"].fillna(FALLBACK_IMG)

    # 특성 로드 (confidence >= 0.7)
    feats = pd.read_csv(FEATURES_CSV)
    feats["confidence"] = pd.to_numeric(feats["confidence"], errors="coerce").fillna(0)
    high = feats[(feats["confidence"] >= 0.7) & (~feats["feature_name"].isin(FEAT_SKIP))]
    feat_map: dict[str, list] = {}
    for _, r in high.iterrows():
        pid = r["place_id"]
        fn  = r["feature_name"]
        if pid not in feat_map:
            feat_map[pid] = []
        if fn not in feat_map[pid]:
            feat_map[pid].append(fn)

    # 리뷰 집계
    revs = pd.read_csv(REVIEWS_CSV)
    agg = (
        revs.groupby("place_id")
        .agg(
            review_count=("doc_id",  "count"),
            review_text =("content", lambda x: " ".join(
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
def load_dev_data() -> pd.DataFrame:
    return pd.read_csv(DEV_CSV)


# ════════════════════════════════════════════════════════════════
#  6. ChromaDB PersistentClient — 속도 최적화 핵심
# ════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def get_chroma(df: pd.DataFrame):
    """
    ChromaDB PersistentClient 로 ./bebenori_db 에 저장.
    이미 컬렉션이 존재하면 재구축 없이 재사용 → 속도 대폭 향상.
    """
    try:
        import chromadb
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction,
        )

        ef     = SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        client = chromadb.PersistentClient(path=CHROMA_DIR)

        # ── 컬렉션이 이미 있고 문서 수가 맞으면 재사용 ──
        existing_names = [c.name for c in client.list_collections()]
        if "bebenori_places" in existing_names:
            col = client.get_collection(
                name="bebenori_places", embedding_function=ef
            )
            if col.count() == len(df):
                return col          # ← 캐시 히트: 인덱싱 생략
            # 문서 수 불일치 → 재구축
            client.delete_collection("bebenori_places")

        col = client.create_collection(
            name="bebenori_places", embedding_function=ef
        )

        # ── 문서 빌드 ──
        docs, ids, metas = [], [], []
        for _, r in df.iterrows():
            pid  = str(r["place_id"])
            prog = str(r.get("program_info_text", ""))[:200]
            feat = ", ".join(r["features"][:6])
            rev  = str(r["review_text"])[:500]
            text = (
                f"{r['place_name']} {r['district']} {r['address']} "
                f"{r['age_text']} {prog} {feat} {rev}"
            )
            docs.append(text)
            ids.append(pid)
            metas.append({
                "place_id": pid,
                "place_name": str(r["place_name"]),
                "district": str(r["district"]),
            })

        # 배치 삽입 (100개씩)
        batch = 100
        for i in range(0, len(docs), batch):
            col.add(
                documents=docs[i:i+batch],
                ids=ids[i:i+batch],
                metadatas=metas[i:i+batch],
            )
        return col

    except ImportError:
        return None
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════
#  7. LLM 클라이언트 (openai → HuggingFace base_url)
# ════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def get_llm():
    try:
        from openai import OpenAI
        return OpenAI(
            base_url="https://router.huggingface.co/hf-inference/v1",
            api_key=HF_TOKEN,
        )
    except ImportError:
        return None


def llm_chat(client, messages: list, max_tokens: int = 400) -> str:
    if client is None:
        return "AI 클라이언트 초기화 실패. HF_TOKEN을 확인해 주세요! 🌸"
    try:
        r = client.chat.completions.create(
            # 안정적인 무료 모델로 변경
            model="HuggingFaceH4/zephyr-7b-beta", 
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.72,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"이모삼촌이 잠깐 쉬고 있어요... 잠시 후 다시 시도해 주세요! (오류: {str(e)[:80]})"


# ════════════════════════════════════════════════════════════════
#  8. RAG 파이프라인 함수들
# ════════════════════════════════════════════════════════════════

def rag_retrieve(col, query: str, district: str, n: int = 5) -> list[str]:
    """STEP 3: ChromaDB 벡터 검색 + 자치구 필터."""
    if col is None:
        return []
    where = {"district": {"$eq": district}} if district and district != "전체" else None
    try:
        res = col.query(
            query_texts=[query],
            n_results=n,
            where=where,
        )
        return res["ids"][0] if res["ids"] else []
    except Exception:
        return []


def build_context(df: pd.DataFrame, pids: list[str]) -> str:
    """STEP 4: 검색된 장소 → LLM 컨텍스트 문자열."""
    rows = df[df["place_id"].isin(pids)]
    parts = []
    for _, r in rows.iterrows():
        feat_str = ", ".join(r["features"][:5]) if r["features"] else "정보 없음"
        rev_str  = str(r["review_text"])[:350]
        parts.append(
            f"[{r['place_name']}]\n"
            f"  위치: {r['district']} {r['address']}\n"
            f"  연령: {r['age_text']} | 주차: {str(r.get('parking_info','정보없음'))[:40]}\n"
            f"  특징: {feat_str}\n"
            f"  리뷰: {rev_str}\n"
            f"  예약/사이트: {r.get('reservation_url','없음')}"
        )
    return "\n\n".join(parts) if parts else "검색 결과 없음."


def gen_answer(client, query: str, context: str) -> str:
    """STEP 4: 프롬프트 결합 + LLM 답변 생성."""
    user_msg = (
        f"사용자 질문: {query}\n\n[검색된 장소 데이터]\n{context}\n\n"
        "위 데이터를 기반으로 따뜻하고 구체적으로 추천해 주세요."
    )
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ], max_tokens=380)


def gen_card_rec(client, name: str, addr: str, feats: list, review: str) -> str:
    """개별 카드용 이모삼촌 추천 이유 생성."""
    feat_str = ", ".join(feats[:5]) if feats else "다양한 시설"
    prompt   = (
        f"장소명: {name} | 위치: {addr}\n"
        f"주요 특징: {feat_str}\n"
        f"방문 리뷰: {review[:350]}\n\n"
        "이 키즈카페를 2~3문장(90자 이내)으로 따뜻하게 추천해 주세요. "
        "안전·시설·발달 효과 중 하나를 자연스럽게 언급. 마크다운 금지."
    )
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ], max_tokens=160)


# ════════════════════════════════════════════════════════════════
#  9. 발달 대시보드 렌더러
# ════════════════════════════════════════════════════════════════

# 도메인 설정 (컬럼명, 아이콘, 제목, CSS 클래스, 진행바 너비%)
DOMAINS = [
    ("gross_motor_skills",    "🦵", "대근육 발달",  "dom-gross",  82),
    ("fine_motor_skills",     "✋", "소근육 발달",  "dom-fine",   75),
    ("language_development",  "🗣", "언어 발달",    "dom-lang",   70),
    ("cognitive_development", "🧠", "인지 발달",    "dom-cog",    78),
    ("social_development",    "👫", "사회성 발달",  "dom-social", 68),
    ("motor_development",     "🏃", "전반적 운동",  "dom-motor",  85),
]
SENSES = [
    ("vision",  "👁", "시각"),
    ("hearing", "👂", "청각"),
    ("smell",   "👃", "후각"),
    ("taste",   "👅", "미각"),
    ("touch",   "🤚", "촉각"),
]


def render_dev_dashboard(dev_df: pd.DataFrame, age_sel: str):
    """
    선택된 개월 수에 맞는 발달 데이터를 가져와
    도메인별 카드 + 감각 발달 미니카드로 렌더링.
    """
    dev_age = AGE_TO_DEV.get(age_sel)
    if not dev_age:
        return  # "전체" 선택 시 숨김

    row_df = dev_df[dev_df["age"] == dev_age]
    if row_df.empty:
        return
    row = row_df.iloc[0]

    st.markdown(f"""
    <div class="dev-wrap">
      <div class="dev-header">
        <span class="dev-header-icon">🌱</span>
        <div class="dev-header-text">
          <h3>우리 아이 이 시기의 발달은?</h3>
          <p>경기도육아종합지원센터 영유아 발달지원 가이드북 기반</p>
        </div>
        <div class="dev-age-badge">📅 {age_sel} ({dev_age}개월)</div>
      </div>
      <div class="dom-grid">
    """, unsafe_allow_html=True)

    for col_name, icon, title, cls, prog in DOMAINS:
        text = str(row.get(col_name, "데이터 준비 중..."))
        # 세미콜론 구분 → 첫 두 항목만
        bullets = [b.strip() for b in text.split(";") if b.strip()][:3]
        display = " · ".join(bullets) if bullets else text[:120]
        st.markdown(f"""
        <div class="dom-card {cls}">
          <span class="dom-icon">{icon}</span>
          <div class="dom-title">{title}</div>
          <div class="dom-text">{display}</div>
          <div class="dom-progress-bar">
            <div class="dom-progress-fill" style="width:{prog}%"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 감각 발달 미니카드
    st.markdown('<div class="sense-row">', unsafe_allow_html=True)
    for col_name, icon, title in SENSES:
        txt = str(row.get(col_name, ""))
        short = txt[:60] + "…" if len(txt) > 60 else txt
        st.markdown(f"""
        <div class="sense-chip">
          <span class="sense-icon">{icon}</span>
          <div class="sense-title">{title} 발달</div>
          <div class="sense-text">{short}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # .dev-wrap 닫기


# ════════════════════════════════════════════════════════════════
#  10. 장소 카드 렌더러
# ════════════════════════════════════════════════════════════════

def render_place_card(row: pd.Series, client, key_prefix: str = ""):
    """단일 장소 카드 렌더링."""
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
    res_url = str(row.get("reservation_url", "")) or ""
    det_url = str(row.get("detail_url", ""))     or ""

    # ── 뱃지 ──
    badges_html = '<span class="cbdg cbdg-star">★ 이모삼촌 추천</span>'
    if "toddler_friendly" in feats or "toddler_positive" in feats:
        badges_html += '<span class="cbdg cbdg-green">👶 영유아</span>'
    if any(k in pid for k in ("2025","2026")):
        badges_html += '<span class="cbdg cbdg-blue">NEW</span>'

    # ── 특징 칩 ──
    feat_chips = ""
    for fn in feats[:5]:
        if fn in FEAT_LABEL:
            icon, label = FEAT_LABEL[fn]
            feat_chips += f"<span class='chip chip-g'>{icon} {label}</span>"

    # 연령 / 주차 칩
    age_chip  = f"<span class='chip chip-b'>👶 {age_txt}</span>" if age_txt else ""
    park_chip = ""
    if parking and parking.lower() not in ("nan","none",""):
        park_chip = f"<span class='chip chip-y'>🅿 {str(parking)[:25]}</span>"

    main_url = res_url if res_url.startswith("http") else det_url
    map_url  = f"https://map.naver.com/p/search/{name}"

    st.markdown(f"""
    <div class="place-card">
      <div class="card-img-wrap">
        <img class="card-img"
             src="{img_url}"
             alt="{name}"
             onerror="this.src='{FALLBACK_IMG}'">
        <div class="card-badges">{badges_html}</div>
        <div class="rev-cnt">💬 {r_cnt}건</div>
      </div>
      <div class="card-body">
        <div class="card-name">{name}</div>
        <div class="card-addr">📍 {dist} · {addr[:32]}{"…" if len(addr)>32 else ""}</div>
        <div class="chip-row">{feat_chips}</div>
        <div class="chip-row">{age_chip}{park_chip}</div>
    """, unsafe_allow_html=True)

    # AI 추천 이유 (세션 캐시)
    rec_key = f"rec_{pid}"
    if rec_key in st.session_state.ai_recs:
        txt = st.session_state.ai_recs[rec_key]
        st.markdown(f"""
        <div class="rec-box">
          <div class="rec-lbl">💡 이모삼촌의 추천 이유 (AI · 리뷰 기반)</div>
          <div class="rec-txt">{txt}</div>
        </div>""", unsafe_allow_html=True)
    else:
        btn_key = f"{key_prefix}btnrec_{pid}"
        if st.button("💡 추천 이유 보기", key=btn_key):
            with st.spinner(f"'{name}' 분석 중... 🔍"):
                st.session_state.ai_recs[rec_key] = gen_card_rec(
                    client, name, addr, feats, r_text
                )
            st.rerun()

    st.markdown(f"""
        <div class="act-row">
          <a href="{main_url if main_url.startswith('http') else '#'}"
             target="_blank" class="btn-main">📋 예약 / 공식 사이트</a>
          <a href="{map_url}" target="_blank" class="btn-sub">🗺 지도</a>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  11. 세션 상태 초기화
# ════════════════════════════════════════════════════════════════
for _k, _v in [
    ("ai_recs",   {}),
    ("chat_hist", []),
    ("ai_ans",    ""),
    ("last_pids", []),
    ("card_page", 0),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ════════════════════════════════════════════════════════════════
#  12. 리소스 로드
# ════════════════════════════════════════════════════════════════
with st.spinner("📂 데이터 불러오는 중..."):
    try:
        df      = load_places()
        dev_df  = load_dev_data()
    except FileNotFoundError as e:
        st.error(f"⚠️ 파일을 찾을 수 없어요: {e}\n\n"
                 "places.csv, place_features.csv, review_docs.csv, "
                 "baby_development_final.csv 를 앱과 같은 폴더에 넣어주세요.")
        st.stop()

with st.spinner("🗄 벡터 DB 준비 중 (최초 1회만)..."):
    chroma = get_chroma(df)

llm = get_llm()

# ════════════════════════════════════════════════════════════════
#  13. 사이드바
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:18px 0 12px;position:relative;z-index:1">
      <img src="{LOGO_B64}"
           style="width:78px;height:78px;object-fit:contain;
                  border-radius:22px;box-shadow:0 5px 18px rgba(0,0,0,.12);
                  border:3px solid rgba(255,255,255,.85)">
      <div style="font-family:'Jua',cursive;font-size:1.55em;color:#33691E;
                  margin-top:9px;line-height:1">베베노리</div>
      <div style="font-size:.72em;color:#558B2F;font-weight:700;margin-top:4px">
        이모삼촌의 찐 육아 큐레이션 🖍
      </div>
    </div>
    <hr style="border:none;border-top:1.5px dashed #A5D6A7;margin:12px 0">
    <div style="font-size:.88em;font-weight:800;color:#2E7D32;
                margin-bottom:10px;position:relative;z-index:1">
      🔎 원하는 조건으로 필터하기
    </div>
    """, unsafe_allow_html=True)

    age_sel  = st.selectbox("👶 아이 개월 수",    AGE_OPTIONS,  index=0, key="age_sel")
    dist_sel = st.selectbox("📍 자치구 선택",      DISTRICTS,    index=0, key="dist_sel")
    sort_sel = st.selectbox("📊 정렬 기준",
        ["리뷰 많은 순", "이름 순", "연령 낮은 순"], index=0, key="sort_sel")

    st.markdown("""
    <hr style="border:none;border-top:1.5px dashed #A5D6A7;margin:16px 0">
    <div style="font-size:.86em;font-weight:800;color:#2E7D32;
                margin-bottom:10px;position:relative;z-index:1">
      💬 이런 질문 어때요?
    </div>
    """, unsafe_allow_html=True)

    SAMPLE_QS = [
        "주말에 16개월 아이랑 마곡 키즈카페",
        "비 오는 날 18개월 아이 실내 추천",
        "부모도 쉴 수 있는 영유아 키즈카페",
        "수유실 있는 아기 친화 카페",
        "예약 없이 갈 수 있는 키즈카페",
    ]
    for sq in SAMPLE_QS:
        if st.button(sq, key=f"sq_{sq}", use_container_width=True):
            st.session_state["preset_q"] = sq
            st.rerun()

    st.markdown(f"""
    <hr style="border:none;border-top:1.5px dashed #A5D6A7;margin:16px 0">
    <div style="font-size:.7em;color:#81C784;line-height:2;position:relative;z-index:1">
      🤖 AI: Qwen/Qwen2.5-72B (HuggingFace)<br>
      🗄 DB: ChromaDB Persistent + MiniLM-L12<br>
      📊 {len(df)}개 장소 · {int(df['review_count'].sum()):,}건 리뷰<br>
      📗 경기도 발달 가이드북 연동<br>
      ♥ 광고 없이 진심만 담았어요
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  14. 히어로 헤더
# ════════════════════════════════════════════════════════════════
total_places  = len(df)
total_reviews = int(df["review_count"].sum())
total_dist    = df["district"].nunique()

st.markdown(f"""
<div class="bebe-hero">
  <div class="hero-text">
    <div class="hero-title">🖍 베베노리</div>
    <div class="hero-sub">
      이모삼촌이 직접 검증한 서울형 키즈카페 AI 큐레이션<br>
      광고 없이 진심만 담았어요 · 팀 2모3촌
    </div>
    <div class="hero-pills">
      <span class="hero-pill">📍 서울 전역 {total_dist}개 구</span>
      <span class="hero-pill">🏠 {total_places}개 키즈카페</span>
      <span class="hero-pill">💬 리뷰 {total_reviews:,}건</span>
      <span class="hero-pill">📗 발달 가이드북 연동</span>
      <span class="hero-pill">🗄 ChromaDB 벡터 검색</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  15. 발달 대시보드 (개월 수 선택 시 상단 표시)
# ════════════════════════════════════════════════════════════════
if age_sel != "전체":
    render_dev_dashboard(dev_df, age_sel)

# ════════════════════════════════════════════════════════════════
#  16. STEP 1 + 4: 채팅 인터페이스
# ════════════════════════════════════════════════════════════════
preset = st.session_state.pop("preset_q", "")

st.markdown("""
<div class="chat-wrap">
  <div class="chat-lbl">🎪 베베노리에게 물어보세요!</div>
  <div class="chat-hint">
    예: "주말에 16개월 아이랑 마곡에서 놀 곳 추천해줘" ·
    "비 오는 날 갈 영유아 키즈카페" ·
    "부모도 쉴 수 있는 곳"
  </div>
</div>
""", unsafe_allow_html=True)

c_inp, c_btn = st.columns([5, 1])
with c_inp:
    query_input = st.text_input(
        label="질문",
        value=preset,
        placeholder="예) 강남에서 18개월 아이랑 갈 키즈카페 추천해줘",
        label_visibility="collapsed",
        key="query_input",
    )
with c_btn:
    ask_clicked = st.button("🔍 물어보기", key="ask_btn", use_container_width=True)

# 이전 대화 표시 (최근 3턴)
if st.session_state.chat_hist:
    for role, msg in st.session_state.chat_hist[-6:]:
        if role == "user":
            st.markdown(f"<div class='user-bubble'>{msg}</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='ai-bubble'>"
                f"<div class='ai-label'>🖍 베베노리</div>{msg}"
                f"</div>",
                unsafe_allow_html=True,
            )

# ── 질문 처리 ──
if ask_clicked and query_input.strip():
    q = query_input.strip()

    # STEP 2: 자치구 자동 감지
    auto_dist = dist_sel if dist_sel != "전체" else ""
    for d in DISTRICTS[1:]:
        if d in q or d.replace("구","") in q:
            auto_dist = d
            break

    with st.spinner("이모삼촌이 최적의 장소를 찾는 중... 🔍"):
        # STEP 3: 벡터 검색
        top_pids = rag_retrieve(chroma, q, auto_dist, n=4)
        if not top_pids:  # 폴백: 지역 필터 직접
            sub = df[df["district"] == auto_dist] if auto_dist else df
            top_pids = sub.sort_values("review_count", ascending=False).head(4)["place_id"].tolist()

        # STEP 4: 답변 생성
        ctx = build_context(df, top_pids)
        ans = gen_answer(llm, q, ctx)

    st.session_state.chat_hist.append(("user", q))
    st.session_state.chat_hist.append(("ai",   ans))
    st.session_state.ai_ans    = ans
    st.session_state.last_pids = top_pids
    st.session_state.card_page = 0
    st.rerun()

# 현재 답변
if st.session_state.ai_ans:
    st.markdown(
        f"<div class='ai-bubble'>"
        f"<div class='ai-label'>🖍 베베노리 (AI 추천)</div>"
        f"{st.session_state.ai_ans}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  17. 필터링 + 카드 목록 (STEP 5)
# ════════════════════════════════════════════════════════════════
filtered = df.copy()

# 자치구 필터
if dist_sel != "전체":
    filtered = filtered[filtered["district"] == dist_sel]

# 연령 필터 (연나이 기준)
yr_range = AGE_TO_YEAR.get(age_sel)
if yr_range:
    lo, hi = yr_range
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

# AI 검색 결과를 상단으로
if st.session_state.last_pids:
    top_pids = st.session_state.last_pids
    top_rows = filtered[filtered["place_id"].isin(top_pids)]
    rest     = filtered[~filtered["place_id"].isin(top_pids)]
    filtered = pd.concat([top_rows, rest]).reset_index(drop=True)
else:
    filtered = filtered.reset_index(drop=True)

# ── 결과 헤더 ──
region_lbl = dist_sel if dist_sel != "전체" else "서울 전체"
age_lbl    = age_sel  if age_sel  != "전체" else "전 연령"
st.markdown(
    f"<div class='result-header'>"
    f"✨ <b>{region_lbl}</b> · <b>{age_lbl}</b> 맞춤 키즈카페"
    f"<span class='result-count'>🏠 {len(filtered)}개</span>"
    f"</div>",
    unsafe_allow_html=True,
)

# ── 카드 그리드 (2열, 페이지네이션) ──
PER_PAGE = 6

if filtered.empty:
    st.markdown("""
    <div class="empty-box">
      <span class="empty-ico">🖍</span>
      <div class="empty-msg">해당 조건의 키즈카페가 없어요!</div>
      <div class="empty-sub">
        이모삼촌이 아직 공부 중이에요 🌸<br>
        지역이나 개월 수 조건을 바꿔보세요.
      </div>
    </div>""", unsafe_allow_html=True)
else:
    total_pages = max(1, (len(filtered) - 1) // PER_PAGE + 1)

    # 페이지 범위 보정
    if st.session_state.card_page >= total_pages:
        st.session_state.card_page = 0

    p_start = st.session_state.card_page * PER_PAGE
    p_end   = min(p_start + PER_PAGE, len(filtered))
    page_df = filtered.iloc[p_start:p_end]

    cols = st.columns(2, gap="medium")
    for i, (_, row) in enumerate(page_df.iterrows()):
        with cols[i % 2]:
            render_place_card(row, llm, key_prefix=f"p{st.session_state.card_page}_")

            # 발달 연계 안내 (장소별 접기/펼치기)
            with st.expander(f"🌱 {row['place_name']} — 이 공간에서 기대되는 발달 효과"):
                if age_sel != "전체":
                    render_dev_dashboard(dev_df, age_sel)
                else:
                    st.markdown("""
                    <div style="padding:12px;background:#F1F8E9;border-radius:14px;
                                font-size:.83em;color:#558B2F;text-align:center">
                      👆 사이드바에서 아이 <b>개월 수를 선택</b>하면<br>
                      발달 정보를 확인할 수 있어요!
                    </div>""", unsafe_allow_html=True)

    # ── 페이지 네이션 ──
    if total_pages > 1:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        pc = st.columns([1, 2, 1])
        with pc[0]:
            if st.session_state.card_page > 0:
                if st.button("◀ 이전", use_container_width=True):
                    st.session_state.card_page -= 1
                    st.rerun()
        with pc[1]:
            st.markdown(
                f"<div style='text-align:center;font-family:Jua,cursive;"
                f"color:#43A047;padding:9px;font-size:1em;font-weight:800'>"
                f"{st.session_state.card_page+1} / {total_pages} 페이지</div>",
                unsafe_allow_html=True,
            )
        with pc[2]:
            if st.session_state.card_page < total_pages - 1:
                if st.button("다음 ▶", use_container_width=True):
                    st.session_state.card_page += 1
                    st.rerun()

# ════════════════════════════════════════════════════════════════
#  18. 일괄 AI 추천 생성 버튼
# ════════════════════════════════════════════════════════════════
st.markdown("<hr>", unsafe_allow_html=True)
c_l, c_r = st.columns([3, 1])
with c_l:
    st.markdown(
        "**💡 이모삼촌 추천 이유**를 아직 보지 못한 카드에 대해 한 번에 생성해드려요!"
    )
with c_r:
    if st.button("✨ 전체 AI 추천", key="gen_all", use_container_width=True):
        pending = [
            row for _, row in filtered.iloc[:PER_PAGE].iterrows()
            if f"rec_{row['place_id']}" not in st.session_state.ai_recs
        ]
        if not pending:
            st.success("이미 모든 추천 이유가 있어요! 🎉")
        else:
            prog = st.progress(0)
            msg  = st.empty()
            for i, row in enumerate(pending):
                pid = str(row["place_id"])
                msg.markdown(f"🖍 **{row['place_name']}** 분석 중... ({i+1}/{len(pending)})")
                try:
                    st.session_state.ai_recs[f"rec_{pid}"] = gen_card_rec(
                        llm,
                        str(row["place_name"]),
                        str(row["address"]),
                        row["features"] if isinstance(row["features"],list) else [],
                        str(row["review_text"]),
                    )
                except Exception:
                    st.session_state.ai_recs[f"rec_{pid}"] = (
                        "이모삼촌이 잠시 쉬고 있어요. 다시 시도해 주세요! 🌸"
                    )
                prog.progress((i + 1) / len(pending))
            msg.empty()
            st.success("✅ 완료! 카드에서 추천 이유를 확인하세요 🎉")
            st.rerun()

# ════════════════════════════════════════════════════════════════
#  19. 푸터
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<hr>
<div class="bebe-footer">
  <strong>🖍 베베노리 (BebeNori) v2.0</strong><br>
  이모삼촌이 만든 세상에서 가장 다정한 서울형 키즈카페 AI 큐레이션<br>
  📊 places.csv ({total_places}개) · review_docs.csv ({total_reviews:,}건) ·
     place_features.csv · baby_development_final.csv<br>
  📗 경기도육아종합지원센터 영유아 발달지원 가이드북 2023-13호 (지연님 데이터)<br>
  📘 초보아빠를위한육아가이드(배포용)_.pdf (Colab 업로드 후 RAG 확장 가능)<br>
  🗄 ChromaDB PersistentClient ({CHROMA_DIR}) + paraphrase-multilingual-MiniLM-L12-v2<br>
  🤖 LLM: Qwen/Qwen2.5-72B-Instruct via HuggingFace Inference API (openai 라이브러리)<br>
  <span style="color:#81C784">♥ 광고 없이 진심만 담았어요 — 팀 2모3촌</span>
</div>
""", unsafe_allow_html=True)
