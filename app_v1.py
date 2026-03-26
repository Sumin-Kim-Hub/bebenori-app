# ╔══════════════════════════════════════════════════════════════════════╗
# ║    베베노리 (BebeNori) v4.0 — 채팅 중심 최종판                        ║
# ║    팀: 2모3촌  |  Google Colab + cloudflared                        ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# ═══════════════════════════════════════════════════════════
#  Colab 실행 가이드
# ═══════════════════════════════════════════════════════════
# !pip install streamlit chromadb sentence-transformers openai pandas -q
#
# import os; os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN_HERE"
#
# !streamlit run app.py --server.port 8501 &>/content/st.log &
# import time; time.sleep(5)
#
# # cloudflared (비밀번호 없는 외부 접속)
# !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
# !dpkg -i cloudflared-linux-amd64.deb
# !cloudflared tunnel --url http://localhost:8501 &
# import time; time.sleep(6)
# # 출력된 https://xxxx.trycloudflare.com 으로 바로 접속!
# ═══════════════════════════════════════════════════════════

import os, base64
from pathlib import Path
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────
# 0. 페이지 설정
# ─────────────────────────────────────────────────
st.set_page_config(
    page_title="베베노리 | 서울형 키즈카페",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────
# 1. 파일 경로 / 환경변수
# ─────────────────────────────────────────────────
PLACES_CSV   = "places.csv"
FEATURES_CSV = "place_features.csv"
REVIEWS_CSV  = "review_docs.csv"
DEV_CSV      = "baby_development_final.csv"
LOGO_FILE    = "logo.jpg"           # 없으면 mascot으로 폴백
MASCOT_FILE  = "bebenori_mascot.png"
GRID_FILE    = "grid_pattern_png.png"
CHROMA_DIR   = "./bebenori_db"
FALLBACK_IMG = "https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&w=800&q=80"
PUBLIC_BOOK  = "https://yeyak.seoul.go.kr"

HF_TOKEN = os.environ.get("HF_TOKEN", "hf_YOUR_TOKEN_HERE")

# ─────────────────────────────────────────────────
# 2. 이미지 유틸
# ─────────────────────────────────────────────────
def _b64(path: str, fallback: str = "") -> str:
    p = Path(path)
    if p.exists():
        ext = "jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "png"
        with open(p, "rb") as f:
            return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
    return fallback

# 로고: logo.jpg 우선, 없으면 마스코트
LOGO_SRC   = _b64(LOGO_FILE) or _b64(MASCOT_FILE, FALLBACK_IMG)
GRID_SRC   = _b64(GRID_FILE)
GRID_CSS   = f"url('{GRID_SRC}')" if GRID_SRC else "none"
MASCOT_SRC = _b64(MASCOT_FILE, FALLBACK_IMG)

# ─────────────────────────────────────────────────
# 3. 전역 CSS
# ─────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Nanum+Square+Round:wght@400;700;800&display=swap');

/* ── 기반 ─────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
    font-family: 'Nanum Square Round', 'Apple SD Gothic Neo', sans-serif;
}}

/* ── 배경: 그리드 패턴 ────────────────────────── */
.stApp {{
    background-color: #FEFCF3 !important;
    background-image: {GRID_CSS} !important;
    background-repeat: repeat !important;
    background-size: 440px !important;
    background-attachment: fixed !important;
}}
[data-testid="stAppViewContainer"] {{ background: transparent !important; }}
[data-testid="stHeader"]           {{ background: transparent !important; }}
.block-container {{ padding-top: 0 !important; max-width: 1060px; }}

/* ── 사이드바 ─────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(170deg,#EBF4FF 0%,#FFF9E6 100%) !important;
    border-right: 2px solid #D6E8FF !important;
}}
[data-testid="stSidebar"] * {{ color: #1A3A6B !important; }}

/* ── 헤더 ─────────────────────────────────────── */
.bebe-header {{
    position: relative; overflow: hidden;
    background: linear-gradient(135deg,#6B9DD4 0%,#4A7FBE 55%,#2E5F9E 100%);
    border-radius: 0 0 44px 44px;
    padding: 36px 40px 44px;
    margin: -1rem -1rem 0;
    text-align: center;
    box-shadow: 0 8px 32px rgba(107,157,212,.38);
    border-bottom: 3px solid rgba(255,255,255,.18);
}}
.bebe-header::before {{
    content: '';
    position: absolute; inset: 0; pointer-events: none;
    background: radial-gradient(circle at 15% 85%, rgba(242,183,5,.22) 0%, transparent 45%),
                radial-gradient(circle at 85% 15%, rgba(255,255,255,.1) 0%, transparent 40%);
}}
.header-logo {{
    display: block; margin: 0 auto 18px;
    max-height: 120px; max-width: 320px;
    object-fit: contain; position: relative; z-index: 2;
    filter: drop-shadow(0 6px 20px rgba(0,0,0,.25));
    animation: hfloat 4s ease-in-out infinite;
}}
@keyframes hfloat {{
    0%,100% {{ transform: translateY(0); }}
    50%      {{ transform: translateY(-7px); }}
}}
.header-slogan {{
    font-family: 'Nanum Square Round', sans-serif;
    font-weight: 800; font-size: 1em;
    color: rgba(255,255,255,.96);
    text-shadow: 0 2px 8px rgba(0,0,0,.28);
    position: relative; z-index: 2;
    letter-spacing: .5px; line-height: 1.6;
}}
.header-pills {{
    display: flex; gap: 8px; flex-wrap: wrap;
    justify-content: center; margin-top: 14px;
    position: relative; z-index: 2;
}}
.hpill {{
    background: rgba(255,255,255,.2); backdrop-filter: blur(6px);
    color: #fff; font-size: .72em; font-weight: 800;
    padding: 5px 13px; border-radius: 20px;
    border: 1px solid rgba(255,255,255,.32);
    text-shadow: 0 1px 3px rgba(0,0,0,.15);
}}

/* ── 퀵 필터 ──────────────────────────────────── */
.quick-wrap {{
    display: flex; gap: 10px; flex-wrap: wrap;
    margin: 22px 0 6px;
}}
.qbtn {{
    background: #F2B705; color: #3D2B00 !important;
    font-weight: 800; font-size: .82em;
    padding: 10px 18px; border-radius: 22px;
    border: none; cursor: pointer;
    box-shadow: 0 4px 14px rgba(242,183,5,.32);
    transition: all .2s; text-decoration: none;
    display: inline-block; white-space: nowrap;
}}
.qbtn:hover {{
    background: #D4A005; transform: translateY(-2px);
    box-shadow: 0 7px 18px rgba(242,183,5,.4);
}}
.qbtn.active {{
    background: #6B9DD4; color: #fff !important;
    box-shadow: 0 4px 14px rgba(107,157,212,.38);
}}

/* ── 채팅 래퍼 ────────────────────────────────── */
.chat-wrap {{
    background: rgba(255,255,255,.88);
    backdrop-filter: blur(10px);
    border-radius: 28px;
    padding: 24px 28px;
    margin: 14px 0 18px;
    border: 1.5px solid #D6E8FF;
    box-shadow: 0 6px 24px rgba(107,157,212,.1);
}}
.chat-lbl {{
    font-family: 'Jua', cursive; font-size: 1.05em;
    color: #1A3A6B; margin-bottom: 5px;
    display: flex; align-items: center; gap: 8px;
}}
.chat-hint {{ font-size:.78em; color:#A8C4E8; line-height:1.7; margin-bottom:14px; }}

/* ── 대화 버블 ────────────────────────────────── */
.bubble-user {{
    background: #6B9DD4; color: #fff;
    border-radius: 22px 4px 22px 22px;
    padding: 13px 18px; margin: 10px 0 4px;
    font-size: .9em; max-width: 74%; margin-left: auto;
    box-shadow: 0 4px 14px rgba(107,157,212,.32);
    line-height: 1.65; font-weight: 700;
}}
.bubble-ai {{
    background: linear-gradient(135deg,#FFFDE7 0%,#FFF9D0 100%);
    border: 1.5px solid #F2B705;
    border-radius: 4px 22px 22px 22px;
    padding: 18px 22px; margin: 4px 0 18px;
    font-size: .9em; color: #3A2800;
    line-height: 1.82;
    box-shadow: 0 4px 18px rgba(242,183,5,.14);
    max-width: 92%;
}}
.bubble-ai-lbl {{
    font-family: 'Jua', cursive;
    font-size: .8em; color: #B8860B;
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 6px;
    font-weight: 800;
}}

/* ── 시설 정보 인포 테이블 ───────────────────── */
.info-table {{
    width: 100%; border-collapse: collapse;
    margin: 14px 0 10px; font-size: .82em;
    background: rgba(255,255,255,.7);
    border-radius: 14px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(107,157,212,.1);
}}
.info-table th {{
    background: #6B9DD4; color: #fff;
    padding: 9px 14px; text-align: left;
    font-weight: 800; font-size: .9em;
}}
.info-table td {{
    padding: 8px 14px; border-bottom: 1px solid #EBF4FF;
    color: #2C3E50; vertical-align: top; line-height: 1.55;
}}
.info-table tr:last-child td {{ border-bottom: none; }}
.info-table tr:nth-child(even) td {{ background: rgba(107,157,212,.04); }}

/* ── 이모삼촌 팁 박스 ─────────────────────────── */
.tip-box {{
    background: linear-gradient(135deg,#FFF8CC,#FFFDE7);
    border: 2px solid #F2B705;
    border-radius: 18px; padding: 14px 18px;
    margin: 14px 0 4px;
    box-shadow: 0 3px 12px rgba(242,183,5,.18);
}}
.tip-lbl {{
    font-family: 'Jua', cursive;
    font-size: .85em; color: #B8860B; margin-bottom: 6px;
    display: flex; align-items: center; gap: 5px;
}}
.tip-txt {{ font-size: .83em; color: #5D4000; line-height: 1.72; }}

/* ── 예약 버튼 (인라인) ───────────────────────── */
.res-link {{
    display: inline-block; background: #F2B705;
    color: #3A2800 !important; font-weight: 800;
    padding: 8px 18px; border-radius: 14px;
    font-size: .8em; text-decoration: none;
    box-shadow: 0 3px 10px rgba(242,183,5,.32);
    transition: background .2s; margin: 4px 4px 4px 0;
}}
.res-link:hover {{ background: #D4A005; text-decoration: none; }}
.map-link {{
    display: inline-block; background: #EBF4FF;
    color: #1A3A6B !important; font-weight: 800;
    padding: 8px 18px; border-radius: 14px;
    font-size: .8em; text-decoration: none;
    border: 1.5px solid #D6E8FF;
    transition: background .2s; margin: 4px 4px 4px 0;
}}
.map-link:hover {{ background: #D6E8FF; text-decoration: none; }}

/* ── 발달 대시보드 ────────────────────────────── */
.dev-wrap {{
    background: rgba(255,255,255,.88);
    border-radius: 26px; padding: 24px 26px;
    margin: 18px 0;
    border: 1.5px solid #D6E8FF;
    box-shadow: 0 5px 20px rgba(107,157,212,.09);
}}
.dev-hdr {{
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 16px; margin-bottom: 18px;
    border-bottom: 2px dashed #D6E8FF;
}}
.dev-hdr-main {{
    font-family: 'Jua', cursive;
    font-size: 1.15em; color: #1A3A6B; margin: 0;
}}
.dev-hdr-sub {{ font-size: .74em; color: #A8C4E8; font-weight: 700; margin-top: 3px; }}
.dev-age-pill {{
    margin-left: auto;
    background: linear-gradient(135deg,#6B9DD4,#4A7FBE);
    color: #fff; font-family:'Jua',cursive; font-size:.95em;
    padding: 7px 18px; border-radius: 20px; white-space: nowrap;
    box-shadow: 0 3px 10px rgba(107,157,212,.3);
}}

.dom-grid {{
    display: grid; gap: 12px;
    grid-template-columns: repeat(auto-fill,minmax(240px,1fr));
}}
.dom-card {{
    border-radius: 18px; padding: 16px 16px 14px;
    border: 1.5px solid transparent;
    transition: transform .2s, box-shadow .2s;
    position: relative; overflow: hidden;
}}
.dom-card::after {{
    content:''; position:absolute; top:-22px; right:-22px;
    width:64px; height:64px; border-radius:50%;
    background:rgba(255,255,255,.22);
}}
.dom-card:hover {{ transform:translateY(-3px); box-shadow:0 9px 24px rgba(0,0,0,.1); }}
.dom-gross  {{ background:linear-gradient(135deg,#E3F2FD,#BBDEFB); border-color:#90CAF9; }}
.dom-fine   {{ background:linear-gradient(135deg,#E8EAF6,#C5CAE9); border-color:#9FA8DA; }}
.dom-lang   {{ background:linear-gradient(135deg,#FFF9C4,#FFF176); border-color:#FDD835; }}
.dom-cog    {{ background:linear-gradient(135deg,#E8F5E9,#C8E6C9); border-color:#A5D6A7; }}
.dom-social {{ background:linear-gradient(135deg,#FCE4EC,#F8BBD0); border-color:#F48FB1; }}
.dom-motor  {{ background:linear-gradient(135deg,#FFF3E0,#FFE0B2); border-color:#FFCC80; }}
.dom-icon  {{ font-size:1.8em; display:block; margin-bottom:6px; }}
.dom-title {{ font-family:'Jua',cursive; font-size:.9em; margin-bottom:6px; }}
.dom-gross  .dom-title {{ color:#1565C0; }}
.dom-fine   .dom-title {{ color:#283593; }}
.dom-lang   .dom-title {{ color:#F57F17; }}
.dom-cog    .dom-title {{ color:#2E7D32; }}
.dom-social .dom-title {{ color:#880E4F; }}
.dom-motor  .dom-title {{ color:#E65100; }}
.dom-text {{ font-size:.74em; line-height:1.7; color:#424242; }}
.dom-bar  {{ height:5px; border-radius:3px; margin-top:10px;
    background:rgba(255,255,255,.45); overflow:hidden; }}
.dom-fill {{ height:100%; border-radius:3px;
    background:rgba(255,255,255,.75);
    animation:barfill 1.4s ease-out forwards; }}
@keyframes barfill {{ from{{width:0}} }}

/* ── 빈 결과 ──────────────────────────────────── */
.empty-box {{
    text-align:center; padding:44px 24px;
    background:rgba(255,255,255,.85);
    border-radius:22px; border:1.5px dashed #D6E8FF; margin:16px 0;
}}

/* ── Streamlit 위젯 오버라이드 ─────────────────── */
.stButton > button {{
    background: #F2B705 !important; color: #3A2800 !important;
    font-weight: 800 !important; border: none !important;
    border-radius: 14px !important;
    font-family: 'Nanum Square Round', sans-serif !important;
    box-shadow: 0 4px 12px rgba(242,183,5,.28) !important;
    transition: background .2s !important;
}}
.stButton > button:hover {{ background: #D4A005 !important; }}
.stTextInput > div > div > input {{
    border-radius: 14px !important;
    border: 1.5px solid #6B9DD4 !important;
    background: rgba(255,255,255,.92) !important;
    color: #1A3A6B !important;
    font-family: 'Nanum Square Round', sans-serif !important;
    padding: 12px 16px !important;
    font-size: 1em !important;
}}
.stSelectbox > div > div {{ border-radius:14px !important; }}
div[data-testid="stExpander"] {{
    border: 1.5px solid #D6E8FF !important;
    border-radius: 18px !important;
    background: rgba(255,255,255,.85) !important;
}}
hr {{ border:none; border-top:2px dashed #D6E8FF !important; margin:24px 0; }}

/* ── 사이드바 섹션 제목 ──────────────────────── */
.sb-title {{
    font-family: 'Jua', cursive; font-size: .95em;
    color: #1A3A6B; margin: 16px 0 8px;
    padding: 8px 12px;
    background: rgba(107,157,212,.1);
    border-radius: 10px; border-left: 4px solid #6B9DD4;
}}

/* ── 푸터 ────────────────────────────────────── */
.bebe-footer {{
    text-align:center; padding:26px 0 20px;
    color:#A8C4E8; font-size:.75em; line-height:2;
}}
.bebe-footer strong {{ color:#6B9DD4; }}
.bebe-footer a {{ color:#F2B705 !important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# 4. 상수 / 매핑
# ─────────────────────────────────────────────────
DISTRICTS = ["전체"] + sorted([
    "강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구",
    "노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구",
    "성동구","성북구","송파구","양천구","영등포구","용산구","은평구",
    "종로구","중구","중랑구",
])

FEAT_LABEL = {
    "parking_available":         ("🅿", "주차 가능"),
    "reservation_available":     ("📋", "예약 필요"),
    "weekend_operation":         ("📅", "주말 운영"),
    "toddler_friendly":          ("👶", "영유아 친화"),
    "toddler_positive":          ("⭐", "영유아 추천"),
    "preschool_friendly":        ("🧒", "유아 적합"),
    "lower_elementary_friendly": ("🎒", "초등 저학년"),
    "program_info_available":    ("🎨", "프로그램"),
    "group_visit_available":     ("👨‍👩‍👧", "단체 가능"),
    "spacious_positive":         ("🏟", "넓어요"),
    "safety_positive":           ("🛡", "안전"),
    "cleanliness_positive":      ("✨", "깨끗해요"),
    "active_play_positive":      ("🏃", "에너지 발산"),
}
FEAT_SKIP = {
    "district","has_phone","guardian_rule_mentioned",
    "socks_rule_mentioned","cleanliness_negative","crowded_warning",
}

QUICK_FILTERS = [
    ("#내 주변 찾기(GPS)",   "내 주변 서울형 키즈카페 추천해줘"),
    ("#에너지 발산(대근육)", "뛰어놀 수 있는 대근육 발달 키즈카페 추천"),
    ("#오감 놀이(감각)",     "오감 자극 감각 놀이가 있는 키즈카페 추천"),
    ("#영유아 전용",         "영유아 전용 키즈카페 추천해줘"),
]

DOMAINS = [
    ("gross_motor_skills",   "🦵","대근육 발달","dom-gross", 82),
    ("fine_motor_skills",    "✋","소근육 발달","dom-fine",  74),
    ("language_development", "🗣","언어 발달",  "dom-lang",  70),
    ("cognitive_development","🧠","인지 발달",  "dom-cog",   78),
    ("social_development",   "👫","사회성 발달","dom-social",67),
    ("motor_development",    "🏃","전반 운동",  "dom-motor", 85),
]

def months_to_dev_age(m: int) -> str:
    if m <= 1:  return "0~1"
    if m <= 3:  return "1~3"
    if m <= 6:  return "4~6"
    if m <= 9:  return "7~9"
    if m <= 12: return "10~12"
    if m <= 24: return "13~24"
    return "25~36"

def months_to_yr(m: int) -> tuple:
    yr = m / 12
    return (max(0, yr - 0.5), yr + 0.8)

# ─────────────────────────────────────────────────
# 5. 시스템 프롬프트 (5단계 구조)
# ─────────────────────────────────────────────────
SYSTEM_PROMPT = """Role
너는 서울시 공공 데이터를 기반으로 부모님들에게 아이와 방문하기 좋은 키즈카페를 추천하는 AI 이모삼촌 '베베노리(BebeNori)'야. 너의 정체성은 아이를 진심으로 아끼는 '2모3촌(이모 2명, 삼촌 3명)'으로, 전문적이면서도 아주 다정하고 친절한 말투를 사용해야 해.

Task
사용자의 입력(지역, 아이 연령, 특징 등)을 바탕으로 제공된 [Context] 내에서 가장 적합한 서울형 키즈카페를 추천해줘. 단순한 정보 나열이 아니라, 해당 시설이 아이의 발달 단계에 어떤 긍정적인 영향을 주는지 반드시 포함해야 해.

RAG
1. [Place_DB]: 장소명, 주소, 주요 시설, 이용료, 예약 링크 정보가 포함됨.
2. [Development_DB]: 연령별(개월수) 발달 특징 및 추천 활동 가이드가 포함됨.
3. 답변 구성 시: [Place_DB]의 '주요 시설'과 [Development_DB]의 '발달 특징'을 논리적으로 연결해. (예: "이곳의 트램펄린 시설은 24개월 아이의 균형 감각과 대근육 발달에 큰 도움을 줍니다.")

Constraints (반드시 지킬 것)
1. Hallucination 방지: 제공된 [Context]에 없는 장소는 절대 추천하지 마. 모르는 정보라면 정직하게 모른다고 답하고 서울시 공공서비스 예약 사이트(https://yeyak.seoul.go.kr)를 안내해.
2. 정확도: 추천하는 장소가 사용자가 언급한 지역 및 연령 기준에 부합하는지 최종 확인해.
3. 페르소나: "조카를 생각하는 마음으로 엄선했어요", "부모님, 오늘 고생 많으셨죠?" 같은 다정한 문구를 섞어서 답변해.

답변 형식 (5단계 — 반드시 이 순서를 지켜):

[1단계] 다정한 인사 + 추천 장소 이름 및 위치 (1~2문장)

[2단계] 추천 이유 — 아동 발달 근거 포함
- [Place_DB]의 시설/특징과 [Development_DB]의 발달 단계를 연결하여 2~3문장으로 설명
- 예: "이곳의 [시설명]이 [X]개월 아이의 [발달 영역]에 [구체적 효과]를 줍니다"

[3단계] 시설 정보 요약표
다음 항목을 반드시 포함한 표 또는 리스트로 정리:
| 항목 | 내용 |
|------|------|
| 💰 이용료 | ... (서울형 키즈카페는 기본 3,000원 수준) |
| 👶 권장 연령 | ... |
| 🅿 주차 | ... (parking_info 데이터 그대로 요약) |
| 🕒 운영 시간 | ... |
| ⚠️ 혼잡도 | ... (crowded_warning 데이터 있으면 반영, 없으면 '예약 확인 권장') |

[4단계] 예약 안내
- 예약 링크: [장소명 예약하기](실제 reservation_url 또는 https://yeyak.seoul.go.kr)

[5단계] 💡 이모삼촌의 한마디
- 리뷰에서 추출한 실질적 방문 팁 1~2가지
- 예: "여기는 미끄럼방지 양말 필수예요! 없으면 입장 불가랍니다 😅", "주차가 협소하니 대중교통을 강력 추천해요 🚌"
- 데이터에 없을 경우 일반적인 서울형 키즈카페 팁 제공"""

# ─────────────────────────────────────────────────
# 6. 데이터 로딩 (st.cache_data)
# ─────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_places() -> pd.DataFrame:
    places = pd.read_csv(PLACES_CSV)
    places["age_min"] = pd.to_numeric(places["age_min"], errors="coerce").fillna(0)
    places["age_max"] = pd.to_numeric(places["age_max"], errors="coerce").fillna(13)
    places["image_url"] = places["image_url"].fillna(FALLBACK_IMG)

    feats = pd.read_csv(FEATURES_CSV)
    feats["confidence"] = pd.to_numeric(feats["confidence"], errors="coerce").fillna(0)
    high = feats[(feats["confidence"] >= 0.7) & (~feats["feature_name"].isin(FEAT_SKIP))]
    feat_map: dict = {}
    for _, r in high.iterrows():
        pid = r["place_id"]; fn = r["feature_name"]
        if pid not in feat_map: feat_map[pid] = []
        if fn not in feat_map[pid]: feat_map[pid].append(fn)

    # crowded_warning (낮은 confidence도 포함)
    cw = feats[feats["feature_name"] == "crowded_warning"]
    crowded_set = set(cw["place_id"].tolist())

    # socks rule
    socks = feats[feats["feature_name"] == "socks_rule_mentioned"]
    socks_set = set(socks["place_id"].tolist())

    revs = pd.read_csv(REVIEWS_CSV)
    agg  = (
        revs.groupby("place_id")
        .agg(
            review_count=("doc_id",  "count"),
            review_text =("content", lambda x: " ".join(
                x.dropna().astype(str).tolist()[:5])),
        )
        .reset_index()
    )
    df = places.merge(agg, on="place_id", how="left")
    df["review_count"] = df["review_count"].fillna(0).astype(int)
    df["review_text"]  = df["review_text"].fillna("")
    df["features"]     = df["place_id"].map(feat_map).apply(
        lambda x: x if isinstance(x, list) else [])
    df["is_crowded"]   = df["place_id"].isin(crowded_set)
    df["needs_socks"]  = df["place_id"].isin(socks_set)
    return df


@st.cache_data(show_spinner=False)
def load_dev() -> pd.DataFrame:
    return pd.read_csv(DEV_CSV)


# ─────────────────────────────────────────────────
# 7. ChromaDB PersistentClient
# ─────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_chroma(df: pd.DataFrame):
    try:
        import chromadb
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction)
        ef     = SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2")
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        names  = [c.name for c in client.list_collections()]
        if "bebe_v4" in names:
            col = client.get_collection("bebe_v4", embedding_function=ef)
            if col.count() == len(df):
                return col
            client.delete_collection("bebe_v4")
        col = client.create_collection("bebe_v4", embedding_function=ef)
        docs, ids, metas = [], [], []
        for _, r in df.iterrows():
            pid  = str(r["place_id"])
            prog = str(r.get("program_info_text",""))[:180]
            feat = ", ".join(r["features"][:6])
            rev  = str(r["review_text"])[:450]
            text = (f"{r['place_name']} {r['district']} {r['address']} "
                    f"{r['age_text']} {prog} {feat} {rev}")
            docs.append(text); ids.append(pid)
            metas.append({"place_id": pid,
                          "place_name": str(r["place_name"]),
                          "district":   str(r["district"])})
        for i in range(0, len(docs), 64):
            col.add(documents=docs[i:i+64],
                    ids=ids[i:i+64],
                    metadatas=metas[i:i+64])
        return col
    except Exception:
        return None


# ─────────────────────────────────────────────────
# 8. LLM 클라이언트 (openai → HuggingFace)
# ─────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_llm():
    try:
        from openai import OpenAI
        return OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=HF_TOKEN)
    except Exception:
        return None


def llm_chat(client, messages: list, max_tokens: int = 600) -> str:
    if client is None:
        return (f"AI 클라이언트가 준비되지 않았어요. HF_TOKEN을 확인해 주세요! 🌸\n"
                f"서울시 공공서비스 예약: {PUBLIC_BOOK}")
    try:
        r = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.72)
        return r.choices[0].message.content.strip()
    except Exception as e:
        return (f"잠깐 쉬고 있어요 😅 잠시 후 다시 시도해 주세요!\n"
                f"👉 {PUBLIC_BOOK} (오류: {str(e)[:80]})")


# ─────────────────────────────────────────────────
# 9. RAG 파이프라인
# ─────────────────────────────────────────────────
def rag_retrieve(col, query: str, district: str, n: int = 4) -> list:
    if col is None: return []
    w = {"district": {"$eq": district}} if district and district != "전체" else None
    try:
        res = col.query(query_texts=[query], n_results=n, where=w)
        return res["ids"][0] if res["ids"] else []
    except Exception:
        return []


def _parking_short(raw: str) -> str:
    """주차 정보를 2줄 이내로 요약."""
    if not raw or str(raw).lower() in ("nan","none",""):
        return "정보 없음"
    raw = str(raw).strip()
    # 첫 번째 문장 또는 80자
    first = raw.split("- ")[1] if "- " in raw else raw
    first = first.split("\n")[0].strip()
    return first[:80] + ("…" if len(first) > 80 else "")


def build_context(df: pd.DataFrame, dev_df: pd.DataFrame,
                  pids: list, months: int) -> str:
    rows = df[df["place_id"].isin(pids)]
    place_parts = []
    for _, r in rows.iterrows():
        feat_str   = ", ".join(r["features"][:5]) or "정보 없음"
        park_str   = _parking_short(str(r.get("parking_info","")))
        op_str     = str(r.get("operating_hours_text",""))[:120] or "홈페이지 확인"
        res_url    = str(r.get("reservation_url","")).strip() or PUBLIC_BOOK
        crowded    = "주말 혼잡 주의" if r.get("is_crowded") else "예약 확인 권장"
        socks_tip  = "미끄럼방지 양말 필수" if r.get("needs_socks") else ""
        rev        = str(r["review_text"])[:300]
        age_min    = r.get("age_min", 0)
        age_max    = r.get("age_max", 13)

        place_parts.append(
            f"[Place]\n"
            f"  장소명: {r['place_name']}\n"
            f"  위치: {r['district']} {r['address']}\n"
            f"  이용 연령: {r['age_text']} (age_min={age_min}세, age_max={age_max}세)\n"
            f"  이용료: 서울형 키즈카페 기본 3,000원 (홈페이지 확인)\n"
            f"  주차: {park_str}\n"
            f"  운영: {op_str}\n"
            f"  혼잡도: {crowded}\n"
            f"  특징(confidence≥0.7): {feat_str}\n"
            f"  방문 팁: {socks_tip}\n"
            f"  예약: {res_url}\n"
            f"  리뷰: {rev}"
        )

    dev_age = months_to_dev_age(months)
    drow    = dev_df[dev_df["age"] == dev_age]
    dev_str = ""
    if not drow.empty:
        row = drow.iloc[0]
        dev_str = (
            f"\n[Development_DB — {dev_age}개월]\n"
            f"  대근육: {str(row.get('gross_motor_skills',''))[:110]}\n"
            f"  소근육: {str(row.get('fine_motor_skills',''))[:110]}\n"
            f"  언어:   {str(row.get('language_development',''))[:110]}\n"
            f"  인지:   {str(row.get('cognitive_development',''))[:110]}\n"
            f"  사회성: {str(row.get('social_development',''))[:110]}"
        )
    return "\n\n".join(place_parts) + dev_str


def gen_answer(client, query: str, ctx: str, months: int, district: str) -> str:
    user_msg = (
        f"사용자 질문: {query}\n"
        f"아이 개월 수: {months}개월 | 관심 지역: {district or '서울 전체'}\n\n"
        f"[Context]\n{ctx}\n\n"
        "Context 데이터만 기반으로 5단계 형식에 맞춰 답변해 주세요."
    )
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ], max_tokens=640)


# ─────────────────────────────────────────────────
# 10. 발달 대시보드 렌더러
# ─────────────────────────────────────────────────
def render_dev(dev_df: pd.DataFrame, months: int):
    dev_age = months_to_dev_age(months)
    rdf = dev_df[dev_df["age"] == dev_age]
    if rdf.empty: return
    row = rdf.iloc[0]

    st.markdown(f"""
    <div class="dev-wrap">
      <div class="dev-hdr">
        <span style="font-size:1.7em">🌱</span>
        <div>
          <div class="dev-hdr-main">이 시기 아이의 발달 포인트</div>
          <div class="dev-hdr-sub">경기도육아종합지원센터 가이드북 기반</div>
        </div>
        <div class="dev-age-pill">{months}개월 기준</div>
      </div>
      <div class="dom-grid">
    """, unsafe_allow_html=True)

    for col_nm, icon, title, cls, prog in DOMAINS:
        raw  = str(row.get(col_nm,"데이터 준비 중..."))
        pts  = [b.strip() for b in raw.split(";") if b.strip()][:2]
        disp = " · ".join(pts) if pts else raw[:110]
        st.markdown(f"""
        <div class="dom-card {cls}">
          <span class="dom-icon">{icon}</span>
          <div class="dom-title">{title}</div>
          <div class="dom-text">{disp}</div>
          <div class="dom-bar">
            <div class="dom-fill" style="width:{prog}%"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# 11. 세션 상태 초기화
# ─────────────────────────────────────────────────
for _k, _v in [
    ("chat",       []),   # [(role, text), ...]
    ("ai_recs",    {}),
    ("last_pids",  []),
    ("quick_q",    ""),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────
# 12. 데이터 / 리소스 로드
# ─────────────────────────────────────────────────
with st.spinner("📂 데이터 불러오는 중..."):
    try:
        df     = load_places()
        dev_df = load_dev()
    except FileNotFoundError as e:
        st.error(f"⚠️ CSV 파일 없음: {e}")
        st.stop()

with st.spinner("🗄 벡터 DB 준비 중 (최초 1회만)..."):
    chroma = get_chroma(df)

llm = get_llm()

# ─────────────────────────────────────────────────
# 13. 사이드바
# ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:18px 0 14px">
      <img src="{MASCOT_SRC}"
           style="width:76px;height:76px;object-fit:contain;
                  border-radius:50%;border:3px solid #F2B705;
                  box-shadow:0 4px 14px rgba(242,183,5,.3)">
      <div style="font-family:'Jua',cursive;font-size:1.42em;
                  color:#1A3A6B;margin-top:8px">베베노리</div>
      <div style="font-size:.7em;color:#6B9DD4;font-weight:700;margin-top:3px">
        이모삼촌의 서울형 키즈카페 AI
      </div>
    </div>
    <hr style="border:none;border-top:1.5px dashed #D6E8FF;margin:10px 0">
    <div class="sb-title">🔎 구조화 검색</div>
    """, unsafe_allow_html=True)

    dist_sel   = st.selectbox("📍 지역구", DISTRICTS, index=0, key="dist_sel")
    months_sel = st.slider("👶 아이 개월 수",
        min_value=0, max_value=48, value=12, step=1, key="months_sel")

    st.markdown(
        f"<div style='text-align:center;font-family:Jua,cursive;"
        f"font-size:1.05em;color:#6B9DD4;margin:-4px 0 10px'>"
        f"<b>{months_sel}개월</b> ({months_to_dev_age(months_sel)}개월 구간)</div>",
        unsafe_allow_html=True)

    sort_sel = st.selectbox("📊 목록 정렬",
        ["리뷰 많은 순","이름 순","연령 낮은 순"], index=0, key="sort_sel")

    st.markdown("""
    <hr style="border:none;border-top:1.5px dashed #D6E8FF;margin:14px 0">
    <div class="sb-title">💬 샘플 질문</div>
    """, unsafe_allow_html=True)

    SAMPLES = [
        "비 오는 날 12개월 아이 실내 놀이",
        "주말에 18개월 아이랑 강남 키즈카페",
        "수유실 있는 영유아 전용 카페",
        "예약 없이 바로 갈 수 있는 곳",
        "3살 아이 에너지 발산 키즈카페",
    ]
    for s in SAMPLES:
        if st.button(s, key=f"sq_{s}", use_container_width=True):
            st.session_state.quick_q = s
            st.rerun()

    st.markdown(f"""
    <hr style="border:none;border-top:1.5px dashed #D6E8FF;margin:14px 0">
    <div style="font-size:.67em;color:#A8C4E8;line-height:2">
      🤖 Qwen/Qwen2.5-72B (HuggingFace API)<br>
      🗄 ChromaDB Persistent · MiniLM-L12<br>
      📊 {len(df)}개 장소 · {int(df['review_count'].sum()):,}건 리뷰<br>
      📗 발달 가이드북 RAG 연동<br>
      🔗 <a href="{PUBLIC_BOOK}" target="_blank"
            style="color:#F2B705 !important">{PUBLIC_BOOK}</a>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# 14. 헤더 (로고 + 슬로건)
# ─────────────────────────────────────────────────
total_rev = int(df["review_count"].sum())

st.markdown(f"""
<div class="bebe-header">
  <img class="header-logo" src="{LOGO_SRC}" alt="베베노리">
  <div class="header-slogan">
    이모삼촌이 직접 검증한 서울형 키즈카페 AI 큐레이션
  </div>
  <div class="header-pills">
    <span class="hpill">📍 서울 {df['district'].nunique()}개 자치구</span>
    <span class="hpill">🏠 {len(df)}개 키즈카페</span>
    <span class="hpill">💬 리뷰 {total_rev:,}건</span>
    <span class="hpill">🌱 발달 가이드북 연동</span>
    <span class="hpill">🗄 ChromaDB RAG</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# 15. 발달 대시보드 (사이드바 개월수 기준)
# ─────────────────────────────────────────────────
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
with st.expander(f"🌱 {months_sel}개월 아이 발달 현황 보기 (클릭해서 펼치기)",
                 expanded=False):
    render_dev(dev_df, months_sel)

# ─────────────────────────────────────────────────
# 16. 퀵 필터 버튼 (채팅창 상단)
# ─────────────────────────────────────────────────
st.markdown("""
<div style="font-family:'Jua',cursive;font-size:.95em;
            color:#1A3A6B;margin:18px 0 8px">
  ⚡ 빠른 검색
</div>
<div class="quick-wrap">
""", unsafe_allow_html=True)

# Streamlit 버튼으로 구현 (CSS class 적용)
qcols = st.columns(len(QUICK_FILTERS))
for i, (label, query) in enumerate(QUICK_FILTERS):
    with qcols[i]:
        # active 상태 표시를 위한 마커
        active = st.session_state.get("active_quick") == label
        btn_style = "background:#6B9DD4;color:white;" if active else ""
        if st.button(label, key=f"qf_{i}", use_container_width=True):
            st.session_state.quick_q = query
            st.session_state["active_quick"] = label
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# 17. 채팅 인터페이스
# ─────────────────────────────────────────────────
preset = st.session_state.pop("quick_q", "")

st.markdown("""
<div class="chat-wrap">
  <div class="chat-lbl">🌙 베베노리에게 물어보세요!</div>
  <div class="chat-hint">
    예: "주말에 16개월 아이랑 강서구 키즈카페 추천해줘" ·
    "비 오는 날 갈 수 있는 영유아 실내 놀이공간" ·
    "수유실 있는 토들러 전용 카페"
  </div>
</div>
""", unsafe_allow_html=True)

ci, cb = st.columns([5, 1])
with ci:
    query_in = st.text_input(
        "질문", value=preset,
        placeholder=f"예) {months_sel}개월 아이랑 {dist_sel if dist_sel!='전체' else '강남구'} 키즈카페 추천해줘",
        label_visibility="collapsed", key="query_in")
with cb:
    ask = st.button("🔍 검색", key="ask_btn", use_container_width=True)

# 대화 이력 렌더링 (최근 6턴)
for role, msg in st.session_state.chat[-12:]:
    if role == "user":
        st.markdown(f"<div class='bubble-user'>{msg}</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div class='bubble-ai'>"
            f"<div class='bubble-ai-lbl'>🌙 베베노리 이모삼촌</div>"
            f"{msg}</div>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# 18. 질문 처리 (STEP 1~5)
# ─────────────────────────────────────────────────
if ask and query_in.strip():
    q = query_in.strip()

    # 자치구 자동 감지 (사이드바 우선)
    auto_dist = dist_sel if dist_sel != "전체" else ""
    for d in DISTRICTS[1:]:
        if d in q or d.replace("구", "") in q:
            auto_dist = d; break

    with st.spinner("이모삼촌이 조카 사랑으로 장소 찾는 중... 🔍"):
        # STEP 3: 벡터 검색
        pids = rag_retrieve(chroma, q, auto_dist, n=4)
        if not pids:
            sub  = df[df["district"] == auto_dist] if auto_dist else df
            pids = sub.sort_values("review_count", ascending=False).head(4)["place_id"].tolist()

        # STEP 4: 컨텍스트 + LLM
        ctx = build_context(df, dev_df, pids, months_sel)
        ans = gen_answer(llm, q, ctx, months_sel, auto_dist)

    st.session_state.chat.append(("user", q))
    st.session_state.chat.append(("ai",   ans))
    st.session_state.last_pids = pids
    st.rerun()

# ─────────────────────────────────────────────────
# 19. 검색 결과 장소 카드 (채팅 아래, 컴팩트)
# ─────────────────────────────────────────────────
if st.session_state.last_pids:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'Jua',cursive;font-size:1.05em;
                color:#1A3A6B;margin-bottom:14px;
                display:flex;align-items:center;gap:8px">
      🏠 추천 장소 상세 정보
    </div>
    """, unsafe_allow_html=True)

    res_rows = df[df["place_id"].isin(st.session_state.last_pids)]
    cols2    = st.columns(2, gap="medium")

    for i, (_, row) in enumerate(res_rows.iterrows()):
        with cols2[i % 2]:
            pid     = str(row["place_id"])
            name    = str(row["place_name"])
            dist    = str(row["district"])
            addr    = str(row["address"])
            img_url = str(row["image_url"])
            r_cnt   = int(row["review_count"])
            r_text  = str(row["review_text"])
            feats   = row["features"] if isinstance(row["features"], list) else []
            age_txt = str(row.get("age_text",""))
            park    = _parking_short(str(row.get("parking_info","")))
            op_txt  = str(row.get("operating_hours_text",""))[:80] or "홈페이지 확인"
            res_url = str(row.get("reservation_url","")).strip() or PUBLIC_BOOK
            det_url = str(row.get("detail_url","")).strip()     or ""
            crowded = "⚠️ 주말 혼잡 주의" if row.get("is_crowded") else "✅ 예약 확인 권장"
            socks   = "🧦 양말 필수 지참" if row.get("needs_socks") else ""

            # 뱃지
            bdg = '<span style="background:#6B9DD4;color:#fff;padding:3px 9px;border-radius:14px;font-size:.67em;font-weight:800;margin-right:4px">★ 이모삼촌 추천</span>'
            if "toddler_friendly" in feats or "toddler_positive" in feats:
                bdg += '<span style="background:#43A047;color:#fff;padding:3px 9px;border-radius:14px;font-size:.67em;font-weight:800;margin-right:4px">👶 영유아</span>'

            # 특징 칩
            chip_html = "".join(
                f"<span style='background:#EBF4FF;color:#1A3A6B;border:1px solid #D6E8FF;"
                f"padding:2px 8px;border-radius:10px;font-size:.68em;font-weight:700;"
                f"margin:2px'>{FEAT_LABEL[fn][0]} {FEAT_LABEL[fn][1]}</span>"
                for fn in feats[:4] if fn in FEAT_LABEL
            )

            link = res_url if res_url.startswith("http") else PUBLIC_BOOK
            map_link = f"https://map.naver.com/p/search/{name}"

            with st.container():
                st.markdown(f"""
                <div style="background:rgba(255,255,255,.92);border-radius:22px;
                            overflow:hidden;border:1.5px solid #D6E8FF;
                            box-shadow:0 5px 18px rgba(107,157,212,.1);margin-bottom:4px">
                  <div style="position:relative;height:180px;overflow:hidden">
                    <img src="{img_url}" alt="{name}"
                         onerror="this.src='{FALLBACK_IMG}'"
                         style="width:100%;height:100%;object-fit:cover;transition:transform .4s">
                    <div style="position:absolute;top:10px;left:10px">{bdg}</div>
                    <div style="position:absolute;bottom:10px;right:10px;
                                background:rgba(255,255,255,.92);color:#6B9DD4;
                                border-radius:12px;padding:3px 9px;
                                font-size:.68em;font-weight:800">
                      💬 {r_cnt}건
                    </div>
                  </div>
                  <div style="padding:16px 18px 4px">
                    <div style="font-family:'Jua',cursive;font-size:1.05em;
                                color:#1A3A6B;margin-bottom:3px">{name}</div>
                    <div style="font-size:.75em;color:#BDBDBD;margin-bottom:8px">
                      📍 {dist} · {addr[:30]}{"…" if len(addr)>30 else ""}
                    </div>
                    <div style="margin-bottom:8px">{chip_html}</div>
                    <table class="info-table" style="font-size:.77em">
                      <tr><th>항목</th><th>내용</th></tr>
                      <tr><td>💰 이용료</td><td>기본 3,000원 (홈페이지 확인)</td></tr>
                      <tr><td>👶 권장 연령</td><td>{age_txt}</td></tr>
                      <tr><td>🅿 주차</td><td>{park}</td></tr>
                      <tr><td>🕒 운영</td><td>{op_txt[:60]}</td></tr>
                      <tr><td>⚠️ 혼잡도</td><td>{crowded}</td></tr>
                    </table>
                    {"<div style='font-size:.75em;color:#C17F00;margin:6px 0 2px;font-weight:800'>🧦 " + socks + "</div>" if socks else ""}
                    <div style="display:flex;gap:8px;margin:10px 0 14px">
                      <a href="{link}" target="_blank" class="res-link">📋 예약 바로가기</a>
                      <a href="{map_link}" target="_blank" class="map-link">🗺 지도</a>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # 이모삼촌 추천 이유 버튼
                rec_key = f"rec_{pid}"
                if rec_key in st.session_state.ai_recs:
                    txt = st.session_state.ai_recs[rec_key]
                    st.markdown(f"""
                    <div class="tip-box" style="margin-bottom:16px">
                      <div class="tip-lbl">💡 이모삼촌의 추천 이유</div>
                      <div class="tip-txt">{txt}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    if st.button("💡 이모삼촌 추천 이유 보기",
                                 key=f"rbtn_{pid}", use_container_width=True):
                        with st.spinner(f"'{name}' 분석 중..."):
                            feat_str = ", ".join(feats[:5]) or "다양한 시설"
                            prompt = (
                                f"장소: {name} ({dist}) | 개월수: {months_sel}개월\n"
                                f"특징: {feat_str}\n리뷰: {r_text[:280]}\n\n"
                                "이 키즈카페를 2~3문장으로 따뜻하게 추천하고, "
                                "마지막에 '💡 이모삼촌의 한마디:' 로 실용적인 방문 팁 1가지를 추가해 주세요."
                            )
                            st.session_state.ai_recs[rec_key] = llm_chat(llm, [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user",   "content": prompt},
                            ], max_tokens=200)
                        st.rerun()

# ─────────────────────────────────────────────────
# 20. 전체 장소 목록 (필터 기반, 접기/펼치기)
# ─────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
with st.expander(
    f"📋 {dist_sel if dist_sel != '전체' else '서울 전체'} · {months_sel}개월 기준 "
    f"— 전체 목록 보기",
    expanded=False
):
    filtered = df.copy()
    if dist_sel != "전체":
        filtered = filtered[filtered["district"] == dist_sel]
    lo, hi = months_to_yr(months_sel)
    filtered = filtered[(filtered["age_min"] <= hi) & (filtered["age_max"] >= lo)]
    if sort_sel == "리뷰 많은 순":
        filtered = filtered.sort_values("review_count", ascending=False)
    elif sort_sel == "이름 순":
        filtered = filtered.sort_values("place_name")
    else:
        filtered = filtered.sort_values("age_min")
    filtered = filtered.reset_index(drop=True)

    st.markdown(
        f"<div style='font-family:Jua,cursive;font-size:.95em;color:#1A3A6B;"
        f"margin-bottom:12px'>총 <b style='color:#F2B705'>{len(filtered)}개</b> 장소</div>",
        unsafe_allow_html=True)

    if filtered.empty:
        st.markdown("""
        <div class="empty-box">
          <span style="font-size:3em;display:block;margin-bottom:12px">🌙</span>
          <div style="font-weight:800;color:#6B9DD4;font-size:1em">조건에 맞는 장소가 없어요!</div>
          <div style="font-size:.84em;color:#BDBDBD;margin-top:6px">조건을 바꿔보거나
            <a href="{PUBLIC_BOOK}" target="_blank"
               style="color:#F2B705;font-weight:800">서울시 공공서비스 예약</a>에서 직접 검색해 보세요.</div>
        </div>""", unsafe_allow_html=True)
    else:
        PER = 6
        if "list_page" not in st.session_state:
            st.session_state.list_page = 0
        total_p = max(1, (len(filtered)-1)//PER + 1)
        if st.session_state.list_page >= total_p:
            st.session_state.list_page = 0
        ps = st.session_state.list_page * PER
        page_df = filtered.iloc[ps:ps+PER]

        gcols = st.columns(2, gap="medium")
        for i, (_, row) in enumerate(page_df.iterrows()):
            with gcols[i % 2]:
                pid_l   = str(row["place_id"])
                name_l  = str(row["place_name"])
                dist_l  = str(row["district"])
                img_l   = str(row["image_url"])
                rc_l    = int(row["review_count"])
                feats_l = row["features"] if isinstance(row["features"],list) else []
                res_l   = str(row.get("reservation_url","")).strip() or PUBLIC_BOOK
                if not res_l.startswith("http"): res_l = PUBLIC_BOOK
                map_l   = f"https://map.naver.com/p/search/{name_l}"
                chip_l  = "".join(
                    f"<span style='background:#EBF4FF;color:#1A3A6B;"
                    f"padding:2px 7px;border-radius:9px;font-size:.67em;"
                    f"font-weight:700;margin:2px'>{FEAT_LABEL[fn][0]} {FEAT_LABEL[fn][1]}</span>"
                    for fn in feats_l[:3] if fn in FEAT_LABEL
                )
                st.markdown(f"""
                <div style="background:rgba(255,255,255,.9);border-radius:20px;
                            overflow:hidden;border:1.5px solid #D6E8FF;
                            box-shadow:0 4px 14px rgba(107,157,212,.09);
                            margin-bottom:14px">
                  <div style="position:relative;height:150px;overflow:hidden">
                    <img src="{img_l}" alt="{name_l}"
                         onerror="this.src='{FALLBACK_IMG}'"
                         style="width:100%;height:100%;object-fit:cover">
                    <div style="position:absolute;bottom:8px;right:8px;
                                background:rgba(255,255,255,.9);color:#6B9DD4;
                                border-radius:10px;padding:2px 8px;
                                font-size:.67em;font-weight:800">💬 {rc_l}건</div>
                  </div>
                  <div style="padding:13px 15px 14px">
                    <div style="font-family:'Jua',cursive;font-size:1em;
                                color:#1A3A6B;margin-bottom:3px">{name_l}</div>
                    <div style="font-size:.73em;color:#BDBDBD;margin-bottom:7px">
                      📍 {dist_l}</div>
                    <div style="margin-bottom:9px">{chip_l}</div>
                    <div style="display:flex;gap:7px">
                      <a href="{res_l}" target="_blank" class="res-link"
                         style="font-size:.76em;padding:7px 14px">📋 예약</a>
                      <a href="{map_l}" target="_blank" class="map-link"
                         style="font-size:.76em;padding:7px 14px">🗺 지도</a>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

        if total_p > 1:
            pc = st.columns([1,2,1])
            with pc[0]:
                if st.session_state.list_page > 0:
                    if st.button("◀ 이전", key="lp_prev"):
                        st.session_state.list_page -= 1; st.rerun()
            with pc[1]:
                st.markdown(
                    f"<div style='text-align:center;font-family:Jua,cursive;"
                    f"color:#6B9DD4;padding:9px;font-weight:800'>"
                    f"{st.session_state.list_page+1} / {total_p}</div>",
                    unsafe_allow_html=True)
            with pc[2]:
                if st.session_state.list_page < total_p - 1:
                    if st.button("다음 ▶", key="lp_nxt"):
                        st.session_state.list_page += 1; st.rerun()

# ─────────────────────────────────────────────────
# 21. 푸터
# ─────────────────────────────────────────────────
st.markdown(f"""
<hr>
<div class="bebe-footer">
  <strong>🌙 베베노리 (BebeNori) v4.0</strong><br>
  이모삼촌이 만든 서울형 키즈카페 AI 큐레이션 · 팀 2모3촌<br>
  📊 places.csv ({len(df)}개) · review_docs.csv ({total_rev:,}건) ·
     place_features.csv · baby_development_final.csv<br>
  📗 경기도육아종합지원센터 영유아 발달지원 가이드북 2023-13호<br>
  🗄 ChromaDB PersistentClient · paraphrase-multilingual-MiniLM-L12-v2<br>
  🤖 LLM: Qwen/Qwen2.5-72B-Instruct (HuggingFace · openai 라이브러리)<br>
  🔗 데이터 없는 장소: <a href="{PUBLIC_BOOK}">{PUBLIC_BOOK}</a><br>
  <span style="color:#F2B705">♥ 광고 없이 진심만 담았어요</span>
</div>
""", unsafe_allow_html=True)
