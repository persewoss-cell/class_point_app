import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta, date

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# (학급 확장용) PDF 텍스트 파싱(간단)
import re

# =========================
# 설정
# =========================
APP_TITLE = "학급 경제 시스템 (포인트 통장 기반)"
st.set_page_config(page_title=APP_TITLE, layout="wide")

KST = timezone(timedelta(hours=9))

# ✅ 기존 관리자 유지(교사)
ADMIN_PIN = "9999"
ADMIN_NAME = "관리자"

# =========================
# 모바일 UI CSS + 템플릿 정렬(촘촘) CSS
# (너가 준 CSS 그대로)
# =========================
st.markdown(
    """
    <style>
    section.main > div:first-child { padding-top: 2.6rem; }
    @media (max-width: 768px) {
        section.main > div:first-child { padding-top: 3.2rem; }
    }
    .block-container { padding-bottom: 2.0rem; }
    @media (max-width: 768px) {
        .block-container { padding-bottom: 6.0rem; }
    }

    /* radio → 버튼처럼 */
/* ✅ 라디오 버튼 내부 요소(원형 버튼 + 문자) 수평/수직 중앙 정렬 및 높이 축소 */
    div[role="radiogroup"] > label {
        background: #f3f4f6;
        padding: 0px 3px !important;    /* 위아래 여백 제거 */
        border-radius: 4px !important;  /* 라운드 사각형 크기 축소 */
        margin-right: 4px;
        margin-bottom: 4px;
        border: 1px solid #ddd;
        font-size: 0.85rem !important;
        
        /* 💡 높이 고정 및 세로 중앙 정렬 핵심 설정 */
        min-height: 1.3rem !important; 
        display: flex !important;
        align-items: center !important;  /* 위아래 중앙 정렬 */
        justify-content: center !important;
        overflow: hidden !important;
    }

/* ✅ 태블릿에서 원형 버튼이 타원으로 찌그러지는 현상 방지 */
    div[role="radiogroup"] > label div[data-testid="stWidgetLabel"] svg {
        width: 14px !important;   /* 원형 버튼 너비 고정 */
        height: 14px !important;  /* 원형 버튼 높이 고정 */
        min-width: 14px !important;
        min-height: 14px !important;
    }

    /* 원형 버튼을 감싸는 컨테이너 여백 조정 */
    div[role="radiogroup"] > label [data-testid="stNumericInput-StepDown"] {
        display: flex !important;
        align-items: center !important;
    }
    
    /* 라벨 내부 마진 초기화로 쏠림 방지 */
    div[role="radiogroup"] label > div:first-child {
        display: flex !important;
        align-items: center !important;
        margin-top: 0 !important;
    }

    /* 💡 원형 버튼 자체에 붙은 기본 위쪽 여백(Margin) 제거 */
    div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
        line-height: 1 !important;
    }

    div[role="radiogroup"] [data-testid="stWidgetLabel"] {
        margin-bottom: 0 !important;
    }
/* --- 기존 63라인 부근의 스타일을 아래 내용으로 교체 또는 추가 --- */

    /* 1. 선택 시 나타나는 중앙의 빨간색 점(svg) 아예 안 보이게 제거 */
    div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) label:has(input:checked) svg {
        display: none !important;
    }

    /* 2. 통계청 전용: O, X, △ 값에 따라 배경색을 선명하게 꽉 채우기 */
    
    /* [O] 선택 시: 선명한 초록색 */
    div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) label:has(input[value="O"]:checked) {
        background-color: #10b981 !important;
        border-color: #059669 !important;
        color: white !important;
    }

    /* [X] 선택 시: 선명한 빨간색 */
    div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) label:has(input[value="X"]:checked) {
        background-color: #ef4444 !important;
        border-color: #dc2626 !important;
        color: white !important;
    }

    /* [△] 선택 시: 선명한 파란색 */
    div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) label:has(input[value="△"]:checked) {
        background-color: #3b82f6 !important;
        border-color: #2563eb !important;
        color: white !important;
    }

    /* 3. 클릭 시 주변에 생기는 빨간색 잔상(포커스 링) 제거 */
    div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) *:focus {
        box-shadow: none !important;
        outline: none !important;
    }
    
/* ✅ DataFrame/DataEditor: 바깥 네모 박스(테두리/여백)만 줄이기 */
[data-testid="stDataFrame"]{
    overflow-x: auto;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* 바깥 wrapper(회색 박스/패딩) 제거 */
[data-testid="stDataFrame"] > div{
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* 그리드 wrapper 여백 최소화(셀 자체는 건드리지 않음) */
[data-testid="stDataFrame"] div[role="grid"],
[data-testid="stDataFrame"] div[role="grid"] > div{
    margin: 0 !important;
    padding: 0 !important;
}

    /* 앱 제목 */
    .app-title {
        font-weight: 900;
        line-height: 1.18;
        margin: 0.6rem 0 1.0rem 0;
        text-align: left;
        font-size: clamp(1.6rem, 5.2vw, 2.8rem);
        white-space: normal;
        word-break: keep-all;
    }
    @media (max-768px) {
        .app-title { font-size: clamp(2.05rem, 7.9vw, 3.3rem); }
    }

    /* ✅ 전체적으로 줄간격 조금 촘촘하게 */
    p, .stMarkdown { margin-bottom: 0.35rem !important; }
    .stCaptionContainer { margin-top: 0.15rem !important; }

    /* ✅ 템플릿 정렬 표(엑셀 느낌) */
    .tpl-head { font-weight: 800; padding: 6px 6px; border-bottom: 2px solid #ddd; margin-bottom: 4px; }
    .tpl-cell { padding: 4px 6px; border-bottom: 1px solid #eee; line-height: 1.15; font-size: 0.95rem; }
    .tpl-label { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    @media (max-768px){
        .tpl-cell { padding: 6px 6px; font-size: 1.02rem; line-height: 1.18; }
        .tpl-label{
            white-space: normal;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow:hidden;
        }
        .tpl-sub { font-size: 0.92rem; line-height: 1.12; }
    }
    .tpl-sub { color:#666; font-size: 0.85rem; margin-top: 2px; line-height: 1.05; }

/* ✅ stat_cellpick_ 전용: 선택 색상(순서 기반) */

/* (중요) 기본 선택 배경 리셋은 "stat_cellpick_"에만 적용 */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:has(input:checked) {
    background: #f3f4f6 !important;
    border-color: #ddd !important;
}

/* 옵션 순서가 [빈칸, O, X, △] 라고 가정:
   1번째=빈칸, 2번째=O, 3번째=X, 4번째=△ */

/* 2번째(O) */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:nth-of-type(2):has(input:checked) {
    background-color: #10b981 !important;
    border-color: #059669 !important;
}
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:nth-of-type(2):has(input:checked) p {
    color: #fff !important;
}

/* 3번째(X) */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:nth-of-type(3):has(input:checked) {
    background-color: #ef4444 !important;
    border-color: #dc2626 !important;
}
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:nth-of-type(3):has(input:checked) p {
    color: #fff !important;
}

/* 4번째(△) */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:nth-of-type(4):has(input:checked) {
    background-color: #3b82f6 !important;
    border-color: #2563eb !important;
}
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  div[role="radiogroup"] > label:nth-of-type(4):has(input:checked) p {
    color: #fff !important;
}

/* ✅ 선택 시 가운데 빨간 점(svg) 숨기기(원하면 유지) */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"])
  label:has(input:checked) svg {
    display: none !important;
}

/* ✅ 포커스 링 제거 */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) *:focus {
    box-shadow: none !important;
    outline: none !important;
}

    /* ✅ 버튼(특히 화살표) 작게 + 가운데 */
    div[data-testid="stButton"] > button {
        padding: 0.05rem 0.28rem !important;
        min-height: 1.45rem !important;
        line-height: 1 !important;
        font-size: 0.95rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    button[kind="primary"] {
        padding: 0.35rem 0.6rem !important;
        min-height: 2.0rem !important;
    }

/* ✅ 왼쪽 텍스트와 라디오 수직 중앙 정렬 */
.stat-tight div[data-testid="element-container"] {
    display: flex !important;
    align-items: center !important;
}

/* 텍스트 줄높이 강제 맞춤 */
.stat-tight p {
    margin: 0 !important;
    line-height: 0.25 !important;
    display: flex !important;
    align-items: center !important;
}

/* ✅ st.radio 행 간격 줄이기 (핵심) */
div[data-testid="stRadio"] {
    margin-bottom: -27px !important;
    padding-bottom: 0 !important;
}

/* 라디오그룹 자체 여백 제거 */
div[role="radiogroup"] {
    margin-bottom: 0 !important;
}

/* label 간 세로 여백 제거 */
div[role="radiogroup"] > label {
    margin-bottom: 0 !important;
}

/* ===============================
   ✅ 라디오 3개(O, X, △) 선택 색상
   =============================== */

div[role="radiogroup"] label:has(input:checked) {
    background-color: #e5e7eb !important;
    border-color: #9ca3af !important;
}

div[role="radiogroup"] label:has(input:checked) svg {
    display: none !important;
}

div[role="radiogroup"] label:has(input:checked) p,
div[role="radiogroup"] label:has(input:checked) span {
    color: #fff !important;
}

/* 1=O */
div[role="radiogroup"] > label:nth-of-type(1):has(input:checked),
div[role="radiogroup"] > div:nth-of-type(1) label:has(input:checked) {
    background-color: #10b981 !important;
    border-color: #059669 !important;
}

/* 2=X */
div[role="radiogroup"] > label:nth-of-type(2):has(input:checked),
div[role="radiogroup"] > div:nth-of-type(2) label:has(input:checked) {
    background-color: #ef4444 !important;
    border-color: #dc2626 !important;
}

/* 3=△ */
div[role="radiogroup"] > label:nth-of-type(3):has(input:checked),
div[role="radiogroup"] > div:nth-of-type(3) label:has(input:checked) {
    background-color: #3b82f6 !important;
    border-color: #2563eb !important;
}

div[role="radiogroup"] *:focus {
    box-shadow: none !important;
    outline: none !important;
}

    /* =========================
       💼 직업/월급 탭: 학생수(+/-), 순서(⬆️⬇️) 버튼(원형) 안정화 - 최종
       ✅ Streamlit은 markdown div로 '위젯을 감싸지' 않음
       ✅ 그래서 .jobcnt-wrap "바로 다음 형제 블록"을 잡아서 스타일 적용해야 함
       ========================= */

    /* ---- 학생수 영역: .jobcnt-wrap 다음에 오는 컬럼 블록을 잡는다 ---- */
    .jobcnt-wrap + div,
    .jobcnt-wrap + div div[data-testid="stHorizontalBlock"]{
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        gap: 0.35rem !important;
        overflow: visible !important;
    }

    /* 학생수 영역 버튼(−/+) */
    .jobcnt-wrap + div div[data-testid="stButton"] button{
        width: 2.35rem !important;
        height: 2.35rem !important;
        min-width: 2.35rem !important;
        min-height: 2.35rem !important;
        max-width: 2.35rem !important;
        max-height: 2.35rem !important;

        padding: 0 !important;
        margin: 0 !important;
        border-radius: 9999px !important;

        display:flex !important;
        align-items:center !important;
        justify-content:center !important;

        line-height: 1 !important;
        box-sizing: border-box !important;
        overflow: visible !important;

        color: #111 !important;       /* ✅ + 안보임 해결 */
    }

    /* 버튼 내부(텍스트/이모지/아이콘) 전부 강제 */
    .jobcnt-wrap + div div[data-testid="stButton"] button *{
        color: #111 !important;
        fill:  #111 !important;
        stroke:#111 !important;
        font-weight: 900 !important;
        line-height: 1 !important;
    }

/* ✅ 학생수 버튼 stButton 래퍼를 강제로 원형 고정 (핵심) */
.jobcnt-num{
    position: relative;
}

.jobcnt-num:has(+ div[data-testid="stButton"]) + div[data-testid="stButton"],
.jobcnt-num:has(+ div[data-testid="stButton"]) + div[data-testid="stButton"] > button{
    width: 2.35rem !important;
    height: 2.35rem !important;
    min-width: 2.35rem !important;
    min-height: 2.35rem !important;
    max-width: 2.35rem !important;
    max-height: 2.35rem !important;

    border-radius: 9999px !important;
    padding: 0 !important;
    margin: 0 !important;

    display:flex !important;
    align-items:center !important;
    justify-content:center !important;

    color: #111 !important;
    font-weight: 900 !important;
    font-size: 1.15rem !important;

    overflow: visible !important;
}


    /* 가운데 숫자(학생 수) */
    .jobcnt-wrap + div .jobcnt-num{
        width: 2.2rem !important;
        height: 2.2rem !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        font-weight: 900 !important;
        flex: 0 0 auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* ---- 순서 영역: .joborder-wrap 다음 형제 블록을 잡는다 ---- */
    .joborder-wrap + div,
    .joborder-wrap + div div[data-testid="stHorizontalBlock"]{
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        gap: 0.25rem !important;
        overflow: visible !important;
    }

    .joborder-wrap + div div[data-testid="stButton"] button{
        width: 2.35rem !important;
        height: 2.35rem !important;
        min-width: 2.35rem !important;
        min-height: 2.35rem !important;
        max-width: 2.35rem !important;
        max-height: 2.35rem !important;

        padding: 0 !important;
        margin: 0 !important;
        border-radius: 9999px !important;

        display:flex !important;
        align-items:center !important;
        justify-content:center !important;

        line-height: 1 !important;
        box-sizing: border-box !important;
        overflow: visible !important;

        color: #111 !important;
    }

    .joborder-wrap + div div[data-testid="stButton"] button *{
        color: #111 !important;
        fill:  #111 !important;
        stroke:#111 !important;
        font-weight: 900 !important;
        line-height: 1 !important;
    }

    /* ✅ 모바일에서 겹침 방지: 크기만 살짝 다운 */
    @media (max-width: 768px){
        .jobcnt-wrap + div div[data-testid="stButton"] button,
        .joborder-wrap + div div[data-testid="stButton"] button{
            width: 2.05rem !important;
            height: 2.05rem !important;
            min-width: 2.05rem !important;
            min-height: 2.05rem !important;
            max-width: 2.05rem !important;
            max-height: 2.05rem !important;
        }
        .jobcnt-wrap + div .jobcnt-num{
            width: 2.0rem !important;
            height: 2.0rem !important;
        }
    }

    .job-empty{
        padding: 0.35rem 0.5rem;
        color: #777;
    }

    /* ✅ 간단 모드(모바일용) 리스트 */
    .tpl-simple {
        border: 1px solid #eee;
        border-radius: 12px;
        padding: 10px 12px;
        background: #fafafa;
        margin-top: 8px;
    }
    .tpl-simple .item { padding: 8px 0; border-bottom: 1px dashed #e6e6e6; }
    .tpl-simple .item:last-child { border-bottom: none; }
    .tpl-simple .idx { font-weight: 900; margin-right: 8px; }
    .tpl-simple .lab { font-weight: 800; }
    .tpl-simple .meta { color:#666; font-size: 0.92rem; margin-top: 2px; }

    /* ✅ 빠른 금액: radiogroup 라벨을 "원형 버튼"처럼 */
    .round-btns div[role="radiogroup"]{
        gap: 0.35rem !important;
    }
    .round-btns div[role="radiogroup"] > label{
        border-radius: 9999px !important;
        padding: 0 !important;
        width: 2.6rem !important;
        height: 2.6rem !important;
        min-width: 2.6rem !important;
        min-height: 2.6rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 0.95rem !important;
        line-height: 1 !important;
    }
    @media (max-width: 768px){
        .round-btns div[role="radiogroup"] > label{
            width: 3.1rem !important;
            height: 3.1rem !important;
            min-width: 3.1rem !important;
            min-height: 3.1rem !important;
            font-size: 1.05rem !important;
        }
    }
/* ✅ 원형 버튼 안 SVG 아이콘 크기 강제 축소 (핵심) */
.jobcnt-wrap div[data-testid="stButton"] button svg,
.joborder-wrap div[data-testid="stButton"] button svg{
    width: 7px !important;
    height: 7px !important;
}

/* 모바일은 더 작게 */
@media (max-width: 768px){
    .jobcnt-wrap div[data-testid="stButton"] button svg,
    .joborder-wrap div[data-testid="stButton"] button svg{
        width: 5px !important;
        height: 5px !important;
    }
}

/* ✅ expander 사이 회색 가로줄 제거 */
div[data-testid="stExpander"]{
    border: none !important;
    box-shadow: none !important;
}
div[data-testid="stExpander"] > div{
    border: none !important;
}

    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="app-title">🏦 {APP_TITLE}</div>', unsafe_allow_html=True)

# =========================
# Firestore init
# =========================
@st.cache_resource
def init_firestore():
    firebase_dict = dict(st.secrets["firebase"])
    firebase_dict["private_key"] = firebase_dict["private_key"].replace("\\n", "\n").strip()
    cred = credentials.Certificate(firebase_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

# =========================
# Utils (너 코드 유지 + 권한 유틸 추가)
# =========================
def pin_ok(pin: str) -> bool:
    return str(pin or "").isdigit() and len(str(pin or "")) == 4

def toast(msg: str, icon: str = "✅"):
    if hasattr(st, "toast"):
        st.toast(msg, icon=icon)
    else:
        st.success(msg)

def is_admin_login(name: str, pin: str) -> bool:
    return (str(name or "").strip() == ADMIN_NAME) and (str(pin or "").strip() == ADMIN_PIN)

def is_admin_pin(pin: str) -> bool:
    return str(pin or "").strip() == ADMIN_PIN

def format_kr_datetime(val) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, datetime):
        dt = val.astimezone(KST) if val.tzinfo else val.replace(tzinfo=KST)
    else:
        s = str(val).strip()
        try:
            if "T" in s and s.endswith("Z"):
                dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(KST)
            else:
                dt = datetime.fromisoformat(s)
            dt = dt.astimezone(KST) if dt.tzinfo else dt.replace(tzinfo=KST)
        except Exception:
            return s
    ampm = "오전" if dt.hour < 12 else "오후"
    hour12 = dt.hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{dt.year}년 {dt.month:02d}월 {dt.day:02d}일 {ampm} {hour12:02d}시 {dt.minute:02d}분"

def _to_utc_datetime(ts):
    if ts is None or ts == "":
        return None
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if hasattr(ts, "to_datetime"):
        dt = ts.to_datetime()
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    try:
        s = str(ts).strip()
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def clamp01(x: float) -> float:
    try:
        if x is None or x != x:
            return 0.0
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return 0.0

def _is_savings_memo(memo: str) -> bool:
    memo = str(memo or "")
    return ("적금 가입" in memo) or ("적금 해지" in memo) or ("적금 만기" in memo)

def render_asset_summary(balance_now: int, savings_list: list[dict], student_id: str, student_name: str):
    sv_total = sum(
        int(s.get("principal", 0) or 0)
        for s in (savings_list or [])
        if str(s.get("status", "")).lower().strip() == "active"
    )

    asset_total = int(balance_now) + int(sv_total)

    # 직업 조회
    job_name = "없음"
    try:
        snap = db.collection("students").document(student_id).get()
        if snap.exists:
            job_name = snap.to_dict().get("role_id") or "없음"
    except Exception:
        pass

    # 신용도 조회
    credit = api_get_credit_grade_by_student_id(student_id)

    st.markdown(f"### 🏦 {student_name} 통장")
    st.markdown(f"**내 자산:** {asset_total}드림")
    st.markdown(f"통장잔액: {int(balance_now)}드림")
    st.markdown(f"적금금액: {int(sv_total)}드림")
    st.markdown(f"직업: {job_name}")
    st.markdown(f"신용도: {credit}등급 ({credit}점)")

def savings_active_total(savings_list: list[dict]) -> int:
    return sum(
        int(s.get("principal", 0) or 0)
        for s in savings_list
        if str(s.get("status", "")).lower() == "active"
    )


# =========================
# Goals
# =========================
def api_get_goal_by_student_id(student_id: str):
    """student_id 기준 목표 조회 (가장 최근 1개)"""
    if not student_id:
        return {"ok": False, "error": "student_id가 없습니다."}
    try:
        q = (
            db.collection(GOAL_COL)
            .where(filter=FieldFilter("student_id", "==", student_id))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        docs = list(q)
        if not docs:
            return {"ok": True, "goal_amount": 0, "goal_date": ""}
        g = docs[0].to_dict() or {}
        return {
            "ok": True,
            "goal_amount": int(g.get("target_amount", 0) or 0),
            "goal_date": str(g.get("goal_date", "") or ""),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_get_goal(name: str, pin: str):
    """사용자 인증 후 목표 조회"""
    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    return api_get_goal_by_student_id(student_doc.id)


def api_set_goal(name: str, pin: str, goal_amount: int, goal_date_str: str):
    """사용자 인증 후 목표 저장(업데이트)"""
    goal_amount = int(goal_amount or 0)
    goal_date_str = str(goal_date_str or "").strip()

    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    if goal_amount <= 0:
        return {"ok": False, "error": "목표 금액은 1 이상이어야 합니다."}

    try:
        q = (
            db.collection(GOAL_COL)
            .where(filter=FieldFilter("student_id", "==", student_doc.id))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        docs = list(q)
        payload = {"student_id": student_doc.id, "target_amount": int(goal_amount), "goal_date": goal_date_str}
        if docs:
            db.collection(GOAL_COL).document(docs[0].id).set(payload, merge=True)
        else:
            payload["created_at"] = firestore.SERVER_TIMESTAMP
            db.collection(GOAL_COL).document().set(payload)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
# =========================
# Firestore helpers (students/auth) - 너 코드 유지
# =========================
def fs_get_student_doc_by_name(name: str):
    name = (name or "").strip()
    if not name:
        return None
    q = (
        db.collection("students")
        .where(filter=FieldFilter("name", "==", name))
        .where(filter=FieldFilter("is_active", "==", True))
        .limit(1)
        .stream()
    )
    docs = list(q)
    return docs[0] if docs else None

def fs_auth_student(name: str, pin: str):
    doc = fs_get_student_doc_by_name(name)
    if not doc:
        return None
    data = doc.to_dict() or {}
    if str(data.get("pin", "")) != str(pin):
        return None
    return doc

# =========================
# Cached lists
# =========================
@st.cache_data(ttl=30, show_spinner=False)
def api_list_accounts_cached():
    docs = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
    items = []
    for d in docs:
        s = d.to_dict() or {}
        nm = s.get("name", "")
        if nm:
            items.append({"student_id": d.id, "name": nm, "balance": int(s.get("balance", 0) or 0)})
    items.sort(key=lambda x: x["name"])
    return {"ok": True, "accounts": items}


@st.cache_data(ttl=300, show_spinner=False)
def api_list_templates_cached():
    docs = db.collection("templates").stream()
    templates = []
    for d in docs:
        t = d.to_dict() or {}
        if t.get("label"):
            templates.append(
                {
                    "template_id": d.id,
                    "label": t.get("label"),
                    "kind": t.get("kind"),
                    "amount": int(t.get("amount", 0) or 0),
                    "order": int(t.get("order", 999999) or 999999),
                }
            )
    templates.sort(key=lambda x: (int(x.get("order", 999999)), str(x.get("label", ""))))
    return {"ok": True, "templates": templates}


# =========================
# ✅ 통계청(제출물) helpers
# - 컬렉션:
#   1) stat_templates : {label, order, created_at}
#   2) stat_submissions: {label, date_iso, date_display, created_at, statuses{student_id:"X|O|△"}}
# =========================
def _weekday_kr_1ch(d: date) -> str:
    # 월화수목금토일 (파이썬: 월0 ~ 일6)
    w = d.weekday()
    return ["월", "화", "수", "목", "금", "토", "일"][w]


def format_kr_md_date(d: date) -> str:
    # "3월 7일(화)"
    return f"{d.month}월 {d.day}일({_weekday_kr_1ch(d)})"


@st.cache_data(ttl=60, show_spinner=False)
def api_list_stat_templates_cached():
    docs = db.collection("stat_templates").stream()
    items = []
    for d in docs:
        t = d.to_dict() or {}
        if t.get("label"):
            items.append(
                {
                    "template_id": d.id,
                    "label": str(t.get("label", "") or ""),
                    "order": int(t.get("order", 999999) or 999999),
                }
            )
    items.sort(key=lambda x: (int(x.get("order", 999999)), str(x.get("label", ""))))
    return {"ok": True, "templates": items}


@st.cache_data(ttl=30, show_spinner=False)
def api_list_stat_submissions_cached(limit_cols: int = 10):
    q = (
        db.collection("stat_submissions")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(int(limit_cols))
        .stream()
    )
    rows = []
    for d in q:
        s = d.to_dict() or {}
        rows.append(
            {
                "submission_id": d.id,
                "label": str(s.get("label", "") or ""),
                "date_iso": str(s.get("date_iso", "") or ""),
                "date_display": str(s.get("date_display", "") or ""),
                "created_at": _to_utc_datetime(s.get("created_at")),
                "statuses": dict(s.get("statuses", {}) or {}),
            }
        )
    return {"ok": True, "rows": rows}


def api_admin_upsert_stat_template(admin_pin: str, template_id: str, label: str, order: int):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    label = (label or "").strip()
    order = int(order or 1)

    if not label:
        return {"ok": False, "error": "내역(label)이 필요합니다."}
    if order <= 0:
        return {"ok": False, "error": "순서는 1 이상이어야 합니다."}

    payload = {"label": label, "order": order, "created_at": firestore.SERVER_TIMESTAMP}
    if template_id:
        db.collection("stat_templates").document(template_id).set(payload, merge=True)
    else:
        db.collection("stat_templates").document().set(payload)

    api_list_stat_templates_cached.clear()
    return {"ok": True}


def api_admin_delete_stat_template(admin_pin: str, template_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    template_id = (template_id or "").strip()
    if not template_id:
        return {"ok": False, "error": "template_id가 필요합니다."}
    db.collection("stat_templates").document(template_id).delete()
    api_list_stat_templates_cached.clear()
    return {"ok": True}


def api_admin_add_stat_submission(admin_pin: str, label: str, active_accounts: list[dict]):
    """
    ✅ 제출물 내역 추가:
    - created_at DESC로 최신이 맨 왼쪽(=가장 최근)으로 오게끔 'created_at' 기준으로만 정렬
    - statuses는 모든 활성 학생을 기본 X로 채움
    """
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    label = (label or "").strip()
    if not label:
        return {"ok": False, "error": "내역이 필요합니다."}

    today = datetime.now(KST).date()
    statuses = {}
    for a in active_accounts or []:
        sid = str(a.get("student_id", "") or "")
        if sid:
            statuses[sid] = "X"

    db.collection("stat_submissions").document().set(
        {
            "label": label,
            "date_iso": today.isoformat(),
            "date_display": format_kr_md_date(today),
            "statuses": statuses,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )

    api_list_stat_submissions_cached.clear()
    return {"ok": True}


def api_admin_save_stat_table(admin_pin: str, submission_ids: list[str], edited: dict, accounts: list[dict]):
    """
    ✅ 표 상단 저장버튼:
    - 클릭 때마다 DB 저장 금지(로컬 상태만 변경)
    - 저장 버튼 누를 때 제출물(컬럼) 단위로 statuses map을 한 번에 업데이트(컬럼 수만큼 write)
    """
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if not submission_ids:
        return {"ok": False, "error": "저장할 제출물이 없습니다."}

    # 활성 학생 목록 (계정 추가 시 자동 반영)
    active_sids = [str(a.get("student_id", "") or "") for a in (accounts or []) if str(a.get("student_id", "") or "")]
    active_sids_set = set(active_sids)

    batch = db.batch()
    for sub_id in submission_ids:
        sub_id = str(sub_id)
        ref = db.collection("stat_submissions").document(sub_id)

        # 기존 + 편집본 병합: 활성 학생은 모두 키가 존재하도록 보정
        cur_map = dict((edited or {}).get(sub_id, {}) or {})
        merged = {}
        for sid in active_sids:
            v = str(cur_map.get(sid, "X") or "X")
            merged[sid] = v if v in ("X", "O", "△") else "X"

        batch.set(ref, {"statuses": merged}, merge=True)

    batch.commit()
    api_list_stat_submissions_cached.clear()
    return {"ok": True, "count": len(submission_ids)}


def api_admin_delete_stat_submission(admin_pin: str, submission_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    submission_id = (submission_id or "").strip()
    if not submission_id:
        return {"ok": False, "error": "submission_id가 필요합니다."}
    db.collection("stat_submissions").document(submission_id).delete()
    api_list_stat_submissions_cached.clear()
    return {"ok": True}


def _cycle_mark(v: str) -> str:
    v = str(v or "X")
    if v == "X":
        return "O"
    if v == "O":
        return "△"
    return "X"

# =========================
# Account CRUD (너 코드 유지 + role_id 추가 함수만 추가)
# =========================
def api_create_account(name, pin):
    name = (name or "").strip()
    pin = (pin or "").strip()
    if not name:
        return {"ok": False, "error": "이름이 필요합니다."}
    if not (pin.isdigit() and len(pin) == 4):
        return {"ok": False, "error": "PIN은 4자리 숫자여야 합니다."}
    if fs_get_student_doc_by_name(name):
        return {"ok": False, "error": "이미 존재하는 계정입니다."}
    db.collection("students").document().set(
        {
            "name": name,
            "pin": pin,
            "balance": 0,
            "is_active": True,
            "role_id": "",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    api_list_accounts_cached.clear()
    return {"ok": True}

def api_delete_account(name, pin):
    doc = fs_auth_student(login_name, login_pin)
    if not doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    db.collection("students").document(doc.id).update({"is_active": False})
    api_list_accounts_cached.clear()
    return {"ok": True}

def api_change_pin_student(name: str, old_pin: str, new_pin: str):
    """
    ✅ 학생 본인 비밀번호(PIN) 변경
    - 이름 + 기존 PIN 인증 후 새 PIN 저장
    """
    name = (name or "").strip()
    old_pin = (old_pin or "").strip()
    new_pin = (new_pin or "").strip()

    if not name:
        return {"ok": False, "error": "이름이 필요합니다."}
    if not pin_ok(old_pin):
        return {"ok": False, "error": "기존 비밀번호는 4자리 숫자여야 합니다."}
    if not pin_ok(new_pin):
        return {"ok": False, "error": "새 비밀번호는 4자리 숫자여야 합니다."}

    doc = fs_auth_student(name, old_pin)  # ✅ 기존 PIN 인증
    if not doc:
        return {"ok": False, "error": "이름 또는 기존 비밀번호가 틀립니다."}

    db.collection("students").document(doc.id).update({"pin": str(new_pin)})
    api_list_accounts_cached.clear()
    return {"ok": True}

def api_admin_set_role(admin_pin: str, student_id: str, role_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if not student_id:
        return {"ok": False, "error": "student_id가 없습니다."}
    db.collection("students").document(student_id).update({"role_id": str(role_id or "")})
    api_list_accounts_cached.clear()
    return {"ok": True}

# =========================
# Transactions (너 코드 그대로)
# =========================
def api_add_tx(name, pin, memo, deposit, withdraw):
    memo = (memo or "").strip()
    deposit = int(deposit or 0)
    withdraw = int(withdraw or 0)
    if not memo:
        return {"ok": False, "error": "내역이 필요합니다."}
    if (deposit > 0 and withdraw > 0) or (deposit == 0 and withdraw == 0):
        return {"ok": False, "error": "입금/출금 중 하나만 입력하세요."}

    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    student_ref = db.collection("students").document(student_doc.id)
    tx_ref = db.collection("transactions").document()

    amount = deposit if deposit > 0 else -withdraw
    tx_type = "deposit" if deposit > 0 else "withdraw"

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        bal = int((snap.to_dict() or {}).get("balance", 0))

        # 일반 출금은 잔액 부족이면 불가
        if tx_type == "withdraw" and bal < withdraw:
            raise ValueError("잔액보다 큰 출금은 불가합니다.")

        new_bal = bal + amount
        transaction.update(student_ref, {"balance": new_bal})
        transaction.set(
            tx_ref,
            {
                "student_id": student_doc.id,
                "type": tx_type,
                "amount": amount,
                "balance_after": new_bal,
                "memo": memo,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return new_bal

    try:
        new_bal = _do(db.transaction())
        return {"ok": True, "balance": new_bal}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"저장 실패: {e}"}

def api_admin_add_tx_by_student_id(admin_pin: str, student_id: str, memo: str, deposit: int, withdraw: int):
    """
    ✅ 관리자 전용: 개별 학생에게 입금/출금
    - 학생 PIN 불필요
    - 출금은 잔액 부족이어도 적용(음수 허용)
    """
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    memo = (memo or "").strip()
    deposit = int(deposit or 0)
    withdraw = int(withdraw or 0)

    if not memo:
        return {"ok": False, "error": "내역이 필요합니다."}
    if (deposit > 0 and withdraw > 0) or (deposit == 0 and withdraw == 0):
        return {"ok": False, "error": "입금/출금 중 하나만 입력하세요."}
    if not student_id:
        return {"ok": False, "error": "student_id가 없습니다."}

    student_ref = db.collection("students").document(student_id)
    tx_ref = db.collection("transactions").document()

    amount = deposit if deposit > 0 else -withdraw
    tx_type = "deposit" if deposit > 0 else "withdraw"

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        if not snap.exists:
            raise ValueError("계정을 찾지 못했습니다.")
        bal = int((snap.to_dict() or {}).get("balance", 0))
        new_bal = bal + amount  # ✅ 음수 허용
        transaction.update(student_ref, {"balance": new_bal})
        transaction.set(
            tx_ref,
            {
                "student_id": student_id,
                "type": tx_type,
                "amount": amount,
                "balance_after": new_bal,
                "memo": memo,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return new_bal

    try:
        new_bal = _do(db.transaction())
        return {"ok": True, "balance": new_bal}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"저장 실패: {e}"}

def api_get_txs_by_student_id(student_id: str, limit=200):
    if not student_id:
        return {"ok": False, "error": "student_id가 없습니다."}
    q = (
        db.collection("transactions")
        .where(filter=FieldFilter("student_id", "==", student_id))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(int(limit))
        .stream()
    )
    rows = []
    for d in q:
        tx = d.to_dict() or {}
        created_dt_utc = _to_utc_datetime(tx.get("created_at"))
        amt = int(tx.get("amount", 0) or 0)
        rows.append(
            {
                "tx_id": d.id,
                "created_at_utc": created_dt_utc,
                "created_at_kr": format_kr_datetime(created_dt_utc.astimezone(KST)) if created_dt_utc else "",
                "memo": tx.get("memo", ""),
                "type": tx.get("type", ""),
                "amount": amt,
                "deposit": amt if amt > 0 else 0,
                "withdraw": -amt if amt < 0 else 0,
                "balance_after": int(tx.get("balance_after", 0) or 0),
            }
        )
    return {"ok": True, "rows": rows}

def api_get_balance(login_name, login_pin):
    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    data = student_doc.to_dict() or {}

    # ✅ 신용등급(없으면 0)
    credit_grade = int(data.get("credit_grade", 0) or 0)

    return {
        "ok": True,
        "balance": int(data.get("balance", 0) or 0),
        "student_id": student_doc.id,
        "credit_grade": credit_grade,
    }

def api_get_credit_grade_by_student_id(student_id: str) -> int:
    """
    ✅ 학생 신용등급 조회
    - 신용등급 탭에서 저장해둔 값을 students 문서의 credit_grade 필드로 사용한다고 가정
    - 없으면 0등급으로 표시
    """
    try:
        if not student_id:
            return 0
        snap = db.collection("students").document(student_id).get()
        if not snap.exists:
            return 0
        data = snap.to_dict() or {}
        return int(data.get("credit_grade", 0) or 0)
    except Exception:
        return 0


# =========================
# Admin rollback (너 코드 그대로)
# =========================
def _already_rolled_back(student_id: str, tx_id: str) -> bool:
    q = (
        db.collection("transactions")
        .where(filter=FieldFilter("student_id", "==", student_id))
        .where(filter=FieldFilter("type", "==", "rollback"))
        .where(filter=FieldFilter("related_tx", "==", tx_id))
        .limit(1)
        .stream()
    )
    return len(list(q)) > 0

def api_admin_rollback_selected(admin_pin: str, student_id: str, tx_ids: list[str]):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if not student_id or not tx_ids:
        return {"ok": False, "error": "되돌릴 항목이 없습니다."}

    student_ref = db.collection("students").document(student_id)

    tx_docs = []
    for tid in tx_ids:
        snap = db.collection("transactions").document(tid).get()
        if not snap.exists:
            continue
        tx = snap.to_dict() or {}
        if tx.get("student_id") != student_id:
            continue
        tx_docs.append((tid, tx))

    if not tx_docs:
        return {"ok": False, "error": "유효한 거래를 찾지 못했습니다."}

    blocked, valid = [], []
    for tid, tx in tx_docs:
        ttype = str(tx.get("type", "") or "")
        memo = str(tx.get("memo", "") or "")
        if ttype == "rollback":
            blocked.append((tid, "이미 되돌리기 기록"))
            continue
        if _is_savings_memo(memo) or ttype in ("maturity",):
            blocked.append((tid, "적금 관련 내역"))
            continue
        if _already_rolled_back(student_id, tid):
            blocked.append((tid, "이미 되돌린 거래"))
            continue
        valid.append((tid, tx))

    if not valid:
        msg = "선택한 항목이 모두 되돌리기 불가합니다."
        if blocked:
            msg += " (예: 적금/이미 되돌림)"
        return {"ok": False, "error": msg}

    def _tx_time(tx):
        dt = _to_utc_datetime(tx.get("created_at"))
        return dt or datetime(1970, 1, 1, tzinfo=timezone.utc)

    valid.sort(key=lambda x: _tx_time(x[1]))

    undone, total_delta = 0, 0
    for tid, tx in valid:
        amount = int(tx.get("amount", 0) or 0)
        rollback_amount = -amount
        rollback_ref = db.collection("transactions").document()

        @firestore.transactional
        def _do_one(transaction):
            st_snap = student_ref.get(transaction=transaction)
            bal = int((st_snap.to_dict() or {}).get("balance", 0))
            new_bal = bal + rollback_amount
            transaction.update(student_ref, {"balance": new_bal})
            transaction.set(
                rollback_ref,
                {
                    "student_id": student_id,
                    "type": "rollback",
                    "amount": rollback_amount,
                    "balance_after": new_bal,
                    "memo": f"{tid} 되돌리기",
                    "related_tx": tid,
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
            )
            return new_bal

        _do_one(db.transaction())
        undone += 1
        total_delta += rollback_amount

    info_msg = None
    if blocked:
        info_msg = f"되돌리기 제외 {len(blocked)}건(적금/이미 되돌림 등)은 건너뛰었습니다."

    return {"ok": True, "undone": undone, "delta": total_delta, "message": info_msg}

# =========================
# Savings / Goal
# (너 코드 그대로이긴 한데, 학급 확장 핵심이 아니라 여기서는 생략하지 않고
# 기존 코드 쓰던 그대로 붙여 넣어도 됨. 이미 너 코드에 있으니 그대로 유지하면 됨.)
# =========================
# ★★★ 너가 올린 Savings/Goal 코드는 그대로 붙여넣어 사용 ★★★
# 여기서는 "학급 확장"이 핵심이라, 아래에서 호출되는 함수만 "이미 존재"한다고 가정:
# - api_savings_list_by_student_id, api_savings_list, api_savings_create, api_savings_cancel, api_process_maturities
# - api_get_goal, api_get_goal_by_student_id, api_set_goal
#
# ✅ 너는 지금 코드에 이미 들어있으니, 그대로 두면 된다.

# =========================
# 🏛️ Treasury(국세청/국고) - helpers + templates + UI
# =========================

TREASURY_UNIT = "드림"   # ✅ 표시 단위만 드림(시스템 숫자는 그대로 int)

@st.cache_data(ttl=30, show_spinner=False)
def api_get_treasury_state_cached():
    ref = db.collection("treasury").document("state")
    snap = ref.get()
    if not snap.exists:
        ref.set({"balance": 0, "updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
        return {"ok": True, "balance": 0}
    d = snap.to_dict() or {}
    return {"ok": True, "balance": int(d.get("balance", 0) or 0)}

def api_add_treasury_tx(admin_pin: str, memo: str, income: int, expense: int, actor: str = "treasury"):
    """
    국고 거래(세입/세출)
    - income: 세입(+) 입력
    - expense: 세출(+) 입력
    - amount는 +income 또는 -expense 로 저장
    """
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    memo = str(memo or "").strip()
    income = int(income or 0)
    expense = int(expense or 0)

    if not memo:
        return {"ok": False, "error": "내역이 필요합니다."}
    if (income > 0 and expense > 0) or (income == 0 and expense == 0):
        return {"ok": False, "error": "세입/세출 중 하나만 입력하세요."}

    state_ref = db.collection("treasury").document("state")
    led_ref = db.collection("treasury_ledger").document()

    amount = income if income > 0 else -expense
    tx_type = "income" if income > 0 else "expense"

    @firestore.transactional
    def _do(transaction):
        st_snap = state_ref.get(transaction=transaction)
        cur_bal = 0
        if st_snap.exists:
            cur_bal = int((st_snap.to_dict() or {}).get("balance", 0) or 0)

        new_bal = int(cur_bal + amount)

        transaction.set(
            state_ref,
            {
                "balance": int(new_bal),
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

        transaction.set(
            led_ref,
            {
                "type": tx_type,
                "amount": int(amount),          # +세입 / -세출
                "income": int(income if income > 0 else 0),
                "expense": int(expense if expense > 0 else 0),
                "balance_after": int(new_bal),
                "memo": memo,
                "actor": str(actor or ""),
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return new_bal

    try:
        new_bal = _do(db.transaction())
        api_get_treasury_state_cached.clear()
        api_list_treasury_ledger_cached.clear()
        return {"ok": True, "balance": int(new_bal)}
    except Exception as e:
        return {"ok": False, "error": f"국고 저장 실패: {e}"}

@st.cache_data(ttl=30, show_spinner=False)
def api_list_treasury_ledger_cached(limit=300):
    q = (
        db.collection("treasury_ledger")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(int(limit))
        .stream()
    )
    rows = []
    for d in q:
        x = d.to_dict() or {}
        created_dt_utc = _to_utc_datetime(x.get("created_at"))
        rows.append(
            {
                "created_at_utc": created_dt_utc,
                "created_at_kr": format_kr_datetime(created_dt_utc.astimezone(KST)) if created_dt_utc else "",
                "memo": str(x.get("memo", "") or ""),
                "income": int(x.get("income", 0) or 0),
                "expense": int(x.get("expense", 0) or 0),
                "balance_after": int(x.get("balance_after", 0) or 0),
            }
        )
    return {"ok": True, "rows": rows}

# ---------- 국고 전용 템플릿 ----------
@st.cache_data(ttl=120, show_spinner=False)
def api_list_treasury_templates_cached():
    docs = db.collection("treasury_templates").stream()
    templates = []
    for d in docs:
        t = d.to_dict() or {}
        label = str(t.get("label", "") or "").strip()
        if label:
            templates.append(
                {
                    "template_id": d.id,
                    "label": label,
                    "kind": str(t.get("kind", "income") or "income"),  # income/expense
                    "amount": int(t.get("amount", 0) or 0),
                    "order": int(t.get("order", 999999) or 999999),
                }
            )
    templates.sort(key=lambda x: (int(x.get("order", 999999)), str(x.get("label", ""))))
    return {"ok": True, "templates": templates}

def api_upsert_treasury_template(admin_pin: str, template_id: str, label: str, kind: str, amount: int, order: int):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    label = str(label or "").strip()
    kind = str(kind or "income").strip()
    amount = int(amount or 0)
    order = int(order or 999999)

    if not label:
        return {"ok": False, "error": "라벨(내역)이 필요합니다."}
    if kind not in ("income", "expense"):
        return {"ok": False, "error": "kind는 income/expense 중 하나여야 합니다."}
    if amount <= 0:
        return {"ok": False, "error": "금액은 0보다 커야 합니다."}

    if template_id:
        ref = db.collection("treasury_templates").document(str(template_id))
    else:
        ref = db.collection("treasury_templates").document()

    ref.set(
        {
            "label": label,
            "kind": kind,
            "amount": amount,
            "order": order,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )

    api_list_treasury_templates_cached.clear()
    return {"ok": True}

def api_delete_treasury_template(admin_pin: str, template_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if not template_id:
        return {"ok": False, "error": "template_id가 없습니다."}
    db.collection("treasury_templates").document(str(template_id)).delete()
    api_list_treasury_templates_cached.clear()
    return {"ok": True}

def treasury_template_display(t):
    kind_kr = "세입" if t.get("kind") == "income" else "세출"
    return f"{t.get('label')}[{kind_kr} {int(t.get('amount', 0))}]"

def build_treasury_template_maps():
    res = api_list_treasury_templates_cached()
    items = res.get("templates", []) if res.get("ok") else []
    disp = [treasury_template_display(t) for t in items]
    by_disp = {treasury_template_display(t): t for t in items}
    by_id = {str(t.get("template_id")): t for t in items if t.get("template_id")}
    return items, disp, by_disp, by_id

# ---------- 국고 입력 UI (개별 관리자 입금/출금과 동일한 원리) ----------
def render_treasury_trade_ui(prefix: str, templates_list: list, template_by_display: dict):
    memo_key = f"{prefix}_memo"
    inc_key = f"{prefix}_inc"
    exp_key = f"{prefix}_out"
    tpl_key = f"{prefix}_tpl"
    tpl_prev_key = f"{prefix}_tpl_prev"

    # 세션 기본값
    st.session_state.setdefault(memo_key, "")
    st.session_state.setdefault(inc_key, 0)
    st.session_state.setdefault(exp_key, 0)
    st.session_state.setdefault(tpl_key, "(직접 입력)")
    st.session_state.setdefault(tpl_prev_key, "(직접 입력)")

    # 템플릿 선택
    tpl_labels = ["(직접 입력)"] + [treasury_template_display(t) for t in templates_list]
    sel = st.selectbox("국고 템플릿", tpl_labels, key=tpl_key)

    # 템플릿 바뀌면 내역/금액 자동채움
    if sel != st.session_state.get(tpl_prev_key):
        st.session_state[tpl_prev_key] = sel

        if sel != "(직접 입력)":
            t = template_by_display.get(sel)
            if t:
                st.session_state[memo_key] = str(t.get("label", "") or "")
                amt = int(t.get("amount", 0) or 0)
                if str(t.get("kind")) == "income":
                    st.session_state[inc_key] = amt
                    st.session_state[exp_key] = 0
                else:
                    st.session_state[inc_key] = 0
                    st.session_state[exp_key] = amt

        st.rerun()

    # 내역 입력
    st.text_input("내역", key=memo_key)

    # ✅ 원형 숫자 버튼(빠른 금액) — 국고 전용 prefix를 그대로 사용
    render_round_amount_picker(
        prefix=prefix,                # ✅ 여기 중요: "treasury_trade" 그대로 연동됨
        plus_label="세입(+)",
        minus_label="세출(-)",
        amounts=[0, 10, 20, 50, 100, 200, 500, 1000],
    )

    # 숫자 입력(세입/세출)
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("세입", min_value=0, step=1, key=inc_key)
    with c2:
        st.number_input("세출", min_value=0, step=1, key=exp_key)

    # ✅ 함수 안에서 return (return outside function 방지)
    memo = str(st.session_state.get(memo_key, "") or "").strip()
    inc = int(st.session_state.get(inc_key, 0) or 0)
    exp = int(st.session_state.get(exp_key, 0) or 0)
    return memo, inc, exp

# =========================
# Templates (공용) - 너 코드 유지
# =========================
tpl_res = api_list_templates_cached()
TEMPLATES = tpl_res.get("templates", []) if tpl_res.get("ok") else []

def template_display_for_trade(t):
    kind_kr = "입금" if t["kind"] == "deposit" else "출금"
    return f"{t['label']}[{kind_kr} {int(t['amount'])}]"

TEMPLATE_BY_DISPLAY = {template_display_for_trade(t): t for t in TEMPLATES}

# =========================
# ✅ 공용: 거래 입력 UI (너 코드 그대로)
# =========================
def render_admin_trade_ui(prefix: str, templates_list: list, template_by_display: dict):
    memo_key = f"{prefix}_memo"
    dep_key = f"{prefix}_dep"
    wd_key = f"{prefix}_wd"
    tpl_key = f"{prefix}_tpl"
    mode_key = f"{prefix}_mode"
    prev_key = f"{prefix}_quick_prev"

    out_key = f"{prefix}_trade_out"

    st.session_state.setdefault(memo_key, "")
    st.session_state.setdefault(dep_key, 0)
    st.session_state.setdefault(wd_key, 0)
    st.session_state.setdefault(tpl_key, "(직접 입력)")
    st.session_state.setdefault(mode_key, "금액(+)")
    st.session_state.setdefault(prev_key, None)

    reset_flag_key = f"{prefix}_reset_request"
    if st.session_state.get(reset_flag_key, False):
        st.session_state[memo_key] = ""
        st.session_state[dep_key] = 0
        st.session_state[wd_key] = 0
        st.session_state[tpl_key] = "(직접 입력)"
        st.session_state[mode_key] = "금액(+)"
        st.session_state[prev_key] = None
        st.session_state[reset_flag_key] = False

    def _get_net() -> int:
        dep = int(st.session_state.get(dep_key, 0) or 0)
        wd = int(st.session_state.get(wd_key, 0) or 0)
        return dep - wd

    def _set_by_net(net: int):
        net = int(net or 0)
        if net >= 0:
            st.session_state[dep_key] = net
            st.session_state[wd_key] = 0
        else:
            st.session_state[dep_key] = 0
            st.session_state[wd_key] = -net

    def _apply_amt(amt: int):
        amt = int(amt or 0)
        if amt == 0:
            st.session_state[dep_key] = 0
            st.session_state[wd_key] = 0
            return

        sign = 1 if st.session_state[mode_key] == "금액(+)" else -1
        net = _get_net() + (sign * amt)
        _set_by_net(net)

    _frag = getattr(st, "fragment", None)
    use_fragment = callable(_frag)

    def _draw_ui():
        tpl_prev_key = f"{prefix}_tpl_prev"
        st.session_state.setdefault(tpl_prev_key, "(직접 입력)")

        tpl_labels = ["(직접 입력)"] + [template_display_for_trade(t) for t in templates_list]
        sel = st.selectbox("내역 템플릿", tpl_labels, key=tpl_key)

        if sel != st.session_state.get(tpl_prev_key):
            st.session_state[tpl_prev_key] = sel

            st.session_state[f"{prefix}_quick_pick"] = "0"
            st.session_state[f"{prefix}_quick_pick_prev"] = "0"
            st.session_state[f"{prefix}_quick_skip_once"] = True

            if sel != "(직접 입력)":
                tpl = template_by_display.get(sel)
                if tpl:
                    st.session_state[memo_key] = tpl["label"]
                    amt = int(tpl["amount"])

                    if tpl["kind"] == "deposit":
                        _set_by_net(amt)
                        st.session_state[mode_key] = "금액(+)"
                    else:
                        _set_by_net(-amt)
                        st.session_state[mode_key] = "금액(-)"

                    st.session_state[f"{prefix}_quick_skip_once"] = True

            if not use_fragment:
                st.rerun()

        st.text_input("내역", key=memo_key)

        st.caption("⚡ 빠른 금액(원형 버튼)")
        QUICK_AMOUNTS = [0, 10, 20, 50, 100, 200, 500, 1000]

        pick_key = f"{prefix}_quick_pick"
        st.session_state.setdefault(pick_key, "0")

        skip_key = f"{prefix}_quick_skip_once"
        st.session_state.setdefault(skip_key, False)

        def _on_mode_change():
            st.session_state[pick_key] = "0"
            st.session_state[skip_key] = True
            st.session_state[f"{prefix}_quick_pick_prev"] = "0"
            st.session_state[f"{prefix}_quick_mode_prev"] = str(st.session_state.get(mode_key, "금액(+)"))

        st.radio(
            "적용",
            ["금액(+)", "금액(-)"],
            horizontal=True,
            key=mode_key,
            on_change=_on_mode_change,
        )

        st.markdown("<div class='round-btns'>", unsafe_allow_html=True)
        opts = [str(a) for a in QUICK_AMOUNTS]
        st.radio(
            "빠른금액",
            opts,
            horizontal=True,
            label_visibility="collapsed",
            key=pick_key,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        mode_prev_key = f"{prefix}_quick_mode_prev"
        pick_prev_key = f"{prefix}_quick_pick_prev"

        cur_mode = str(st.session_state.get(mode_key, "금액(+)"))
        cur_pick = str(st.session_state.get(pick_key, "0"))

        st.session_state.setdefault(mode_prev_key, cur_mode)
        st.session_state.setdefault(pick_prev_key, cur_pick)

        if st.session_state.get(skip_key, False):
            st.session_state[mode_prev_key] = cur_mode
            st.session_state[pick_prev_key] = cur_pick
            st.session_state[skip_key] = False
        else:
            prev_mode = str(st.session_state.get(mode_prev_key, cur_mode))
            prev_pick = str(st.session_state.get(pick_prev_key, cur_pick))

            if cur_mode != prev_mode:
                st.session_state[mode_prev_key] = cur_mode
                st.session_state[pick_prev_key] = cur_pick
            elif cur_pick != prev_pick:
                st.session_state[pick_prev_key] = cur_pick
                _apply_amt(int(cur_pick))
                if not use_fragment:
                    st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            st.number_input("입금", min_value=0, step=1, key=dep_key)
        with c2:
            st.number_input("출금", min_value=0, step=1, key=wd_key)

        memo = str(st.session_state.get(memo_key, "") or "").strip()
        dep = int(st.session_state.get(dep_key, 0) or 0)
        wd = int(st.session_state.get(wd_key, 0) or 0)
        st.session_state[out_key] = (memo, dep, wd)

    if use_fragment:
        @_frag
        def _frag_draw():
            _draw_ui()
        _frag_draw()
    else:
        _draw_ui()

    memo, dep, wd = st.session_state.get(out_key, ("", 0, 0))
    return memo, dep, wd

# =========================
# ✅ 공용: 원형 숫자 버튼(빠른 금액) - 세입/세출 버전
#   - 세입/세출 두 칸을 "계산기처럼" 조작
#   - 0 누르면 둘 다 0
# =========================
def render_round_amount_picker(prefix: str, plus_label: str, minus_label: str, amounts=None):
    if amounts is None:
        amounts = [0, 10, 20, 50, 100, 200, 500, 1000]

    inc_key = f"{prefix}_inc"
    out_key = f"{prefix}_out"
    mode_key = f"{prefix}_mode"
    pick_key = f"{prefix}_pick"
    pick_prev_key = f"{prefix}_pick_prev"
    mode_prev_key = f"{prefix}_mode_prev"
    skip_key = f"{prefix}_skip_once"

    st.session_state.setdefault(inc_key, 0)
    st.session_state.setdefault(out_key, 0)
    st.session_state.setdefault(mode_key, plus_label)
    st.session_state.setdefault(pick_key, "0")
    st.session_state.setdefault(pick_prev_key, "0")
    st.session_state.setdefault(mode_prev_key, str(st.session_state.get(mode_key, plus_label)))
    st.session_state.setdefault(skip_key, False)

    def _get_net() -> int:
        inc = int(st.session_state.get(inc_key, 0) or 0)
        out = int(st.session_state.get(out_key, 0) or 0)
        return inc - out

    def _set_by_net(net: int):
        net = int(net or 0)
        if net >= 0:
            st.session_state[inc_key] = net
            st.session_state[out_key] = 0
        else:
            st.session_state[inc_key] = 0
            st.session_state[out_key] = -net

    def _apply_amt(amt: int):
        amt = int(amt or 0)
        if amt == 0:
            st.session_state[inc_key] = 0
            st.session_state[out_key] = 0
            return

        sign = 1 if str(st.session_state.get(mode_key)) == plus_label else -1
        net = _get_net() + (sign * amt)
        _set_by_net(net)

    def _on_mode_change():
        st.session_state[pick_key] = "0"
        st.session_state[pick_prev_key] = "0"
        st.session_state[skip_key] = True
        st.session_state[mode_prev_key] = str(st.session_state.get(mode_key, plus_label))

    st.caption("⚡ 빠른 금액(원형 버튼)")
    st.radio(
        "적용",
        [plus_label, minus_label],
        horizontal=True,
        key=mode_key,
        on_change=_on_mode_change,
    )

    st.markdown("<div class='round-btns'>", unsafe_allow_html=True)
    st.radio(
        "빠른금액",
        [str(a) for a in amounts],
        horizontal=True,
        label_visibility="collapsed",
        key=pick_key,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    cur_mode = str(st.session_state.get(mode_key, plus_label))
    cur_pick = str(st.session_state.get(pick_key, "0"))

    prev_mode = str(st.session_state.get(mode_prev_key, cur_mode))
    prev_pick = str(st.session_state.get(pick_prev_key, cur_pick))

    if st.session_state.get(skip_key, False):
        st.session_state[mode_prev_key] = cur_mode
        st.session_state[pick_prev_key] = cur_pick
        st.session_state[skip_key] = False
        return

    if cur_mode != prev_mode:
        st.session_state[mode_prev_key] = cur_mode
        st.session_state[pick_prev_key] = cur_pick
        return

    if cur_pick != prev_pick:
        st.session_state[pick_prev_key] = cur_pick
        _apply_amt(int(cur_pick))

# =========================
# 학급 확장: Roles/Permissions
# =========================
@st.cache_data(ttl=120, show_spinner=False)
def api_list_roles_cached():
    docs = db.collection("roles").stream()
    roles = []
    for d in docs:
        r = d.to_dict() or {}
        roles.append(
            {
                "role_id": d.id,
                "role_name": str(r.get("role_name", "") or ""),
                "permissions": list(r.get("permissions", []) or []),
                "salary_gross": int(r.get("salary_gross", 0) or 0),
                "tax_rate": float(r.get("tax_rate", 0.1) or 0.1),
                "desk_rent": int(r.get("desk_rent", 50) or 50),
                "electric_fee": int(r.get("electric_fee", 10) or 10),
                "health_fee": int(r.get("health_fee", 10) or 10),
            }
        )
    roles.sort(key=lambda x: x["role_name"])
    return {"ok": True, "roles": roles}

def get_my_permissions(student_id: str, is_admin: bool):
    if is_admin:
        return {"admin_all"}
    if not student_id:
        return set()
    snap = db.collection("students").document(student_id).get()
    if not snap.exists:
        return set()
    role_id = str((snap.to_dict() or {}).get("role_id", "") or "")
    if not role_id:
        return set()
    rdoc = db.collection("roles").document(role_id).get()
    if not rdoc.exists:
        return set()
    perms = set((rdoc.to_dict() or {}).get("permissions", []) or [])
    return perms

def can(perms: set, need: str) -> bool:
    return ("admin_all" in perms) or (need in perms)

# =========================
# 학급 확장: 초기 데이터 업로드(직업표/월급/은행금리표)
# =========================
def parse_jobs_xlsx(uploaded_file) -> tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.ExcelFile(uploaded_file)
    # 직업표: '순'이 있는 행 찾기
    raw = xl.parse("직업표", header=None)
    idx = None
    for i, row in raw.iterrows():
        if any(str(x).strip() == "순" for x in row.values):
            idx = i
            break
    jobs = xl.parse("직업표", header=idx).dropna(how="all")

    raw2 = xl.parse("월급 명세서", header=None)
    idx2 = None
    for i, row in raw2.iterrows():
        if any(str(x).strip() == "순" for x in row.values):
            idx2 = i
            break
    pay = xl.parse("월급 명세서", header=idx2).dropna(how="all")
    pay = pay.loc[:, ~pay.columns.astype(str).str.contains("^Unnamed")]
    return jobs, pay

def upsert_roles_from_paytable(admin_pin: str, pay_df: pd.DataFrame):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if pay_df is None or pay_df.empty:
        return {"ok": False, "error": "월급표가 비어있습니다."}

    # 월급표 마지막 합계행 제거(텍스트 포함된 행)
    df = pay_df.copy()
    df["직업"] = df["직업"].astype(str)
    df = df[df["직업"].str.contains("합계") == False]

    # permissions 기본 템플릿(직업명에 따라 자동 부여는 “초기값”만)
    def default_perms(job_name: str):
        job_name = str(job_name or "")
        perms = ["schedule_read"]
        if "은행" in job_name:
            perms += ["bank_read", "bank_write", "schedule_bank_write"]
        if "통계" in job_name:
            perms += ["stats_write"]
        if "환경" in job_name:
            perms += ["schedule_env_write"]
        if "국세" in job_name or "세무" in job_name:
            perms += ["treasury_read", "treasury_write", "schedule_treasury_write"]
        if "대통령" in job_name or "장관" in job_name:
            perms += ["treasury_read"]
        return list(sorted(set(perms)))

    # Firestore upsert: role_name을 키로 삼고 싶으면 별도 index가 필요하므로
    # 여기서는 "role_name 문서"를 생성(간단)
    # 문서ID를 role_name으로 쓰면 초보에게 가장 쉬움.
    batch = db.batch()
    for _, r in df.iterrows():
        role_name = str(r.get("직업", "") or "").strip()
        if not role_name or role_name == "nan":
            continue
        gross = int(float(r.get("월급", 0) or 0))
        tax = float(r.get("세금(10%)", 0) or 0)
        desk = int(float(r.get("자리임대료", 50) or 50))
        elec = int(float(r.get("전기세", 10) or 10))
        health = int(float(r.get("건강보험료", 10) or 10))
        tax_rate = 0.1
        if gross > 0 and tax > 0:
            tax_rate = round(tax / gross, 4)

        ref = db.collection("roles").document(role_name)  # ✅ 문서ID=직업명
        batch.set(
            ref,
            {
                "role_name": role_name,
                "description": "",
                "permissions": default_perms(role_name),
                "salary_gross": gross,
                "tax_rate": tax_rate,
                "desk_rent": desk,
                "electric_fee": elec,
                "health_fee": health,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    batch.commit()
    api_list_roles_cached.clear()
    return {"ok": True}

def parse_bank_rate_pdf_text(text: str):
    # 업로드된 금리표 pdf는 텍스트가 "기간 2주/4주..." + 1~10등급 금리 숫자 나열 구조
    # 예: 2주: 8 7 6 ... 3
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    # 기간 행을 찾아 숫자 10개를 매칭
    data = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(\d+)주$", ln)
        if m:
            weeks = int(m.group(1))
            # 다음 10개 숫자 수집
            rates = []
            j = i + 1
            while j < len(lines) and len(rates) < 10:
                if re.match(r"^\d+$", lines[j]):
                    rates.append(int(lines[j]))
                j += 1
            if len(rates) == 10:
                row = {"weeks": weeks}
                for g in range(1, 11):
                    row[f"grade{g}"] = rates[g - 1]
                data.append(row)
    return data

def upsert_bank_rates(admin_pin: str, rate_rows: list[dict]):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if not rate_rows:
        return {"ok": False, "error": "금리 데이터가 없습니다."}
    batch = db.batch()
    for row in rate_rows:
        weeks = int(row.get("weeks", 0) or 0)
        if weeks <= 0:
            continue
        ref = db.collection("bank_products_rates").document(str(weeks))
        batch.set(ref, row, merge=True)
    batch.commit()
    return {"ok": True}

def get_bank_rate(weeks: int, credit_grade: int) -> int:
    # % 정수 반환
    snap = db.collection("bank_products_rates").document(str(int(weeks))).get()
    if not snap.exists:
        return 0
    d = snap.to_dict() or {}
    g = max(1, min(10, int(credit_grade)))
    return int(d.get(f"grade{g}", 0) or 0)

# =========================
# Session init
# =========================
defaults = {
    "logged_in": False,
    "admin_ok": False,
    "login_name": "",
    "login_pin": "",
    "data": {},
    "last_maturity_check": {},
    "tpl_prev": {},
    "delete_confirm": False,
    "bulk_confirm": False,
    "bulk_w_confirm": False,
    "undo_mode": False,
    "tpl_sort_mode": False,
    "tpl_work_ids": [],
    "tpl_mobile_sort_ui": False,
    "tpl_sort_panel_open": False,
    # ✅ (1번) 템플릿 순서정렬 패널 접기/펼치기(기본 접힘)

    # =========================
    # ✅ 통계청(제출물) UI state
    # =========================
    "stat_edit": {},              # {submission_id: {student_id: "X|O|△"}}
    "stat_loaded_sig": "",        # 로드 시그니처(불필요한 초기화 방지)
    "stat_delete_confirm": False, # 삭제 확인
    "stat_tpl_pick_prev": None,   # 템플릿 select 변경 감지
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# Sidebar: 계정 만들기/삭제 + (관리자) 학생 엑셀 샘플 다운로드/일괄 업로드 + PIN 변경
# =========================
with st.sidebar:

    # =========================
    # [학생] 비밀번호 변경 (사이드바 최상단)
    # =========================
    st.header("🔑 [학생] 비밀번호 변경")

    stu_name = st.text_input("이름(계정)", key="stu_pw_name").strip()
    old_pin = st.text_input("기존 비밀번호(4자리)", type="password", key="stu_pw_old").strip()
    new_pin1 = st.text_input("새 비밀번호(4자리)", type="password", key="stu_pw_new1").strip()
    new_pin2 = st.text_input("새 비밀번호(확인)", type="password", key="stu_pw_new2").strip()

    if st.button("비밀번호 변경(학생)", key="stu_pw_change_btn", use_container_width=True):
        if not stu_name:
            st.error("이름(계정)을 입력해 주세요.")
        elif not pin_ok(old_pin):
            st.error("기존 비밀번호는 4자리 숫자여야 해요.")
        elif not pin_ok(new_pin1) or not pin_ok(new_pin2):
            st.error("새 비밀번호는 4자리 숫자여야 해요.")
        elif new_pin1 != new_pin2:
            st.error("새 비밀번호와 확인이 일치하지 않습니다.")
        elif old_pin == new_pin1:
            st.error("새 비밀번호는 기존 비밀번호와 달라야 합니다.")
        else:
            res = api_change_pin_student(stu_name, old_pin, new_pin1)
            if res.get("ok"):
                toast("비밀번호 변경 완료!", icon="✅")
                st.session_state.pop("stu_pw_name", None)
                st.session_state.pop("stu_pw_old", None)
                st.session_state.pop("stu_pw_new1", None)
                st.session_state.pop("stu_pw_new2", None)
                st.rerun()
            else:
                st.error(res.get("error", "비밀번호 변경 실패"))

    st.divider()

    
    st.header("🔐 [관리자] 계정생성 / PIN변경 / 삭제")

    # ✅ 공통 입력(한 블록으로 통합)
    admin_manage_pin = st.text_input("관리자 비밀번호(4자리)", type="password", key="admin_manage_pin").strip()
    manage_name = st.text_input("이름(계정)", key="manage_name").strip()
    manage_pin = st.text_input("비밀번호(4자리 숫자)", type="password", key="manage_pin").strip()

    # ✅ 공통 체크(관리자 비번)
    def _admin_guard():
        if not pin_ok(admin_manage_pin):
            st.error("관리자 비밀번호는 4자리 숫자여야 해요.")
            return False
        if not is_admin_pin(admin_manage_pin):
            st.error("관리자 비밀번호가 틀립니다.")
            return False
        return True

    # ✅ 관리자 강제 PIN 변경 함수(이 블록 안에서만 사용)
    def api_admin_force_change_pin(admin_pin: str, target_name: str, new_pin: str):
        if not is_admin_pin(admin_pin):
            return {"ok": False, "error": "관리자 비밀번호가 틀립니다."}
        target_name = (target_name or "").strip()
        new_pin = (new_pin or "").strip()
        if not target_name:
            return {"ok": False, "error": "대상 이름을 입력해 주세요."}
        if not pin_ok(new_pin):
            return {"ok": False, "error": "새 비밀번호는 4자리 숫자여야 합니다."}

        doc = fs_get_student_doc_by_name(target_name)
        if not doc:
            return {"ok": False, "error": "해당 이름의 계정을 찾지 못했습니다."}

        db.collection("students").document(doc.id).update({"pin": str(new_pin)})
        api_list_accounts_cached.clear()
        return {"ok": True}

    # ✅ 버튼 3개: 생성 / PIN변경 / 삭제
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("계정 생성", key="btn_create", use_container_width=True):
            if not _admin_guard():
                st.stop()
            if not manage_name:
                st.error("이름을 입력해 주세요.")
            elif not pin_ok(manage_pin):
                st.error("비밀번호는 4자리 숫자여야 해요. (예: 0123)")
            else:
                # ✅ 새 계정은 '마지막 번호 + 1'로 저장 (students.no 사용)
                if fs_get_student_doc_by_name(manage_name):
                    st.error("이미 존재하는 계정입니다.")
                else:
                    # 현재 활성 계정 중 최대 번호 찾기
                    cur_docs = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
                    max_no = 0
                    for d in cur_docs:
                        x = d.to_dict() or {}
                        try:
                            n0 = int(x.get("no", 0) or 0)
                            if n0 > max_no:
                                max_no = n0
                        except Exception:
                            pass
                    new_no = int(max_no + 1)

                    # 계정 생성(no 포함)
                    db.collection("students").document().set(
                        {
                            "no": new_no,
                            "name": manage_name,
                            "pin": manage_pin,
                            "balance": 0,
                            "is_active": True,
                            "role_id": "",
                            "io_enabled": True,
                            "invest_enabled": True,
                            "created_at": firestore.SERVER_TIMESTAMP,
                        }
                    )

                    toast(f"계정 생성 완료! (번호 {new_no})", icon="✅")
                    st.session_state.pop("manage_name", None)
                    st.session_state.pop("manage_pin", None)
                    api_list_accounts_cached.clear()
                    st.rerun()

    with c2:
        if st.button("PIN 변경", key="btn_pin_change", use_container_width=True):
            if not _admin_guard():
                st.stop()
            if not manage_name:
                st.error("이름을 입력해 주세요.")
            elif not pin_ok(manage_pin):
                st.error("새 비밀번호는 4자리 숫자여야 해요.")
            else:
                res = api_admin_force_change_pin(admin_manage_pin, manage_name, manage_pin)
                if res.get("ok"):
                    toast("PIN 변경 완료!", icon="🔁")
                    st.session_state.pop("manage_name", None)
                    st.session_state.pop("manage_pin", None)
                    st.rerun()
                else:
                    st.error(res.get("error", "PIN 변경 실패"))


    with c3:
        if st.button("삭제", key="btn_delete", use_container_width=True):
            # ✅ 삭제는 확인창 띄우기
            st.session_state.delete_confirm = True

    # ✅ 삭제 확인
    if st.session_state.get("delete_confirm", False):
        st.warning("정말로 삭제하시겠습니까?")
        y, n = st.columns(2)
        with y:
            if st.button("예", key="delete_yes", use_container_width=True):
                if not _admin_guard():
                    st.stop()
                if not manage_name:
                    st.error("삭제할 이름(계정)을 입력해 주세요.")
                elif not pin_ok(manage_pin):
                    st.error("비밀번호는 4자리 숫자여야 해요.")
                else:
                    # ✅ 여기서는 '해당 계정 PIN'이 아니라, '관리자 PIN'으로 삭제를 허용하려면
                    # api_delete_account가 (이름+PIN) 인증 구조라서 아래처럼 "관리자 강제 삭제"로 바꾸는 게 맞음.
                    # => 기존 api_delete_account는 학생 본인 삭제용 구조이므로, 관리자가 강제 삭제하려면 별도 구현.
                    doc = fs_get_student_doc_by_name(manage_name)
                    if not doc:
                        st.error("해당 이름의 계정을 찾지 못했습니다.")
                    else:
                        db.collection("students").document(doc.id).update({"is_active": False})
                        api_list_accounts_cached.clear()
                        toast("삭제 완료!", icon="🗑️")
                        st.session_state.delete_confirm = False
                        st.session_state.data.pop(manage_name, None)
                        st.session_state.pop("manage_name", None)
                        st.session_state.pop("manage_pin", None)
                        st.rerun()
        with n:
            if st.button("아니오", key="delete_no", use_container_width=True):
                st.session_state.delete_confirm = False
                st.rerun()

    st.divider()

# =========================
# Main: 로그인 (너 코드 방식 유지: form)
# =========================
st.subheader("🔐 로그인")

if not st.session_state.logged_in:
    with st.form("login_form", clear_on_submit=False):
        login_c1, login_c2, login_c3 = st.columns([2, 2, 1])
        with login_c1:
            login_name = st.text_input("이름", key="login_name_input").strip()
        with login_c2:
            login_pin = st.text_input("비밀번호(4자리)", type="password", key="login_pin_input").strip()
        with login_c3:
            login_btn = st.form_submit_button("로그인", use_container_width=True)

    if login_btn:
        if not login_name:
            st.error("이름을 입력해 주세요.")
        elif not pin_ok(login_pin):
            st.error("비밀번호는 4자리 숫자여야 해요.")
        else:
            if is_admin_login(login_name, login_pin):
                st.session_state.admin_ok = True
                st.session_state.logged_in = True
                st.session_state.login_name = ADMIN_NAME
                st.session_state.login_pin = ADMIN_PIN
                toast("관리자 모드 ON", icon="🔓")
                st.rerun()
            else:
                doc = fs_auth_student(login_name, login_pin)
                if not doc:
                    st.error("이름 또는 비밀번호가 틀립니다.")
                else:
                    st.session_state.admin_ok = False
                    st.session_state.logged_in = True
                    st.session_state.login_name = login_name
                    st.session_state.login_pin = login_pin
                    toast("로그인 완료!", icon="✅")
                    st.rerun()

else:
    if st.button("로그아웃", key="logout_btn", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.admin_ok = False
        st.session_state.login_name = ""
        st.session_state.login_pin = ""
        st.session_state.undo_mode = False
        st.rerun()

if not st.session_state.logged_in:
    st.stop()

# =========================
# 로그인 정보/권한
# =========================
is_admin = bool(st.session_state.admin_ok)
login_name = st.session_state.login_name
login_pin = st.session_state.login_pin

my_student_id = None
if not is_admin:
    bal_res = api_get_balance(login_name, login_pin)
    if bal_res.get("ok"):
        my_student_id = bal_res.get("student_id")

my_perms = get_my_permissions(my_student_id, is_admin=is_admin)

# =========================
# (관리자) 학급 시스템 탭 + (학생) 접근 가능한 탭만
# =========================
ALL_TABS = [
    "🏦 내 통장",
    "💼 직업/월급",
    "🏛️ 국세청(국고)",
    "📊 통계청",
    "💳 신용등급",
    "🏦 은행(적금)",
    "📈 투자",
    "🛒 구입/벌금",
    "🗓️ 일정",
    "👥 계정 정보/활성화",
]

def tab_visible(tab_name: str):
    if is_admin:
        return True

    # 학생은 기본 "내 통장" + 일정(읽기)
    if tab_name == "🏦 내 통장":
        return True
    if tab_name == "🗓️ 일정":
        return True

    # 권한별 탭 표시
    if tab_name == "🏛️ 국세청(국고)":
        return can(my_perms, "treasury_read") or can(my_perms, "treasury_write")
    if tab_name == "📊 통계청":
        return can(my_perms, "stats_write")
    if tab_name == "💳 신용등급":
        return can(my_perms, "credit_write")
    if tab_name == "🏦 은행(적금)":
        return can(my_perms, "bank_read") or can(my_perms, "bank_write")

    if tab_name == "📈 투자":
        return True
    if tab_name == "🛒 구입/벌금":
        return True

    # 학생에게 숨김
    if tab_name in ("💼 직업/월급", "👥 계정 정보/활성화"):
        return False

    return False

# -------------------------
# ✅ 탭 구성
# - 관리자: 기존 ALL_TABS(tab_visible) 그대로
# - 학생(개별로그인): "거래/적금/목표" 3개만 표시 (캡쳐 UI)
# -------------------------
if is_admin:
    tabs = [t for t in ALL_TABS if tab_visible(t)]
    tab_objs = st.tabs(tabs)
    tab_map = {name: tab_objs[i] for i, name in enumerate(tabs)}
else:
    # 화면에는 "거래/적금/목표"로 보이지만,
    # 아래 기존 로직(내 통장/은행 탭 코드)을 그대로 재사용하기 위해 tab_map 키는 유지합니다.
    user_tab_labels = ["📝 거래", "💰 적금", "🎯 목표"]
    tab_objs = st.tabs(user_tab_labels)
    tab_map = {
        "🏦 내 통장": tab_objs[0],
        "🏦 은행(적금)": tab_objs[1],
        "🎯 목표": tab_objs[2],
    }
    tabs = list(tab_map.keys())


# =========================
# 1) 🏦 내 통장 (기존 사용자 화면 거의 그대로)
# =========================
def render_tx_table(df_tx: pd.DataFrame):
    if df_tx is None or df_tx.empty:
        st.info("거래 내역이 없어요.")
        return
    view = df_tx.rename(
        columns={
            "created_at_kr": "날짜-시간",
            "memo": "내역",
            "deposit": "입금",
            "withdraw": "출금",
            "balance_after": "총액",
        }
    )
    st.dataframe(
        view[["내역", "입금", "출금", "총액", "날짜-시간"]],
        use_container_width=True,
        hide_index=True,
    )

def refresh_account_data_light(name: str, pin: str, force: bool = False):
    now = datetime.now(KST)
    slot = st.session_state.data.get(name, {})
    last_ts = slot.get("ts")
    if (not force) and last_ts and (now - last_ts).total_seconds() < 2:
        return

    bal_res = api_get_balance(login_name, login_pin)
    if not bal_res.get("ok"):
        st.session_state.data[name] = {"error": bal_res.get("error", "잔액 로드 실패"), "ts": now}
        return

    balance = int(bal_res["balance"])
    student_id = bal_res.get("student_id")
    credit_grade = int(bal_res.get("credit_grade", 0) or 0)

    tx_res = api_get_txs_by_student_id(student_id, limit=300)
    if not tx_res.get("ok"):
        st.session_state.data[name] = {"error": tx_res.get("error", "내역 로드 실패"), "ts": now}
        return

    df_tx = pd.DataFrame(tx_res["rows"])
    if not df_tx.empty:
        df_tx = df_tx.sort_values("created_at_utc", ascending=False)

    st.session_state.data[name] = {
        "df_tx": df_tx,
        "balance": balance,
        "student_id": student_id,
        "ts": now,
        "credit_grade": credit_grade,

    }


# =========================
# 🏦 내 통장 탭
# =========================
if "🏦 내 통장" in tabs:
    with tab_map["🏦 내 통장"]:
        if is_admin:
            st.info("관리자는 ‘내 통장’ 대신 아래 탭에서 학급 전체를 관리합니다.")
        else:
            refresh_account_data_light(login_name, login_pin, force=True)
            slot = st.session_state.data.get(login_name, {})
            if slot.get("error"):
                st.error(slot["error"])
                st.stop()

            df_tx = slot["df_tx"]
            balance = int(slot["balance"])
            student_id = slot.get("student_id")

            st.markdown(f"## 🧾 {login_name} 통장")
            st.markdown(f"#### 통장 잔액: **{balance} 포인트**")

            # ✅ 서브탭 제거: 한 화면에 거래 → 되돌리기 → 내역 순서로 표시(하우스 포인트뱅크 스타일)
            st.subheader("📝 거래 기록(통장에 찍기)")

            memo_u, dep_u, wd_u = render_admin_trade_ui(
                prefix=f"user_trade_{login_name}",
                templates_list=TEMPLATES,
                template_by_display=TEMPLATE_BY_DISPLAY,
            )

            col_btn1, col_btn2 = st.columns([1, 1])

            with col_btn1:
                if st.button("저장", key=f"save_{login_name}", use_container_width=True):
                    memo = str(memo_u or "").strip()
                    deposit = int(dep_u or 0)
                    withdraw = int(wd_u or 0)

                    if not memo:
                        st.error("내역을 입력해 주세요.")
                    elif (deposit > 0 and withdraw > 0) or (deposit == 0 and withdraw == 0):
                        st.error("입금/출금은 둘 중 하나만 입력해 주세요.")
                    else:
                        res = api_add_tx(login_name, login_pin, memo, deposit, withdraw)
                        if res.get("ok"):
                            toast("저장 완료!", icon="✅")

                            new_bal = int(res.get("balance", balance) or balance)
                            st.session_state.data.setdefault(login_name, {})
                            st.session_state.data[login_name]["balance"] = new_bal

                            if student_id:
                                tx_res = api_get_txs_by_student_id(student_id, limit=120)
                                if tx_res.get("ok"):
                                    df_new = pd.DataFrame(tx_res.get("rows", []))
                                    if not df_new.empty:
                                        df_new = df_new.sort_values("created_at_utc", ascending=False)
                                    st.session_state.data[login_name]["df_tx"] = df_new

                            pfx = f"user_trade_{login_name}"
                            st.session_state[f"{pfx}_reset_request"] = True
                            st.rerun()
                        else:
                            st.error(res.get("error", "저장 실패"))

            with col_btn2:
                if st.button("되돌리기(관리자)", key=f"undo_btn_{login_name}", use_container_width=True):
                    st.session_state.undo_mode = not st.session_state.undo_mode

            if st.session_state.undo_mode:
                st.divider()
                st.subheader("↩️ 선택 되돌리기(관리자 전용)")
                admin_pin2 = st.text_input("관리자 PIN 입력", type="password", key=f"undo_admin_pin_{login_name}").strip()

                if df_tx is None or df_tx.empty:
                    st.info("거래 내역이 없어요.")
                else:
                    view_df = df_tx.head(50).copy()

                    def _can_rollback_row(row):
                        if str(row.get("type", "")) == "rollback":
                            return False
                        if _is_savings_memo(row.get("memo", "")) or str(row.get("type", "")) in ("maturity",):
                            return False
                        return True

                    view_df["가능"] = view_df.apply(_can_rollback_row, axis=1)
                    st.caption("✅ 체크한 항목만 되돌립니다. (이미 되돌림/적금은 제외)")

                    selected_ids = []
                    for _, r in view_df.iterrows():
                        tx_id = r["tx_id"]
                        label = f"{r['created_at_kr']} | {r['memo']} | +{int(r['deposit'])} / -{int(r['withdraw'])}"
                        ck = st.checkbox(label, key=f"rb_ck_{login_name}_{tx_id}", disabled=(not bool(r["가능"])))
                        if ck and bool(r["가능"]):
                            selected_ids.append(tx_id)

                    if st.button("선택 항목 되돌리기", key=f"do_rb_{login_name}", use_container_width=True):
                        if not is_admin_pin(admin_pin2):
                            st.error("관리자 PIN이 틀립니다.")
                        elif not selected_ids:
                            st.warning("체크된 항목이 없어요.")
                        else:
                            res2 = api_admin_rollback_selected(admin_pin2, student_id, selected_ids)
                            if res2.get("ok"):
                                toast(f"선택 {res2.get('undone')}건 되돌림 완료", icon="↩️")
                                tx_res2 = api_get_txs_by_student_id(student_id, limit=120)
                                if tx_res2.get("ok"):
                                    df_new2 = pd.DataFrame(tx_res2.get("rows", []))
                                    if not df_new2.empty:
                                        df_new2 = df_new2.sort_values("created_at_utc", ascending=False)
                                    st.session_state.data[login_name]["df_tx"] = df_new2

                                bal_res2 = api_get_balance(login_name, login_pin)
                                if bal_res2.get("ok"):
                                    st.session_state.data[login_name]["balance"] = int(bal_res2.get("balance", 0) or 0)

                                st.session_state.undo_mode = False
                                st.rerun()
                            else:
                                st.error(res2.get("error", "되돌리기 실패"))

            st.divider()
            st.subheader("📒 통장 내역(최신순)")
            render_tx_table(df_tx)

# =========================
# 👥 계정 정보/활성화 (관리자 전용)
# =========================
if "👥 계정 정보/활성화" in tabs:
    with tab_map["👥 계정 정보/활성화"]:
        st.subheader("📋 계정정보 / 활성화 관리")

        if not is_admin:
            st.error("관리자 전용 탭입니다.")
            st.stop()

        # -------------------------------------------------
        # ✅ (탭 상단) 엑셀 일괄 계정 추가 + 샘플 다운로드
        #   - 사이드바가 아니라 이 탭 본문 최상단에 표시
        # -------------------------------------------------
        st.markdown("### 📥 일괄 엑셀 계정 추가")
        st.caption("엑셀을 올리면 아래 리스트(학생 표)에 바로 반영됩니다.")

        # ✅ 샘플 다운로드
        import io
        sample_df = pd.DataFrame(
            [
                {"번호": 1, "이름": "홍길동", "비밀번호": "1234", "입출금활성화": True, "투자활성화": True},
                {"번호": 2, "이름": "김철수", "비밀번호": "2345", "입출금활성화": True, "투자활성화": False},
            ]
        )
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            sample_df.to_excel(writer, index=False, sheet_name="accounts")
        st.download_button(
            "📄 샘플 엑셀 다운로드",
            data=bio.getvalue(),
            file_name="accounts_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="acc_bulk_sample_down",
        )

        up = st.file_uploader("📤 엑셀 업로드(xlsx)", type=["xlsx"], key="acc_bulk_upl")

        if st.button("엑셀 일괄 등록 실행", use_container_width=True, key="acc_bulk_run"):
            if not up:
                st.warning("엑셀 파일을 업로드하세요.")
            else:
                try:
                    df_up = pd.read_excel(up)
                    need_cols = {"번호", "이름", "비밀번호"}
                    if not need_cols.issubset(set(df_up.columns)):
                        st.error("엑셀 컬럼이 부족합니다. 최소: 번호, 이름, 비밀번호")
                        st.stop()

                    # 활성화 컬럼이 없으면 기본 True
                    if "입출금활성화" not in df_up.columns:
                        df_up["입출금활성화"] = True
                    if "투자활성화" not in df_up.columns:
                        df_up["투자활성화"] = True

                    # 현재 active 학생들 맵(번호->docid, 이름->docid)
                    cur_docs = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
                    by_no = {}
                    by_name = {}
                    for d in cur_docs:
                        x = d.to_dict() or {}
                        no0 = x.get("no")
                        nm0 = str(x.get("name", "") or "").strip()
                        if isinstance(no0, (int, float)) and str(no0) != "nan":
                            by_no[int(no0)] = d.id
                        if nm0:
                            by_name[nm0] = d.id

                    created, updated, skipped = 0, 0, 0

                    for _, r in df_up.iterrows():
                        try:
                            no = int(r.get("번호"))
                        except Exception:
                            skipped += 1
                            continue

                        name = str(r.get("이름", "") or "").strip()
                        pin = str(r.get("비밀번호", "") or "").strip()

                        if not name or not pin_ok(pin):
                            skipped += 1
                            continue

                        io_ok = bool(r.get("입출금활성화", True))
                        inv_ok = bool(r.get("투자활성화", True))

                        payload = {
                            "no": int(no),
                            "name": name,
                            "pin": pin,
                            "is_active": True,
                            "io_enabled": io_ok,
                            "invest_enabled": inv_ok,
                        }

                        # ✅ 번호 우선 업데이트, 없으면 이름으로 업데이트, 없으면 신규 생성
                        if int(no) in by_no:
                            db.collection("students").document(by_no[int(no)]).update(payload)
                            updated += 1
                        elif name in by_name:
                            db.collection("students").document(by_name[name]).update(payload)
                            updated += 1
                        else:
                            db.collection("students").document().set(
                                {
                                    **payload,
                                    "balance": 0,
                                    "role_id": "",
                                    "created_at": firestore.SERVER_TIMESTAMP,
                                }
                            )
                            created += 1

                    api_list_accounts_cached.clear()
                    toast(f"엑셀 등록 완료 (신규 {created} / 수정 {updated} / 제외 {skipped})", icon="📥")
                    st.rerun()

                except Exception as e:
                    st.error(f"엑셀 처리 실패: {e}")

        st.divider()

        # -------------------------------------------------
        # ✅ 학생 리스트 로드 (번호=엑셀 번호, 그 순서대로 정렬)
        #   - student_id 컬럼은 화면에서 제거(내부로만 유지)
        # -------------------------------------------------
        docs = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()

        rows = []
        for d in docs:
            x = d.to_dict() or {}
            # 엑셀 번호를 의미하는 "no"를 사용 (없으면 큰 값으로 뒤로)
            no = x.get("no", 999999)
            try:
                no = int(no)
            except Exception:
                no = 999999

            rows.append(
                {
                    "_sid": d.id,  # 내부용(삭제할 때만 사용) -> 화면에는 안 보이게 처리
                    "선택": False,
                    "번호": no,
                    "이름": x.get("name", ""),
                    "비밀번호": x.get("pin", ""),
                    "입출금활성화": bool(x.get("io_enabled", True)),
                    "투자활성화": bool(x.get("invest_enabled", True)),
                }
            )

        df_all = pd.DataFrame(rows)
        if not df_all.empty:
            df_all = df_all.sort_values(["번호", "이름"], ascending=[True, True], kind="mergesort").reset_index(drop=True)

        # ✅ account_df 세션 초기화 (없으면 생성)
        if "account_df" not in st.session_state:
            st.session_state.account_df = df_all.copy()
        
        # -------------------------------------------------
        # ✅ 상단 버튼(2줄): [전체선택/전체해제/계정삭제] + [입출금/투자 일괄]
        # -------------------------------------------------
        st.markdown("#### 🧰 일괄 관리")

        # 1줄: 전체 선택/해제/삭제
        r1c1, r1c2, r1c3 = st.columns(3)

        with r1c1:
            if st.button("✅ 전체 선택", use_container_width=True, key="acc_select_all"):
                st.session_state.account_df["선택"] = True
                st.rerun()

        with r1c2:
            if st.button("⬜ 전체 해제", use_container_width=True, key="acc_unselect_all"):
                st.session_state.account_df["선택"] = False
                st.rerun()

        with r1c3:
            if st.button("🗑️ 계정 삭제(선택)", use_container_width=True, key="acc_del_top"):
                sel = st.session_state.account_df[st.session_state.account_df["선택"] == True]
                if sel.empty:
                    st.warning("삭제할 계정을 체크하세요.")
                else:
                    st.session_state._delete_targets = sel["_sid"].tolist()

        # 2줄: 입출금/투자 일괄 켜기/끄기
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)

        with r2c1:
            if st.button("🔌 입출금 켜기", use_container_width=True, key="io_all_on"):
                if "입출금활성화" in st.session_state.account_df.columns:
                    st.session_state.account_df["입출금활성화"] = True
                st.rerun()

        with r2c2:
            if st.button("⛔ 입출금 끄기", use_container_width=True, key="io_all_off"):
                if "입출금활성화" in st.session_state.account_df.columns:
                    st.session_state.account_df["입출금활성화"] = False
                st.rerun()

        with r2c3:
            if st.button("📈 투자 켜기", use_container_width=True, key="inv_all_on"):
                if "투자활성화" in st.session_state.account_df.columns:
                    st.session_state.account_df["투자활성화"] = True
                st.rerun()

        with r2c4:
            if st.button("📉 투자 끄기", use_container_width=True, key="inv_all_off"):
                if "투자활성화" in st.session_state.account_df.columns:
                    st.session_state.account_df["투자활성화"] = False
                st.rerun()

        # 삭제 확인
        if "_delete_targets" in st.session_state:
            st.warning("정말 삭제하시겠습니까?")
            y, n = st.columns(2)
            with y:
                if st.button("예", key="acc_del_yes2", use_container_width=True):
                    for sid in st.session_state._delete_targets:
                        db.collection("students").document(sid).update({"is_active": False})
                    st.session_state.pop("_delete_targets")
                    api_list_accounts_cached.clear()
                    toast("삭제 완료", icon="🗑️")
                    # ✅ 삭제 후 리스트 즉시 반영
                    st.session_state.pop("account_df", None)
                    st.rerun()
            with n:
                if st.button("아니오", key="acc_del_no2", use_container_width=True):
                    st.session_state.pop("_delete_targets")
                    st.rerun()

        # -------------------------------------------------
        # ✅ 표(편집): student_id 컬럼은 화면에서 제거
        #   - 체크박스 클릭해도 번호순이 유지되도록 mergesort + 세션 df 유지
        #   - '회색 하이라이트'는 data_editor가 직접 지원이 어려워서,
        #     선택 행을 아래에 '회색 강조 미리보기'로 추가 표시(대신 확실히 보임)
        # -------------------------------------------------
        show_df = st.session_state.account_df.drop(columns=["_sid"], errors="ignore")

        # ✅ 표 높이: 화면에 최대한 크게(표 안 스크롤 최소화)
        # - row_height는 Streamlit 버전에 따라 무시될 수 있음(무시돼도 문제 없음)
        # - height는 가장 확실하게 적용됨
        # - 계정이 많으면 너무 길어질 수 있어서 "최대 900" 같은 캡을 둠
        row_h = 35
        try:
            nrows = int(len(show_df)) + 2
        except Exception:
            nrows = 20
        desired_h = min(900, max(420, nrows * row_h))

        edited_view = st.data_editor(
            show_df,
            use_container_width=True,
            hide_index=True,
            height=desired_h,
            key="account_editor",
            column_config={
                "선택": st.column_config.CheckboxColumn(),
                "입출금활성화": st.column_config.CheckboxColumn(),
                "투자활성화": st.column_config.CheckboxColumn(),
            },
        )


        # ✅ editor 결과를 내부 df에 다시 합치기(_sid 유지)
        #    (행 순서 고정: 번호 기준으로 다시 정렬해서 '체크하면 아래로 내려감' 현상 최소화)
        if not df_all.empty and edited_view is not None:
            tmp = st.session_state.account_df.copy()
            for col in ["선택", "번호", "이름", "비밀번호", "입출금활성화", "투자활성화"]:
                if col in edited_view.columns and col in tmp.columns:
                    tmp[col] = edited_view[col].values
            tmp = tmp.sort_values(["번호", "이름"], ascending=[True, True], kind="mergesort").reset_index(drop=True)
            st.session_state.account_df = tmp

# =========================
# 3) 💼 직업/월급 (관리자 중심, 학생은 읽기만)
# =========================
if "💼 직업/월급" in tabs:
    with tab_map["💼 직업/월급"]:
        st.subheader("💼 직업/월급 시스템")

        if not is_admin:
            st.info("관리자 전용 탭입니다.")
            st.stop()

        # -------------------------------------------------
        # ✅ 계정 목록(드롭다운: 번호+이름)
        # -------------------------------------------------
        accounts = api_list_accounts_cached().get("accounts", [])
        # students 컬렉션에서 'no'도 같이 가져와서 "번호+이름" 만들기
        docs_acc = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
        acc_rows = []
        for d in docs_acc:
            x = d.to_dict() or {}
            try:
                no = int(x.get("no", 999999) or 999999)
            except Exception:
                no = 999999
            acc_rows.append(
                {
                    "student_id": d.id,
                    "no": no,
                    "name": str(x.get("name", "") or ""),
                }
            )
        acc_rows.sort(key=lambda r: (r["no"], r["name"]))
        acc_options = ["(선택 없음)"] + [f"{r['no']} {r['name']}" for r in acc_rows]
        label_to_id = {f"{r['no']} {r['name']}": r["student_id"] for r in acc_rows}
        id_to_label = {r["student_id"]: f"{r['no']} {r['name']}" for r in acc_rows}

        # -------------------------------------------------
        # ✅ 공제 설정(세금% / 자리임대료 / 전기세 / 건강보험료)
        #   - Firestore config/salary_deductions 에 저장
        # -------------------------------------------------
        def _get_salary_cfg():
            ref = db.collection("config").document("salary_deductions")
            snap = ref.get()
            if not snap.exists:
                return {
                    "tax_percent": 10.0,
                    "desk_rent": 50,
                    "electric_fee": 10,
                    "health_fee": 10,
                }
            d = snap.to_dict() or {}
            return {
                "tax_percent": float(d.get("tax_percent", 10.0) or 10.0),
                "desk_rent": int(d.get("desk_rent", 50) or 50),
                "electric_fee": int(d.get("electric_fee", 10) or 10),
                "health_fee": int(d.get("health_fee", 10) or 10),
            }

        def _save_salary_cfg(cfg: dict):
            db.collection("config").document("salary_deductions").set(
                {
                    "tax_percent": float(cfg.get("tax_percent", 10.0) or 10.0),
                    "desk_rent": int(cfg.get("desk_rent", 50) or 50),
                    "electric_fee": int(cfg.get("electric_fee", 10) or 10),
                    "health_fee": int(cfg.get("health_fee", 10) or 10),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        def _calc_net(gross: int, cfg: dict) -> int:
            gross = int(gross or 0)
            tax_percent = float(cfg.get("tax_percent", 10.0) or 10.0)
            desk = int(cfg.get("desk_rent", 50) or 50)
            elec = int(cfg.get("electric_fee", 10) or 10)
            health = int(cfg.get("health_fee", 10) or 10)

            tax = int(round(gross * (tax_percent / 100.0)))
            net = gross - tax - desk - elec - health
            return max(0, int(net))

        cfg = _get_salary_cfg()

        with st.expander("⚙️ 실수령액 계산식(공제 설정) 변경", expanded=False):
            c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1, 1.2])
            with c1:
                tax_percent = st.number_input("세금(%)", min_value=0.0, max_value=100.0, step=0.5, value=float(cfg["tax_percent"]), key="sal_cfg_tax")
            with c2:
                desk_rent = st.number_input("자리임대료", min_value=0, step=1, value=int(cfg["desk_rent"]), key="sal_cfg_desk")
            with c3:
                electric_fee = st.number_input("전기세", min_value=0, step=1, value=int(cfg["electric_fee"]), key="sal_cfg_elec")
            with c4:
                health_fee = st.number_input("건강보험료", min_value=0, step=1, value=int(cfg["health_fee"]), key="sal_cfg_health")
            with c5:
                if st.button("✅ 공제 설정 저장", use_container_width=True, key="sal_cfg_save"):
                    _save_salary_cfg(
                        {
                            "tax_percent": tax_percent,
                            "desk_rent": desk_rent,
                            "electric_fee": electric_fee,
                            "health_fee": health_fee,
                        }
                    )
                    toast("공제 설정 저장 완료!", icon="✅")
                    st.rerun()

                # -------------------------------------------------
        # ✅ 월급 지급 설정(자동/수동)
        #  - config/salary_payroll : pay_day(1~31), auto_enabled(bool)
        #  - payroll_log/{YYYY-MM}_{student_id} 로 "이번달 지급 여부" 기록
        # -------------------------------------------------
        def _get_payroll_cfg():
            ref = db.collection("config").document("salary_payroll")
            snap = ref.get()
            if not snap.exists:
                return {"pay_day": 25, "auto_enabled": False}
            d = snap.to_dict() or {}
            return {
                "pay_day": int(d.get("pay_day", 25) or 25),
                "auto_enabled": bool(d.get("auto_enabled", False)),
            }

        def _save_payroll_cfg(cfg2: dict):
            db.collection("config").document("salary_payroll").set(
                {
                    "pay_day": int(cfg2.get("pay_day", 25) or 25),
                    "auto_enabled": bool(cfg2.get("auto_enabled", False)),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        def _month_key(dt: datetime) -> str:
            return f"{dt.year:04d}-{dt.month:02d}"

        def _paylog_id(month_key: str, student_id: str) -> str:
            return f"{month_key}_{student_id}"

        def _already_paid_this_month(month_key: str, student_id: str) -> bool:
            snap = db.collection("payroll_log").document(_paylog_id(month_key, student_id)).get()
            return bool(snap.exists)

        def _write_paylog(month_key: str, student_id: str, amount: int, job_name: str, method: str):
            db.collection("payroll_log").document(_paylog_id(month_key, student_id)).set(
                {
                    "month": month_key,
                    "student_id": student_id,
                    "amount": int(amount),
                    "job": str(job_name or ""),
                    "method": str(method or ""),  # "auto" / "manual"
                    "paid_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        def _pay_one_student(student_id: str, amount: int, memo: str):
            # 관리자 지급으로 통장 입금(+)
            return api_admin_add_tx_by_student_id(
                admin_pin=ADMIN_PIN,
                student_id=student_id,
                memo=memo,
                deposit=int(amount),
                withdraw=0,
            )

        def _run_auto_payroll_if_due(cfg_pay: dict):
            # ✅ 자동지급: 매월 지정일에만 실행
            if not bool(cfg_pay.get("auto_enabled", False)):
                return

            now = datetime.now(KST)
            pay_day = int(cfg_pay.get("pay_day", 25) or 25)
            pay_day = max(1, min(31, pay_day))

            if int(now.day) != pay_day:
                return

            mkey = _month_key(now)

            # 학생 id -> 이름 맵 (메모용)
            accs = api_list_accounts_cached().get("accounts", []) or []
            id_to_name = {a.get("student_id"): a.get("name") for a in accs if a.get("student_id")}

            # job_salary 기준으로 배정된 학생들에게 지급
            q = db.collection("job_salary").order_by("order").stream()
            paid_cnt, skip_cnt, err_cnt = 0, 0, 0

            for d in q:
                x = d.to_dict() or {}
                job_name = str(x.get("job", "") or "")
                gross = int(x.get("salary", 0) or 0)
                net_amt = int(_calc_net(gross, cfg) or 0)
                assigned_ids = list(x.get("assigned_ids", []) or [])

                if net_amt <= 0:
                    continue

                for sid in assigned_ids:
                    sid = str(sid or "").strip()
                    if not sid:
                        continue

                    # ✅ 이번 달에 수동/자동 지급 기록이 있으면 자동 지급은 패스
                    if _already_paid_this_month(mkey, sid):
                        skip_cnt += 1
                        continue

                    nm = id_to_name.get(sid, "")
                    memo = f"월급 자동지급({mkey}) {job_name}" + (f" - {nm}" if nm else "")
                    res = _pay_one_student(sid, net_amt, memo)
                                        # ✅ (국고 세입) 월급 공제액을 국고로 입금
                    deduction = int(max(0, gross - net_amt))
                    if deduction > 0:
                        api_add_treasury_tx(
                            admin_pin=ADMIN_PIN,
                            memo=f"월급 공제 세입({mkey}) {job_name}",
                            income=deduction,
                            expense=0,
                            actor="system_salary",
                        )
                    if res.get("ok"):
                        _write_paylog(mkey, sid, net_amt, job_name, method="auto")
                        paid_cnt += 1
                    else:
                        err_cnt += 1

            # 자동지급 결과는 너무 시끄럽지 않게 토스트 1번만
            if paid_cnt > 0:
                toast(f"월급 자동지급 완료: {paid_cnt}명(패스 {skip_cnt})", icon="💸")
                api_list_accounts_cached.clear()
            elif err_cnt > 0:
                st.warning("월급 자동지급 중 일부 오류가 있었어요. (로그 확인)")

        payroll_cfg = _get_payroll_cfg()

        # ✅ 자동지급 조건이면 즉시 한번 실행(해당 날짜일 때만 실제 지급됨)
        _run_auto_payroll_if_due(payroll_cfg)

        with st.expander("💸 월급 지급 설정", expanded=False):
            cc1, cc2, cc3 = st.columns([1.4, 1.2, 1.4])

            with cc1:
                pay_day_in = st.number_input(
                    "월급 지급 날짜 지정: 매월 (일)",
                    min_value=1,
                    max_value=31,
                    step=1,
                    value=int(payroll_cfg.get("pay_day", 25) or 25),
                    key="payroll_day_in",
                )

            with cc2:
                auto_on = st.checkbox(
                    "자동지급",
                    value=bool(payroll_cfg.get("auto_enabled", False)),
                    key="payroll_auto_on",
                    help="해당 날짜에 매월, 학생의 직업 실수령액 기준으로 자동 지급합니다.\n이미 이번 달에 수동지급을 했으면 자동지급은 그 달에는 패스됩니다.",
                )

            with cc3:
                if st.button("✅ 지급 설정 저장", use_container_width=True, key="payroll_save_cfg"):
                    _save_payroll_cfg({"pay_day": int(pay_day_in), "auto_enabled": bool(auto_on)})
                    toast("월급 지급 설정 저장 완료!", icon="✅")
                    st.rerun()

            st.caption("• 수동지급: 이번 달(현재 월)에 즉시 지급합니다. 이미 지급한 기록이 있으면 확인 후 재지급합니다.")

            # -------------------------
            # 수동지급 버튼 + 이미 지급 여부 확인(이번 달)
            # -------------------------
            now = datetime.now(KST)
            cur_mkey = _month_key(now)

            # 이번 달에 지급된 로그가 있는지 빠르게 확인
            # (수동지급은 '모든 배정 학생' 대상으로 동일 로직)
            q2 = db.collection("job_salary").order_by("order").stream()
            targets = []  # (student_id, amount, job_name)
            for d in q2:
                x = d.to_dict() or {}
                job_name = str(x.get("job", "") or "")
                gross = int(x.get("salary", 0) or 0)
                net_amt = int(_calc_net(gross, cfg) or 0)
                if net_amt <= 0:
                    continue
                for sid in list(x.get("assigned_ids", []) or []):
                    sid = str(sid or "").strip()
                    if sid:
                        targets.append((sid, net_amt, job_name, gross))

            # 중복 학생(여러 직업에 배정되는 경우) 방지: 마지막 것만 남김
            dedup = {}
            for sid, amt, jb, gross in targets:
                dedup[sid] = (amt, jb, gross)
            targets = [(sid, v[0], v[1], v[2]) for sid, v in dedup.items()]

            already_any = any(_already_paid_this_month(cur_mkey, sid) for sid, *_ in targets)

            if st.button("💸 수동지급(이번 달 즉시 지급)", use_container_width=True, key="payroll_manual_btn"):
                # 이미 지급된 적 있으면 확인창 띄우기
                if already_any:
                    st.session_state["payroll_manual_confirm"] = True
                else:
                    st.session_state["payroll_manual_confirm"] = False
                    st.session_state["payroll_manual_do"] = True
                st.rerun()

            if st.session_state.get("payroll_manual_confirm", False):
                st.warning("이번 달에 이미 월급 지급(자동/수동)한 기록이 있습니다. 그래도 지급하시겠습니까?")
                y1, n1 = st.columns(2)
                with y1:
                    if st.button("예", use_container_width=True, key="payroll_manual_yes"):
                        st.session_state["payroll_manual_confirm"] = False
                        st.session_state["payroll_manual_do"] = True
                        st.rerun()
                with n1:
                    if st.button("아니오", use_container_width=True, key="payroll_manual_no"):
                        st.session_state["payroll_manual_confirm"] = False
                        st.session_state["payroll_manual_do"] = False
                        toast("수동지급 취소", icon="🛑")
                        st.rerun()

            # 실제 수동지급 실행(1회)
            if st.session_state.get("payroll_manual_do", False):
                st.session_state["payroll_manual_do"] = False

                accs2 = api_list_accounts_cached().get("accounts", []) or []
                id_to_name2 = {a.get("student_id"): a.get("name") for a in accs2 if a.get("student_id")}

                paid_cnt, err_cnt = 0, 0
                for sid, amt, jb, gross in targets:
                    nm = id_to_name2.get(sid, "")
                    memo = f"월급 수동지급({cur_mkey}) {jb}" + (f" - {nm}" if nm else "")
                    res = _pay_one_student(sid, int(amt), memo)
                    # ✅ (국고 세입) 월급 공제액을 국고로 입금
                    deduction = int(max(0, int(gross) - int(amt))) if "gross" in locals() else 0
                    if deduction > 0:
                        api_add_treasury_tx(
                            admin_pin=ADMIN_PIN,
                            memo=f"월급 공제 세입({cur_mkey}) {jb}",
                            income=deduction,
                            expense=0,
                            actor="system_salary",
                        )

                    if res.get("ok"):
                        # ✅ 수동지급도 이번달 지급 기록 남김(자동 패스 조건 충족)
                        _write_paylog(cur_mkey, sid, int(amt), jb, method="manual")
                        paid_cnt += 1
                    else:
                        err_cnt += 1

                api_list_accounts_cached.clear()
                if paid_cnt > 0:
                    toast(f"월급 수동지급 완료: {paid_cnt}명", icon="💸")
                if err_cnt > 0:
                    st.warning(f"일부 지급 실패가 있었어요: {err_cnt}건")
                st.rerun()

        # -------------------------------------------------
        # ✅ 직업/월급 표 데이터 로드 (job_salary 컬렉션)
        # -------------------------------------------------
        def _list_job_rows():
            q = db.collection("job_salary").order_by("order").stream()
            rows = []
            for d in q:
                x = d.to_dict() or {}
                rows.append(
                    {
                        "_id": d.id,
                        "order": int(x.get("order", 999999) or 999999),
                        "job": str(x.get("job", "") or ""),
                        "salary": int(x.get("salary", 0) or 0),
                        "student_count": int(x.get("student_count", 1) or 1),
                        "assigned_ids": list(x.get("assigned_ids", []) or []),
                    }
                )
            rows.sort(key=lambda r: r["order"])
            return rows

        def _next_order(rows):
            if not rows:
                return 1
            return int(max(r["order"] for r in rows) + 1)

        def _swap_order(a_id, a_order, b_id, b_order):
            batch = db.batch()
            batch.update(db.collection("job_salary").document(a_id), {"order": int(b_order)})
            batch.update(db.collection("job_salary").document(b_id), {"order": int(a_order)})
            batch.commit()

        rows = _list_job_rows()

        # -------------------------------------------------
        # ✅ 직업/월급 목록
        # -------------------------------------------------
        st.markdown("### 📋 직업/월급 목록")
        st.caption("• 아래에 직업을 추가/수정하면 이 리스트에 반영됩니다. • 체크 후 ⬆️⬇️🗑️ 버튼으로 순서 이동/삭제가 됩니다.")

        # -------------------------
        # ✅ 선택(체크박스) 세션 상태 준비 (버튼보다 먼저!)
        # -------------------------
        if "job_sel" not in st.session_state:
            st.session_state.job_sel = {}

        current_ids = [rr["_id"] for rr in rows]
        for rid0 in current_ids:
            st.session_state.job_sel.setdefault(rid0, False)
        for rid0 in list(st.session_state.job_sel.keys()):
            if rid0 not in current_ids:
                st.session_state.job_sel.pop(rid0, None)

        def _selected_job_ids():
            return [rid0 for rid0 in current_ids if bool(st.session_state.job_sel.get(rid0, False))]

        # -------------------------
        # ✅ 일괄 순서 이동
        # -------------------------
        def _bulk_move(direction: str):
            sel_ids = _selected_job_ids()
            if not sel_ids:
                st.warning("먼저 체크(선택)하세요.")
                return

            # 최신 rows 다시 읽기(순서 꼬임 방지)
            _rows = _list_job_rows()
            if not _rows:
                return

            # id -> index 빠른 조회
            id_to_idx = {r["_id"]: i for i, r in enumerate(_rows)}
            selected = set([sid for sid in sel_ids if sid in id_to_idx])

            if not selected:
                st.warning("선택된 항목을 찾지 못했어요.")
                return

            # 위로: 앞에서부터 스캔하며 '선택'이 '비선택' 앞에 있으면 swap
            # 아래로: 뒤에서부터 스캔
            if direction == "up":
                scan = range(len(_rows))
                step = -1
            else:
                scan = range(len(_rows) - 1, -1, -1)
                step = 1

            batch = db.batch()
            swapped = 0

            for i in scan:
                cur = _rows[i]
                cur_id = cur["_id"]
                if cur_id not in selected:
                    continue

                j = i + step
                if j < 0 or j >= len(_rows):
                    continue

                prev = _rows[j]
                prev_id = prev["_id"]

                # 선택끼리는 묶어서 이동(선택과 비선택 사이만 swap)
                if prev_id in selected:
                    continue

                # order swap
                a_id, a_order = cur_id, int(cur.get("order", 999999) or 999999)
                b_id, b_order = prev_id, int(prev.get("order", 999999) or 999999)

                batch.update(db.collection("job_salary").document(a_id), {"order": b_order})
                batch.update(db.collection("job_salary").document(b_id), {"order": a_order})

                # 로컬 리스트에서도 swap 반영(연쇄 이동 안정)
                _rows[i], _rows[j] = _rows[j], _rows[i]
                swapped += 1

            if swapped > 0:
                batch.commit()
                toast("순서 이동 완료!", icon="✅")
            else:
                st.info("더 이동할 수 없습니다.")

        # -------------------------
        # ✅ 일괄 삭제 준비(확인창 띄우기)
        # -------------------------
        def _bulk_delete_prepare():
            sel_ids = _selected_job_ids()
            if not sel_ids:
                st.warning("삭제할 항목을 체크하세요.")
                return
            st.session_state["_job_bulk_delete_ids"] = sel_ids

        # -------------------------
        # ✅ 상단 버튼(⬆️⬇️🗑️)
        # -------------------------
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("⬆️", use_container_width=True, key="job_bulk_up"):
                _bulk_move("up")
                st.rerun()
        with btn2:
            if st.button("⬇️", use_container_width=True, key="job_bulk_dn"):
                _bulk_move("down")
                st.rerun()
        with btn3:
            if st.button("🗑️", use_container_width=True, key="job_bulk_del"):
                _bulk_delete_prepare()
                st.rerun()

        # -------------------------
        # ✅ 일괄 삭제 확인
        # -------------------------
        if "_job_bulk_delete_ids" in st.session_state:
            st.warning("체크된 직업을 삭제하시겠습니까?")
            y, n = st.columns(2)
            with y:
                if st.button("예", key="job_bulk_del_yes", use_container_width=True):
                    del_ids = list(st.session_state.get("_job_bulk_delete_ids", []))
                    for rid0 in del_ids:
                        db.collection("job_salary").document(rid0).delete()
                        st.session_state.job_sel.pop(rid0, None)
                    st.session_state.pop("_job_bulk_delete_ids", None)
                    toast("삭제 완료", icon="🗑️")
                    st.rerun()
            with n:
                if st.button("아니오", key="job_bulk_del_no", use_container_width=True):
                    st.session_state.pop("_job_bulk_delete_ids", None)
                    st.rerun()

        # -------------------------------------------------
        # ✅ 열 제목(헤더) - 내용 columns 비율과 동일하게 맞춰 정렬
        # -------------------------------------------------
        st.markdown(
            """
            <style>
            .jobhdr { font-weight: 900; color:#111; padding: 6px 4px; }
            .jobhdr-center { display:flex; align-items:center; justify-content:center; }
            .jobhdr-left { display:flex; align-items:center; justify-content:flex-start; }
            .jobhdr-line { border-bottom: 2px solid #ddd; margin: 6px 0 10px 0; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        hdr = st.columns([1.1, 2.2, 1.1, 1.2, 1.4, 4.0])
        with hdr[0]:
            st.markdown("<div class='jobhdr jobhdr-center'>선택/순</div>", unsafe_allow_html=True)
        with hdr[1]:
            st.markdown("<div class='jobhdr jobhdr-left'>직업</div>", unsafe_allow_html=True)
        with hdr[2]:
            st.markdown("<div class='jobhdr jobhdr-center'>월급</div>", unsafe_allow_html=True)
        with hdr[3]:
            st.markdown("<div class='jobhdr jobhdr-center'>실수령</div>", unsafe_allow_html=True)
        with hdr[4]:
            st.markdown("<div class='jobhdr jobhdr-center'>학생수</div>", unsafe_allow_html=True)
        with hdr[5]:
            st.markdown("<div class='jobhdr jobhdr-left'>배정 계정</div>", unsafe_allow_html=True)

        st.markdown("<div class='jobhdr-line'></div>", unsafe_allow_html=True)

        for i, r in enumerate(rows):
            rid = r["_id"]
            order = int(r["order"])
            job = r["job"]
            salary = int(r["salary"])
            cnt = max(0, int(r.get("student_count", 1) or 1))
            assigned_ids = list(r.get("assigned_ids", []) or [])

            # assigned 길이를 student_count에 맞추기 (cnt=0이면 빈 리스트)
            if cnt == 0:
                assigned_ids = []
            else:
                if len(assigned_ids) < cnt:
                    assigned_ids = assigned_ids + [""] * (cnt - len(assigned_ids))
                if len(assigned_ids) > cnt:
                    assigned_ids = assigned_ids[:cnt]

            net = _calc_net(salary, cfg)

            rowc = st.columns([0.8, 1.0, 2.6, 1.3, 1.3, 1.6, 4.0])

            # ✅ 선택 체크
            with rowc[0]:
                st.session_state.job_sel[rid] = st.checkbox(
                    "",
                    value=bool(st.session_state.job_sel.get(rid, False)),
                    key=f"job_sel_{rid}",
                    label_visibility="collapsed",
                )

            # ✅ 순
            with rowc[1]:
                st.markdown(f"<div style='text-align:center;font-weight:900'>{order}</div>", unsafe_allow_html=True)

            # ✅ 직업
            with rowc[2]:
                st.markdown(f"<div style='font-weight:900'>{job}</div>", unsafe_allow_html=True)

            # ✅ 월급
            with rowc[3]:
                st.markdown(f"<div style='text-align:center;font-weight:900'>{salary}</div>", unsafe_allow_html=True)

            # ✅ 실수령
            with rowc[4]:
                st.markdown(f"<div style='text-align:center;font-weight:900'>{net}</div>", unsafe_allow_html=True)

            # ✅ 학생수 +/- (기존 로직 그대로)
            with rowc[5]:
                st.markdown("<div class='jobcnt-wrap'>", unsafe_allow_html=True)
                a1, a2, a3 = st.columns([0.9, 1.0, 0.9])

                with a1:
                    if st.button("➖", key=f"job_cnt_minus_{rid}"):
                        new_cnt = max(0, cnt - 1)
                        new_assigned = assigned_ids[:new_cnt] if new_cnt > 0 else []
                        db.collection("job_salary").document(rid).update(
                            {"student_count": new_cnt, "assigned_ids": new_assigned}
                        )
                        st.rerun()

                with a2:
                    st.markdown(f"<div class='jobcnt-num'>{cnt}</div>", unsafe_allow_html=True)

                with a3:
                    if st.button("➕", key=f"job_cnt_plus_{rid}"):
                        new_cnt = cnt + 1
                        new_assigned = assigned_ids + [""]
                        db.collection("job_salary").document(rid).update(
                            {"student_count": new_cnt, "assigned_ids": new_assigned}
                        )
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

            # ✅ 배정 계정 드롭다운(기존 로직 그대로)
            with rowc[6]:
                if cnt > 0:
                    new_ids = []
                    for k in range(cnt):
                        cur_id = assigned_ids[k] if k < len(assigned_ids) else ""
                        cur_label = id_to_label.get(cur_id, "(선택 없음)") if cur_id else "(선택 없음)"

                        sel = st.selectbox(
                            f"계정{k+1}",
                            acc_options,
                            index=acc_options.index(cur_label) if cur_label in acc_options else 0,
                            key=f"job_assign_{rid}_{k}",
                            label_visibility="collapsed",
                        )
                        new_ids.append(label_to_id.get(sel, "") if sel != "(선택 없음)" else "")

                    if new_ids != assigned_ids:
                        db.collection("job_salary").document(rid).update({"assigned_ids": new_ids})

            st.markdown("<div style='margin:0.35rem 0; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

        st.divider()

        # -------------------------------------------------
        # ✅ 하단: 직업 추가/수정 (하우스포인트 템플릿처럼)
        # -------------------------------------------------
        st.markdown("### ➕ 직업 추가 / 수정")

        pick_labels = ["(새로 추가)"] + [f"{r['order']} | {r['job']} (월급 {int(r['salary'])})" for r in rows]
        picked = st.selectbox("편집 대상", pick_labels, key="job_edit_pick")

        edit_row = None
        if picked != "(새로 추가)":
            # order|job로 찾기(표시 문자열 기준)
            for rr in rows:
                label = f"{rr['order']} | {rr['job']} (월급 {int(rr['salary'])})"
                if label == picked:
                    edit_row = rr
                    break

        # 입력폼(직업/월급)
        f1, f2, f3 = st.columns([2.2, 1.2, 1.2])
        with f1:
            job_in = st.text_input("직업", value=(edit_row["job"] if edit_row else ""), key="job_in_job").strip()
        with f2:
            sal_in = st.number_input("월급", min_value=0, step=1, value=int(edit_row["salary"]) if edit_row else 0, key="job_in_salary")
        with f3:
            # 실수령 미리보기
            st.metric("실수령액(자동)", _calc_net(int(sal_in), cfg))

        # 학생 수(기본 1)
        sc_in = st.number_input(
            "학생 수(최소 1)",
            min_value=1,
            step=1,
            value=int(edit_row["student_count"]) if edit_row else 1,
            key="job_in_count",
        )

        b1, b2, b3 = st.columns([1, 1, 1])
        with b1:
            if st.button("✅ 저장", use_container_width=True, key="job_save_btn"):
                if not job_in:
                    st.error("직업을 입력해 주세요.")
                    st.stop()

                if edit_row:
                    # 수정
                    rid = edit_row["_id"]
                    # assigned_ids 길이 맞추기(수정 시 학생수 바뀔 수 있음)
                    cur_ids = list(edit_row.get("assigned_ids", []) or [])
                    if len(cur_ids) < int(sc_in):
                        cur_ids = cur_ids + [""] * (int(sc_in) - len(cur_ids))
                    if len(cur_ids) > int(sc_in):
                        cur_ids = cur_ids[: int(sc_in)]

                    db.collection("job_salary").document(rid).update(
                        {
                            "job": job_in,
                            "salary": int(sal_in),
                            "student_count": int(sc_in),
                            "assigned_ids": cur_ids,
                            "updated_at": firestore.SERVER_TIMESTAMP,
                        }
                    )
                    toast("수정 완료!", icon="✅")
                    st.rerun()
                else:
                    # 신규 추가(order는 입력 순서대로 마지막+1)
                    new_order = _next_order(rows)
                    db.collection("job_salary").document().set(
                        {
                            "order": int(new_order),
                            "job": job_in,
                            "salary": int(sal_in),
                            "student_count": int(sc_in),
                            "assigned_ids": [""] * int(sc_in),
                            "created_at": firestore.SERVER_TIMESTAMP,
                            "updated_at": firestore.SERVER_TIMESTAMP,
                        }
                    )
                    toast("추가 완료!", icon="✅")
                    st.rerun()

        with b2:
            if st.button("🧹 입력 초기화", use_container_width=True, key="job_clear_btn"):
                st.session_state.pop("job_in_job", None)
                st.session_state.pop("job_in_salary", None)
                st.session_state.pop("job_in_count", None)
                st.session_state["job_edit_pick"] = "(새로 추가)"
                st.rerun()

        with b3:
            if st.button("🗑️ 삭제", use_container_width=True, key="job_delete_btn", disabled=(edit_row is None)):
                if not edit_row:
                    st.stop()
                st.session_state._job_delete_id = edit_row["_id"]

        if "_job_delete_id" in st.session_state:
            st.warning("정말 삭제하시겠습니까?")
            y, n = st.columns(2)
            with y:
                if st.button("예", use_container_width=True, key="job_del_yes"):
                    db.collection("job_salary").document(st.session_state._job_delete_id).delete()
                    st.session_state.pop("_job_delete_id", None)
                    toast("삭제 완료", icon="🗑️")
                    st.rerun()
            with n:
                if st.button("아니오", use_container_width=True, key="job_del_no"):
                    st.session_state.pop("_job_delete_id", None)
                    st.rerun()

# =========================
# 🏛️ 국세청(국고) 탭
# =========================
if "🏛️ 국세청(국고)" in tabs:
    with tab_map["🏛️ 국세청(국고)"]:
        st.subheader("🏛️ 국세청(국고)")

        # 관리자만 쓰기 가능 / 학생은 읽기만(원하면 later: treasury_read 권한으로 확장)
        writable = bool(is_admin)

        # 1) 상단 잔액 표시: [국고] : 00000드림
        st_res = api_get_treasury_state_cached()
        treasury_bal = int(st_res.get("balance", 0) or 0)
        st.markdown(f"## [국고] : **{treasury_bal:,}{TREASURY_UNIT}**")

        st.markdown("### [세입/세출 내역]")

        # 2) 세입/세출 내역(최신순 표)
        led = api_list_treasury_ledger_cached(limit=300)
        df_led = pd.DataFrame(led.get("rows", [])) if led.get("ok") else pd.DataFrame()

        if df_led.empty:
            st.info("국고 내역이 아직 없어요.")
        else:
            view = df_led.rename(
                columns={
                    "memo": "내역",
                    "income": "세입",
                    "expense": "세출",
                    "balance_after": "총액",
                    "created_at_kr": "날짜-시간",
                }
            )
            st.dataframe(
                view[["내역", "세입", "세출", "총액", "날짜-시간"]],
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        # 3) 세입/세출 입력(개별 관리자 입금/출금과 같은 원리)
        st.markdown("### 📝 세입/세출 내역 입력")

        tre_tpls, _, tre_by_disp, _ = build_treasury_template_maps()
        memo_t, inc_t, exp_t = render_treasury_trade_ui(
            prefix="treasury_trade",
            templates_list=tre_tpls,
            template_by_display=tre_by_disp,
        )

        btnc1, btnc2 = st.columns([1.2, 1.0])
        with btnc1:
            if st.button("저장 (관리자, 국세청)", use_container_width=True, key="treasury_save_btn", disabled=(not writable)):
                if not writable:
                    st.error("관리자 전용입니다.")
                else:
                    res = api_add_treasury_tx(
                        admin_pin=ADMIN_PIN,
                        memo=memo_t,
                        income=int(inc_t),
                        expense=int(exp_t),
                        actor="treasury",
                    )
                    if res.get("ok"):
                        toast("국고 저장 완료!", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "국고 저장 실패"))

        with btnc2:
            st.caption("※ 세입/세출 중 하나만 입력")

        st.divider()

        # 4) 국고 템플릿 추가/수정/삭제 (국고 전용)
        st.markdown("### 🧩 국고 템플릿 추가/수정/삭제")

        tpls = api_list_treasury_templates_cached().get("templates", [])
        pick_labels = ["(새로 추가)"] + [f"{t.get('order', 999999)} | {treasury_template_display(t)}" for t in tpls]
        picked = st.selectbox("편집 대상", pick_labels, key="tre_tpl_pick")

        edit_tpl = None
        if picked != "(새로 추가)":
            for t in tpls:
                lab = f"{t.get('order', 999999)} | {treasury_template_display(t)}"
                if lab == picked:
                    edit_tpl = t
                    break

        f1, f2, f3, f4 = st.columns([2.2, 1.2, 1.2, 1.0])
        with f1:
            lab_in = st.text_input("라벨(내역)", value=(edit_tpl.get("label") if edit_tpl else ""), key="tre_tpl_label").strip()
        with f2:
            # ✅ 화면에는 한글(세입/세출)로, 저장은 income/expense 그대로
            kind_map = {"세입": "income", "세출": "expense"}
            kind_rev = {v: k for k, v in kind_map.items()}

            cur_kind = (edit_tpl.get("kind") if edit_tpl else "income")
            cur_kind_kr = kind_rev.get(str(cur_kind), "세입")

            kind_kr = st.selectbox(
                "종류",
                ["세입", "세출"],
                index=(0 if cur_kind_kr == "세입" else 1),
                key="tre_tpl_kind_kr",
                help="세입=income, 세출=expense (저장은 자동으로 처리됩니다)",
            )

            # ✅ 아래 저장 버튼에서 kind_in을 그대로 쓰도록, 변수명 kind_in 유지
            kind_in = kind_map.get(kind_kr, "income")
        with f3:
            amt_in = st.number_input("금액", min_value=0, step=1, value=int(edit_tpl.get("amount", 0)) if edit_tpl else 0, key="tre_tpl_amount")
        with f4:
            ord_in = st.number_input("순서", min_value=1, step=1, value=int(edit_tpl.get("order", 1)) if edit_tpl else 1, key="tre_tpl_order")

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("✅ 저장", use_container_width=True, key="tre_tpl_save", disabled=(not writable)):
                if not writable:
                    st.error("관리자 전용입니다.")
                else:
                    res = api_upsert_treasury_template(
                        admin_pin=ADMIN_PIN,
                        template_id=(edit_tpl.get("template_id") if edit_tpl else ""),
                        label=lab_in,
                        kind=kind_in,
                        amount=int(amt_in),
                        order=int(ord_in),
                    )
                    if res.get("ok"):
                        toast("국고 템플릿 저장 완료!", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "저장 실패"))

        with b2:
            if st.button("🧹 입력 초기화", use_container_width=True, key="tre_tpl_clear"):
                st.session_state.pop("tre_tpl_label", None)
                st.session_state.pop("tre_tpl_amount", None)
                st.session_state.pop("tre_tpl_order", None)
                st.session_state["tre_tpl_pick"] = "(새로 추가)"
                st.rerun()

        with b3:
            if st.button("🗑️ 삭제", use_container_width=True, key="tre_tpl_del", disabled=(not writable or edit_tpl is None)):
                if not writable:
                    st.error("관리자 전용입니다.")
                elif not edit_tpl:
                    st.stop()
                else:
                    res = api_delete_treasury_template(ADMIN_PIN, str(edit_tpl.get("template_id")))
                    if res.get("ok"):
                        toast("국고 템플릿 삭제 완료!", icon="🗑️")
                        st.rerun()
                    else:
                        st.error(res.get("error", "삭제 실패"))

# =========================
# 📊 통계청(제출물) 탭  ✅(관리자용 UI 추가)
# - 클릭은 로컬만 변경(X→O→△→X)
# - [저장] 버튼 눌렀을 때만 DB 반영
# =========================
if "📊 통계청" in tabs:
    with tab_map["📊 통계청"]:
        st.subheader("📊 통계청(제출물 관리)")

        if not is_admin:
            st.error("관리자 전용 탭입니다.")
            st.stop()

        # -------------------------
        # 계정(학생) 목록: 번호/이름 자동 반영
        # -------------------------
        # api_list_accounts_cached()는 name/balance/student_id만 주므로,
        # 번호(no)까지 필요해서 students에서 직접 읽어옴.
        docs_acc2 = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
        stu_rows = []
        for d in docs_acc2:
            x = d.to_dict() or {}
            try:
                no = int(x.get("no", 999999) or 999999)
            except Exception:
                no = 999999
            nm = str(x.get("name", "") or "").strip()
            if nm:
                stu_rows.append({"student_id": d.id, "no": no, "name": nm})
        stu_rows.sort(key=lambda r: (r["no"], r["name"]))

        # -------------------------
        # (상단) 제출물 내역 추가
        # -------------------------
        st.markdown("### ➕ 제출물 내역 추가")

        stat_tpls = api_list_stat_templates_cached().get("templates", [])
        stat_tpl_labels = ["(직접 입력)"] + [str(t.get("label", "") or "") for t in stat_tpls]
        # (PATCH) 저장 후 템플릿/내역 입력값을 안전하게 초기화(위젯 생성 전에만 세팅 가능)

        if st.session_state.get("stat_add_reset_req", False):
            st.session_state["stat_add_tpl"] = "(직접 입력)"
            st.session_state["stat_add_tpl_prev"] = "(직접 입력)"
            st.session_state.pop("stat_add_label", None)

            # 표 로컬 편집 상태도 새로 로드되게
            st.session_state["stat_loaded_sig"] = ""
            st.session_state["stat_edit"] = {}

            st.session_state["stat_add_reset_req"] = False

        # 템플릿 선택
        stat_pick = st.selectbox("제출물 템플릿", stat_tpl_labels, key="stat_add_tpl")

        # 템플릿 고르면 내역 자동 입력
        if "stat_add_tpl_prev" not in st.session_state:
            st.session_state["stat_add_tpl_prev"] = stat_pick

        if stat_pick != st.session_state.get("stat_add_tpl_prev"):
            st.session_state["stat_add_tpl_prev"] = stat_pick
            if stat_pick != "(직접 입력)":
                st.session_state["stat_add_label"] = stat_pick
            st.rerun()

        add_c1, add_c2 = st.columns([3.0, 1.0])
        with add_c1:
            add_label = st.text_input("내역", key="stat_add_label").strip()
        with add_c2:
            if st.button("저장", use_container_width=True, key="stat_add_save"):
                if not add_label:
                    st.error("내역을 입력해 주세요.")
                else:
                    res = api_admin_add_stat_submission(ADMIN_PIN, add_label, active_accounts=stu_rows)
                    if res.get("ok"):
                        toast("제출물 내역 추가 완료!", icon="✅")

                        # (PATCH) 위젯 key(stat_add_tpl)는 여기서 직접 바꾸면 오류남
                        # → 리셋 요청만 걸고 rerun (위젯 생성 전에 초기화됨)
                        st.session_state["stat_add_reset_req"] = True
                        st.rerun()
                    else:
                        st.error(res.get("error", "추가 실패"))

        st.divider()

        # -------------------------
        # (중간) 통계청 통계표
        # - 최신 제출물이 "왼쪽" (created_at DESC)
        # - 클릭은 로컬 변경, [저장] 시 DB 반영
        # -------------------------
        st.markdown("### 📋 통계청 통계표")

        # 최신 제출물 N개(왼쪽부터 최신)
        sub_res = api_list_stat_submissions_cached(limit_cols=50)
        sub_rows_all = sub_res.get("rows", []) if sub_res.get("ok") else []

        submission_ids = [r.get("submission_id") for r in sub_rows_all if r.get("submission_id")]

        # -------------------------
        # (PATCH) 가로 "좌우 이동" + 페이지 숫자(클릭 이동)
        # ✅ 기준 통일: page_idx(0=최신 페이지)로 관리
        # - 한 화면 7개(VISIBLE_COLS)
        # - 숫자 버튼은 작게, "/전체페이지 N"은 텍스트(클릭 불가)
        # -------------------------
        import math

        VISIBLE_COLS = 7
        total_cols = len(sub_rows_all)

        total_pages = max(1, int(math.ceil(total_cols / VISIBLE_COLS)))
        if "stat_page_idx" not in st.session_state:
            st.session_state["stat_page_idx"] = 0  # ✅ 0 = 최신 페이지

        # page_idx 안전 클램프
        st.session_state["stat_page_idx"] = max(0, min(int(st.session_state["stat_page_idx"]), total_pages - 1))
        page_idx = int(st.session_state["stat_page_idx"])
        cur_page = page_idx + 1  # 1-based

        def _goto_page(p: int):
            # p = 1..total_pages, 1이 최신 페이지
            p = max(1, min(int(p), total_pages))
            st.session_state["stat_page_idx"] = p - 1
            st.rerun()

        def _page_items(cur: int, last: int):
            if last <= 9:
                return list(range(1, last + 1))
            items = [1]
            left = max(2, cur - 1)
            right = min(last - 1, cur + 1)
            if left > 2:
                items.append("…")
            items.extend(range(left, right + 1))
            if right < last - 1:
                items.append("…")
            items.append(last)
            out = []
            for x in items:
                if not out or out[-1] != x:
                    out.append(x)
            return out

        # ✅ 한 줄: [◀ + 페이지 + /전체페이지 + ▶] | [저장/초기화/삭제]
        row = st.columns([7.6, 2.4], gap="small")

        with row[0]:
            items = _page_items(cur_page, total_pages)

            # 폭을 더 촘촘히: 마지막에 ▶가 "/전체페이지" 바로 옆에 붙게
            widths = [0.9] + [0.6] * len(items) + [1.1] + [0.9]
            nav_cols = st.columns(widths, gap="small")

            # ◀ : 최신(1페이지)면 비활성
            with nav_cols[0]:
                if st.button("◀", key="stat_nav_left", use_container_width=True, disabled=(cur_page <= 1)):
                    _goto_page(cur_page - 1)

            # 페이지 버튼
            for i, it in enumerate(items):
                with nav_cols[i + 1]:
                    if it == "…":
                        st.markdown("<div style='text-align:center; opacity:0.55;'>…</div>", unsafe_allow_html=True)
                    else:
                        p = int(it)
                        if st.button(f"{p}", key=f"stat_nav_p_{p}", use_container_width=True, disabled=(p == cur_page)):
                            _goto_page(p)

            # "/전체페이지 N" : 텍스트만
            with nav_cols[len(items) + 1]:
                st.markdown(
                    f"<div style='text-align:left; font-weight:700; padding-top:6px;'>/ 전체페이지 {total_pages}</div>",
                    unsafe_allow_html=True,
                )

            # ▶ : 마지막 페이지면 비활성
            with nav_cols[len(items) + 2]:
                if st.button("▶", key="stat_nav_right", use_container_width=True, disabled=(cur_page >= total_pages)):
                    _goto_page(cur_page + 1)

        with row[1]:
            bsave, breset, bdel = st.columns([1, 1, 1], gap="small")
            with bsave:
                save_clicked = st.button("✅ 저장", use_container_width=True, key="stat_table_save")
            with breset:
                reset_clicked = st.button("🧹 초기화", use_container_width=True, key="stat_table_reset")
            with bdel:
                del_clicked = st.button("🗑️ 삭제", use_container_width=True, key="stat_table_del")

        # (PATCH) 초기화(전체 내역 삭제) 확인 플래그
        if reset_clicked:
            st.session_state["stat_reset_confirm"] = True

        if not sub_rows_all:
            st.info("제출물 내역이 없습니다. 위에서 ‘제출물 내역 추가’를 먼저 해주세요.")
        else:
            # ✅ page_idx(0=최신 페이지) 기준 슬라이스
            page_idx = int(st.session_state.get("stat_page_idx", 0) or 0)
            start = page_idx * VISIBLE_COLS
            end = start + VISIBLE_COLS
            sub_rows = sub_rows_all[start:end]

            # 로드 시그니처: (제출물 목록 + 학생 목록) 바뀔 때만 로컬 편집 초기화
            sig = "||".join(
                [
                    ",".join([str(s.get("submission_id")) for s in sub_rows_all]),
                    ",".join([str(s.get("student_id")) for s in stu_rows]),
                ]
            )

            if st.session_state.get("stat_loaded_sig", "") != sig:
                st.session_state["stat_loaded_sig"] = sig
                st.session_state["stat_edit"] = {}

                # (PATCH) 표 구성이 바뀌면 셀 위젯 key 버전을 올려서 라디오 상태 꼬임 방지
                st.session_state["stat_cell_ver"] = int(st.session_state.get("stat_cell_ver", 0) or 0) + 1

                # 제출물별 기본 상태맵(학생 전원 X) + 기존 DB값 반영
                for subx in sub_rows_all:
                    sid = str(subx.get("submission_id"))
                    cur_map = dict(subx.get("statuses", {}) or {})

                    st.session_state["stat_edit"][sid] = {}
                    for stx in stu_rows:
                        stid = str(stx.get("student_id"))
                        v = str(cur_map.get(stid, "X") or "X")
                        st.session_state["stat_edit"][sid][stid] = v if v in ("X", "O", "△") else "X"

            # -------------------------
            # (PATCH) 초기화: 전체 제출물 내역 삭제(삭제 전 확인)
            # -------------------------
            if st.session_state.get("stat_reset_confirm", False):
                st.error("⚠️ 초기화하면 모든 제출물 내역(열)이 전부 삭제됩니다. 진행할까요?")

                yy2, nn2 = st.columns(2)
                with yy2:
                    if st.button("예(전체 삭제)", use_container_width=True, key="stat_reset_yes"):
                        ok_cnt = 0
                        fail_msgs = []

                        # 현재 존재하는 모든 제출물(sub_rows_all) 삭제
                        for s in sub_rows_all:
                            sid = str(s.get("submission_id") or "")
                            if not sid:
                                continue
                            resd = api_admin_delete_stat_submission(ADMIN_PIN, sid)
                            if resd.get("ok"):
                                ok_cnt += 1
                            else:
                                fail_msgs.append(resd.get("error", "삭제 실패"))

                        if ok_cnt > 0:
                            toast(f"초기화 완료! ({ok_cnt}개 삭제)", icon="🧹")

                        if fail_msgs:
                            st.error("일부 삭제 실패: " + " / ".join(fail_msgs[:3]))

                        # 로컬 상태 초기화
                        st.session_state["stat_reset_confirm"] = False
                        st.session_state["stat_delete_confirm"] = False
                        st.session_state["stat_loaded_sig"] = ""
                        st.session_state["stat_edit"] = {}
                        st.rerun()

                with nn2:
                    if st.button("아니오", use_container_width=True, key="stat_reset_no"):
                        st.session_state["stat_reset_confirm"] = False
                        st.rerun()


            
            # -------------------------
            # (PATCH) 삭제: 체크박스로 여러 개 선택해서 삭제
            # -------------------------
            if del_clicked:
                st.session_state["stat_delete_confirm"] = True

            if st.session_state.get("stat_delete_confirm", False):
                st.warning("삭제할 제출물을 체크하세요. (여러 개 선택 가능)")

                del_targets = []
                for s in sub_rows_all:
                    sid = str(s.get("submission_id"))
                    label = f"{s.get('date_display','')} | {s.get('label','')}"
                    ck = st.checkbox(label, key=f"stat_del_ck_{sid}")
                    if ck:
                        del_targets.append(sid)

                yy, nn = st.columns(2)
                with yy:
                    if st.button("예", use_container_width=True, key="stat_del_yes"):
                        if not del_targets:
                            st.error("삭제할 항목을 하나 이상 체크해 주세요.")
                        else:
                            ok_cnt = 0
                            fail_msgs = []
                            for tid in del_targets:
                                resd = api_admin_delete_stat_submission(ADMIN_PIN, tid)
                                if resd.get("ok"):
                                    ok_cnt += 1
                                else:
                                    fail_msgs.append(resd.get("error", "삭제 실패"))

                            if ok_cnt > 0:
                                toast(f"삭제 완료! ({ok_cnt}개)", icon="🗑️")

                            if fail_msgs:
                                st.error("일부 삭제 실패: " + " / ".join(fail_msgs[:3]))

                            # 체크박스 상태/로컬 상태 초기화
                            st.session_state["stat_delete_confirm"] = False
                            st.session_state["stat_loaded_sig"] = ""
                            st.session_state["stat_edit"] = {}
                            st.rerun()
                with nn:
                    if st.button("아니오", use_container_width=True, key="stat_del_no"):
                        st.session_state["stat_delete_confirm"] = False
                        st.rerun()

            # ---- 표 헤더(현재 화면에 보일 제출물만) ----
            col_titles = []
            for s in sub_rows:
                date_disp = str(s.get("date_display", "") or "")
                label = str(s.get("label", "") or "")
                col_titles.append(f"{date_disp}\n{label}")

            # (PATCH) 통계표 전용: 한 칸에 O/X/△ 3개 원형 선택 UI (즉시 표시)
            # - div 래퍼 방식은 Streamlit 위젯을 실제로 감싸지 못해서 적용이 불안정함
            # - 대신 input id에 'stat_cellpick_' 들어간 라디오만 CSS 적용
            st.markdown(
                """
<style>
/* ===== 통계표 셀 라디오( id에 stat_cellpick_ 포함 )만 원형 버튼처럼 + 높이/여백 압축 ===== */

/* 1) radiogroup 자체 여백/정렬 */
div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  gap: 4px !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* 2) 각 원형 버튼(label) — ✅ 높이 170px → 18px 로 수정 */
div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) > label {
  border: 1px solid #d1d5db !important;
  background: #ffffff !important;
  border-radius: 999px !important;

  width: 18px !important;
  height: 18px !important;     /* ✅ 핵심: 170px 절대 금지 */
  min-height: 18px !important;

  padding: 0 !important;
  margin: 0 !important;

  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;

  line-height: 1 !important;
  font-size: 0.75rem !important;
}

/* (추가) 혹시 input 자체에 잡히는 포커스 효과까지 제거 */
div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) input:focus {
  outline: none !important;
  box-shadow: none !important;
}

    
/* 4) 라디오 위젯 “바깥 박스(라운드 사각)”를 줄이는 핵심:
      - 여기서 위아래 padding/margin을 강제로 0
      - min-height 음수 대신, line-height + padding 제거로 압축 */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) {
  margin: 0 !important;
  padding: 0 !important;
}

/* 5) stRadio가 들어있는 element/container 쪽에 생기는 기본 여백 제거 */
div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) > div {
  margin: 0 !important;
  padding: 0 !important;
}

/* 6) label 안의 불필요한 텍스트/여백 요소가 높이 만드는 경우까지 눌러버리기 */
div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) > label * {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
}
/* stRadio를 감싸는 상위 컨테이너 여백까지 제거 (통계셀만) */
div[data-testid="stElementContainer"]:has(input[id*="stat_cellpick_"]) {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
/* 1. 모든 라디오 버튼의 기본 빨간색 그림자/테두리 강제 제거 */
        div[data-testid="stRadio"]:has(input[id*="stat_cellpick_"]) div {
            box-shadow: none !important;
            outline: none !important;
        }

        /* 2. 선택된 버튼(Checked)의 테두리 및 그림자 색상 개별 지정 */

        /* [O] 선택 시 초록색 */
        div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) label:has(input[value="O"]:checked) > div:last-child {
            border-color: #10b981 !important;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.4) !important;
        }

        /* [X] 선택 시 빨간색 */
        div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) label:has(input[value="X"]:checked) > div:last-child {
            border-color: #ef4444 !important;
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.4) !important;
        }

        /* [△] 선택 시 파란색 */
        div[role="radiogroup"]:has(input[id*="stat_cellpick_"]) label:has(input[value="△"]:checked) > div:last-child {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.4) !important;
        }
</style>
""",
                unsafe_allow_html=True,
            )

            hdr_cols = st.columns([0.37, 0.7] + [1.2] * len(col_titles))
            with hdr_cols[0]:
                st.markdown("**번호**")
            with hdr_cols[1]:
                st.markdown("**이름**")
            for j, s in enumerate(sub_rows):
                with hdr_cols[j + 2]:
                    date_disp = str(s.get("date_display", "") or "")
                    label = str(s.get("label", "") or "")
                    st.markdown(
                        f"<div style='text-align:center; font-weight:700; line-height:1.15;'>"
                        f"{date_disp}<br>{label}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            for stx in stu_rows:
                stid = str(stx.get("student_id"))
                no = stx.get("no", 999999)
                nm = stx.get("name", "")

                row_cols = st.columns([0.37, 0.7] + [1.2] * len(col_titles))
                with row_cols[0]:
                    st.markdown(f"{int(no)}")
                with row_cols[1]:
                    st.markdown(f"{nm}")

                for j, sub in enumerate(sub_rows):
                    sub_id = str(sub.get("submission_id"))
                    cur_v = str(st.session_state["stat_edit"].get(sub_id, {}).get(stid, "X") or "X")

                    with row_cols[j + 2]:
                        ver = int(st.session_state.get("stat_cell_ver", 0) or 0)
                        cell_key = f"stat_cellpick_{ver}_{sub_id}_{stid}"

                        # 처음 생성 때만 기본값 세팅(사용자 클릭값은 덮어쓰지 않음)
                        if cell_key not in st.session_state:
                            st.session_state[cell_key] = cur_v if cur_v in ("O", "X", "△") else "X"

                        picked = st.radio(
                            label="",
                            options=("O", "X", "△"),
                            index=("O", "X", "△").index(st.session_state[cell_key]),
                            horizontal=True,
                            key=cell_key,
                            label_visibility="collapsed",
                        )

                        # 선택은 즉시 로컬에 반영(저장은 상단 '✅ 저장'에서만 DB 반영)
                        st.session_state["stat_edit"].setdefault(sub_id, {})
                        st.session_state["stat_edit"][sub_id][stid] = picked

            st.markdown("</div>", unsafe_allow_html=True)

            
            # ---- 저장 버튼 처리(표 오른쪽 상단) ----
            if save_clicked:
                res_sv = api_admin_save_stat_table(
                    admin_pin=ADMIN_PIN,
                    submission_ids=submission_ids,
                    edited=st.session_state.get("stat_edit", {}) or {},
                    accounts=stu_rows,
                )
                if res_sv.get("ok"):
                    toast(f"저장 완료! ({res_sv.get('count', 0)}개 제출물 반영)", icon="✅")
                    st.session_state["stat_loaded_sig"] = ""
                    st.rerun()
                else:
                    st.error(res_sv.get("error", "저장 실패"))

        st.divider()

        # -------------------------
        # (하단) 통계표 템플릿 추가/수정/삭제
        # -------------------------
        st.markdown("### 🧩 통계표 템플릿 추가/수정/삭제")

        tpl_items = api_list_stat_templates_cached().get("templates", [])
        tpl_pick_labels = ["(새로 추가)"] + [f"{t.get('order', 999999)} | {t.get('label','')}" for t in tpl_items]
        tpl_picked = st.selectbox("편집 대상", tpl_pick_labels, key="stat_tpl_pick")

        edit_tpl = None
        if tpl_picked != "(새로 추가)":
            for t in tpl_items:
                lab = f"{t.get('order', 999999)} | {t.get('label','')}"
                if lab == tpl_picked:
                    edit_tpl = t
                    break

        t1, t2 = st.columns([3.0, 1.0])
        with t1:
            tpl_label_in = st.text_input("템플릿 내역", value=(edit_tpl.get("label") if edit_tpl else ""), key="stat_tpl_label").strip()
        with t2:
            tpl_order_in = st.number_input("순서", min_value=1, step=1, value=int(edit_tpl.get("order", 1)) if edit_tpl else 1, key="stat_tpl_order")

        bb1, bb2, bb3 = st.columns(3)
        with bb1:
            if st.button("✅ 저장", use_container_width=True, key="stat_tpl_save_btn"):
                resu = api_admin_upsert_stat_template(
                    admin_pin=ADMIN_PIN,
                    template_id=(edit_tpl.get("template_id") if edit_tpl else ""),
                    label=tpl_label_in,
                    order=int(tpl_order_in),
                )
                if resu.get("ok"):
                    toast("템플릿 저장 완료!", icon="✅")
                    st.session_state["stat_loaded_sig"] = ""
                    st.rerun()
                else:
                    st.error(resu.get("error", "저장 실패"))

        with bb2:
            if st.button("🧹 입력 초기화", use_container_width=True, key="stat_tpl_clear_btn"):
                st.session_state.pop("stat_tpl_label", None)
                st.session_state.pop("stat_tpl_order", None)
                st.session_state["stat_tpl_pick"] = "(새로 추가)"
                st.rerun()

        with bb3:
            if st.button("🗑️ 삭제", use_container_width=True, key="stat_tpl_del_btn", disabled=(edit_tpl is None)):
                if not edit_tpl:
                    st.stop()
                resd2 = api_admin_delete_stat_template(ADMIN_PIN, str(edit_tpl.get("template_id")))
                if resd2.get("ok"):
                    toast("템플릿 삭제 완료!", icon="🗑️")
                    st.session_state["stat_loaded_sig"] = ""
                    st.rerun()
                else:
                    st.error(resd2.get("error", "삭제 실패"))

# =========================
# 💳 신용등급 탭
# - 통계청 제출(O/X/△) 누적 기반 신용점수/등급 기록표
# =========================
if "💳 신용등급" in tabs:
    with tab_map["💳 신용등급"]:
        st.subheader("💳 신용등급")

        if not is_admin:
            st.info("관리자 전용 탭입니다.")
            st.stop()

        # -------------------------
        # 0) 학생 목록(번호/이름) : 계정정보 탭과 동일(활성 학생)
        # -------------------------
        docs_acc = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
        stu_rows = []
        for d in docs_acc:
            x = d.to_dict() or {}
            try:
                no = int(x.get("no", 999999) or 999999)
            except Exception:
                no = 999999
            nm = str(x.get("name", "") or "").strip()
            if nm:
                stu_rows.append({"student_id": d.id, "no": no, "name": nm})
        stu_rows.sort(key=lambda r: (r["no"], r["name"]))

        if not stu_rows:
            st.info("활성화된 학생(계정)이 없습니다.")
            st.stop()

        # -------------------------
        # 1) 점수/등급 규칙표(1~10등급)
        # -------------------------
        st.markdown("### 📌 신용등급 구분표")
        st.markdown(
            """
<style>
.credit-band { border:1px solid #ddd; border-radius:12px; overflow:hidden; }
.credit-band table { width:100%; border-collapse:collapse; font-weight:700; }
.credit-band th, .credit-band td { border-right:1px solid #ddd; padding:10px 6px; text-align:center; }
.credit-band th:last-child, .credit-band td:last-child { border-right:none; }
.credit-band th { background:#f3f4f6; }
</style>
<div class="credit-band">
  <table>
    <tr>
      <th>1등급</th><th>2등급</th><th>3등급</th><th>4등급</th><th>5등급</th>
      <th>6등급</th><th>7등급</th><th>8등급</th><th>9등급</th><th>10등급</th>
    </tr>
    <tr>
      <td>90이상</td><td>80-89</td><td>70-79</td><td>60-69</td><td>50-59</td>
      <td>40-49</td><td>30-39</td><td>20-29</td><td>10-19</td><td>0-9</td>
    </tr>
  </table>
</div>
""",
            unsafe_allow_html=True,
        )

        def _score_to_grade(score: int) -> int:
            s = int(score)
            if s >= 90:
                return 1
            if s >= 80:
                return 2
            if s >= 70:
                return 3
            if s >= 60:
                return 4
            if s >= 50:
                return 5
            if s >= 40:
                return 6
            if s >= 30:
                return 7
            if s >= 20:
                return 8
            if s >= 10:
                return 9
            return 10

        def _fmt_kor_date_short(iso_utc: str) -> str:
            # "0월 0일(요일한글자)" 형태
            try:
                # 예: 2026-02-07T00:00:00Z
                dt = datetime.fromisoformat(str(iso_utc).replace("Z", "+00:00")).astimezone(KST)
                wd = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
                return f"{dt.month}월 {dt.day}일({wd})"
            except Exception:
                return ""

        st.divider()

        # -------------------------
        # 2) 점수 계산 설정(기본값)
        # -------------------------
        def _get_credit_cfg():
            ref = db.collection("config").document("credit_scoring")
            snap = ref.get()
            if not snap.exists:
                return {"base": 50, "o": 1, "x": -3, "tri": 0}
            d = snap.to_dict() or {}
            return {
                "base": int(d.get("base", 50) or 50),
                "o": int(d.get("o", 1) or 1),
                "x": int(d.get("x", -3) or -3),
                "tri": int(d.get("tri", 0) or 0),
            }

        def _save_credit_cfg(cfg: dict):
            db.collection("config").document("credit_scoring").set(
                {
                    "base": int(cfg.get("base", 50) or 50),
                    "o": int(cfg.get("o", 1) or 1),
                    "x": int(cfg.get("x", -3) or -3),
                    "tri": int(cfg.get("tri", 0) or 0),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        credit_cfg = _get_credit_cfg()

        with st.expander("⚙️ 점수 계산 설정(O/X/△ 점수 변경)", expanded=False):
            c1, c2, c3, c4, c5 = st.columns([1.1, 1, 1, 1, 1.2])
            with c1:
                base_in = st.number_input("초기 점수", min_value=0, max_value=100, step=1, value=int(credit_cfg["base"]), key="cred_base")
            with c2:
                o_in = st.number_input("O 일 때", step=1, value=int(credit_cfg["o"]), key="cred_o")
            with c3:
                x_in = st.number_input("X 일 때", step=1, value=int(credit_cfg["x"]), key="cred_x")
            with c4:
                tri_in = st.number_input("△ 일 때", step=1, value=int(credit_cfg["tri"]), key="cred_tri")
            with c5:
                if st.button("✅ 설정 저장", use_container_width=True, key="cred_cfg_save"):
                    _save_credit_cfg({"base": base_in, "o": o_in, "x": x_in, "tri": tri_in})
                    toast("설정 저장 완료!", icon="✅")
                    st.rerun()

        # -------------------------
        # 3) 통계청 제출물(열) 로드 → 누적 점수 계산
        # -------------------------
        sub_res = api_list_stat_submissions_cached(limit_cols=60)
        sub_rows_all = sub_res.get("rows", []) if sub_res.get("ok") else []

        if not sub_rows_all:
            st.info("통계청 제출물 내역이 없습니다. 먼저 통계청 탭에서 제출물을 추가하세요.")
            st.stop()

        # API가 내려주는 "원래 순서"를 표시용 최신순으로 사용 (가장 안정적)
        # - sub_rows_desc: 최신 → 오래된 (표시용)
        # - sub_rows_asc : 오래된 → 최신 (누적 계산용)
        sub_rows_desc = list(sub_rows_all)            # ✅ 그대로(최신→과거라고 가정)
        sub_rows_asc  = list(reversed(sub_rows_desc)) # ✅ 누적 계산은 과거→최신

        base = int(credit_cfg.get("base", 50) or 50)
        o_pt = int(credit_cfg.get("o", 1) or 1)
        x_pt = int(credit_cfg.get("x", -3) or -3)
        tri_pt = int(credit_cfg.get("tri", 0) or 0)

        def _norm_status(v) -> str:
            """상태값을 무조건 'O' / 'X' / '△' 중 하나로 강제"""
            v = str(v or "").strip().upper()
            if v in ("O", "○"):
                return "O"
            if v in ("△", "▲", "Δ"):
                return "△"
            return "X"

        def _delta(v) -> int:
            v = _norm_status(v)
            if v == "O":
                return o_pt
            if v == "△":
                return tri_pt
            return x_pt

        # 학생별 누적 점수 스냅샷: scores_by_sub[sub_id][student_id] = score_after
        scores_by_sub = {}  # submission_id -> {student_id: score}
        cur_score = {str(s["student_id"]): int(base) for s in stu_rows}

        for sub in sub_rows_asc:
            sub_id = str(sub.get("submission_id") or "")
            if not sub_id:
                continue
            statuses = dict(sub.get("statuses", {}) or {})
            snap_map = {}

            for stx in stu_rows:
                stid = str(stx["student_id"])
                v_raw = statuses.get(stid, "X")  # 없으면 X
                v = _norm_status(v_raw)
                nxt = int(cur_score.get(stid, base) + _delta(v))
                if nxt > 100:
                    nxt = 100
                if nxt < 0:
                    nxt = 0
                cur_score[stid] = nxt
                snap_map[stid] = nxt

            scores_by_sub[sub_id] = snap_map

        # -------------------------
        # (PATCH) 가로 페이징 (통계청과 동일 로직)
        # 기준: credit_page_idx (0 = 최신 페이지)
        # -------------------------
        import math

        VISIBLE_COLS = 7
        total_cols = len(sub_rows_desc)
        total_pages = max(1, int(math.ceil(total_cols / VISIBLE_COLS)))

        if "credit_page_idx" not in st.session_state:
            st.session_state["credit_page_idx"] = 0  # ✅ 최신 페이지

        # page_idx 안전 보정
        st.session_state["credit_page_idx"] = max(
            0,
            min(int(st.session_state["credit_page_idx"]), total_pages - 1),
        )
        page_idx = int(st.session_state["credit_page_idx"])
        cur_page = page_idx + 1  # 1-based

        def _credit_goto_page(p: int):
            p = max(1, min(int(p), total_pages))
            st.session_state["credit_page_idx"] = p - 1
            st.rerun()

        def _page_items(cur: int, last: int):
            if last <= 9:
                return list(range(1, last + 1))
            items = [1]
            left = max(2, cur - 1)
            right = min(last - 1, cur + 1)
            if left > 2:
                items.append("…")
            items.extend(range(left, right + 1))
            if right < last - 1:
                items.append("…")
            items.append(last)
            out = []
            for x in items:
                if not out or out[-1] != x:
                    out.append(x)
            return out

        # -------------------------
        # 네비게이션 UI
        # -------------------------
        nav_row = st.columns([7.6, 2.4], gap="small")

        with nav_row[0]:
            items = _page_items(cur_page, total_pages)
            widths = [0.9] + [0.6] * len(items) + [1.1] + [0.9]
            nav_cols = st.columns(widths, gap="small")

            # ◀
            with nav_cols[0]:
                if st.button(
                    "◀",
                    key="credit_nav_left",
                    use_container_width=True,
                    disabled=(cur_page <= 1),
                ):
                    _credit_goto_page(cur_page - 1)

            # 페이지 숫자
            for i, it in enumerate(items):
                with nav_cols[i + 1]:
                    if it == "…":
                        st.markdown(
                            "<div style='text-align:center; opacity:0.55;'>…</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        p = int(it)
                        if st.button(
                            f"{p}",
                            key=f"credit_nav_p_{p}",
                            use_container_width=True,
                            disabled=(p == cur_page),
                        ):
                            _credit_goto_page(p)

            # / 전체페이지 N (텍스트)
            with nav_cols[len(items) + 1]:
                st.markdown(
                    f"<div style='text-align:left; font-weight:700; padding-top:6px;'>"
                    f"/ 전체페이지 {total_pages}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # ▶
            with nav_cols[len(items) + 2]:
                if st.button(
                    "▶",
                    key="credit_nav_right",
                    use_container_width=True,
                    disabled=(cur_page >= total_pages),
                ):
                    _credit_goto_page(cur_page + 1)

        # -------------------------
        # ✅ page_idx 기준으로 날짜 컬럼 슬라이스
        # -------------------------
        start = page_idx * VISIBLE_COLS
        end = start + VISIBLE_COLS
        sub_rows_view = sub_rows_desc[start:end]

        # ---- 헤더(날짜 + 제출물 내역 2줄) ----
        hdr_cols = st.columns([0.55, 1.2] + [1.9] * len(sub_rows_view))
        with hdr_cols[0]:
            st.markdown("**번호**")
        with hdr_cols[1]:
            st.markdown("**이름**")

        for j, s in enumerate(sub_rows_view):
            with hdr_cols[j + 2]:
                date_disp = str(s.get("date_display", "") or "").strip()
                if not date_disp:
                    date_disp = _fmt_kor_date_short(s.get("created_at_utc", ""))

                lab = str(s.get("label", "") or "").strip()

                st.markdown(
                    f"<div style='text-align:center; font-weight:900; line-height:1.15;'>"
                    f"{date_disp}<br>{lab}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # ---- 본문(학생별) ----
        for stx in stu_rows:
            stid = str(stx["student_id"])
            no = int(stx["no"])
            nm = stx["name"]

            row_cols = st.columns([0.55, 1.2] + [1.9] * len(sub_rows_view))
            with row_cols[0]:
                st.markdown(str(no))
            with row_cols[1]:
                st.markdown(str(nm))

            for j, sub in enumerate(sub_rows_view):
                sub_id = str(sub.get("submission_id") or "")
                if sub_id and sub_id in scores_by_sub:
                    sc = int(scores_by_sub[sub_id].get(stid, base))
                else:
                    sc = int(base)

                gr = _score_to_grade(sc)

                with row_cols[j + 2]:
                    st.markdown(
                        f"<div style='text-align:center; font-weight:900;'>{sc}점/{gr}등급</div>",
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.caption("• 왼쪽/오른쪽 버튼으로 날짜(제출물) 열을 이동해서 확인할 수 있어요.")

# =========================
# 🏦 은행(적금) 탭
# - (관리자) 적금 관리 장부(최신순) + 이자율표
# - (학생) 적금 가입/내 적금 목록/중도해지 + 신용등급 미리보기 + 이자율표
# =========================
if "🏦 은행(적금)" in tabs:
    with tab_map["🏦 은행(적금)"]:
        st.subheader("🏦 은행(적금)")

        # -------------------------------------------------
        # 공통 유틸
        # -------------------------------------------------
        def _fmt_kor_date_short_from_dt(dt: datetime) -> str:
            try:
                dt2 = dt.astimezone(KST)
                wd = ["월", "화", "수", "목", "금", "토", "일"][dt2.weekday()]
                return f"{dt2.month}월 {dt2.day}일({wd})"
            except Exception:
                return ""

        def _parse_iso_to_dt(iso_utc: str):
            try:
                return datetime.fromisoformat(str(iso_utc).replace("Z", "+00:00"))
            except Exception:
                return None

        def _dt_to_iso_z(dt: datetime) -> str:
            try:
                return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except Exception:
                return ""

        def _score_to_grade(score: int) -> int:
            s = int(score)
            if s >= 90:
                return 1
            if s >= 80:
                return 2
            if s >= 70:
                return 3
            if s >= 60:
                return 4
            if s >= 50:
                return 5
            if s >= 40:
                return 6
            if s >= 30:
                return 7
            if s >= 20:
                return 8
            if s >= 10:
                return 9
            return 10

        def _norm_status(v) -> str:
            v = str(v or "").strip().upper()
            if v in ("O", "○"):
                return "O"
            if v in ("△", "▲", "Δ"):
                return "△"
            return "X"

        # -------------------------------------------------
        # (1) 이자율 표(설정값 Firestore에서 로드)
        #  - config/bank_rates : {"weeks":[1..10], "rates": {"1":{"1":10, ...}, ...}}
        #  - ✅ 엑셀 표(1~10주) 기준. DB값이 다르면 자동으로 덮어씀.
        # -------------------------------------------------
        def _build_excel_bank_rates():
            weeks = [1,2,3,4,5,6,7,8,9,10]
            rates = {}
            for g in range(1, 11):
                rates[str(g)] = {}
                for w in weeks:
                    rates[str(g)][str(w)] = int((11 - g) * w)  # ✅ 너 엑셀 표 그대로
            return weeks, rates

        def _is_same_excel_table(d: dict) -> bool:
            try:
                weeks_db = [int(x) for x in (d.get("weeks", []) or [])]
                rates_db = d.get("rates", {}) or {}
                weeks_x, rates_x = _build_excel_bank_rates()

                if weeks_db != weeks_x:
                    return False

                for g in range(1, 11):
                    gk = str(g)
                    if gk not in rates_db:
                        return False
                    for w in weeks_x:
                        wk = str(w)
                        if str(int(rates_db[gk].get(wk, -999))) != str(int(rates_x[gk][wk])):
                            return False
                return True
            except Exception:
                return False

        def _get_bank_rate_cfg(force_excel: bool = True):
            ref = db.collection("config").document("bank_rates")
            snap = ref.get()

            # ✅ 엑셀 표 만들기
            weeks_x, rates_x = _build_excel_bank_rates()

            # 1) DB에 있고, 엑셀 표와 동일하면 그대로 사용
            if snap.exists:
                d = snap.to_dict() or {}
                if (not force_excel) or _is_same_excel_table(d):
                    return {
                        "weeks": list(d.get("weeks", []) or []),
                        "rates": dict(d.get("rates", {}) or {})
                    }

            # 2) DB가 없거나 / 내용이 다르면 → 엑셀 표로 덮어쓰기
            ref.set(
                {"weeks": weeks_x, "rates": rates_x, "updated_at": firestore.SERVER_TIMESTAMP},
                merge=False
            )
            return {"weeks": weeks_x, "rates": rates_x}

        # ✅ 여기서 엑셀표 강제 적용
        bank_rate_cfg = _get_bank_rate_cfg(force_excel=True)

        def _get_interest_rate_percent(credit_grade: int, weeks: int) -> float:
            try:
                g = int(credit_grade)
                w = int(weeks)
            except Exception:
                return 0.0

            # 등급 1~10, 주 1~10으로 제한
            g = 1 if g < 1 else 10 if g > 10 else g
            w = 1 if w < 1 else 10 if w > 10 else w

            rates = bank_rate_cfg.get("rates", {}) or {}
            gmap = rates.get(str(g), {}) or {}
            try:
                return float(gmap.get(str(w), 0) or 0)
            except Exception:
                return 0.0

        # -------------------------------------------------
        # (2) 신용점수/등급(현재 시점) 계산 (학생 1명용)
        #  - credit_scoring 설정 + 통계청 제출물(statuses) 누적
        # -------------------------------------------------
        def _get_credit_cfg():
            ref = db.collection("config").document("credit_scoring")
            snap = ref.get()
            if not snap.exists:
                return {"base": 50, "o": 1, "x": -3, "tri": 0}
            d = snap.to_dict() or {}
            return {
                "base": int(d.get("base", 50) or 50),
                "o": int(d.get("o", 1) or 1),
                "x": int(d.get("x", -3) or -3),
                "tri": int(d.get("tri", 0) or 0),
            }

        def _calc_credit_score_for_student(student_id: str) -> tuple[int, int]:
            cfg = _get_credit_cfg()
            base = int(cfg.get("base", 50) or 50)
            o_pt = int(cfg.get("o", 1) or 1)
            x_pt = int(cfg.get("x", -3) or -3)
            tri_pt = int(cfg.get("tri", 0) or 0)

            def _delta(v):
                vv = _norm_status(v)
                if vv == "O":
                    return o_pt
                if vv == "△":
                    return tri_pt
                return x_pt

            sub_res = api_list_stat_submissions_cached(limit_cols=200)
            sub_rows_all = sub_res.get("rows", []) if sub_res.get("ok") else []

            # ✅ 오래된→최신 누적
            def _k(d):
                t = _parse_iso_to_dt(d.get("created_at_utc", "") or "")
                return t.timestamp() if t else 0

            sub_rows_all = sorted(sub_rows_all, key=_k)

            score = int(base)
            sid = str(student_id)

            for sub in sub_rows_all:
                statuses = dict(sub.get("statuses", {}) or {})
                v = statuses.get(sid, "X")
                score = int(score + _delta(v))
                if score > 100:
                    score = 100
                if score < 0:
                    score = 0

            grade = _score_to_grade(score)
            return score, grade

        # -------------------------------------------------
        # (3) 적금 저장/조회/처리 (Firestore: savings)
        # -------------------------------------------------
        SAV_COL = "savings"
        GOAL_COL = "goals"

        def _compute_interest(principal: int, rate_percent: float) -> int:
            # 소수 첫째자리에서 반올림 → 정수
            try:
                v = float(principal) * (float(rate_percent) / 100.0)
                return int(round(v, 0))
            except Exception:
                return 0

        def _ensure_maturity_processing_once():
            """
            관리자 화면에서 열 때:
            - status=running 이고 maturity_utc <= now 인 것들을 자동 만기 처리
            - 원금+이자를 학생 통장에 입금(+)
            """
            now = datetime.now(timezone.utc)
            q = db.collection(SAV_COL).where(filter=FieldFilter("status", "==", "running")).stream()

            proc_cnt = 0
            for d in q:
                x = d.to_dict() or {}
                mdt = _parse_iso_to_dt(x.get("maturity_utc", "") or "")
                if not mdt:
                    continue
                if mdt <= now:
                    student_id = str(x.get("student_id") or "")
                    if not student_id:
                        continue

                    payout = int(x.get("maturity_amount", 0) or 0)
                    memo = f"적금 만기 지급 ({x.get('weeks')}주)"
                    res = api_admin_add_tx_by_student_id(
                        admin_pin=ADMIN_PIN,
                        student_id=student_id,
                        memo=memo,
                        deposit=payout,
                        withdraw=0,
                    )
                    if res.get("ok"):
                        db.collection(SAV_COL).document(d.id).update(
                            {
                                "status": "matured",
                                "payout_amount": payout,
                                "processed_at": firestore.SERVER_TIMESTAMP,
                            }
                        )
                        proc_cnt += 1

            if proc_cnt > 0:
                toast(f"만기 자동 처리: {proc_cnt}건", icon="🏦")

        def _cancel_savings(doc_id: str):
            """
            중도해지:
            - 원금만 학생 통장에 입금(+)
            - status=canceled
            """
            snap = db.collection(SAV_COL).document(doc_id).get()
            if not snap.exists:
                return {"ok": False, "error": "해당 적금을 찾지 못했어요."}
            x = snap.to_dict() or {}
            if str(x.get("status")) != "running":
                return {"ok": False, "error": "진행중인 적금만 중도해지할 수 있어요."}

            student_id = str(x.get("student_id") or "")
            principal = int(x.get("principal", 0) or 0)

            res = api_admin_add_tx_by_student_id(
                admin_pin=ADMIN_PIN,
                student_id=student_id,
                memo=f"적금 중도해지 지급 ({x.get('weeks')}주)",
                deposit=principal,
                withdraw=0,
            )
            if res.get("ok"):
                db.collection(SAV_COL).document(doc_id).update(
                    {
                        "status": "canceled",
                        "payout_amount": principal,
                        "processed_at": firestore.SERVER_TIMESTAMP,
                    }
                )
                return {"ok": True}
            return {"ok": False, "error": res.get("error", "중도해지 실패")}

        def _make_savings(student_id: str, no: int, name: str, weeks: int, principal: int):
            """
            적금 가입:
            - 학생 통장에서 principal 출금(-) 처리
            - savings 문서 생성 (신용등급/이자율/만기금액 자동)
            """
            principal = int(principal or 0)
            weeks = int(weeks or 0)
            if principal <= 0:
                return {"ok": False, "error": "적금 금액이 0보다 커야 해요."}
            if weeks <= 0:
                return {"ok": False, "error": "적금 기간(주)을 선택해 주세요."}

            # ✅ 현재 신용등급(적금 당시 등급 저장)
            score, grade = _calc_credit_score_for_student(student_id)
            rate = _get_interest_rate_percent(grade, weeks)

            interest = _compute_interest(principal, rate)
            maturity_amt = int(principal + interest)

            now_kr = datetime.now(KST)
            now_utc = now_kr.astimezone(timezone.utc)
            maturity_utc = now_utc + timedelta(days=int(weeks) * 7)

            # 1) 통장에서 출금(적금 넣기)
            res_wd = api_admin_add_tx_by_student_id(
                admin_pin=ADMIN_PIN,
                student_id=student_id,
                memo=f"적금 가입 ({weeks}주)",
                deposit=0,
                withdraw=principal,
            )
            if not res_wd.get("ok"):
                return {"ok": False, "error": res_wd.get("error", "통장 출금 실패")}

            # 2) savings 문서 생성
            payload = {
                "student_id": str(student_id),
                "no": int(no),
                "name": str(name),
                "weeks": int(weeks),
                "credit_score": int(score),
                "credit_grade": int(grade),
                "rate_percent": float(rate),
                "principal": int(principal),
                "interest": int(interest),
                "maturity_amount": int(maturity_amt),
                "start_utc": _dt_to_iso_z(now_utc),
                "maturity_utc": _dt_to_iso_z(maturity_utc),
                "status": "running",          # running / matured / canceled
                "payout_amount": None,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            db.collection(SAV_COL).document().set(payload)
            return {"ok": True}

        def _load_savings_rows(limit=500):
            q = db.collection(SAV_COL).order_by("start_utc", direction=firestore.Query.DESCENDING).limit(int(limit)).stream()
            rows = []
            for d in q:
                x = d.to_dict() or {}
                x["_id"] = d.id
                rows.append(x)
            return rows

        # -------------------------------------------------
        # (관리자) 자동 만기 처리(열 때마다 한 번)
        # -------------------------------------------------
        if is_admin:
            _ensure_maturity_processing_once()

        # -------------------------------------------------
        # (A) 관리자: 적금 관리 장부 (엑셀형 표 느낌) + 최신순
        # -------------------------------------------------
        if is_admin:
            st.markdown("### 📒 적금 관리 장부")

            st.markdown(
                """
<style>
/* 은행(적금) 탭의 표 글씨를 조금 작게 */
div[data-testid="stDataFrame"] * { font-size: 0.80rem !important; }
</style>
""",
                unsafe_allow_html=True,
            )

            sav_rows = _load_savings_rows(limit=800)
            if not sav_rows:
                st.info("적금 내역이 아직 없어요.")
            else:
                now_utc = datetime.now(timezone.utc)

                out = []
                for r in sav_rows:
                    start_dt = _parse_iso_to_dt(r.get("start_utc", "") or "")
                    mat_dt = _parse_iso_to_dt(r.get("maturity_utc", "") or "")

                    status = str(r.get("status", "running") or "running")
                    if status == "canceled":
                        result = "중도해지"
                    else:
                        if mat_dt and mat_dt <= now_utc:
                            result = "만기"
                        else:
                            result = "진행중"

                    if result == "진행중":
                        payout_disp = "-"
                    elif result == "중도해지":
                        payout_disp = int(r.get("payout_amount") or r.get("principal", 0) or 0)
                    else:
                        payout_disp = int(r.get("payout_amount") or r.get("maturity_amount", 0) or 0)

                    start_disp = _fmt_kor_date_short_from_dt(start_dt.astimezone(KST)) if start_dt else ""
                    mat_disp = _fmt_kor_date_short_from_dt(mat_dt.astimezone(KST)) if mat_dt else ""

                    out.append(
                        {
                            "번호": int(r.get("no", 0) or 0),
                            "이름": str(r.get("name", "") or ""),
                            "적금기간": f"{int(r.get('weeks', 0) or 0)}주",
                            "신용등급": f"{int(r.get('credit_grade', 10) or 10)}등급",
                            "이자율": f"{float(r.get('rate_percent', 0.0) or 0.0)}%",
                            "적금 금액": int(r.get("principal", 0) or 0),
                            "이자": int(r.get("interest", 0) or 0),
                            "만기 금액": int(r.get("maturity_amount", 0) or 0),
                            "적금 날짜": start_disp,
                            "만기 날짜": mat_disp,
                            "처리 결과": result,
                            "지급 금액": payout_disp,
                            "_id": r.get("_id"),
                        }
                    )

                df = pd.DataFrame(out)
                show_cols = [
                    "번호","이름","적금기간","신용등급","이자율","적금 금액","이자","만기 금액",
                    "적금 날짜","만기 날짜","처리 결과","지급 금액"
                ]
                st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

                st.markdown("#### 🧯 중도해지 처리(관리자)")
                st.caption("• 진행중인 적금만 중도해지 가능(원금만 지급)")

                running = df[df["처리 결과"] == "진행중"].copy()
                if running.empty:
                    st.info("진행중인 적금이 없습니다.")
                else:
                    running = running.head(50)
                    options = ["(선택 없음)"] + [
                        f"{r['번호']} {r['이름']} | {r['적금기간']} | {r['적금 날짜']} | {r['적금 금액']}P"
                        for _, r in running.iterrows()
                    ]
                    label_to_id = {options[i+1]: running.iloc[i]["_id"] for i in range(len(running))}

                    pick = st.selectbox("중도해지할 적금 선택", options, key="bank_cancel_pick")
                    if pick != "(선택 없음)":
                        if st.button("중도해지 처리(원금 지급)", use_container_width=True, key="bank_cancel_do"):
                            doc_id = str(label_to_id.get(pick))
                            res = _cancel_savings(doc_id)
                            if res.get("ok"):
                                toast("중도해지 처리 완료", icon="✅")
                                st.rerun()
                            else:
                                st.error(res.get("error", "중도해지 실패"))

            st.divider()

        # -------------------------------------------------
        # (B) 학생: 적금 가입 UI + 내 적금 목록 + 신용등급 미리보기
        # -------------------------------------------------
        if not is_admin:
            # ✅ 학생 화면에서는 하우스포인트뱅크처럼 '적금' 기능을 기본 허용합니다.
            # (추후 직업/역할별로 제한하려면 여기서 can_write/can_read를 role 기반으로 다시 연결하세요.)
            can_write = True
            can_read = True

            refresh_account_data_light(login_name, login_pin, force=True)
            slot = st.session_state.data.get(login_name, {})
            if slot.get("error"):
                st.error(slot["error"])
                st.stop()

            balance = int(slot.get("balance", 0) or 0)
            my_student_id = slot.get("student_id")

            if my_student_id:
                sc, gr = _calc_credit_score_for_student(my_student_id)
                st.info(f"신용등급: {gr}등급  (점수 {sc}점)")

            st.markdown(f"#### 현재 잔액: **{balance} 포인트**")

            st.markdown("### 📝 적금 가입")
            st.caption("• 적금 가입 시 통장에서 해당 금액이 출금됩니다. • 만기면 원금+이자가 자동 지급됩니다. • 중도해지는 원금만 지급됩니다.")

            week_opts = list(bank_rate_cfg.get("weeks", []) or [])
            week_opts = [int(w) for w in week_opts if str(w).isdigit()]
            week_opts = sorted(list(set(week_opts)))
            if not week_opts:
                week_opts = [1,2,3,4,5,6,7,8,9,10]

            c1, c2, c3 = st.columns([1.1, 1.3, 1.6])
            with c1:
                weeks_in = st.selectbox("적금기간(주)", week_opts, key="stu_bank_weeks")
            with c2:
                principal_in = st.number_input("적금 금액", min_value=0, step=10, value=0, key="stu_bank_principal")
            with c3:
                if my_student_id:
                    sc, gr = _calc_credit_score_for_student(my_student_id)
                    rate = _get_interest_rate_percent(gr, int(weeks_in))
                    it = _compute_interest(int(principal_in or 0), float(rate))
                    mat = int(int(principal_in or 0) + int(it))
                    st.metric("미리보기(이자율/만기)", f"{rate:.0f}% / {mat}P")

            if st.button("🏦 적금 가입(저장)", use_container_width=True, key="stu_bank_join", disabled=(not can_write)):
                if not can_write:
                    st.error("적금 가입 권한(bank_write)이 없습니다.")
                elif not my_student_id:
                    st.error("학생 ID를 찾지 못했어요(로그인 정보를 확인).")
                else:
                    if int(principal_in or 0) > balance:
                        st.error("잔액이 부족해요.")
                    else:
                        me_no = 999999
                        try:
                            snap_me = db.collection("students").document(my_student_id).get()
                            if snap_me.exists:
                                me_no = int((snap_me.to_dict() or {}).get("no", 999999) or 999999)
                        except Exception:
                            me_no = 999999

                        res = _make_savings(
                            student_id=my_student_id,
                            no=int(me_no),
                            name=str(login_name),
                            weeks=int(weeks_in),
                            principal=int(principal_in),
                        )
                        if res.get("ok"):
                            toast("적금 가입 완료!", icon="✅")
                            st.session_state.pop("stu_bank_principal", None)
                            st.rerun()
                        else:
                            st.error(res.get("error", "적금 가입 실패"))

            st.divider()

            st.markdown("### 📒 내 적금")
            my_rows = []
            if my_student_id:
                q = db.collection(SAV_COL).where(filter=FieldFilter("student_id", "==", str(my_student_id))).stream()
                for d in q:
                    x = d.to_dict() or {}
                    x["_id"] = d.id
                    my_rows.append(x)

            def _k2(x):
                dt = _parse_iso_to_dt(x.get("start_utc", "") or "")
                return -(dt.timestamp() if dt else 0)

            my_rows = sorted(my_rows, key=_k2)

            if not my_rows:
                st.info("내 적금 내역이 없어요.")
            else:
                now_utc = datetime.now(timezone.utc)
                view = []
                for r in my_rows:
                    start_dt = _parse_iso_to_dt(r.get("start_utc", "") or "")
                    mat_dt = _parse_iso_to_dt(r.get("maturity_utc", "") or "")

                    status = str(r.get("status", "running") or "running")
                    if status == "canceled":
                        result = "중도해지"
                    else:
                        if mat_dt and mat_dt <= now_utc:
                            result = "만기"
                        else:
                            result = "진행중"

                    if result == "진행중":
                        payout_disp = "-"
                    elif result == "중도해지":
                        payout_disp = int(r.get("payout_amount") or r.get("principal", 0) or 0)
                    else:
                        payout_disp = int(r.get("payout_amount") or r.get("maturity_amount", 0) or 0)

                    view.append(
                        {
                            "적금기간": f"{int(r.get('weeks', 0) or 0)}주",
                            "신용등급": f"{int(r.get('credit_grade', 10) or 10)}등급",
                            "이자율": f"{float(r.get('rate_percent', 0.0) or 0.0)}%",
                            "적금 금액": int(r.get("principal", 0) or 0),
                            "이자": int(r.get("interest", 0) or 0),
                            "만기 금액": int(r.get("maturity_amount", 0) or 0),
                            "적금 날짜": _fmt_kor_date_short_from_dt(start_dt.astimezone(KST)) if start_dt else "",
                            "만기 날짜": _fmt_kor_date_short_from_dt(mat_dt.astimezone(KST)) if mat_dt else "",
                            "처리 결과": result,
                            "지급 금액": payout_disp,
                            "_id": r.get("_id"),
                            "_status": status,
                        }
                    )

                df_my = pd.DataFrame(view)
                show_cols = ["적금기간","신용등급","이자율","적금 금액","이자","만기 금액","적금 날짜","만기 날짜","처리 결과","지급 금액"]
                st.dataframe(df_my[show_cols], use_container_width=True, hide_index=True)

                running_ids = df_my[(df_my["_status"] == "running") & (df_my["처리 결과"] == "진행중")].copy()
                if not running_ids.empty and can_write:
                    st.markdown("#### 🧯 중도해지(원금만 지급)")
                    opts = ["(선택 없음)"] + [
                        f"{r['적금기간']} | {r['적금 날짜']} | {int(r['적금 금액'])}P"
                        for _, r in running_ids.head(30).iterrows()
                    ]
                    lab_to_id = {opts[i+1]: running_ids.iloc[i]["_id"] for i in range(len(running_ids.head(30)))}
                    pick2 = st.selectbox("중도해지할 적금 선택", opts, key="stu_bank_cancel_pick")
                    if pick2 != "(선택 없음)":
                        if st.button("중도해지 실행", use_container_width=True, key="stu_bank_cancel_do"):
                            rid = str(lab_to_id.get(pick2))
                            res = _cancel_savings(rid)
                            if res.get("ok"):
                                toast("중도해지 완료", icon="✅")
                                st.rerun()
                            else:
                                st.error(res.get("error", "중도해지 실패"))

            st.divider()

        # -------------------------------------------------
        # (C) 이자율 표(캡쳐 표 위치): 장부 아래 / 학생 화면 맨 아래
        # -------------------------------------------------
        st.markdown("### 📌 신용등급 × 적금기간 이자율(%) 표")

        weeks = list(bank_rate_cfg.get("weeks", []) or [])
        rates = dict(bank_rate_cfg.get("rates", {}) or {})

        table_rows = []
        for g in range(1, 11):
            row = {"신용등급": f"{g}등급"}
            gmap = dict(rates.get(str(g), {}) or {})
            for w in weeks:
                try:
                    row[f"{int(w)}주"] = int(float(gmap.get(str(int(w)), 0) or 0))
                except Exception:
                    row[f"{w}주"] = 0
            table_rows.append(row)

        df_rate = pd.DataFrame(table_rows)
        st.dataframe(df_rate, use_container_width=True, hide_index=True)
        st.caption("• 이 표는 Firestore config/bank_rates 값으로 자동 반영됩니다.")

# =========================
# 10) 🗓️ 일정 (권한별 수정)
# =========================
def add_schedule(area: str, d: date, title: str, owner_roles: list[str], created_by: str):
    db.collection("schedule_items").document().set(
        {
            "area": area,
            "date": d.isoformat(),
            "title": title,
            "owner_role_ids": owner_roles,
            "created_by": created_by,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return {"ok": True}

def list_schedule(limit=200):
    q = db.collection("schedule_items").order_by("date", direction=firestore.Query.DESCENDING).limit(int(limit)).stream()
    rows = []
    for d in q:
        x = d.to_dict() or {}
        rows.append(x)
    return rows

def can_edit_schedule(area: str, perms: set) -> bool:
    if "admin_all" in perms:
        return True
    if area == "bank":
        return "schedule_bank_write" in perms
    if area == "treasury":
        return "schedule_treasury_write" in perms
    if area == "env":
        return "schedule_env_write" in perms
    return False


# -------------------------
# 🎯 목표 저금 (학생 개별로그인 전용 탭)
# -------------------------
if "🎯 목표" in tabs and (not is_admin):
    with tab_map["🎯 목표"]:
        st.subheader("🎯 목표 저금")

        # 1) 현재 목표 불러오기
        gres = api_get_goal(login_name, login_pin)
        if not gres.get("ok"):
            st.error(gres.get("error", "목표 정보를 불러오지 못했어요."))
            st.stop()

        cur_goal_amt = int(gres.get("goal_amount", 0) or 0)
        cur_goal_date = str(gres.get("goal_date", "") or "")

        # 2) 입력 UI
        c1, c2 = st.columns(2)
        with c1:
            g_amt = st.number_input(
                "목표 금액",
                min_value=1,
                step=1,
                value=cur_goal_amt if cur_goal_amt > 0 else 1000,
                key=f"goal_amt_{login_name}",
            )
        with c2:
            default_date = date.today() + timedelta(days=30)
            if cur_goal_date:
                try:
                    default_date = datetime.fromisoformat(cur_goal_date).date().date()
                except Exception:
                    pass
            g_date = st.date_input("목표 날짜", value=default_date, key=f"goal_date_{login_name}")

        if st.button("목표 저장", key=f"goal_save_{login_name}", use_container_width=True):
            res = api_set_goal(login_name, login_pin, int(g_amt), g_date.isoformat())
            if res.get("ok"):
                toast("목표 저장 완료!", icon="🎯")
                st.rerun()
            else:
                st.error(res.get("error", "목표 저장 실패"))

        # 3) 달성률 계산
        # - 진행 중(=running) 적금 원금은 항상 자산이므로 포함
        # - 목표 날짜 이전 만기되는 적금만 이자까지 포함
        student_doc = fs_auth_student(login_name, login_pin)
        if not student_doc:
            st.error("이름 또는 비밀번호가 틀립니다.")
            st.stop()

        sid = student_doc.id
        bal_now = int((student_doc.to_dict() or {}).get("balance", 0) or 0)

        # running 적금 로드
        principal_all_running = 0
        interest_before_goal = 0

        try:
            sdocs = (
                db.collection(SAV_COL)
                .where(filter=FieldFilter("student_id", "==", sid))
                .where(filter=FieldFilter("status", "==", "running"))
                .stream()
            )
            for d in sdocs:
                s = d.to_dict() or {}
                principal = int(s.get("principal", 0) or 0)
                interest = int(s.get("interest", 0) or 0)
                principal_all_running += principal

                mdt = _to_utc_datetime(s.get("maturity_date"))
                if isinstance(mdt, datetime):
                    m_date = mdt.astimezone(KST).date()
                    if m_date <= g_date:
                        interest_before_goal += interest
        except Exception:
            # 로드 실패해도 목표 UI는 동작
            pass

        goal_amount = int(g_amt)
        expected_amount = bal_now + principal_all_running + interest_before_goal

        now_ratio = clamp01(bal_now / goal_amount if goal_amount > 0 else 0)
        exp_ratio = clamp01(expected_amount / goal_amount if goal_amount > 0 else 0)

        st.write(f"통장 잔액 기준: **{now_ratio*100:.1f}%** (현재 {bal_now} / 목표 {goal_amount})")
        st.progress(exp_ratio)
        st.write(f"총 자산 기준 예상 달성률: **{exp_ratio*100:.1f}%** (예상 {expected_amount} / 목표 {goal_amount})")

        if principal_all_running > 0:
            st.info(f"📌 진행 중 적금 원금 **+{principal_all_running}** 포함 (목표일 이후 만기 적금은 원금만 반영)")
        if interest_before_goal > 0:
            st.caption(f"※ 목표일({g_date.isoformat()}) 이전 만기 적금 이자 **+{interest_before_goal}** 포함")
        if principal_all_running == 0 and interest_before_goal == 0:
            st.caption("진행 중 적금이 없어 예상 금액은 현재 잔액과 같아요.")

if "🗓️ 일정" in tabs:
    
        area = st.selectbox("영역", ["bank", "treasury", "env", "etc"], key="sch_area")
        d = st.date_input("날짜", value=date.today(), key="sch_date")
        title = st.text_input("일정 내용", key="sch_title").strip()

        writable = is_admin or can_edit_schedule(area, my_perms)

        if st.button("일정 추가", use_container_width=True, disabled=(not writable)):
            if not title:
                st.error("일정 내용을 입력하세요.")
            else:
                add_schedule(area, d, title, owner_roles=[], created_by=("admin" if is_admin else login_name))
                toast("일정 추가 완료", icon="🗓️")
                st.rerun()

        st.divider()
        rows = list_schedule(200)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("일정이 없습니다.")
