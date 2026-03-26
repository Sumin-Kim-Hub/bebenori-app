# ╔══════════════════════════════════════════════════════════════════════╗
# ║    베베노리 (BebeNori) v5.0 — 서울형 키즈카페 AI 큐레이터 최종판       ║
# ║    팀: 2모3촌  |  Streamlit Cloud / Colab 공용                      ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# ── Streamlit Cloud 배포 ──────────────────────────────────────────────
#   Settings → Secrets 탭에 추가:
#   [secrets]
#   OPENAI_API_KEY = "sk-..."
#
# ── Colab 실행 ────────────────────────────────────────────────────────
#   !pip install streamlit chromadb sentence-transformers openai pandas -q
#   import os; os.environ["OPENAI_API_KEY"] = "sk-..."  ← 직접 지정 시
#   !streamlit run app.py --server.port 8501 &>/content/st.log &
#   # cloudflared 외부 접속
#   !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
#   !dpkg -i cloudflared-linux-amd64.deb
#   !cloudflared tunnel --url http://localhost:8501 &

import os, base64
from pathlib import Path
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# 0. 페이지 설정
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="베베노리 | 서울형 키즈카페",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# 1. 파일 경로
# ─────────────────────────────────────────────────────────────
PLACES_CSV   = "places.csv"
FEATURES_CSV = "place_features.csv"
REVIEWS_CSV  = "review_docs.csv"
DEV_CSV      = "baby_development_final.csv"
LOGO_FILE    = "logo.jpg.png"          # ← 업로드된 로고
GRID_FILE    = "pattern.png.png"
CHROMA_DIR   = "./bebenori_db"
FALLBACK_IMG = "https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&w=800&q=80"
PUBLIC_BOOK  = "https://yeyak.seoul.go.kr"

# ─────────────────────────────────────────────────────────────
# 2. 이미지 → base64
# ─────────────────────────────────────────────────────────────
def _b64(path: str, fallback: str = "") -> str:
    p = Path(path)
    if p.exists():
        ext = "jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "png"
        with open(p, "rb") as f:
            return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
    return fallback

LOGO_SRC = _b64(LOGO_FILE, FALLBACK_IMG)
GRID_SRC = _b64(GRID_FILE)
GRID_CSS = f"url('{GRID_SRC}')" if GRID_SRC else "none"

# ─────────────────────────────────────────────────────────────
# 3. 전역 CSS
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Nanum+Square+Round:wght@400;700;800&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
    font-family: 'Nanum Square Round', 'Apple SD Gothic Neo', sans-serif;
}}

/* 배경 그리드 */
.stApp {{
    background-color: #FEFCF3 !important;
    background-image: {GRID_CSS} !important;
    background-repeat: repeat !important;
    background-size: 420px !important;
    background-attachment: fixed !important;
}}
[data-testid="stAppViewContainer"] {{ background: transparent !important; }}
[data-testid="stHeader"]           {{ background: transparent !important; }}
.block-container {{ padding-top: 0 !important; max-width: 1100px; }}

/* 사이드바 */
[data-testid="stSidebar"] {{
    background: linear-gradient(175deg, #FFF9E6 0%, #EBF4FF 100%) !important;
    border-right: 2px solid #FFE082 !important;
}}
[data-testid="stSidebar"] * {{ color: #3A2800 !important; }}
[data-testid="stSidebar"] .stButton > button {{
    background: #F2B705 !important; color: #3A2800 !important;
    font-weight: 800 !important; border: none !important;
    border-radius: 12px !important; font-size: .82em !important;
    box-shadow: 0 2px 8px rgba(242,183,5,.22) !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: #D4A005 !important;
}}
.sb-sep {{ border: none; border-top: 1.5px dashed #FFE082; margin: 12px 0; }}
.sb-ttl {{
    font-family: 'Jua', cursive; font-size: .88em; color: #5D4000;
    padding: 6px 10px; background: rgba(242,183,5,.1);
    border-radius: 9px; border-left: 4px solid #F2B705; margin: 10px 0 7px;
}}

/* 헤더: 로고 이미지만 */
.bebe-header {{
    width: calc(100% + 2rem); margin-left: -1rem;
    overflow: hidden; border-radius: 0 0 32px 32px;
    box-shadow: 0 8px 28px rgba(0,0,0,.13);
    background: #fff; display: block; position: relative;
    max-height: 280px;
}}
.bebe-header img {{
    width: 100%; height: 280px;
    object-fit: cover; object-position: center top;
    display: block;
}}

/* 통계 바 */
.stat-bar {{ display:flex; gap:10px; margin:16px 0 0; flex-wrap:wrap; }}
.stat-chip {{
    background: rgba(255,255,255,.9); border: 1.5px solid #FFE082;
    border-radius: 16px; padding: 10px 14px; text-align: center;
    flex: 1; min-width: 85px; box-shadow: 0 3px 9px rgba(242,183,5,.1);
    transition: transform .2s;
}}
.stat-chip:hover {{ transform: translateY(-2px); }}
.stat-num {{ display:block; font-size:1.45em; font-weight:800; color:#F2B705; }}
.stat-lbl {{ font-size:.67em; color:#BCAAA4; font-weight:700; margin-top:2px; }}

/* 채팅 래퍼 */
.chat-outer {{
    background: rgba(255,255,255,.92); border-radius: 22px;
    padding: 18px 22px 14px; border: 1.5px solid #FFE082;
    box-shadow: 0 5px 18px rgba(242,183,5,.09);
}}
.chat-lbl {{
    font-family: 'Jua', cursive; font-size: .98em; color: #5D4000;
    margin-bottom: 3px; display: flex; align-items: center; gap: 7px;
}}
.chat-hint {{ font-size: .74em; color: #BCAAA4; line-height: 1.6; margin-bottom: 12px; }}

/* 대화 버블 */
.bubble-user {{
    background: #F2B705; color: #3A2800;
    border-radius: 18px 3px 18px 18px;
    padding: 11px 16px; margin: 9px 0 3px;
    font-size: .87em; font-weight: 700;
    max-width: 72%; margin-left: auto;
    box-shadow: 0 3px 11px rgba(242,183,5,.28); line-height: 1.65;
}}
.bubble-ai {{
    background: #ffffff; border: 1.5px solid #6B9DD4;
    border-radius: 3px 18px 18px 18px;
    padding: 15px 19px; margin: 3px 0 14px;
    font-size: .87em; color: #1A3A6B; line-height: 1.82;
    box-shadow: 0 4px 14px rgba(107,157,212,.11); max-width: 92%;
}}
.bubble-ai-lbl {{
    font-family: 'Jua', cursive; font-size: .76em; color: #6B9DD4;
    margin-bottom: 7px; display: flex; align-items: center; gap: 5px;
}}

/* 업체 카드 */
.place-card {{
    background: #fff; border-radius: 20px; overflow: hidden;
    border: 1.5px solid #FFE082;
    box-shadow: 0 5px 18px rgba(242,183,5,.1);
    transition: transform .2s, box-shadow .2s; margin-bottom: 6px;
}}
.place-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 13px 32px rgba(242,183,5,.2);
}}
.card-img-wrap {{ position:relative; height:196px; overflow:hidden; }}
.card-img {{ width:100%; height:100%; object-fit:cover; transition:transform .4s; }}
.place-card:hover .card-img {{ transform:scale(1.05); }}
.card-badges {{ position:absolute; top:10px; left:10px; display:flex; gap:5px; flex-wrap:wrap; }}
.cbdg {{ padding:3px 9px; border-radius:14px; font-size:.66em; font-weight:800; backdrop-filter:blur(5px); }}
.cbdg-star  {{ background:rgba(242,183,5,.92);  color:#3A2800; }}
.cbdg-green {{ background:rgba(56,142,60,.88);  color:#fff; }}
.cbdg-blue  {{ background:rgba(107,157,212,.9); color:#fff; }}
.rev-cnt {{
    position:absolute; bottom:9px; right:9px;
    background:rgba(255,255,255,.92); color:#6B9DD4;
    border-radius:11px; padding:3px 8px;
    font-size:.67em; font-weight:800;
}}
.card-body {{ padding:15px 17px 3px; }}
.card-name {{ font-family:'Jua',cursive; font-size:1.06em; color:#1A3A6B; margin-bottom:3px; line-height:1.3; }}
.card-addr {{ font-size:.73em; color:#BDBDBD; margin-bottom:8px; }}
.chip-row {{ display:flex; flex-wrap:wrap; gap:5px; margin-bottom:7px; }}
.chip {{ padding:3px 9px; border-radius:10px; font-size:.68em; font-weight:700; }}
.chip-y {{ background:#FFF8CC; color:#7A5700; border:1px solid #F2B705; }}
.chip-b {{ background:#EBF4FF; color:#1A3A6B; border:1px solid #90CAF9; }}
.chip-g {{ background:#E8F5E9; color:#1B5E20; border:1px solid #A5D6A7; }}

/* AI 추천 이유 박스 */
.rec-box {{
    background: linear-gradient(135deg,#FFFDE7,#FFF9D0);
    border-left: 4px solid #F2B705;
    border-radius: 0 14px 14px 0;
    padding: 12px 15px; margin: 9px 0 3px;
    box-shadow: 0 2px 9px rgba(242,183,5,.11);
}}
.rec-lbl {{ font-size:.71em; font-weight:800; color:#C17F00; margin-bottom:4px; display:flex; align-items:center; gap:4px; }}
.rec-txt {{ font-size:.81em; color:#5D4000; line-height:1.76; }}

/* 액션 버튼 */
.act-row {{ display:flex; gap:8px; margin:10px 0 15px; }}
.btn-main {{
    flex:1; text-align:center; background:#F2B705; color:#3A2800 !important;
    padding:10px 6px; border-radius:12px; font-weight:800; font-size:.78em;
    text-decoration:none; display:block;
    box-shadow:0 3px 10px rgba(242,183,5,.3); transition:background .2s;
}}
.btn-main:hover {{ background:#D4A005; text-decoration:none; }}
.btn-sub {{
    text-align:center; background:#EBF4FF; color:#1A3A6B !important;
    padding:10px 12px; border-radius:12px; font-weight:800; font-size:.78em;
    text-decoration:none; display:block;
    border:1.5px solid #90CAF9; transition:background .2s;
}}
.btn-sub:hover {{ background:#BBDEFB; text-decoration:none; }}

/* 결과 헤더 */
.result-header {{
    display:flex; align-items:center; gap:9px;
    background:rgba(255,255,255,.88); border-radius:13px;
    padding:11px 17px; margin-bottom:15px;
    border-left:5px solid #F2B705;
    border-top:1.5px solid #FFE082; border-right:1.5px solid #FFE082;
    border-bottom:1.5px solid #FFE082;
    font-family:'Jua',cursive; font-size:1em; color:#5D4000;
}}
.result-count {{ margin-left:auto; color:#F2B705; font-size:1.1em; }}

/* 빈 결과 */
.empty-box {{
    text-align:center; padding:44px 20px;
    background:rgba(255,255,255,.85); border-radius:20px;
    border:1.5px dashed #FFE082; margin:14px 0;
}}

/* Streamlit 오버라이드 */
.stButton > button {{
    background:#F2B705 !important; color:#3A2800 !important;
    font-weight:800 !important; border:none !important;
    border-radius:12px !important;
    font-family:'Nanum Square Round',sans-serif !important;
    box-shadow:0 3px 9px rgba(242,183,5,.22) !important;
}}
.stButton > button:hover {{ background:#D4A005 !important; }}
.stTextInput > div > div > input {{
    border-radius:13px !important; border:2px solid #F2B705 !important;
    background:rgba(255,255,255,.96) !important; color:#3A2800 !important;
    font-family:'Nanum Square Round',sans-serif !important;
    padding:11px 15px !important; font-size:.93em !important;
}}
.stSelectbox > div > div {{ border-radius:12px !important; }}
div[data-testid="stExpander"] {{
    border:1.5px solid #FFE082 !important; border-radius:15px !important;
    background:rgba(255,255,255,.88) !important;
}}
hr {{ border:none; border-top:2px dashed #FFE082 !important; margin:20px 0; }}

/* 푸터 */
.bebe-footer {{
    text-align:center; padding:24px 0 18px;
    color:#BCAAA4; font-size:.73em; line-height:2;
}}
.bebe-footer strong {{ color:#F2B705; }}
.bebe-footer a {{ color:#6B9DD4 !important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 4. 상수 / 매핑
# ─────────────────────────────────────────────────────────────
AGE_OPTIONS = [
    "전체", "0~6개월", "6~12개월", "12~18개월",
    "18~24개월", "24~30개월", "30~36개월", "36개월 이상",
]
AGE_TO_DEV = {
    "0~6개월":  "4~6",
    "6~12개월": "7~9",
    "12~18개월":"13~24",
    "18~24개월":"13~24",
    "24~30개월":"25~36",
    "30~36개월":"25~36",
    "36개월 이상":"25~36",
}
AGE_TO_YEAR = {
    "0~6개월":  (0, 0),
    "6~12개월": (0, 1),
    "12~18개월":(0, 1),
    "18~24개월":(0, 2),
    "24~30개월":(0, 2),
    "30~36개월":(2, 3),
    "36개월 이상":(3, 99),
}
FEAT_LABEL = {
    "parking_available":         ("🅿", "주차 가능"),
    "reservation_available":     ("📋", "예약 가능"),
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
SYSTEM_PROMPT = """Role
너는 서울시 공공 데이터를 기반으로 부모님들에게 아이와 방문하기 좋은 키즈카페를 추천하는 AI 이모삼촌 '베베노리(BebeNori)'야. 너의 정체성은 아이를 진심으로 아끼는 '2모3촌(이모 2명, 삼촌 3명)'으로, 전문적이면서도 아주 다정하고 친절한 말투를 사용해야 해.

Task
사용자의 입력(지역, 아이 연령, 특징 등)을 바탕으로 제공된 [Context] 내에서 가장 적합한 서울형 키즈카페를 추천해줘. 단순한 정보 나열이 아니라, 해당 시설이 아이의 발달 단계에 어떤 긍정적인 영향을 주는지 반드시 포함해야 해.

Constraints
1. 제공된 [Context]에 없는 장소는 절대 추천하지 마. 모르면 https://yeyak.seoul.go.kr 을 안내해.
2. 추천 장소가 사용자의 지역·연령 기준에 부합하는지 확인해.
3. "조카를 생각하는 마음으로 엄선했어요", "부모님 오늘 고생 많으셨죠?" 같은 다정한 문구를 섞어줘.
4. 답변 형식:
   📍 추천 장소 이름·위치
   💚 추천 이유 (발달 근거 포함)
   ℹ️ 이용료·권장연령·주차
   🔗 예약 링크
   💡 이모삼촌의 한마디 (실용적 방문 팁)
5. 마크다운 기호(##, **) 금지, 이모지+줄바꿈으로 구조화. 250자 내외."""

# ─────────────────────────────────────────────────────────────
# 5. 데이터 로딩
# ─────────────────────────────────────────────────────────────
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

    socks_set   = set(feats[feats["feature_name"] == "socks_rule_mentioned"]["place_id"])
    crowded_set = set(feats[feats["feature_name"] == "crowded_warning"]["place_id"])

    revs = pd.read_csv(REVIEWS_CSV)
    agg = (
        revs.groupby("place_id")
        .agg(
            review_count=("doc_id",  "count"),
            review_text =("content", lambda x: " ".join(
                x.dropna().astype(str).tolist()[:6])),
        )
        .reset_index()
    )
    df = places.merge(agg, on="place_id", how="left")
    df["review_count"] = df["review_count"].fillna(0).astype(int)
    df["review_text"]  = df["review_text"].fillna("")
    df["features"]     = df["place_id"].map(feat_map).apply(
        lambda x: x if isinstance(x, list) else [])
    df["needs_socks"]  = df["place_id"].isin(socks_set)
    df["is_crowded"]   = df["place_id"].isin(crowded_set)
    return df


@st.cache_data(show_spinner=False)
def load_dev() -> pd.DataFrame:
    return pd.read_csv(DEV_CSV)


# ─────────────────────────────────────────────────────────────
# 6. ChromaDB PersistentClient
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_chroma(df: pd.DataFrame):
    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        ef = SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2")
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        names = [c.name for c in client.list_collections()]
        if "bebenori_v5" in names:
            col = client.get_collection("bebenori_v5", embedding_function=ef)
            if col.count() == len(df):
                return col
            client.delete_collection("bebenori_v5")
        col = client.create_collection("bebenori_v5", embedding_function=ef)
        docs, ids, metas = [], [], []
        for _, r in df.iterrows():
            pid = str(r["place_id"])
            text = (f"{r['place_name']} {r['district']} {r['address']} "
                    f"{r['age_text']} "
                    f"{str(r.get('program_info_text',''))[:180]} "
                    f"{', '.join(r['features'][:6])} "
                    f"{str(r['review_text'])[:450]}")
            docs.append(text); ids.append(pid)
            metas.append({"place_id": pid, "place_name": str(r["place_name"]),
                          "district": str(r["district"])})
        for i in range(0, len(docs), 64):
            col.add(documents=docs[i:i+64], ids=ids[i:i+64],
                    metadatas=metas[i:i+64])
        return col
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 7. LLM — OpenAI 정식 API (gpt-4o-mini)
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_llm():
    try:
        from openai import OpenAI
        # Streamlit Secrets 또는 환경변수에서 API 키 읽기
        api_key = st.secrets.get("OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        # base_url 없음 → OpenAI 정식 서버로 자동 연결
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def llm_chat(client, messages: list, max_tokens: int = 400) -> str:
    if client is None or not client.api_key:
        return (
            "AI 클라이언트 초기화 실패.\n"
            "Streamlit Cloud: Settings → Secrets → OPENAI_API_KEY 확인\n"
            "Colab: os.environ['OPENAI_API_KEY'] = 'sk-...' 실행\n"
            f"직접 찾아보기: {PUBLIC_BOOK}"
        )
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.72,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"이모삼촌이 잠깐 쉬고 있어요... (오류: {str(e)[:80]})"


# ─────────────────────────────────────────────────────────────
# 8. RAG 파이프라인
# ─────────────────────────────────────────────────────────────
def rag_retrieve(col, query: str, district: str, n: int = 4) -> list:
    if col is None: return []
    w = {"district": {"$eq": district}} if district and district != "전체" else None
    try:
        res = col.query(query_texts=[query], n_results=n, where=w)
        return res["ids"][0] if res["ids"] else []
    except Exception:
        return []


def _park_short(raw: str) -> str:
    if not raw or str(raw).lower() in ("nan","none",""):
        return "정보 없음"
    s = str(raw).strip()
    first = s.split("- ")[1] if "- " in s else s
    first = first.split("\n")[0].strip()
    return first[:65] + ("…" if len(first) > 65 else "")


def build_context(df: pd.DataFrame, dev_df: pd.DataFrame,
                  pids: list, age_sel: str) -> str:
    rows = df[df["place_id"].isin(pids)]
    parts = []
    for _, r in rows.iterrows():
        feat_str = ", ".join(r["features"][:5]) or "정보 없음"
        park_str = _park_short(str(r.get("parking_info","")))
        res_url  = str(r.get("reservation_url","")).strip() or PUBLIC_BOOK
        tip      = "미끄럼방지 양말 필수" if r.get("needs_socks") else ""
        crowded  = "주말 혼잡 주의" if r.get("is_crowded") else "예약 확인 권장"
        parts.append(
            f"[{r['place_name']}]\n"
            f"  위치: {r['district']} {r['address']}\n"
            f"  연령: {r['age_text']} | 이용료: 기본 3,000원\n"
            f"  주차: {park_str} | 혼잡: {crowded}\n"
            f"  특징: {feat_str}\n"
            f"  방문팁: {tip}\n"
            f"  예약: {res_url}\n"
            f"  리뷰: {str(r['review_text'])[:280]}"
        )
    dev_age = AGE_TO_DEV.get(age_sel, "")
    dev_str = ""
    if dev_age:
        drow = dev_df[dev_df["age"] == dev_age]
        if not drow.empty:
            row = drow.iloc[0]
            dev_str = (
                f"\n[발달 정보 — {dev_age}개월]\n"
                f"  대근육: {str(row.get('gross_motor_skills',''))[:90]}\n"
                f"  소근육: {str(row.get('fine_motor_skills',''))[:90]}\n"
                f"  언어:   {str(row.get('language_development',''))[:90]}\n"
                f"  인지:   {str(row.get('cognitive_development',''))[:90]}\n"
                f"  사회성: {str(row.get('social_development',''))[:90]}"
            )
    return "\n\n".join(parts) + dev_str


def gen_answer(client, query: str, ctx: str, age_sel: str, dist: str) -> str:
    user_msg = (
        f"사용자 질문: {query}\n"
        f"아이 개월 수: {age_sel} | 관심 지역: {dist or '서울 전체'}\n\n"
        f"[Context]\n{ctx}\n\n"
        "Context 데이터만 기반으로 답변해 주세요."
    )
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ], max_tokens=480)


def gen_card_rec(client, name: str, addr: str,
                 feats: list, review: str, age_sel: str) -> str:
    feat_str = ", ".join(feats[:5]) or "다양한 놀이 시설"
    return llm_chat(client, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": (
            f"장소: {name} ({addr})\n"
            f"아이 연령: {age_sel}\n특징: {feat_str}\n"
            f"리뷰: {review[:300]}\n\n"
            "이 키즈카페를 2~3문장으로 따뜻하게 추천하고, "
            "마지막에 '💡 이모삼촌의 한마디:' 로 방문 팁 1가지를 추가해 주세요. "
            "마크다운 기호 금지."
        )},
    ], max_tokens=200)


# ─────────────────────────────────────────────────────────────
# 9. 발달 대시보드
# ─────────────────────────────────────────────────────────────
DOMAINS = [
    ("gross_motor_skills",   "🦵","대근육 발달","linear-gradient(135deg,#E3F2FD,#BBDEFB)","#90CAF9","#1565C0",82),
    ("fine_motor_skills",    "✋","소근육 발달","linear-gradient(135deg,#E8EAF6,#C5CAE9)","#9FA8DA","#283593",74),
    ("language_development", "🗣","언어 발달",  "linear-gradient(135deg,#FFF9C4,#FFF176)","#FDD835","#F57F17",70),
    ("cognitive_development","🧠","인지 발달",  "linear-gradient(135deg,#E8F5E9,#C8E6C9)","#A5D6A7","#2E7D32",78),
    ("social_development",   "👫","사회성 발달","linear-gradient(135deg,#FCE4EC,#F8BBD0)","#F48FB1","#880E4F",67),
    ("motor_development",    "🏃","전반 운동",  "linear-gradient(135deg,#FFF3E0,#FFE0B2)","#FFCC80","#E65100",85),
]

def render_dev_dashboard(dev_df: pd.DataFrame, age_sel: str):
    dev_age = AGE_TO_DEV.get(age_sel)
    if not dev_age: return
    rdf = dev_df[dev_df["age"] == dev_age]
    if rdf.empty: return
    row = rdf.iloc[0]
    st.markdown(f"""
    <div style="background:rgba(255,255,255,.9);border-radius:20px;
                padding:20px 22px;border:1.5px solid #FFE082;
                box-shadow:0 4px 14px rgba(242,183,5,.08);margin:12px 0">
      <div style="display:flex;align-items:center;gap:10px;
                  padding-bottom:13px;margin-bottom:15px;
                  border-bottom:2px dashed #FFE082">
        <span style="font-size:1.5em">🌱</span>
        <div>
          <div style="font-family:'Jua',cursive;font-size:1.05em;color:#5D4000">
            이 시기 아이의 발달 포인트</div>
          <div style="font-size:.7em;color:#BCAAA4;font-weight:700;margin-top:2px">
            경기도육아종합지원센터 가이드북 기반</div>
        </div>
        <div style="margin-left:auto;background:linear-gradient(135deg,#F2B705,#D4A005);
                    color:#fff;font-family:'Jua',cursive;font-size:.88em;
                    padding:5px 14px;border-radius:16px;white-space:nowrap">{age_sel}</div>
      </div>
      <div style="display:grid;gap:10px;
                  grid-template-columns:repeat(auto-fill,minmax(220px,1fr))">
    """, unsafe_allow_html=True)
    for col_nm, icon, title, bg, border, tc, prog in DOMAINS:
        raw  = str(row.get(col_nm, "데이터 준비 중..."))
        pts  = [b.strip() for b in raw.split(";") if b.strip()][:2]
        disp = " · ".join(pts) if pts else raw[:100]
        st.markdown(f"""
        <div style="background:{bg};border-radius:14px;padding:14px 14px 12px;
                    border:1.5px solid {border}">
          <span style="font-size:1.6em;display:block;margin-bottom:5px">{icon}</span>
          <div style="font-family:'Jua',cursive;font-size:.85em;
                      color:{tc};margin-bottom:5px">{title}</div>
          <div style="font-size:.71em;line-height:1.68;color:#424242">{disp}</div>
          <div style="height:4px;border-radius:3px;margin-top:9px;
                      background:rgba(255,255,255,.45);overflow:hidden">
            <div style="width:{prog}%;height:100%;border-radius:3px;
                        background:rgba(255,255,255,.68)"></div>
          </div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 10. 업체 카드 렌더러
# ─────────────────────────────────────────────────────────────
def render_place_card(row: pd.Series, client, age_sel: str, key_pfx: str = ""):
    pid     = str(row["place_id"])
    name    = str(row["place_name"])
    dist    = str(row["district"])
    addr    = str(row["address"])
    img_url = str(row["image_url"])
    r_cnt   = int(row["review_count"])
    r_text  = str(row["review_text"])
    feats   = row["features"] if isinstance(row["features"], list) else []
    age_txt = str(row.get("age_text", ""))
    parking = _park_short(str(row.get("parking_info", "")))
    res_url = str(row.get("reservation_url","")).strip() or ""
    det_url = str(row.get("detail_url","")).strip() or ""
    socks   = bool(row.get("needs_socks", False))
    crowded = bool(row.get("is_crowded", False))

    # 뱃지
    bdg = '<span class="cbdg cbdg-star">★ 이모삼촌 추천</span>'
    if "toddler_friendly" in feats or "toddler_positive" in feats:
        bdg += '<span class="cbdg cbdg-green">👶 영유아</span>'
    if any(k in pid for k in ("2025","2026")):
        bdg += '<span class="cbdg cbdg-blue">NEW</span>'

    chip_html = "".join(
        f"<span class='chip chip-b'>{FEAT_LABEL[fn][0]} {FEAT_LABEL[fn][1]}</span>"
        for fn in feats[:4] if fn in FEAT_LABEL
    )
    age_chip  = f"<span class='chip chip-y'>👶 {age_txt}</span>" if age_txt else ""
    park_chip = (f"<span class='chip chip-g'>🅿 {parking[:18]}</span>"
                 if parking != "정보 없음" else "")
    tip_chips = ""
    if socks:   tip_chips += "<span class='chip chip-y'>🧦 양말 필수</span>"
    if crowded: tip_chips += "<span class='chip chip-y'>⚠️ 주말 혼잡</span>"

    link = res_url if res_url.startswith("http") else (
        det_url if det_url.startswith("http") else PUBLIC_BOOK)
    map_link = f"https://map.naver.com/p/search/{name}"

    with st.container():
        st.markdown(f"""
        <div class="place-card">
          <div class="card-img-wrap">
            <img class="card-img" src="{img_url}" alt="{name}"
                 onerror="this.src='{FALLBACK_IMG}'">
            <div class="card-badges">{bdg}</div>
            <div class="rev-cnt">💬 {r_cnt}건</div>
          </div>
          <div class="card-body">
            <div class="card-name">{name}</div>
            <div class="card-addr">📍 {dist} · {addr[:34]}{"…" if len(addr)>34 else ""}</div>
            <div class="chip-row">{chip_html}</div>
            <div class="chip-row">{age_chip}{park_chip}{tip_chips}</div>
        """, unsafe_allow_html=True)

        rec_key = f"rec_{pid}"
        if rec_key in st.session_state.ai_recs:
            txt = st.session_state.ai_recs[rec_key]
            st.markdown(f"""
            <div class="rec-box">
              <div class="rec-lbl">💡 이모삼촌의 추천 이유</div>
              <div class="rec-txt">{txt}</div>
            </div>""", unsafe_allow_html=True)
        else:
            if st.button("💡 추천 이유 보기",
                         key=f"{key_pfx}r_{pid}", use_container_width=True):
                with st.spinner(f"'{name}' 분석 중..."):
                    st.session_state.ai_recs[rec_key] = gen_card_rec(
                        client, name, addr, feats, r_text, age_sel)
                st.rerun()

        st.markdown(f"""
            <div class="act-row">
              <a href="{link}" target="_blank" class="btn-main">📋 예약 바로가기</a>
              <a href="{map_link}" target="_blank" class="btn-sub">🗺 지도</a>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 11. 세션 상태
# ─────────────────────────────────────────────────────────────
for _k, _v in [
    ("ai_recs",   {}),
    ("chat_hist", []),
    ("ai_ans",    ""),
    ("last_pids", []),
    ("card_page", 0),
    ("preset_q",  ""),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────
# 12. 데이터 로드
# ─────────────────────────────────────────────────────────────
with st.spinner("📂 데이터 불러오는 중..."):
    try:
        df     = load_places()
        dev_df = load_dev()
    except FileNotFoundError as e:
        st.error(f"⚠️ 파일 없음: {e}")
        st.stop()

with st.spinner("🗄 벡터 DB 준비 중 (최초 1회만)..."):
    chroma = get_chroma(df)

llm = get_llm()

# ─────────────────────────────────────────────────────────────
# 13. 사이드바
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:14px 0 10px">
      <img src="{LOGO_SRC}"
           style="width:100%;max-height:80px;object-fit:contain;
                  border-radius:12px">
    </div>
    <hr class="sb-sep">
    <div class="sb-ttl">🔎 검색 조건</div>
    """, unsafe_allow_html=True)

    age_sel  = st.selectbox("👶 아이 개월 수", AGE_OPTIONS, index=0, key="age_sel")
    dist_sel = st.selectbox("📍 자치구",        DISTRICTS,   index=0, key="dist_sel")
    sort_sel = st.selectbox("📊 정렬",
        ["리뷰 많은 순","이름 순","연령 낮은 순"], index=0, key="sort_sel")

    st.markdown('<hr class="sb-sep"><div class="sb-ttl">💬 샘플 질문</div>',
                unsafe_allow_html=True)
    for s in [
        "주말에 18개월 아이랑 강남 키즈카페",
        "비 오는 날 12개월 아이 실내 놀이",
        "부모도 쉴 수 있는 영유아 카페",
        "예약 없이 바로 갈 수 있는 곳",
        "3살 에너지 발산 키즈카페",
    ]:
        if st.button(s, key=f"sq_{s}", use_container_width=True):
            st.session_state.preset_q = s
            st.rerun()

    st.markdown(f"""
    <hr class="sb-sep">
    <div style="font-size:.65em;color:#BCAAA4;line-height:2">
      🤖 GPT-4o-mini (OpenAI 정식 API)<br>
      🗄 ChromaDB Persistent · MiniLM-L12<br>
      📊 {len(df)}개 장소 · {int(df['review_count'].sum()):,}건 리뷰<br>
      🔗 <a href="{PUBLIC_BOOK}" target="_blank"
            style="color:#F2B705 !important">{PUBLIC_BOOK}</a>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 14. 헤더: 로고 이미지만 (텍스트 없음)
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="bebe-header">
  <img src="{LOGO_SRC}" alt="베베노리">
</div>
""", unsafe_allow_html=True)

# 통계 바
total_rev = int(df["review_count"].sum())
st.markdown(f"""
<div class="stat-bar">
  <div class="stat-chip"><span class="stat-num">{len(df)}</span>
    <div class="stat-lbl">서울형 키즈카페</div></div>
  <div class="stat-chip"><span class="stat-num">{total_rev:,}</span>
    <div class="stat-lbl">네이버 리뷰</div></div>
  <div class="stat-chip"><span class="stat-num">25</span>
    <div class="stat-lbl">서울 자치구</div></div>
  <div class="stat-chip"><span class="stat-num">100%</span>
    <div class="stat-lbl">광고 없음</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 15. 발달 대시보드 (개월 수 선택 시)
# ─────────────────────────────────────────────────────────────
if age_sel != "전체":
    with st.expander(f"🌱 {age_sel} 아이 발달 현황 보기", expanded=False):
        render_dev_dashboard(dev_df, age_sel)

# ─────────────────────────────────────────────────────────────
# 16. 채팅 인터페이스
# ─────────────────────────────────────────────────────────────
preset = ""
if st.session_state.preset_q:
    preset = st.session_state.preset_q
    st.session_state.preset_q = ""

age_hint = age_sel if age_sel != "전체" else "18개월"
dist_hint = dist_sel if dist_sel != "전체" else "강남"

st.markdown(f"""
<div class="chat-outer">
  <div class="chat-lbl">🌙 베베노리에게 물어보세요!</div>
  <div class="chat-hint">
    예: "주말에 {age_hint} 아이랑 {dist_hint}에서 갈 키즈카페 추천해줘"
    · "비 오는 날 영유아 실내 놀이공간" · "수유실 있는 영아 카페"
  </div>
</div>
""", unsafe_allow_html=True)

ci, cb = st.columns([5, 1])
with ci:
    query_in = st.text_input(
        "질문", value=preset,
        placeholder="예) 12개월 아이랑 주말에 갈 강서구 키즈카페 추천해줘",
        label_visibility="collapsed", key="query_in")
with cb:
    ask = st.button("🔍 검색", key="ask_btn", use_container_width=True)

# 대화 이력
if st.session_state.chat_hist:
    for role, msg in st.session_state.chat_hist[-6:]:
        if role == "user":
            st.markdown(f"<div class='bubble-user'>{msg}</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='bubble-ai'>"
                f"<div class='bubble-ai-lbl'>🌙 베베노리 이모삼촌</div>"
                f"{msg}</div>", unsafe_allow_html=True)

# 질문 처리
if ask and query_in.strip():
    q = query_in.strip()
    auto_dist = dist_sel if dist_sel != "전체" else ""
    for d in DISTRICTS[1:]:
        if d in q or d.replace("구","") in q:
            auto_dist = d; break

    with st.spinner("이모삼촌이 조카 사랑으로 장소 찾는 중... 🔍"):
        pids = rag_retrieve(chroma, q, auto_dist, n=4)
        if not pids:
            sub  = df[df["district"] == auto_dist] if auto_dist else df
            pids = sub.sort_values("review_count", ascending=False).head(4)["place_id"].tolist()
        ctx = build_context(df, dev_df, pids, age_sel)
        ans = gen_answer(llm, q, ctx, age_sel, auto_dist)

    st.session_state.chat_hist.append(("user", q))
    st.session_state.chat_hist.append(("ai",   ans))
    st.session_state.ai_ans    = ans
    st.session_state.last_pids = pids
    st.session_state.card_page = 0
    st.rerun()

if st.session_state.ai_ans:
    st.markdown(
        f"<div class='bubble-ai'>"
        f"<div class='bubble-ai-lbl'>🌙 베베노리 이모삼촌 (AI 답변)</div>"
        f"{st.session_state.ai_ans}</div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 18. 필터링 + 업체 카드 목록
# ─────────────────────────────────────────────────────────────
filtered = df.copy()
if dist_sel != "전체":
    filtered = filtered[filtered["district"] == dist_sel]
yr = AGE_TO_YEAR.get(age_sel)
if yr:
    lo, hi = yr
    filtered = filtered[(filtered["age_min"] <= hi) & (filtered["age_max"] >= lo)]
if sort_sel == "리뷰 많은 순":
    filtered = filtered.sort_values("review_count", ascending=False)
elif sort_sel == "이름 순":
    filtered = filtered.sort_values("place_name")
else:
    filtered = filtered.sort_values("age_min")

if st.session_state.last_pids:
    top_rows = filtered[filtered["place_id"].isin(st.session_state.last_pids)]
    rest     = filtered[~filtered["place_id"].isin(st.session_state.last_pids)]
    filtered = pd.concat([top_rows, rest]).reset_index(drop=True)
else:
    filtered = filtered.reset_index(drop=True)

rl = dist_sel if dist_sel != "전체" else "서울 전체"
al = age_sel  if age_sel  != "전체" else "전 연령"
st.markdown(
    f"<div class='result-header'>"
    f"✨ <b>{rl}</b> · <b>{al}</b> 맞춤 키즈카페"
    f"<span class='result-count'>🏠 {len(filtered)}개</span>"
    f"</div>", unsafe_allow_html=True)

PER_PAGE = 6
if filtered.empty:
    st.markdown(f"""
    <div class="empty-box">
      <span style="font-size:3em;display:block;margin-bottom:11px">🌙</span>
      <div style="font-weight:800;color:#F2B705;font-size:1em">
        해당 조건의 키즈카페가 없어요!</div>
      <div style="font-size:.82em;color:#BCAAA4;margin-top:6px;line-height:1.7">
        조건을 바꿔보거나
        <a href="{PUBLIC_BOOK}" target="_blank"
           style="color:#6B9DD4;font-weight:800">서울시 공공서비스 예약</a>
        에서 직접 찾아보세요.
      </div>
    </div>""", unsafe_allow_html=True)
else:
    total_pages = max(1, (len(filtered)-1)//PER_PAGE + 1)
    if st.session_state.card_page >= total_pages:
        st.session_state.card_page = 0
    p_start = st.session_state.card_page * PER_PAGE
    page_df = filtered.iloc[p_start: p_start + PER_PAGE]

    cols = st.columns(2, gap="medium")
    for i, (_, row) in enumerate(page_df.iterrows()):
        with cols[i % 2]:
            render_place_card(row, llm, age_sel,
                              key_pfx=f"pg{st.session_state.card_page}_")
            with st.expander(
                f"🌱 {row['place_name']} — 발달 연계 효과"):
                if age_sel != "전체":
                    render_dev_dashboard(dev_df, age_sel)
                else:
                    st.markdown("""
                    <div style="padding:11px;background:#FFF9C4;border-radius:11px;
                                font-size:.8em;color:#7A5700;text-align:center">
                      사이드바에서 아이 <b>개월 수</b>를 선택하면<br>발달 정보를 볼 수 있어요!
                    </div>""", unsafe_allow_html=True)

    if total_pages > 1:
        pc = st.columns([1, 2, 1])
        with pc[0]:
            if st.session_state.card_page > 0:
                if st.button("◀ 이전", use_container_width=True, key="prev_pg"):
                    st.session_state.card_page -= 1; st.rerun()
        with pc[1]:
            st.markdown(
                f"<div style='text-align:center;font-family:Jua,cursive;"
                f"color:#F2B705;padding:9px;font-weight:800'>"
                f"{st.session_state.card_page+1} / {total_pages}</div>",
                unsafe_allow_html=True)
        with pc[2]:
            if st.session_state.card_page < total_pages - 1:
                if st.button("다음 ▶", use_container_width=True, key="next_pg"):
                    st.session_state.card_page += 1; st.rerun()

# ─────────────────────────────────────────────────────────────
# 19. 일괄 AI 추천
# ─────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
cl, cr = st.columns([3, 1])
with cl:
    st.markdown("**💡 이모삼촌 추천 이유**를 아직 못 본 카드들에 한 번에 생성해드려요!")
with cr:
    if st.button("✨ 전체 AI 추천", key="gen_all", use_container_width=True):
        pending = [
            row for _, row in filtered.iloc[:PER_PAGE].iterrows()
            if f"rec_{row['place_id']}" not in st.session_state.ai_recs
        ]
        if not pending:
            st.success("이미 모든 추천 이유가 있어요! 🎉")
        else:
            bar = st.progress(0); msg = st.empty()
            for i, row in enumerate(pending):
                pid = str(row["place_id"])
                msg.markdown(f"🌙 **{row['place_name']}** 분석 중... ({i+1}/{len(pending)})")
                try:
                    st.session_state.ai_recs[f"rec_{pid}"] = gen_card_rec(
                        llm, str(row["place_name"]), str(row["address"]),
                        row["features"] if isinstance(row["features"],list) else [],
                        str(row["review_text"]), age_sel)
                except Exception:
                    st.session_state.ai_recs[f"rec_{pid}"] = (
                        "이모삼촌이 잠시 쉬고 있어요. 다시 시도해 주세요! 🌸")
                bar.progress((i+1)/len(pending))
            msg.empty()
            st.success("✅ 완료! 카드에서 추천 이유를 확인하세요 🎉")
            st.rerun()

# ─────────────────────────────────────────────────────────────
# 20. 푸터
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<hr>
<div class="bebe-footer">
  <strong>🌙 베베노리 (BebeNori) v5.0</strong><br>
  이모삼촌이 만든 서울형 키즈카페 AI 큐레이션 · 팀 2모3촌<br>
  📊 places.csv ({len(df)}개) · review_docs.csv ({total_rev:,}건) ·
     place_features.csv · baby_development_final.csv<br>
  📗 경기도육아종합지원센터 영유아 발달지원 가이드북 2023-13호<br>
  🗄 ChromaDB PersistentClient · paraphrase-multilingual-MiniLM-L12-v2<br>
  🤖 GPT-4o-mini (OpenAI 정식 API 연동)<br>
  🔗 <a href="{PUBLIC_BOOK}">{PUBLIC_BOOK}</a><br>
  <span style="color:#F2B705">♥ 광고 없이 진심만 담았어요</span>
</div>
""", unsafe_allow_html=True)
