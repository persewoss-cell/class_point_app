import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
import pandas as pd
import altair as alt
from io import BytesIO
import random

from datetime import datetime, timezone, timedelta, date

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import FailedPrecondition

# (학급 확장용) PDF 텍스트 파싱(간단)
import re

# =========================
# 설정
# =========================
APP_TITLE = "🏫학급 경제 시스템🪙"
st.set_page_config(page_title=APP_TITLE, layout="wide")

KST = timezone(timedelta(hours=9))

# ✅ 기존 관리자 유지(교사)
ADMIN_PIN = "9999"
ADMIN_NAME = "관리자"

# 신용등급 미반영 학생도 기본 기능(은행/경매/복권)을 바로 사용하도록 기본값 고정
DEFAULT_CREDIT_SCORE = 50
DEFAULT_CREDIT_GRADE = 5

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
    .block-container { padding-bottom: 7.0rem; }
    @media (max-width: 768px) {
        .block-container { padding-bottom: 7.0rem; }
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

    /* 🎟️ 복권 구매(사용자 모드) 숫자 입력칸 게임별 배경색 */
    input[aria-label^="1게임 "] { background-color: #f6ddc7 !important; }
    input[aria-label^="2게임 "] { background-color: #efe5a6 !important; }
    input[aria-label^="3게임 "] { background-color: #cfe3c0 !important; }
    input[aria-label^="4게임 "] { background-color: #d3ddf0 !important; }
    input[aria-label^="5게임 "] { background-color: #e3d8ef !important; }

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

/* ✅ 총자산 강조 */
.total-asset{
    font-size: 1.15rem;
    font-weight: 900;
    margin-bottom: 0.35rem;
}

/* =========================
   헤더(제목 줄) 중앙정렬
   ========================= */
div[data-testid="stDataFrame"] div[role="columnheader"],
div[data-testid="stDataEditor"] div[role="columnheader"] {
    justify-content: center !important;
    text-align: center !important;
}

/* =========================
   번호 / 이름 컬럼만 중앙정렬
   ========================= */

/* 첫 번째 컬럼 */
div[data-testid="stDataFrame"] div[role="gridcell"]:nth-child(1),
div[data-testid="stDataEditor"] div[role="gridcell"]:nth-child(1) {
    justify-content: center !important;
    text-align: center !important;
}

/* 두 번째 컬럼 */
div[data-testid="stDataFrame"] div[role="gridcell"]:nth-child(2),
div[data-testid="stDataEditor"] div[role="gridcell"]:nth-child(2) {
    justify-content: center !important;
    text-align: center !important;
}
    
    /* ✅ (PATCH) Expander(개별조회 포함) 제목 글자 크기 축소 — Streamlit DOM 변화에도 먹게 넓게 타겟 */
    details summary { font-size: 0.78rem !important; line-height: 1.2 !important; }
    details summary * { font-size: 0.78rem !important; line-height: 1.2 !important; }

    /* 일부 버전에서 summary 안에 markdown container로 감싸지는 경우 */
    details summary div[data-testid="stMarkdownContainer"] p,
    details summary div[data-testid="stMarkdownContainer"] span,
    details summary p,
    details summary span {
        font-size: 0.78rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

</style>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="app-title"> {APP_TITLE}</div>', unsafe_allow_html=True)

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

try:
    db = init_firestore()
except StreamlitSecretNotFoundError:
    st.error("Firebase 설정(secrets.toml)이 없어 앱을 시작할 수 없습니다. `.streamlit/secrets.toml`에 firebase 설정을 추가해 주세요.")
    st.info("현재 화면이 비어 보이거나 로딩처럼 보이는 원인은 Firestore 연결 초기화 실패입니다.")
    st.stop()
except Exception as e:
    st.error(f"Firestore 초기화 실패: {e}")
    st.stop()

# =========================
# Utils (너 코드 유지 + 권한 유틸 추가)
# =========================
def pin_ok(pin: str) -> bool:
    return len(str(pin or "")) == 4
    
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

    # ✅ 요일(한글 한 글자) 추가: 월~일
    dow = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]

    ampm = "오전" if dt.hour < 12 else "오후"
    hour12 = dt.hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{dt.year}년 {dt.month:02d}월 {dt.day:02d}일({dow}) {ampm} {hour12:02d}시 {dt.minute:02d}분"


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

def _is_invest_memo(memo: str) -> bool:
    """✅ 투자 내역 판별(되돌리기 대상에서 제외 용도)
    - 통장 내역에 '투자 매입(...), 투자 회수(...)'가 들어오므로 memo 기반으로 차단
    """
    memo = str(memo or "").strip()
    return memo.startswith("투자 ") or ("투자 매입" in memo) or ("투자 회수" in memo)

def render_asset_summary(balance_now: int, savings_list: list[dict]):
    sv_total = sum(
        int(s.get("principal", 0) or 0)
        for s in (savings_list or [])
        if str(s.get("status", "")).lower().strip() == "active"
    )
    asset_total = int(balance_now) + int(sv_total)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 자산", f"{asset_total}")
    with c2:
        st.metric("통장 잔액", f"{int(balance_now)}")
    with c3:
        st.metric("적금 총액", f"{int(sv_total)}")

def savings_active_total(savings_list: list[dict]) -> int:
    # ✅ running/active 모두 "진행중"으로 인정
    return sum(
        int(s.get("principal", 0) or 0)
        for s in (savings_list or [])
        if str(s.get("status", "")).lower().strip() in ("active", "running")
    )

@st.cache_data(ttl=20, show_spinner=False)
def _list_active_students_full_cached() -> list[dict]:
    """활성 학생 전체를 1회 조회 후 재사용(리렌더/버튼 rerun read 절감)."""
    docs = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
    rows = []
    for d in docs:
        x = d.to_dict() or {}
        rows.append({"student_id": d.id, **x})
    return rows


@st.cache_data(ttl=60, show_spinner=False)
def _get_invest_products_map_cached() -> dict[str, tuple[str, float]]:
    """invest_products 전체 스냅샷 캐시(학생별 요약 계산 시 중복 stream 방지)."""
    prod_map = {}
    for d in db.collection(INV_PROD_COL).stream():
        x = d.to_dict() or {}
        pid = str(x.get("product_id", d.id) or d.id)
        pname = (
            str(x.get("name", "") or "").strip()
            or str(x.get("label", "") or "").strip()
            or str(x.get("title", "") or "").strip()
            or str(x.get("subject", "") or "").strip()
            or pid
        )
        cur_price = float(x.get("current_price", 0.0) or 0.0)
        prod_map[pid] = (pname, cur_price)
    return prod_map


@st.cache_data(ttl=60, show_spinner=False)
def _get_role_lookup_cached() -> tuple[dict[str, str], dict[str, list[str]]]:
    """roles + job_salary를 캐시해 학생별 직업명 조회 read를 최소화."""
    role_by_id = {}
    for d in db.collection("roles").stream():
        x = d.to_dict() or {}
        role_by_id[d.id] = str(x.get("role_name") or x.get("name") or d.id).strip() or d.id

    jobs_by_student = {}
    for jdoc in db.collection("job_salary").stream():
        jd = jdoc.to_dict() or {}
        jname = str(jd.get("job") or jd.get("role_name") or "").strip()
        if not jname:
            continue
        for sid in [str(x) for x in (jd.get("assigned_ids", []) or [])]:
            if sid not in jobs_by_student:
                jobs_by_student[sid] = []
            if jname not in jobs_by_student[sid]:
                jobs_by_student[sid].append(jname)
    return role_by_id, jobs_by_student

# =========================
# (관리자 개별조회용) 요약 정보 helpers
# - 학생 번호(no) 기준 정렬 + 접힘/펼침 한 줄 요약
# =========================
INV_PROD_COL = "invest_products"
INV_LEDGER_COL = "invest_ledger"

@st.cache_data(ttl=60, show_spinner=False)
def _get_role_name_by_student_id(student_id: str) -> str:
    try:
        sid = str(student_id or "").strip()
        if not sid:
            return "없음"

        # (1) students 문서에서 먼저 찾기 (job_name/job/role_id/job_role_id/job_id 등)
        snap = db.collection("students").document(sid).get()
        if snap.exists:
            sdata = snap.to_dict() or {}

            rid = str(
                sdata.get("role_id")
                or sdata.get("job_role_id")
                or sdata.get("job_id")
                or ""
            ).strip()

            # ✅ 학생 문서에 job_name/job이 직접 들어있는 경우
            job_direct = str(sdata.get("job_name") or sdata.get("job") or "").strip()
            if job_direct:
                return job_direct

            # ✅ role_id가 있으면 roles 컬렉션에서 이름 조회
            if rid:
                role_by_id, _ = _get_role_lookup_cached()
                nm = str(role_by_id.get(rid, rid)).strip()
                if nm:
                    return nm

                # roles 문서가 없으면 role_id 자체를 직업명으로 보여주기
                return rid

        # (2) students에 없으면 job_salary에서 assigned_ids로 찾기 (직업/월급 탭 방식)
        _, jobs_by_student = _get_role_lookup_cached()
        jobs = list(jobs_by_student.get(sid, []))

        if jobs:
            # 중복 제거(순서 유지)
            uniq = []
            for j in jobs:
                if j not in uniq:
                    uniq.append(j)
            return ", ".join(uniq)

        return "없음"

    except Exception:
        return "없음"

@st.cache_data(ttl=30, show_spinner=False)
def _get_invest_summary_by_student_id(student_id: str) -> tuple[str, int]:
    """
    ✅ return (표시문구, 투자총액_현재가치추정)
    - 표시문구 예: "국어 100드림" / 여러개면 "국어 100드림, 수학 50드림"
    - invest_ledger: redeemed=False 항목을 보유로 간주
    - invest_products: current_price 사용 + 종목명(name/label/title/subject) 대응
    """
    try:
        sid = str(student_id)

        # 1) 종목 정보 맵 (id -> (name, current_price))
        prod_map = _get_invest_products_map_cached()

        # 2) 보유 장부(미환매) → 종목별 현재가치 합산
        q = db.collection(INV_LEDGER_COL).where(filter=FieldFilter("student_id", "==", sid)).stream()
        per_prod_val = {}  # pid -> value

        for d in q:
            x = d.to_dict() or {}
            if bool(x.get("redeemed", False)):
                continue

            pid = str(x.get("product_id", "") or "")
            if not pid:
                continue

            buy_price = float(x.get("buy_price", 0.0) or 0.0)
            invest_amount = int(x.get("invest_amount", 0) or 0)

            pname, cur_price = prod_map.get(pid, (pid, 0.0))

            # 현재 평가금은 투자 회수(지급) 계산과 동일 규칙 사용
            _, _, cur_val = _calc_invest_redeem_projection(invest_amount, buy_price, cur_price)

            per_prod_val[pid] = per_prod_val.get(pid, 0) + cur_val

        if not per_prod_val:
            return ("없음", 0)

        # 총합
        total_val = int(round(sum(v for v in per_prod_val.values())))

        # 표시: 종목명 오름차순, 개수 제한 없이 모두 표시
        items = sorted(
            per_prod_val.items(),
            key=lambda kv: str(prod_map.get(kv[0], (kv[0], 0.0))[0] or kv[0]),
        )
        shown = []
        for pid, v in items:
            pname = prod_map.get(pid, (pid, 0.0))[0]
            shown.append(f"{pname} {int(round(v))}드림")
        text = ", ".join(shown)

        return (text, total_val)
    except Exception:
        return ("없음", 0)


def _calc_invest_redeem_projection(invest_amount: int, buy_price: float, sell_price: float):
    """
    투자 회수(지급)와 동일한 기준으로 현재 평가/예상 회수금 계산.
    return: (등락폭, 수익/손실, 회수예상금[int])
    """
    def _as_price1_local(v):
        try:
            return float(f"{float(v):.1f}")
        except Exception:
            return 0.0
    invest_amount = int(invest_amount or 0)
    buy_price = _as_price1_local(buy_price)
    sell_price = _as_price1_local(sell_price)
    diff = _as_price1_local(sell_price - buy_price)

    # diff <= -100 : 전액 손실
    if diff <= -100:
        profit = -invest_amount
        redeem_amt = 0
    else:
        profit = invest_amount * float(diff) / 10.0
        redeem_amt = invest_amount + profit
        if redeem_amt < 0:
            redeem_amt = 0

    return diff, profit, int(round(redeem_amt))
    

@st.cache_data(ttl=30, show_spinner=False)
def _get_invest_principal_by_student_id(student_id: str) -> tuple[str, int]:
    """
    ✅ return (표시문구, 투자원금합계)
    - 표시문구 예: "국어 100드림, 수학 50드림"
    - invest_ledger: redeemed=False 항목의 invest_amount를 '원금'으로 간주해 종목별 합산
    """
    try:
        sid = str(student_id)

        # 1) 종목 정보 맵 (id -> name)
        prod_name = {k: v[0] for k, v in _get_invest_products_map_cached().items()}

        # 2) 보유 장부(미환매) → 종목별 원금 합산
        q = db.collection(INV_LEDGER_COL).where(filter=FieldFilter("student_id", "==", sid)).stream()
        per_prod_amt = {}  # pid -> principal(sum invest_amount)

        for d in q:
            x = d.to_dict() or {}
            if bool(x.get("redeemed", False)):
                continue

            pid = str(x.get("product_id", "") or "")
            if not pid:
                continue

            invest_amount = int(x.get("invest_amount", 0) or 0)
            if invest_amount <= 0:
                continue

            per_prod_amt[pid] = per_prod_amt.get(pid, 0) + invest_amount

        if not per_prod_amt:
            return ("없음", 0)

        total_principal = int(sum(int(v) for v in per_prod_amt.values()))

        # 표시: 종목명 오름차순, 개수 제한 없이 모두 표시
        items = sorted(per_prod_amt.items(), key=lambda kv: str(prod_name.get(kv[0], kv[0]) or kv[0]))

        shown = []
        for pid, v in items:
            shown.append(f"{prod_name.get(pid, pid)} {int(v)}드림")

        return (", ".join(shown), total_principal)

    except Exception:
        return ("없음", 0)



# =========================
# ✅ Credit helpers (사용자 헤더에서도 신용도 계산 가능하도록: 정의 위치를 앞쪽으로 배치)
# =========================
def _score_to_grade(score: int) -> int:
    s = int(score or 0)
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

@st.cache_data(ttl=60, show_spinner=False)
def _get_credit_cfg():
    ref = db.collection("config").document("credit_scoring")
    snap = ref.get()
    if not snap.exists:
        return {"base": 50, "o": 1, "x": -3, "tri": 0}
    d = snap.to_dict() or {}
    return {
        "base": int(d.get("base", 50) if d.get("base", None) is not None else 50),
        "o": int(d.get("o", 1) if d.get("o", None) is not None else 1),
        "x": int(d.get("x", -3) if d.get("x", None) is not None else -3),
        "tri": int(d.get("tri", 0) if d.get("tri", None) is not None else 0),
    }

def _norm_status(v) -> str:
    v = str(v or "").strip().upper()
    if v in ("O", "○"):
        return "O"
    if v in ("△", "▲", "Δ"):
        return "△"
    return "X"

def _calc_credit_score_for_student(student_id: str):
    credit_cfg = _get_credit_cfg()
    base = int(credit_cfg.get("base", 50) if credit_cfg.get("base", None) is not None else 50)
    o_pt = int(credit_cfg.get("o", 1) if credit_cfg.get("o", None) is not None else 1)
    x_pt = int(credit_cfg.get("x", -3) if credit_cfg.get("x", None) is not None else -3)
    tri_pt = int(credit_cfg.get("tri", 0) if credit_cfg.get("tri", None) is not None else 0)

    def _delta(v) -> int:
        v = _norm_status(v)
        if v == "O":
            return o_pt
        if v == "△":
            return tri_pt
        return x_pt

    res = api_list_stat_submissions_cached(limit_cols=200)
    rows_desc = list(res.get("rows", []) or []) if res.get("ok") else []

    score = int(base)
    # rows_desc는 최신→과거 / 누적은 과거→최신으로
    for sub in reversed(rows_desc):
        statuses = dict(sub.get("statuses", {}) or {})
        v_raw = statuses.get(str(student_id), "X")
        score = int(score + _delta(v_raw))
        if score > 100:
            score = 100
        if score < 0:
            score = 0

    grade = _score_to_grade(score)
    return score, grade


def _render_user_bank_header(student_id: str):
    """✅ 사용자 모드: 탭 위에 통장/사용자 정보 요약 표시"""
    try:
        sid = str(student_id or "")
        if not sid:
            return

        # 통장잔액
        bal_now = 0
        try:
            snap = db.collection("students").document(sid).get()
            if snap.exists:
                bal_now = int((snap.to_dict() or {}).get("balance", 0) or 0)
        except Exception:
            bal_now = 0

        # 적금 총 원금(전체)
        sv_total = 0
        try:
            sdocs = (
                db.collection("savings")
                .where(filter=FieldFilter("student_id", "==", sid))
                .stream()
            )
            for d in sdocs:
                s = d.to_dict() or {}
                sv_total += int(s.get("principal", 0) or 0)
        except Exception:
            sv_total = 0

        # 투자: 원금 / 현재평가
        inv_principal_text, inv_principal_total = _get_invest_principal_by_student_id(sid)
        inv_eval_text, inv_eval_total = _get_invest_summary_by_student_id(sid)


        # 직업 / 신용도
        role_name = _get_role_name_by_student_id(sid)
        credit_score, credit_grade = _safe_credit(sid)

        # 총 자산(투자는 현재평가 기준)
        asset_total = int(bal_now) + int(sv_total) + int(inv_eval_total)

        # 표시 형식(캡쳐 스타일)
        who = str(st.session_state.get("login_name", "") or "").strip()
        
        st.markdown(f"### 🧮 총 자산: {int(asset_total)} 드림")

        # ✅ (PATCH) 총자산 줄은 유지 + 나머지는 글자/간격만 컴팩트하게
        st.markdown(
            """
            <style>
              .bank-info-line{
                font-size: 22px;
                line-height: 1.20;
                margin: 0.20rem 0 0.20rem 0;
              }
              /* st.markdown 기본 p 마진도 줄이기 */
              .bank-info-wrap p { margin: 0.20rem 0 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""<div class='bank-info-wrap'>
            <div class='bank-info-line'>💰 통장 잔액: {int(bal_now)} 드림</div>
            <div class='bank-info-line'>🏦 적금 총액: {int(sv_total)} 드림</div>
            <div class='bank-info-line'>🪙 투자 원금: 총 {int(inv_principal_total)} 드림({inv_principal_text})</div>
            <div class='bank-info-line'>📈 현재 평가: 총 {int(inv_eval_total)} 드림({inv_eval_text})</div>
            <div class='bank-info-line'>💼 직업: {role_name if role_name else '없음'}</div>
            <div class='bank-info-line'>💳 신용도: {int(credit_grade)}등급({int(credit_score)}점)</div>
            </div>""",
            unsafe_allow_html=True,
        )
    except Exception:
        # 헤더는 실패해도 앱 전체가 죽지 않게 조용히 패스
        pass

def _safe_credit(student_id: str):
    """
    ✅ (score, grade) 안전 조회
    - 가능하면 _calc_credit_score_for_student()로 즉시 계산(사용자 헤더에서도 동작)
    - 그래도 안되면 students 문서에 저장된 credit_score/credit_grade 사용
    - 실패 시 기본값(50점/5등급)
    """
    try:
        if not student_id:
            return (DEFAULT_CREDIT_SCORE, DEFAULT_CREDIT_GRADE)
            
        f = globals().get("_calc_credit_score_for_student")
        if callable(f):
            out = f(str(student_id))
            # out이 (score, grade) 튜플인 경우
            if isinstance(out, (tuple, list)) and len(out) >= 2:
                sc = int(out[0] if out[0] is not None else DEFAULT_CREDIT_SCORE)
                gr = int(out[1] if out[1] is not None else 0)
                if gr <= 0:
                    gr = int(_score_to_grade(sc))
                return (sc, gr)
            # out이 score(int)만 오는 경우
            try:
                sc = int(out if out is not None else DEFAULT_CREDIT_SCORE)
                return (sc, int(globals().get("_score_to_grade")(sc) if callable(globals().get("_score_to_grade")) else DEFAULT_CREDIT_GRADE))
            except Exception:
                pass

        # students 문서에 저장된 값 사용
        snap = db.collection("students").document(str(student_id)).get()
        if not snap.exists:
            return (DEFAULT_CREDIT_SCORE, DEFAULT_CREDIT_GRADE)
        data = snap.to_dict() or {}
        sc = int(data.get("credit_score", DEFAULT_CREDIT_SCORE) or DEFAULT_CREDIT_SCORE)
        gr = int(data.get("credit_grade", 0) or 0)

        # grade가 비어있는데 score는 있으면 grade 계산
        if gr <= 0:
            gfn = globals().get("_score_to_grade")
            if callable(gfn):
                gr = int(gfn(sc))

        return (sc, gr)

    except Exception:
        return (DEFAULT_CREDIT_SCORE, DEFAULT_CREDIT_GRADE)
        
def _fmt_admin_one_line(
    no: int,
    name: str,
    asset_total: int,
    bal_now: int,
    sv_total: int,
    inv_text: str,
    inv_total: int,
    role_name: str,
    credit_score: int,
    credit_grade: int,
) -> str:
    inv_text = str(inv_text or "").strip()
    inv_part = "투자: 없음" if (not inv_text or inv_text == "없음") else f"투자: {inv_text}"

    role_part = f"직업: {str(role_name or '없음')}"
    credit_part = f"신용: {int(credit_grade)}등급({int(credit_score)}점)"

    return (
        f"👤 {int(no)}번 {name} | "
        f"총 {int(asset_total)}드림 | 통장: {int(bal_now)}드림 | 적금: {int(sv_total)}드림 | "
        f"{inv_part} | {role_part} | {credit_part}"
    )

# =========================
# Goals
# =========================
def api_get_goal_by_student_id(student_id: str):
    """학생별 목표(학생 1명당 문서 1개: doc_id = student_id) 조회"""
    GOAL_COL = "goals"
    try:
        ref = db.collection(GOAL_COL).document(student_id).get()
        if not ref.exists:
            return {"ok": True, "goal_amount": 0, "goal_date": ""}
        g = ref.to_dict() or {}
        return {
            "ok": True,
            "goal_amount": int(g.get("target_amount", 0) or 0),
            "goal_date": str(g.get("goal_date", "") or ""),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_set_goal_by_student_id(student_id: str, target_amount: int, goal_date_str: str):
    """학생별 목표 저장(학생 1명당 문서 1개: doc_id = student_id)"""
    GOAL_COL = "goals"
    try:
        db.collection(GOAL_COL).document(student_id).set(
            {
                "student_id": student_id,
                "target_amount": int(target_amount or 0),
                "goal_date": goal_date_str,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_get_goal(name: str, pin: str):
    """사용자 인증 후 목표 조회"""
    student_doc = fs_auth_student(name, pin)  # ✅ login_name/login_pin 버그 수정
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    return api_get_goal_by_student_id(student_doc.id)


def api_set_goal(name: str, pin: str, goal_amount: int, goal_date_str: str):
    """사용자 인증 후 목표 저장(학생 1명당 문서 1개: doc_id = student_id)"""
    goal_amount = int(goal_amount or 0)
    goal_date_str = str(goal_date_str or "").strip()

    student_doc = fs_auth_student(name, pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    if goal_amount <= 0:
        return {"ok": False, "error": "목표 금액은 1 이상이어야 합니다."}

    # ✅ 목표 저장은 student_id 문서에 1개로 고정(로그아웃/재로그인 후에도 그대로 불러옴)
    return api_set_goal_by_student_id(student_doc.id, int(goal_amount), goal_date_str)
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


def _set_login_student_context_from_doc(doc):
    """로그인 시점 1회만 student 스냅샷 저장(렌더링 중 재인증 read 방지)."""
    if not doc:
        st.session_state["login_student_ctx"] = {}
        return
    data = doc.to_dict() or {}
    st.session_state["login_student_ctx"] = {
        "student_id": str(doc.id),
        "name": str(data.get("name", "") or ""),
        "balance": int(data.get("balance", 0) or 0),
        "credit_grade": int(data.get("credit_grade", DEFAULT_CREDIT_GRADE) or DEFAULT_CREDIT_GRADE),
        "role_id": str(data.get("role_id", "") or ""),
        "extra_permissions": list(data.get("extra_permissions", []) or []),
    }


def _get_login_student_context() -> dict:
    return dict(st.session_state.get("login_student_ctx", {}) or {})


def _get_my_permissions_from_ctx(student_ctx: dict, is_admin: bool):
    if is_admin:
        return {"admin_all"}
    if not student_ctx:
        return set()

    perms = set()
    role_id = str(student_ctx.get("role_id", "") or "")
    if role_id:
        # 역할 문서는 캐시 함수 사용(렌더링 중 직접 get 방지)
        role_rows = api_list_roles_cached().get("roles", [])
        for r in role_rows:
            if str(r.get("role_id", "")) == role_id:
                perms |= set(list(r.get("permissions", []) or []))
                break

    extra = student_ctx.get("extra_permissions", []) or []
    if isinstance(extra, list):
        perms |= set([str(x) for x in extra if str(x).strip()])
    return perms

# =========================
# Cached lists
# =========================
@st.cache_data(ttl=30, show_spinner=False)
def api_list_accounts_cached():
    items = []
    for s in _list_active_students_full_cached():
        nm = s.get("name", "")
        if nm:
            items.append({"student_id": s.get("student_id", ""), "no": int(s.get("no", 0) or 0), "name": nm, "balance": int(s.get("balance", 0) or 0)})
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
                    # label에는 화면에 보여줄 문자열(※ 구분이 있으면 "[구분] ..." 형태 포함)
                    "label": t.get("label"),
                    # 선택적으로 별도 저장해둔 값(없으면 label에서 파싱해서 사용)
                    "category": str(t.get("category", "") or ""),
                    "base_label": str(t.get("base_label", "") or ""),
                    "kind": t.get("kind"),
                    "amount": int(t.get("amount", 0) or 0),
                    "order": int(t.get("order", 999999) or 999999),
                }
            )
    templates.sort(key=lambda x: (int(x.get("order", 999999)), str(x.get("label", ""))))
    return {"ok": True, "templates": templates}
# =========================
# ✅ (관리자) 보상/벌금용 helpers
# - templates 컬렉션: {label, category?, base_label?, kind, amount, order}
# =========================
def _parse_template_label(label: str):
    """label이 '[구분] 내용' 형태면 (구분, 내용) 반환"""
    s = str(label or "").strip()
    if s.startswith("[") and "]" in s:
        end = s.find("]")
        cat = s[1:end].strip()
        rest = s[end + 1 :].strip()
        if rest.startswith("-"):
            rest = rest[1:].strip()
        return cat, rest
    return "", s


def _compose_template_label(base_label: str, category: str):
    base_label = str(base_label or "").strip()
    category = str(category or "").strip()
    if category:
        return f"[{category}] {base_label}"
    return base_label


def api_admin_bulk_deposit(admin_pin: str, amount: int, memo: str):
    """✅ 전체 일괄 지급"""
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    amount = int(amount or 0)
    memo = (memo or "").strip() or "일괄 지급"
    if amount <= 0:
        return {"ok": False, "error": "금액은 1 이상이어야 합니다."}

    docs = list(db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream())
    count = 0
    for d in docs:
        student_id = d.id
        student_ref = db.collection("students").document(student_id)
        tx_ref = db.collection("transactions").document()

        @firestore.transactional
        def _do(transaction):
            snap = student_ref.get(transaction=transaction)
            bal = int((snap.to_dict() or {}).get("balance", 0))
            new_bal = bal + amount
            transaction.update(student_ref, {"balance": new_bal})
            transaction.set(
                tx_ref,
                {
                    "student_id": student_id,
                    "type": "deposit",
                    "amount": amount,
                    "balance_after": new_bal,
                    "memo": memo,
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
            )

        _do(db.transaction())
        count += 1

    api_list_accounts_cached.clear()
    return {"ok": True, "count": count}


def api_admin_bulk_withdraw(admin_pin: str, amount: int, memo: str):
    """✅ 전체 일괄 벌금(잔액 부족이어도 적용 → 음수 허용)"""
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    amount = int(amount or 0)
    memo = (memo or "").strip() or "일괄 벌금"
    if amount <= 0:
        return {"ok": False, "error": "금액은 1 이상이어야 합니다."}

    docs = list(db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream())
    count = 0
    for d in docs:
        student_id = d.id
        student_ref = db.collection("students").document(student_id)
        tx_ref = db.collection("transactions").document()

        @firestore.transactional
        def _do(transaction):
            snap = student_ref.get(transaction=transaction)
            bal = int((snap.to_dict() or {}).get("balance", 0))
            new_bal = bal - amount
            transaction.update(student_ref, {"balance": new_bal})
            transaction.set(
                tx_ref,
                {
                    "student_id": student_id,
                    "type": "withdraw",
                    "amount": -amount,
                    "balance_after": new_bal,
                    "memo": memo,
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
            )

        _do(db.transaction())
        count += 1

    api_list_accounts_cached.clear()
    return {"ok": True, "count": count}


def api_admin_upsert_template(admin_pin: str, template_id: str, base_label: str, category: str, kind: str, amount: int, order: int):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    base_label = (base_label or "").strip()
    category = (category or "").strip()
    label = _compose_template_label(base_label, category)

    kind = (kind or "").strip()
    amount = int(amount or 0)
    order = int(order or 1)

    if not label:
        return {"ok": False, "error": "내역 이름이 필요합니다."}
    if kind not in ("deposit", "withdraw"):
        return {"ok": False, "error": "종류는 deposit/withdraw만 가능합니다."}
    if amount <= 0:
        return {"ok": False, "error": "금액은 1 이상이어야 합니다."}
    if order <= 0:
        return {"ok": False, "error": "순서는 1 이상이어야 합니다."}

    payload = {
        "label": label,
        "base_label": base_label,
        "category": category,
        "kind": kind,
        "amount": amount,
        "order": order,
    }
    if template_id:
        db.collection("templates").document(template_id).set(payload, merge=True)
    else:
        db.collection("templates").document().set(payload)

    api_list_templates_cached.clear()
    return {"ok": True}


def api_admin_delete_template(admin_pin: str, template_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    template_id = (template_id or "").strip()
    if not template_id:
        return {"ok": False, "error": "template_id가 필요합니다."}
    db.collection("templates").document(template_id).delete()
    api_list_templates_cached.clear()
    return {"ok": True}


def api_admin_backfill_template_order(admin_pin: str):
    """order가 없는 템플릿에만 1회 채우기"""
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    docs = list(db.collection("templates").stream())
    items = []
    for d in docs:
        t = d.to_dict() or {}
        if t.get("label"):
            items.append((d.id, t))
    items.sort(key=lambda x: str((x[1] or {}).get("label", "")))

    batch = db.batch()
    for idx, (doc_id, t) in enumerate(items, start=1):
        if (t or {}).get("order", None) is None:
            ref = db.collection("templates").document(doc_id)
            batch.set(ref, {"order": idx}, merge=True)
    batch.commit()

    api_list_templates_cached.clear()
    return {"ok": True, "count": len(items)}


def api_admin_normalize_template_order(admin_pin: str):
    """현재 정렬 기준으로 order를 1..N으로 재정렬"""
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    docs = list(db.collection("templates").stream())
    items = []
    for d in docs:
        t = d.to_dict() or {}
        if t.get("label"):
            items.append((d.id, t))

    items.sort(
        key=lambda x: (
            int((x[1] or {}).get("order", 999999) or 999999),
            str((x[1] or {}).get("label", "")),
        )
    )

    batch = db.batch()
    for idx, (doc_id, _) in enumerate(items, start=1):
        ref = db.collection("templates").document(doc_id)
        batch.set(ref, {"order": idx}, merge=True)
    batch.commit()

    api_list_templates_cached.clear()
    return {"ok": True, "count": len(items)}


def api_admin_save_template_orders(admin_pin: str, ordered_template_ids: list[str]):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    if not ordered_template_ids:
        return {"ok": False, "error": "저장할 순서가 없습니다."}
    try:
        batch = db.batch()
        for idx, tid in enumerate(ordered_template_ids, start=1):
            ref = db.collection("templates").document(str(tid))
            batch.set(ref, {"order": idx}, merge=True)
        batch.commit()

        api_list_templates_cached.clear()
        return {"ok": True, "count": len(ordered_template_ids)}
    except Exception as e:
        return {"ok": False, "error": str(e)}



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
    if not pin_ok(pin):
        return {"ok": False, "error": "PIN은 4자리여야 합니다."}
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
        return {"ok": False, "error": "기존 비밀번호는 4자리여야 합니다."}
    if not pin_ok(new_pin):
        return {"ok": False, "error": "새 비밀번호는 4자리여야 합니다."}

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
    """✅ 학생 거래(국고 반영 없는 기본 버전)"""
    memo = (memo or "").strip()
    deposit = int(deposit or 0)
    withdraw = int(withdraw or 0)

    if not memo:
        return {"ok": False, "error": "내역이 필요합니다."}
    if (deposit > 0 and withdraw > 0) or (deposit == 0 and withdraw == 0):
        return {"ok": False, "error": "입금/출금 중 하나만 입력하세요."}

    student_doc = fs_auth_student(name, pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    student_ref = db.collection("students").document(student_doc.id)
    tx_ref = db.collection("transactions").document()

    amount = deposit if deposit > 0 else -withdraw
    tx_type = "deposit" if deposit > 0 else "withdraw"

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        bal = int((snap.to_dict() or {}).get("balance", 0) or 0)

        # 출금은 잔액 부족이면 불가
        if tx_type == "withdraw" and bal < withdraw:
            raise ValueError("잔액보다 큰 출금은 불가합니다.")

        new_bal = int(bal + amount)
        transaction.update(student_ref, {"balance": int(new_bal)})
        transaction.set(
            tx_ref,
            {
                "student_id": student_doc.id,
                "type": tx_type,
                "amount": int(amount),
                "balance_after": int(new_bal),
                "memo": memo,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return new_bal

    try:
        new_bal = _do(db.transaction())
        return {"ok": True, "balance": int(new_bal)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"저장 실패: {e}"}

def api_admin_add_tx_by_student_id(admin_pin: str, student_id: str, memo: str, deposit: int, withdraw: int):
    """
    ✅ 관리자 전용: 개별 학생에게 입금/출금
    - 국고 반영이 필요하면 api_admin_add_tx_by_student_id_with_treasury() 사용
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

    student_ref = db.collection("students").document(str(student_id))
    tx_ref = db.collection("transactions").document()

    amount = deposit if deposit > 0 else -withdraw
    tx_type = "deposit" if deposit > 0 else "withdraw"

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        if not snap.exists:
            raise ValueError("계정을 찾지 못했습니다.")
        bal = int((snap.to_dict() or {}).get("balance", 0) or 0)

        # 출금은 잔액 부족이면 불가
        if tx_type == "withdraw" and bal < withdraw:
            raise ValueError("잔액보다 큰 출금은 불가합니다.")

        new_bal = int(bal + amount)
        transaction.update(student_ref, {"balance": int(new_bal)})
        transaction.set(
            tx_ref,
            {
                "student_id": str(student_id),
                "type": tx_type,
                "amount": int(amount),
                "balance_after": int(new_bal),
                "memo": memo,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return new_bal

    try:
        new_bal = _do(db.transaction())
        api_list_accounts_cached.clear()
        return {"ok": True, "balance": int(new_bal)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"저장 실패: {e}"}

def api_broker_deposit_by_student_id(actor_student_id: str, student_id: str, memo: str, deposit: int, withdraw: int = 0):
    """
    ✅ '투자증권' 직업(roles.role_name == '투자증권') 학생이 다른 학생 통장에 '입금(+)'만 할 수 있게 하는 함수
    - 투자 회수(지급) 용도
    - 출금은 불가
    """
    try:
        actor_student_id = str(actor_student_id or "").strip()
        student_id = str(student_id or "").strip()
        memo = str(memo or "").strip()
        deposit = int(deposit or 0)

        if not actor_student_id:
            return {"ok": False, "error": "actor_student_id가 없습니다."}
        if not student_id:
            return {"ok": False, "error": "student_id가 없습니다."}
        if not memo:
            return {"ok": False, "error": "내역이 필요합니다."}
        if deposit <= 0:
            return {"ok": False, "error": "입금 금액이 1 이상이어야 합니다."}

        # ✅ 역할 확인: roles에서 role_name == '투자증권'
        try:
            actor_snap = db.collection("students").document(actor_student_id).get()
            if not actor_snap.exists:
                return {"ok": False, "error": "권한 확인 실패(계정 없음)."}
            actor = actor_snap.to_dict() or {}
            rid = str(actor.get("role_id", "") or "")
            if not rid:
                return {"ok": False, "error": "투자 회수 권한이 없습니다."}
            roles = api_list_roles_cached()
            role_name = ""
            for r in roles:
                if str(r.get("role_id")) == rid:
                    role_name = str(r.get("role_name", "") or "")
                    break
            if role_name != "투자증권":
                return {"ok": False, "error": "투자 회수 권한이 없습니다."}
        except Exception:
            return {"ok": False, "error": "권한 확인 실패."}

        student_ref = db.collection("students").document(student_id)
        tx_ref = db.collection("transactions").document()

        @firestore.transactional
        def _do(transaction):
            snap = student_ref.get(transaction=transaction)
            if not snap.exists:
                raise ValueError("대상 학생을 찾지 못했어요.")
            bal = int((snap.to_dict() or {}).get("balance", 0) or 0)
            new_bal = bal + int(deposit)

            transaction.update(student_ref, {"balance": new_bal})
            transaction.set(
                tx_ref,
                {
                    "student_id": student_id,
                    "type": "deposit",
                    "amount": int(deposit),
                    "balance_after": new_bal,
                    "memo": memo,
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
            )
            return new_bal

        new_bal = _do(db.transaction())
        return {"ok": True, "balance": int(new_bal)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

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
    credit_grade = int(data.get("credit_grade", DEFAULT_CREDIT_GRADE) or DEFAULT_CREDIT_GRADE)
    
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
    - 없으면 기본 5등급으로 표시
    """
    try:
        if not student_id:
            return DEFAULT_CREDIT_GRADE
        snap = db.collection("students").document(student_id).get()
        if not snap.exists:
            return DEFAULT_CREDIT_GRADE
        data = snap.to_dict() or {}
        return int(data.get("credit_grade", DEFAULT_CREDIT_GRADE) or DEFAULT_CREDIT_GRADE)
    except Exception:
        return DEFAULT_CREDIT_GRADE
        
# =========================
# ✅ Deposit Approval (입금 승인) - NEW
# - 컬렉션: deposit_requests
#   { student_id, no, name, memo, amount, apply_treasury, treasury_memo,
#     status: "pending|approved|rejected", created_at, processed_at, tx_id }
# =========================
DEP_REQ_COL = "deposit_requests"

def api_create_deposit_request(name: str, pin: str, memo: str, amount: int, apply_treasury: bool, treasury_memo: str):
    """✅ (사용자) 입금 신청(승인 대기) 생성
    - 출금은 제외(이 함수는 deposit만)
    - 통장/국고는 '승인될 때' 반영
    """
    try:
        memo = str(memo or "").strip()
        amount = int(amount or 0)
        apply_treasury = bool(apply_treasury)
        treasury_memo = str(treasury_memo or memo).strip()

        if not memo:
            return {"ok": False, "error": "내역이 필요합니다."}
        if amount <= 0:
            return {"ok": False, "error": "입금 금액은 1 이상이어야 합니다."}

        stu_doc = fs_auth_student(name, pin)
        if not stu_doc:
            return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

        sdata = stu_doc.to_dict() or {}
        req_ref = db.collection(DEP_REQ_COL).document()

        payload = {
            "student_id": str(stu_doc.id),
            "no": int(sdata.get("no", 0) or 0),
            "name": str(sdata.get("name", "") or name),
            "memo": memo,
            "amount": int(amount),
            "apply_treasury": bool(apply_treasury),
            "treasury_memo": treasury_memo,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
            "processed_at": None,
            "tx_id": "",
        }
        req_ref.set(payload)
        return {"ok": True, "request_id": req_ref.id}

    except Exception as e:
        return {"ok": False, "error": str(e)}

def api_list_pending_deposit_requests(limit: int = 300):
    """✅ (관리자) 승인 대기 입금 목록"""
    try:
        rows = []
        # 인덱스 문제 피하려고 where+order_by 조합 최소화(파이썬에서 pending만 필터)
        q = (
            db.collection(DEP_REQ_COL)
            .order_by("created_at", direction=firestore.Query.ASCENDING)
            .limit(int(limit))
            .stream()
        )
        for d in q:
            x = d.to_dict() or {}
            if str(x.get("status", "pending") or "pending") != "pending":
                continue
            rows.append({**x, "request_id": d.id})
        return {"ok": True, "rows": rows}
    except Exception as e:
        # fallback(정렬 실패 등)
        try:
            rows = []
            q = db.collection(DEP_REQ_COL).limit(int(limit)).stream()
            for d in q:
                x = d.to_dict() or {}
                if str(x.get("status", "pending") or "pending") != "pending":
                    continue
                rows.append({**x, "request_id": d.id})
            return {"ok": True, "rows": rows}
        except Exception as e2:
            return {"ok": False, "error": str(e2), "rows": []}

def api_admin_approve_deposit_request(admin_pin: str, request_id: str):
    """✅ (관리자) 입금 승인
    - 승인 시: 학생 통장에 입금 거래 기록 + balance 갱신
    - apply_treasury=True였으면: 국고장부에도 같이 반영(학생 입금 => 국고 세출(-))
    """
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    request_id = str(request_id or "").strip()
    if not request_id:
        return {"ok": False, "error": "request_id가 없습니다."}

    req_ref = db.collection(DEP_REQ_COL).document(request_id)

    @firestore.transactional
    def _do(transaction):
        req_snap = req_ref.get(transaction=transaction)
        if not req_snap.exists:
            raise ValueError("신청서를 찾지 못했습니다.")
        req = req_snap.to_dict() or {}

        if str(req.get("status", "pending") or "pending") != "pending":
            raise ValueError("이미 처리된 신청입니다.")

        student_id = str(req.get("student_id", "") or "").strip()
        if not student_id:
            raise ValueError("student_id가 없습니다.")

        amount = int(req.get("amount", 0) or 0)
        if amount <= 0:
            raise ValueError("금액이 올바르지 않습니다.")

        memo = str(req.get("memo", "") or "").strip() or "입금"
        apply_treasury = bool(req.get("apply_treasury", False))
        treasury_memo = str(req.get("treasury_memo", "") or memo).strip()

        # 학생 문서
        student_ref = db.collection("students").document(student_id)
        st_snap = student_ref.get(transaction=transaction)
        if not st_snap.exists:
            raise ValueError("대상 학생을 찾지 못했습니다.")

        bal = int((st_snap.to_dict() or {}).get("balance", 0) or 0)

        # ✅ 국고 반영(승인 시점에 처리)
        # 학생 입금(+) => 국고 세출(-amount)
        if apply_treasury:
            _treasury_apply_in_transaction(
                transaction,
                memo=treasury_memo,
                signed_amount=int(-amount),
                actor="deposit_approve",
            )

        new_bal = int(bal + amount)

        # 거래 기록
        tx_ref = db.collection("transactions").document()
        transaction.update(student_ref, {"balance": int(new_bal)})
        transaction.set(
            tx_ref,
            {
                "student_id": student_id,
                "type": "deposit",
                "amount": int(amount),
                "balance_after": int(new_bal),
                "memo": memo,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )

        # 신청서 상태 업데이트
        transaction.update(
            req_ref,
            {
                "status": "approved",
                "processed_at": firestore.SERVER_TIMESTAMP,
                "tx_id": str(tx_ref.id),
            },
        )

        return new_bal

    try:
        new_bal = _do(db.transaction())

        # 캐시 갱신
        try:
            api_list_accounts_cached.clear()
        except Exception:
            pass
        try:
            api_get_treasury_state_cached.clear()
            api_list_treasury_ledger_cached.clear()
        except Exception:
            pass

        return {"ok": True, "balance": int(new_bal)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"승인 실패: {e}"}

def api_admin_reject_deposit_request(admin_pin: str, request_id: str):
    """✅ (관리자) 입금 거절 - 아무 변화 없음(통장/국고 반영 X), 목록에서만 사라지게 status 변경"""
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    request_id = str(request_id or "").strip()
    if not request_id:
        return {"ok": False, "error": "request_id가 없습니다."}

    req_ref = db.collection(DEP_REQ_COL).document(request_id)

    @firestore.transactional
    def _do(transaction):
        req_snap = req_ref.get(transaction=transaction)
        if not req_snap.exists:
            raise ValueError("신청서를 찾지 못했습니다.")
        req = req_snap.to_dict() or {}

        if str(req.get("status", "pending") or "pending") != "pending":
            raise ValueError("이미 처리된 신청입니다.")

        transaction.update(
            req_ref,
            {"status": "rejected", "processed_at": firestore.SERVER_TIMESTAMP}
        )
        return True

    try:
        _do(db.transaction())
        return {"ok": True}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"거절 실패: {e}"}

def render_deposit_approval_ui(admin_pin: str, prefix: str = "dep_approve", allow: bool = False):
    """✅ 관리자 화면: 입금 승인 목록 + 승인/거절 버튼"""

    # ✅ 학생 화면에서는 절대 노출하지 않기(관리자만)
    if not bool(allow):
        return
    
    st.markdown("### ✅ 입금 승인(승인 대기 목록)")

    res = api_list_pending_deposit_requests(limit=300)
    rows = res.get("rows", []) if res.get("ok") else []

    if not rows:
        st.info("승인 대기 중인 입금 신청이 없습니다.")
        return

    # 헤더(번호 | 이름 | 날짜 | 금액 | 국고반영 | 승인여부)
    h = st.columns([0.9, 1.4, 2.2, 3.2, 1.2, 1.1, 1.9], vertical_alignment="center")
    h[0].markdown("**번호**")
    h[1].markdown("**이름**")
    h[2].markdown("**날짜**")
    h[3].markdown("**내역**")
    h[4].markdown("**금액**")
    h[5].markdown("**국고반영**")
    h[6].markdown("**승인여부**")

    def _fmt_md(dt_utc):
        try:
            # created_at이 Firestore Timestamp일 수 있음
            dt = _to_utc_datetime(dt_utc)
            if not dt:
                return ""
            d = dt.astimezone(KST).date()
            return format_kr_md_date(d)  # "2월 17일(화)"
        except Exception:
            return ""

    for i, r in enumerate(rows, start=1):
        rid = str(r.get("request_id", "") or "")
        no = int(r.get("no", 0) or 0)
        nm = str(r.get("name", "") or "")
        when = _fmt_md(r.get("created_at"))
        amt = int(r.get("amount", 0) or 0)
        tre = "O" if bool(r.get("apply_treasury", False)) else "X"

        memo = str(r.get("memo", "") or "")

        c = st.columns([0.9, 1.4, 2.2, 3.2, 1.2, 1.1, 1.9], vertical_alignment="center")
        c[0].write(str(no if no > 0 else i))
        c[1].write(nm)
        c[2].write(when)
        c[3].write(memo)
        c[4].write(str(amt))
        c[5].write(tre)

        b1, b2 = c[6].columns(2)
        with b1:
            if st.button("승인", key=f"{prefix}_ok_{rid}", use_container_width=True):
                out = api_admin_approve_deposit_request(admin_pin, rid)
                if out.get("ok"):
                    toast("승인 완료! (통장에 반영됨)", icon="✅")
                    st.rerun()
                else:
                    st.error(out.get("error", "승인 실패"))
        with b2:
            if st.button("거절", key=f"{prefix}_no_{rid}", use_container_width=True):
                out = api_admin_reject_deposit_request(admin_pin, rid)
                if out.get("ok"):
                    toast("거절 처리 완료!", icon="🧾")
                    st.rerun()
                else:
                    st.error(out.get("error", "거절 실패"))

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
        if _is_invest_memo(memo):
            blocked.append((tid, "투자 내역"))
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

        # ✅ 되돌리기 메모를 "내역명(mm.dd.) 되돌리기" 형식으로 표시
        _orig_memo = str(tx.get("memo", "") or "").strip()
        _dt_utc = _to_utc_datetime(tx.get("created_at"))
        if _dt_utc:
            _dt_kst = _dt_utc.astimezone(KST)
            _mmdd = f"{_dt_kst.month:02d}.{_dt_kst.day:02d}."
        else:
            _mmdd = "--.--."
        rollback_memo = f"{(_orig_memo or '내역')}({_mmdd}) 되돌리기"

        # ✅ 원거래가 국고(국세청) 반영된 경우: 되돌리기도 국고장부에 반영
        orig_tre_signed = int(tx.get("treasury_signed", 0) or 0)
        orig_tre_memo = str(tx.get("treasury_memo", "") or "").strip() or _orig_memo

        @firestore.transactional
        def _do_one(transaction):
            st_snap = student_ref.get(transaction=transaction)
            bal = int((st_snap.to_dict() or {}).get("balance", 0))

            # ✅ 국고 되돌리기(원거래가 국고 반영된 경우에만)
            if int(orig_tre_signed) != 0:
                _treasury_apply_in_transaction(
                    transaction,
                    memo=str(rollback_memo),
                    signed_amount=int(-orig_tre_signed),
                    actor="rollback",
                )

            new_bal = bal + rollback_amount
            transaction.update(student_ref, {"balance": new_bal})
            transaction.set(
                rollback_ref,
                {
                    "student_id": student_id,
                    "type": "rollback",
                    "amount": rollback_amount,
                    "balance_after": new_bal,
                    "memo": rollback_memo,
                    "apply_treasury": (int(orig_tre_signed) != 0),
                    "treasury_signed": int(-orig_tre_signed),
                    "treasury_memo": str(rollback_memo),
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
# Savings (적금)
# =========================
def api_savings_list_by_student_id(student_id: str):
    """✅ student_id 기준 적금 목록 조회
    - DB에 start_date 필드가 없을 수도 있어서 order_by 제거(쿼리 실패 방지)
    - maturity_date / maturity_utc, start_date / start_utc 등 스키마 차이도 흡수
    """
    try:
        col = SAV_COL if "SAV_COL" in globals() else "savings"

        sid_str = str(student_id)
        out = []

        def _push_docs(docs_iter):
            for d in docs_iter:
                s = d.to_dict() or {}
                out.append(
                    {
                        "savings_id": d.id,
                        "principal": int(s.get("principal", 0) or 0),
                        "weeks": int(s.get("weeks", 0) or 0),
                        "interest": int(s.get("interest", 0) or 0),

                        # ✅ 둘 중 뭐가 와도 처리
                        "start_date": _to_utc_datetime(s.get("start_date") or s.get("start_utc") or s.get("created_at")),
                        "maturity_date": _to_utc_datetime(s.get("maturity_date") or s.get("maturity_utc")),

                        # ✅ 상태도 스키마 차이 흡수
                        "status": str(s.get("status", "active") or "active"),
                    }
                )

        # 1) student_id가 문자열로 저장된 경우
        docs1 = (
            db.collection(col)
            .where(filter=FieldFilter("student_id", "==", sid_str))
            .limit(50)
            .stream()
        )
        _push_docs(docs1)

        # 2) 결과가 없고, 숫자로 저장된 경우까지 추가 탐색
        if (not out) and sid_str.isdigit():
            sid_int = int(sid_str)
            docs2 = (
                db.collection(col)
                .where(filter=FieldFilter("student_id", "==", sid_int))
                .limit(50)
                .stream()
            )
            _push_docs(docs2)

        # (옵션) 화면용 정렬: start_date 최신순(없으면 맨 뒤)
        out.sort(key=lambda x: (x.get("start_date") is not None, x.get("start_date")), reverse=True)

        return {"ok": True, "savings": out}

    except Exception as e:
        return {"ok": False, "error": str(e), "savings": []}

def api_savings_list(login_name: str, login_pin: str):
    """✅ (사용자) 로그인 정보로 적금 목록 조회"""
    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    return api_savings_list_by_student_id(student_doc.id)


def api_savings_create(login_name: str, login_pin: str, principal: int, weeks: int):
    """✅ (사용자) 적금 가입"""
    principal = int(principal or 0)
    weeks = int(weeks or 0)

    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    if principal <= 0:
        return {"ok": False, "error": "원금은 1 이상이어야 합니다."}
    if principal % 10 != 0:
        return {"ok": False, "error": "원금은 10단위만 가능합니다."}
    if weeks < 1 or weeks > 10:
        return {"ok": False, "error": "기간은 1~10주만 가능합니다."}

    student_ref = db.collection("students").document(student_doc.id)
    savings_ref = db.collection(SAV_COL if "SAV_COL" in globals() else "savings").document()

    # 이자율: 1주=5% (기존 하우스포인트뱅크 로직과 동일)
    rate = float(weeks) * 0.05
    interest = round(principal * rate)
    maturity_date = datetime.now(timezone.utc) + timedelta(days=weeks * 7)

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        bal = int((snap.to_dict() or {}).get("balance", 0) or 0)
        if principal > bal:
            raise ValueError("잔액보다 큰 원금은 가입할 수 없습니다.")
        new_bal = bal - principal
        transaction.update(student_ref, {"balance": new_bal})

        tx_ref = db.collection("transactions").document()
        transaction.set(
            tx_ref,
            {
                "student_id": student_doc.id,
                "type": "withdraw",
                "amount": -principal,
                "balance_after": new_bal,
                "memo": f"적금 가입({weeks}주)",
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        transaction.set(
            savings_ref,
            {
                "student_id": student_doc.id,
                "principal": principal,
                "weeks": weeks,
                "interest": interest,
                "start_date": firestore.SERVER_TIMESTAMP,
                "maturity_date": maturity_date,
                "status": "active",
            },
        )
        return interest, maturity_date

    try:
        interest2, maturity_dt = _do(db.transaction())
        return {"ok": True, "interest": int(interest2), "maturity_datetime": maturity_dt}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"적금 가입 실패: {e}"}


def api_savings_cancel(login_name: str, login_pin: str, savings_id: str):
    """✅ (사용자) 적금 해지 - 원금만 반환"""
    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    savings_id = str(savings_id or "").strip()
    if not savings_id:
        return {"ok": False, "error": "savings_id가 필요합니다."}

    student_ref = db.collection("students").document(student_doc.id)
    savings_ref = db.collection(SAV_COL if "SAV_COL" in globals() else "savings").document(savings_id)

    @firestore.transactional
    def _do(transaction):
        s_snap = savings_ref.get(transaction=transaction)
        if not s_snap.exists:
            raise ValueError("해당 적금을 찾지 못했습니다.")
        s = s_snap.to_dict() or {}
        if str(s.get("student_id", "")) != str(student_doc.id):
            raise ValueError("권한이 없습니다.")
        if str(s.get("status", "")) != "active":
            raise ValueError("이미 처리된 적금입니다.")

        principal = int(s.get("principal", 0) or 0)
        weeks = int(s.get("weeks", 0) or 0)

        st_snap = student_ref.get(transaction=transaction)
        bal = int((st_snap.to_dict() or {}).get("balance", 0) or 0)
        new_bal = bal + principal

        transaction.update(savings_ref, {"status": "canceled"})
        transaction.update(student_ref, {"balance": new_bal})

        tx_ref = db.collection("transactions").document()
        transaction.set(
            tx_ref,
            {
                "student_id": student_doc.id,
                "type": "deposit",
                "amount": principal,
                "balance_after": new_bal,
                "memo": f"적금 해지({weeks}주)",
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return principal

    try:
        refunded = _do(db.transaction())
        return {"ok": True, "refunded": int(refunded)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"해지 실패: {e}"}


def api_process_maturities(login_name: str, login_pin: str):
    """✅ (사용자) 만기 도착한 적금 자동 반환"""
    student_doc = fs_auth_student(login_name, login_pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    student_ref = db.collection("students").document(student_doc.id)
    now = datetime.now(timezone.utc)

    q = (
        db.collection(SAV_COL if "SAV_COL" in globals() else "savings")
        .where(filter=FieldFilter("student_id", "==", student_doc.id))
        .where(filter=FieldFilter("status", "==", "active"))
        .stream()
    )

    matured = []
    for d in q:
        s = d.to_dict() or {}
        m_dt = _to_utc_datetime(s.get("maturity_date"))
        if m_dt and m_dt <= now:
            matured.append((d.id, s))

    if not matured:
        return {"ok": True, "matured_count": 0, "paid_total": 0}

    matured_count, paid_total = 0, 0
    for sid, s in matured:
        principal = int(s.get("principal", 0) or 0)
        interest = int(s.get("interest", 0) or 0)
        amount = principal + interest
        weeks = int(s.get("weeks", 0) or 0)

        savings_ref = db.collection(SAV_COL if "SAV_COL" in globals() else "savings").document(sid)
        tx_ref = db.collection("transactions").document()

        @firestore.transactional
        def _do_one(transaction):
            st_snap = student_ref.get(transaction=transaction)
            bal = int((st_snap.to_dict() or {}).get("balance", 0) or 0)
            new_bal = bal + amount

            transaction.update(student_ref, {"balance": new_bal})
            transaction.update(savings_ref, {"status": "matured"})
            transaction.set(
                tx_ref,
                {
                    "student_id": student_doc.id,
                    "type": "maturity",
                    "amount": amount,
                    "balance_after": new_bal,
                    "memo": f"적금 만기({weeks}주)",
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
            )
            return new_bal

        _do_one(db.transaction())
        matured_count += 1
        paid_total += amount

    return {"ok": True, "matured_count": matured_count, "paid_total": paid_total}

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



# =========================
# ✅ 자동 국고 반영(체크박스용)
#   - 사용자/관리자 거래에서 "국고 반영" 체크 시 사용
#   - 관리자 PIN 없이도 동작(수업용 편의 기능)
# =========================
def _treasury_apply_in_transaction(transaction, memo: str, signed_amount: int, actor: str):
    """signed_amount: +세입 / -세출"""
    memo = str(memo or "").strip()
    signed_amount = int(signed_amount or 0)

    if signed_amount == 0 or (not memo):
        return

    state_ref = db.collection("treasury").document("state")
    led_ref = db.collection("treasury_ledger").document()

    if signed_amount > 0:
        tx_type = "income"
        income = int(signed_amount)
        expense = 0
    else:
        tx_type = "expense"
        income = 0
        expense = int(-signed_amount)

    st_snap = state_ref.get(transaction=transaction)
    cur_bal = 0
    if st_snap.exists:
        cur_bal = int((st_snap.to_dict() or {}).get("balance", 0) or 0)

    new_bal = int(cur_bal + signed_amount)

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
            "amount": int(signed_amount),  # +세입 / -세출
            "income": int(income),
            "expense": int(expense),
            "balance_after": int(new_bal),
            "memo": memo,
            "actor": str(actor or ""),
            "created_at": firestore.SERVER_TIMESTAMP,
        },
    )


def api_add_tx_with_treasury(name, pin, memo, deposit, withdraw, apply_treasury: bool, treasury_memo: str, actor: str = "auto"):
    """학생 거래 + (선택)국고 반영을 한 트랜잭션에서 처리"""
    memo = (memo or "").strip()
    deposit = int(deposit or 0)
    withdraw = int(withdraw or 0)

    if not memo:
        return {"ok": False, "error": "내역이 필요합니다."}
    if (deposit > 0 and withdraw > 0) or (deposit == 0 and withdraw == 0):
        return {"ok": False, "error": "입금/출금 중 하나만 입력하세요."}

    student_doc = fs_auth_student(login_name, login_pin)  # ✅ 기존 로그인 정보 사용(원코드 유지)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    student_ref = db.collection("students").document(student_doc.id)
    tx_ref = db.collection("transactions").document()

    amount = deposit if deposit > 0 else -withdraw
    tx_type = "deposit" if deposit > 0 else "withdraw"

    # ✅ 국고 반영 금액(학생 기준)
    # - 학생 입금  -> 국고 세출(음수)
    # - 학생 출금  -> 국고 세입(양수)
    tre_signed = 0
    if bool(apply_treasury):
        tre_signed = int(withdraw) if tx_type == "withdraw" else -int(deposit)

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        bal = int((snap.to_dict() or {}).get("balance", 0))

        # 일반 출금은 잔액 부족이면 불가
        if tx_type == "withdraw" and bal < withdraw:
            raise ValueError("잔액보다 큰 출금은 불가합니다.")

        # ✅ 국고 반영(같은 트랜잭션) - 반드시 WRITE(학생/tx) 전에 처리(READ 먼저!)
        if tre_signed != 0:
            _treasury_apply_in_transaction(
                transaction,
                memo=str(treasury_memo or memo),
                signed_amount=int(tre_signed),
                actor=str(actor or "auto"),
            )

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
        # 캐시 갱신
        api_get_treasury_state_cached.clear()
        api_list_treasury_ledger_cached.clear()
        return {"ok": True, "balance": new_bal}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"저장 실패: {e}"}


def api_admin_add_tx_by_student_id_with_treasury(admin_pin: str, student_id: str, memo: str, deposit: int, withdraw: int, apply_treasury: bool, treasury_memo: str, actor: str = "admin_auto"):
    """관리자 개별 지급/벌금 + (선택)국고 반영"""
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

    tre_signed = 0
    if bool(apply_treasury):
        tre_signed = int(withdraw) if tx_type == "withdraw" else -int(deposit)

    @firestore.transactional
    def _do(transaction):
        snap = student_ref.get(transaction=transaction)
        bal = int((snap.to_dict() or {}).get("balance", 0))

        # 일반 출금은 잔액 부족이면 불가
        if tx_type == "withdraw" and bal < withdraw:
            raise ValueError("잔액보다 큰 출금은 불가합니다.")

        # ✅ 국고 반영(같은 트랜잭션) - 먼저 처리(READ 먼저, WRITE는 나중)
        if tre_signed != 0:
            _treasury_apply_in_transaction(
                transaction,
                memo=str(treasury_memo or memo),
                signed_amount=int(tre_signed),
                actor=str(actor or "auto"),
            )

        new_bal = bal + amount
        transaction.update(student_ref, {"balance": new_bal})
        transaction.set(
            tx_ref,
            {
                "student_id": str(student_id),
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
        api_get_treasury_state_cached.clear()
        api_list_treasury_ledger_cached.clear()
        api_list_accounts_cached.clear()
        return {"ok": True, "balance": new_bal}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"저장 실패: {e}"}


def api_treasury_auto_bulk_adjust(memo: str, signed_amount: int, actor: str = "admin_bulk_auto"):
    """일괄 지급/벌금 시 국고를 한 번만 합산 반영"""
    memo = str(memo or "").strip()
    signed_amount = int(signed_amount or 0)
    if (not memo) or signed_amount == 0:
        return {"ok": True}

    state_ref = db.collection("treasury").document("state")
    led_ref = db.collection("treasury_ledger").document()

    if signed_amount > 0:
        tx_type = "income"
        income = int(signed_amount)
        expense = 0
    else:
        tx_type = "expense"
        income = 0
        expense = int(-signed_amount)

    @firestore.transactional
    def _do(transaction):
        st_snap = state_ref.get(transaction=transaction)
        cur_bal = 0
        if st_snap.exists:
            cur_bal = int((st_snap.to_dict() or {}).get("balance", 0) or 0)
        new_bal = int(cur_bal + signed_amount)

        transaction.set(
            state_ref,
            {"balance": int(new_bal), "updated_at": firestore.SERVER_TIMESTAMP},
            merge=True,
        )
        transaction.set(
            led_ref,
            {
                "type": tx_type,
                "amount": int(signed_amount),
                "income": int(income),
                "expense": int(expense),
                "balance_after": int(new_bal),
                "memo": memo,
                "actor": str(actor or ""),
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return new_bal

    try:
        _do(db.transaction())
        api_get_treasury_state_cached.clear()
        api_list_treasury_ledger_cached.clear()
        return {"ok": True}
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
def _get_trade_templates_state():
    """전역 실행 시 Firestore read 방지: 템플릿은 함수 내부에서만 조회."""
    tpl_res = api_list_templates_cached()
    templates = tpl_res.get("templates", []) if tpl_res.get("ok") else []
    return {
        "templates": templates,
        "by_display": {template_display_for_trade(t): t for t in templates},
    }

def template_display_for_trade(t):
    kind_kr = "입금" if t["kind"] == "deposit" else "출금"
    return f"{t['label']}[{kind_kr} {int(t['amount'])}]"

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

        # ✅ 국고 반영(항상 사용 가능)
        tre_key = f"{prefix}_treasury_apply"
        st.session_state.setdefault(tre_key, True)   # ✅ 기본 체크(ON)
        st.checkbox("국고 반영", key=tre_key)

        st.caption("⚡ 빠른 금액(누른 만큼 더해지거나 줄어듬, 0은 초기화)")
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

    st.caption("⚡ 빠른 금액(누른 만큼 더해지거나 줄어듬, 0은 초기화)")
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
# 🏷️ 경매
# =========================
AUC_STATE_DOC = "auction_state"

def _fmt_auction_dt(val) -> str:
    dt = _to_utc_datetime(val)
    if not dt:
        return ""
    kst_dt = dt.astimezone(KST)
    ampm = "오전" if kst_dt.hour < 12 else "오후"
    hour12 = kst_dt.hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{kst_dt.year}년 {kst_dt.month:02d}월 {kst_dt.day:02d}일 {ampm} {hour12}시 {kst_dt.minute:02d}분 {kst_dt.second:02d}초"

def _get_auction_state() -> dict:
    snap = db.collection("config").document(AUC_STATE_DOC).get()
    if not snap.exists:
        return {"current_round_no": 0, "current_round_id": "", "status": "idle"}
    d = snap.to_dict() or {}
    return {
        "current_round_no": int(d.get("current_round_no", 0) or 0),
        "current_round_id": str(d.get("current_round_id", "") or ""),
        "status": str(d.get("status", "idle") or "idle"),
    }

def api_get_open_auction_round() -> dict:
    stt = _get_auction_state()
    rid = str(stt.get("current_round_id", "") or "")
    if rid:
        snap = db.collection("auction_rounds").document(rid).get()
        if snap.exists:
            row = snap.to_dict() or {}
            if str(row.get("status", "")).strip() == "open":
                row["round_id"] = snap.id
                return {"ok": True, "round": row}

    try:
        q = (
            db.collection("auction_rounds")
            .where(filter=FieldFilter("status", "==", "open"))
            .order_by("round_no", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for d in q:
            row = d.to_dict() or {}
            row["round_id"] = d.id
            return {"ok": True, "round": row}
    except FailedPrecondition:
        # 복합 인덱스가 아직 준비되지 않은 프로젝트에서도 앱이 중단되지 않도록
        # 정렬 없이 조회한 뒤 round_no 최대값을 선택한다.
        fallback_docs = (
            db.collection("auction_rounds")
            .where(filter=FieldFilter("status", "==", "open"))
            .stream()
        )
        best_row = None
        for d in fallback_docs:
            row = d.to_dict() or {}
            row["round_id"] = d.id
            round_no = int(row.get("round_no", 0) or 0)
            if not best_row or round_no > best_row["round_no"]:
                best_row = {"round_no": round_no, "row": row}
        if best_row:
            return {"ok": True, "round": best_row["row"]}

    return {"ok": False, "error": "진행 중인 경매가 없습니다."}

def api_open_auction(admin_pin: str, bid_name: str, affiliation: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    bid_name = str(bid_name or "").strip()
    affiliation = str(affiliation or "").strip()
    if not bid_name:
        return {"ok": False, "error": "입찰 내역(입찰 이름)을 입력해 주세요."}
    if not affiliation:
        return {"ok": False, "error": "소속을 입력해 주세요."}

    state_ref = db.collection("config").document(AUC_STATE_DOC)
    round_ref = db.collection("auction_rounds").document()

    @firestore.transactional
    def _do(tx):
        st_snap = state_ref.get(transaction=tx)
        st_data = st_snap.to_dict() if st_snap.exists else {}
        cur_no = int((st_data or {}).get("current_round_no", 0) or 0)
        cur_id = str((st_data or {}).get("current_round_id", "") or "")
        cur_status = str((st_data or {}).get("status", "idle") or "idle")

        if cur_status == "open" and cur_id:
            cur_round_snap = db.collection("auction_rounds").document(cur_id).get(transaction=tx)
            if cur_round_snap.exists and str((cur_round_snap.to_dict() or {}).get("status", "")) == "open":
                raise ValueError("이미 진행 중인 경매가 있습니다. 먼저 마감해 주세요.")

        next_no = int(cur_no + 1)
        tx.set(
            round_ref,
            {
                "round_no": next_no,
                "round_code": f"{next_no:02d}",
                "bid_name": bid_name,
                "affiliation": affiliation,
                "status": "open",
                "opened_at": firestore.SERVER_TIMESTAMP,
                "closed_at": None,
                "ledger_applied": False,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        tx.set(
            state_ref,
            {
                "current_round_no": next_no,
                "current_round_id": round_ref.id,
                "status": "open",
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        return next_no, round_ref.id

    try:
        round_no, round_id = _do(db.transaction())
        return {"ok": True, "round_no": int(round_no), "round_id": str(round_id)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"경매 개시 실패: {e}"}

def api_submit_auction_bid(name: str, pin: str, amount: int):
    amount = int(amount or 0)
    if amount < 0:
        return {"ok": False, "error": "입찰 가격은 0 이상이어야 합니다."}

    student_doc = fs_auth_student(name, pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    open_res = api_get_open_auction_round()
    if not open_res.get("ok"):
        return {"ok": False, "error": "진행 중인 경매가 없습니다."}

    round_row = open_res.get("round", {}) or {}
    round_id = str(round_row.get("round_id", "") or "")
    if not round_id:
        return {"ok": False, "error": "경매 정보가 올바르지 않습니다."}

    student_id = str(student_doc.id)
    st_data = student_doc.to_dict() or {}
    student_no = int(st_data.get("no", 0) or 0)
    student_name = str(st_data.get("name", name) or name)

    bid_ref = db.collection("auction_bids").document(f"{round_id}_{student_id}")
    student_ref = db.collection("students").document(student_id)
    round_ref = db.collection("auction_rounds").document(round_id)
    tx_ref = db.collection("transactions").document()

    memo = f"[경매 {int(round_row.get('round_no', 0) or 0):02d}회] {str(round_row.get('bid_name', '') or '')} 입찰 제출"

    @firestore.transactional
    def _do(tx):
        b_snap = bid_ref.get(transaction=tx)
        if b_snap.exists:
            raise ValueError("이미 이번 경매에 입찰표를 제출했습니다.")

        r_snap = round_ref.get(transaction=tx)
        if (not r_snap.exists) or (str((r_snap.to_dict() or {}).get("status", "")) != "open"):
            raise ValueError("경매가 마감되어 제출할 수 없습니다.")

        s_snap = student_ref.get(transaction=tx)
        if not s_snap.exists:
            raise ValueError("학생 계정을 찾을 수 없습니다.")
        bal = int((s_snap.to_dict() or {}).get("balance", 0) or 0)
        if bal < amount:
            raise ValueError("잔액이 부족하여 제출할 수 없습니다.")

        new_bal = int(bal - amount)
        tx.update(student_ref, {"balance": int(new_bal)})
        tx.set(
            tx_ref,
            {
                "student_id": student_id,
                "type": "withdraw",
                "amount": int(-amount),
                "balance_after": int(new_bal),
                "memo": memo,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        tx.set(
            bid_ref,
            {
                "round_id": round_id,
                "round_no": int(round_row.get("round_no", 0) or 0),
                "student_id": student_id,
                "student_no": int(student_no),
                "student_name": student_name,
                "affiliation": str(round_row.get("affiliation", "") or ""),
                "bid_name": str(round_row.get("bid_name", "") or ""),
                "amount": int(amount),
                "submitted_at": firestore.SERVER_TIMESTAMP,
                "status": "submitted",
            },
        )

    try:
        _do(db.transaction())
        return {"ok": True}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"입찰 제출 실패: {e}"}

def api_close_auction(admin_pin: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    open_res = api_get_open_auction_round()
    if not open_res.get("ok"):
        return {"ok": False, "error": "진행 중인 경매가 없습니다."}

    row = open_res.get("round", {}) or {}
    round_id = str(row.get("round_id", "") or "")
    if not round_id:
        return {"ok": False, "error": "경매 정보를 찾지 못했습니다."}

    db.collection("auction_rounds").document(round_id).set(
        {
            "status": "closed",
            "closed_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    db.collection("config").document(AUC_STATE_DOC).set(
        {
            "current_round_id": "",
            "status": "closed",
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return {"ok": True, "round_id": round_id}

def api_list_auction_bids(round_id: str):
    round_id = str(round_id or "").strip()
    if not round_id:
        return {"ok": True, "rows": []}

    q = db.collection("auction_bids").where(filter=FieldFilter("round_id", "==", round_id)).stream()
    rows = []
    for d in q:
        r = d.to_dict() or {}
        dt_utc = _to_utc_datetime(r.get("submitted_at"))
        rows.append(
            {
                "bid_id": d.id,
                "round_no": int(r.get("round_no", 0) or 0),
                "student_id": str(r.get("student_id", "") or ""),
                "student_no": int(r.get("student_no", 0) or 0),
                "student_name": str(r.get("student_name", "") or ""),
                "amount": int(r.get("amount", 0) or 0),
                "submitted_at": dt_utc,
                "submitted_at_text": _fmt_auction_dt(dt_utc),
            }
        )

    rows.sort(key=lambda x: (-int(x.get("amount", 0) or 0), x.get("submitted_at") or datetime.max.replace(tzinfo=timezone.utc)))
    return {"ok": True, "rows": rows}

def api_get_latest_closed_auction_round():
    try:
        q = (
            db.collection("auction_rounds")
            .where(filter=FieldFilter("status", "==", "closed"))
            .order_by("round_no", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for d in q:
            row = d.to_dict() or {}
            row["round_id"] = d.id
            return {"ok": True, "round": row}
    except FailedPrecondition:
        # 복합 인덱스가 아직 준비되지 않은 환경(예: 신규 Streamlit Cloud 배포) 대비
        fallback_docs = (
            db.collection("auction_rounds")
            .where(filter=FieldFilter("status", "==", "closed"))
            .stream()
        )
        best_row = None
        for d in fallback_docs:
            row = d.to_dict() or {}
            row["round_id"] = d.id
            round_no = int(row.get("round_no", 0) or 0)
            if not best_row or round_no > best_row["round_no"]:
                best_row = {"round_no": round_no, "row": row}
        if best_row:
            return {"ok": True, "round": best_row["row"]}
            
    return {"ok": False, "error": "마감된 경매가 없습니다."}

def api_apply_auction_ledger(admin_pin: str, round_id: str, refund_non_winners: bool = False):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    round_id = str(round_id or "").strip()
    if not round_id:
        return {"ok": False, "error": "round_id가 없습니다."}

    r_ref = db.collection("auction_rounds").document(round_id)
    r_snap = r_ref.get()
    if not r_snap.exists:
        return {"ok": False, "error": "경매 회차를 찾지 못했습니다."}

    r = r_snap.to_dict() or {}
    if str(r.get("status", "")) != "closed":
        return {"ok": False, "error": "마감된 경매만 장부 반영할 수 있습니다."}
    if bool(r.get("ledger_applied", False)):
        return {"ok": False, "error": "이미 장부 반영된 경매입니다."}

    bid_res = api_list_auction_bids(round_id)
    bids = list(bid_res.get("rows", []) or [])
    participants = int(len(bids))

    total = int(sum(int(x.get("amount", 0) or 0) for x in bids))
    fee_total = 0
    winner_amount = 0

    if refund_non_winners and bids:
        winner = bids[0]
        winner_amount = int(winner.get("amount", 0) or 0)
        winner_name = str(winner.get("student_name", "") or "")
        
        for bid in bids[1:]:
            refund_amt = int(bid.get("amount", 0) or 0)
            sid = str(bid.get("student_id", "") or "").strip()
            if refund_amt <= 0 or not sid:
                continue

            fee_amt = int(refund_amt // 10)
            payback_amt = int(refund_amt - fee_amt)
            fee_total += int(fee_amt)
            if payback_amt <= 0:
                continue
            
            s_ref = db.collection("students").document(sid)
            s_snap = s_ref.get()
            if not s_snap.exists:
                continue
            bal = int((s_snap.to_dict() or {}).get("balance", 0) or 0)
            new_bal = int(bal + payback_amt)
            s_ref.update({"balance": new_bal})
            db.collection("transactions").document().set(
                {
                    "student_id": sid,
                    "type": "deposit",
                    "amount": int(payback_amt),
                    "balance_after": int(new_bal),
                    "memo": f"[경매 {int(r.get('round_no', 0) or 0):02d}회] 낙찰 실패 입찰금 반환(수수료 10% 차감)",
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )

        tre_total = int(max(winner_amount, 0))
        tre_memo = (
            f"경매 {int(r.get('round_no', 0) or 0)}회 세입(낙찰자만 반영: "
            f"{winner_name} {winner_amount})"
        )
    else:
        tre_total = int(total)
        if bids:
            winner_amount = int(bids[0].get("amount", 0) or 0)
        tre_memo = f"경매 {int(r.get('round_no', 0) or 0)}회 세입"

    if tre_total > 0:
        tre_res = api_add_treasury_tx(ADMIN_PIN, tre_memo, income=tre_total, expense=0, actor="auction")
        if not tre_res.get("ok"):
            return {"ok": False, "error": f"국고 반영 실패: {tre_res.get('error', 'unknown')}"}

    if refund_non_winners and fee_total > 0:
        fee_res = api_add_treasury_tx(
            ADMIN_PIN,
            "낙잘금 수수료 총액",
            income=int(fee_total),
            expense=0,
            actor="auction",
        )
        if not fee_res.get("ok"):
            return {"ok": False, "error": f"국고 반영 실패: {fee_res.get('error', 'unknown')}"}
        tre_total += int(fee_total)
    
    db.collection("auction_admin_ledger").document().set(
        {
            "round_id": round_id,
            "round_no": int(r.get("round_no", 0) or 0),
            "bid_date": _fmt_auction_dt(r.get("opened_at")),
            "bid_name": str(r.get("bid_name", "") or ""),
            "participants": participants,
            "total_bid_amount": int(total),
            "total_amount": int(tre_total),
            "refund_non_winners": bool(refund_non_winners),
            "fee_amount": int(fee_total),
            "winner_amount": int(winner_amount),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )

    r_ref.set({"ledger_applied": True, "ledger_applied_at": firestore.SERVER_TIMESTAMP}, merge=True)
    return {"ok": True, "total": int(tre_total), "participants": participants, "fee_total": int(fee_total)}
    
def api_list_auction_admin_ledger(limit=100):
    q = db.collection("auction_admin_ledger").order_by("created_at", direction=firestore.Query.DESCENDING).limit(int(limit)).stream()
    rows = []
    for d in q:
        x = d.to_dict() or {}
        refund_non_winners = bool(x.get("refund_non_winners", False))
        winner_amount = int(x.get("winner_amount", 0) or 0)
        total_bid_amount = int(x.get("total_bid_amount", x.get("total_amount", 0)) or 0)
        settled_bid_amount = int(winner_amount if refund_non_winners else total_bid_amount)
        rows.append(
            {
                "입찰번호": int(x.get("round_no", 0) or 0),
                "입찰기일": str(x.get("bid_date", "") or ""),
                "입찰 내역": str(x.get("bid_name", "") or ""),
                "입찰 참가수": int(x.get("participants", 0) or 0),
                "입찰금 총액": settled_bid_amount,
                "낙찰금 수수료 총액": int(x.get("fee_amount", 0) or 0),
                "국고 반영 총액": "-" if int(x.get("total_amount", 0) or 0) == 0 else int(x.get("total_amount", 0) or 0),
            }
        )
    return {"ok": True, "rows": rows}

# =========================
# 🍀 복권
# =========================
LOT_STATE_DOC = "lottery_state"

def _fmt_lottery_dt(val) -> str:
    dt = _to_utc_datetime(val)
    if not dt:
        return ""
    kst_dt = dt.astimezone(KST)
    ampm = "오전" if kst_dt.hour < 12 else "오후"
    hour12 = kst_dt.hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{kst_dt.month:02d}월 {kst_dt.day:02d}일 {ampm} {hour12:02d}시 {kst_dt.minute:02d}분 {kst_dt.second:02d}초"

def _fmt_lottery_draw_date(val) -> str:
    dt = _to_utc_datetime(val)
    if not dt:
        return ""
    kst_dt = dt.astimezone(KST)
    weekday_ko = ["월", "화", "수", "목", "금", "토", "일"][kst_dt.weekday()]
    return f"{kst_dt.month}월 {kst_dt.day}일({weekday_ko})"

def _normalize_lottery_numbers(nums) -> list[int]:
    out = []
    for n in (nums or []):
        try:
            x = int(n)
        except Exception:
            continue
        if 1 <= x <= 20:
            out.append(x)
    out = sorted(list(dict.fromkeys(out)))
    return out

@st.cache_data(ttl=5, show_spinner=False)
def _get_lottery_state() -> dict:
    snap = db.collection("config").document(LOT_STATE_DOC).get()
    if not snap.exists:
        return {"current_round_no": 0, "current_round_id": "", "status": "idle"}
    d = snap.to_dict() or {}
    return {
        "current_round_no": int(d.get("current_round_no", 0) or 0),
        "current_round_id": str(d.get("current_round_id", "") or ""),
        "status": str(d.get("status", "idle") or "idle"),
    }

@st.cache_data(ttl=5, show_spinner=False)
def api_get_open_lottery_round() -> dict:
    stt = _get_lottery_state()
    rid = str(stt.get("current_round_id", "") or "")
    if rid:
        snap = db.collection("lottery_rounds").document(rid).get()
        if snap.exists:
            row = snap.to_dict() or {}
            if str(row.get("status", "")).strip() == "open":
                row["round_id"] = snap.id
                return {"ok": True, "round": row}

    try:
        q = (
            db.collection("lottery_rounds")
            .where(filter=FieldFilter("status", "==", "open"))
            .order_by("round_no", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for d in q:
            row = d.to_dict() or {}
            row["round_id"] = d.id
            return {"ok": True, "round": row}
    except FailedPrecondition:
        fallback_docs = db.collection("lottery_rounds").where(filter=FieldFilter("status", "==", "open")).stream()
        best_row = None
        for d in fallback_docs:
            row = d.to_dict() or {}
            row["round_id"] = d.id
            round_no = int(row.get("round_no", 0) or 0)
            if (best_row is None) or (round_no > best_row["round_no"]):
                best_row = {"round_no": round_no, "row": row}
        if best_row:
            return {"ok": True, "round": best_row["row"]}

    return {"ok": False, "error": "개시된 복권이 없습니다."}

def api_open_lottery(admin_pin: str, cfg: dict):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    ticket_price = int(cfg.get("ticket_price", 20) or 20)
    tax_rate = int(cfg.get("tax_rate", 40) or 40)
    first_pct = int(cfg.get("first_pct", 80) or 80)
    second_pct = int(cfg.get("second_pct", 20) or 20)
    third_prize = int(cfg.get("third_prize", 20) or 20)

    if ticket_price <= 1:
        return {"ok": False, "error": "복권 가격은 1보다 커야 합니다."}
    if not (1 <= tax_rate <= 100):
        return {"ok": False, "error": "세금(%)은 1~100 사이여야 합니다."}
    if first_pct < 0 or second_pct < 0 or (first_pct + second_pct != 100):
        return {"ok": False, "error": "1등/2등 당첨 백분율의 합은 100이어야 합니다."}
    if third_prize < 0:
        return {"ok": False, "error": "3등 당첨금은 0 이상이어야 합니다."}

    state_ref = db.collection("config").document(LOT_STATE_DOC)
    round_ref = db.collection("lottery_rounds").document()

    @firestore.transactional
    def _do(tx):
        st_snap = state_ref.get(transaction=tx)
        st_row = st_snap.to_dict() if st_snap.exists else {}
        cur_id = str((st_row or {}).get("current_round_id", "") or "")

        if cur_id:
            cur_ref = db.collection("lottery_rounds").document(cur_id)
            cur_snap = cur_ref.get(transaction=tx)
            if cur_snap.exists:
                cur = cur_snap.to_dict() or {}
                if str(cur.get("status", "")) == "open":
                    raise ValueError("이미 개시된 복권이 있습니다. 먼저 마감해 주세요.")

        next_no = int((st_row or {}).get("current_round_no", 0) or 0) + 1
        tx.set(
            round_ref,
            {
                "round_no": int(next_no),
                "status": "open",
                "ticket_price": int(ticket_price),
                "tax_rate": int(tax_rate),
                "first_pct": int(first_pct),
                "second_pct": int(second_pct),
                "third_prize": int(third_prize),
                "winning_numbers": [],
                "winners": [],
                "payout_done": False,
                "ledger_applied": False,
                "opened_at": firestore.SERVER_TIMESTAMP,
                "closed_at": None,
                "drawn_at": None,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        tx.set(
            state_ref,
            {
                "current_round_no": int(next_no),
                "current_round_id": round_ref.id,
                "status": "open",
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        return next_no

    try:
        no = int(_do(db.transaction()))
        _get_lottery_state.clear()
        api_get_open_lottery_round.clear()
        return {"ok": True, "round_no": no}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"복권 개시 실패: {e}"}

def api_close_lottery(admin_pin: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    state_ref = db.collection("config").document(LOT_STATE_DOC)

    @firestore.transactional
    def _do(tx):
        st_snap = state_ref.get(transaction=tx)
        st_row = st_snap.to_dict() if st_snap.exists else {}
        rid = str((st_row or {}).get("current_round_id", "") or "")
        if not rid:
            raise ValueError("개시된 복권이 없습니다.")

        r_ref = db.collection("lottery_rounds").document(rid)
        r_snap = r_ref.get(transaction=tx)
        if not r_snap.exists:
            raise ValueError("복권 회차를 찾지 못했습니다.")
        r = r_snap.to_dict() or {}
        if str(r.get("status", "")) != "open":
            raise ValueError("진행 중인 복권만 마감할 수 있습니다.")

        tx.update(r_ref, {"status": "closed", "closed_at": firestore.SERVER_TIMESTAMP})
        tx.set(state_ref, {"status": "closed", "updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
        return {"round_id": rid, "round_no": int(r.get("round_no", 0) or 0)}

    try:
        out = _do(db.transaction())
        _get_lottery_state.clear()
        api_get_open_lottery_round.clear()
        return {"ok": True, **out}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"복권 마감 실패: {e}"}

@st.cache_data(ttl=5, show_spinner=False)
def api_list_lottery_entries(round_id: str):
    rid = str(round_id or "").strip()
    if not rid:
        return {"ok": True, "rows": []}

    def _rows_from_stream(stream_docs):
        out = []
        for d in stream_docs:
            x = d.to_dict() or {}
            nums = _normalize_lottery_numbers(x.get("numbers", []))
            out.append(
                {
                    "entry_id": d.id,
                    "round_id": rid,
                    "round_no": int(x.get("round_no", 0) or 0),
                    "student_id": str(x.get("student_id", "") or ""),
                    "student_no": int(x.get("student_no", 0) or 0),
                    "student_name": str(x.get("student_name", "") or ""),
                    "numbers": nums,
                    "numbers_text": ", ".join([f"{n:02d}" for n in nums]),
                    "submitted_at": x.get("submitted_at"),
                    "submitted_at_text": _fmt_lottery_dt(x.get("submitted_at")),
                    "is_admin": bool(x.get("is_admin", False)),
                    "treasury_applied": bool(x.get("treasury_applied", False)),
                }
            )
        return out

    try:
        q = (
            db.collection("lottery_entries")
            .where(filter=FieldFilter("round_id", "==", rid))
            .order_by("submitted_at", direction=firestore.Query.ASCENDING)
            .stream()
        )
        rows = _rows_from_stream(q)
    except FailedPrecondition:
        # 복합 인덱스가 없어도 동작하도록 서버 정렬 없이 조회 후 앱에서 정렬
        q = db.collection("lottery_entries").where(filter=FieldFilter("round_id", "==", rid)).stream()
        rows = _rows_from_stream(q)
        rows.sort(
            key=lambda r: (
                r.get("submitted_at") is None,
                r.get("submitted_at") or datetime.min.replace(tzinfo=timezone.utc),
                str(r.get("entry_id", "") or ""),
            )
        )

    return {"ok": True, "rows": rows}


@st.cache_data(ttl=5, show_spinner=False)
def api_list_lottery_entries_by_student(student_id: str, round_id: str = ""):
    sid = str(student_id or "").strip()
    if not sid:
        return {"ok": True, "rows": []}

    rid = str(round_id or "").strip()
    
    q_ref = db.collection("lottery_entries").where(filter=FieldFilter("student_id", "==", sid))
    if rid:
        q_ref = q_ref.where(filter=FieldFilter("round_id", "==", rid))
    
    rows = []
    try:
        q = q_ref.order_by("submitted_at", direction=firestore.Query.DESCENDING).stream()
        for d in q:
            x = d.to_dict() or {}
            rows.append(
                {
                    "회차": int(x.get("round_no", 0) or 0),
                    "번호": int(x.get("student_no", 0) or 0),
                    "이름": str(x.get("student_name", "") or ""),
                    "복권 참여 번호": ", ".join([f"{n:02d}" for n in _normalize_lottery_numbers(x.get("numbers", []))]),
                    "_submitted_at": x.get("submitted_at"),
                }
            )
    except FailedPrecondition:
        q = q_ref.stream()
        for d in q:
            x = d.to_dict() or {}
            rows.append(
                {
                    "회차": int(x.get("round_no", 0) or 0),
                    "번호": int(x.get("student_no", 0) or 0),
                    "이름": str(x.get("student_name", "") or ""),
                    "복권 참여 번호": ", ".join([f"{n:02d}" for n in _normalize_lottery_numbers(x.get("numbers", []))]),
                    "_submitted_at": x.get("submitted_at"),
                }
            )

    if rows:
        rows.sort(
            key=lambda r: _to_utc_datetime(r.get("_submitted_at")).timestamp() if r.get("_submitted_at") else float("-inf"),
            reverse=True,
        )
        for r in rows:
            r.pop("_submitted_at", None)
    return {"ok": True, "rows": rows}

def api_submit_lottery_entry(name: str, pin: str, numbers: list[int]):
    student_doc = fs_auth_student(name, pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    nums = _normalize_lottery_numbers(numbers)
    if len(nums) != 4:
        return {"ok": False, "error": "1~20 숫자 중 중복 없이 4개를 선택해 주세요."}

    op = api_get_open_lottery_round()
    if not op.get("ok"):
        return {"ok": False, "error": "개시된 복권이 없습니다."}
    rnd = op.get("round", {}) or {}
    rid = str(rnd.get("round_id", "") or "")
    round_no = int(rnd.get("round_no", 0) or 0)
    price = int(rnd.get("ticket_price", 20) or 20)
    if price <= 0:
        return {"ok": False, "error": "복권 가격 설정이 올바르지 않습니다."}

    student_ref = db.collection("students").document(student_doc.id)
    round_ref = db.collection("lottery_rounds").document(rid)
    entry_ref = db.collection("lottery_entries").document()
    tx_ref = db.collection("transactions").document()

    @firestore.transactional
    def _do(tx):
        r_snap = round_ref.get(transaction=tx)
        if not r_snap.exists:
            raise ValueError("복권 회차를 찾지 못했습니다.")
        r = r_snap.to_dict() or {}
        if str(r.get("status", "")) != "open":
            raise ValueError("마감된 복권은 구매할 수 없습니다.")

        s_snap = student_ref.get(transaction=tx)
        if not s_snap.exists:
            raise ValueError("학생 계정을 찾지 못했습니다.")
        s = s_snap.to_dict() or {}
        bal = int(s.get("balance", 0) or 0)
        if bal < price:
            raise ValueError("잔액이 부족하여 복권을 구매할 수 없습니다.")

        new_bal = int(bal - price)
        tx.update(student_ref, {"balance": new_bal})
        tx.set(
            tx_ref,
            {
                "student_id": student_doc.id,
                "type": "withdraw",
                "amount": int(-price),
                "balance_after": int(new_bal),
                "memo": f"복권 {int(round_no)}회 구매",
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        tx.set(
            entry_ref,
            {
                "round_id": rid,
                "round_no": int(round_no),
                "student_id": student_doc.id,
                "student_no": int(s.get("no", 0) or 0),
                "student_name": str(s.get("name", "") or name),
                "numbers": nums,
                "submitted_at": firestore.SERVER_TIMESTAMP,
                "ticket_price": int(price),
            },
        )
        return new_bal

    try:
        nb = int(_do(db.transaction()))
        api_list_lottery_entries.clear()
        api_list_lottery_entries_by_student.clear()
        api_get_open_lottery_round.clear()
        return {"ok": True, "balance": nb}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"복권 구매 실패: {e}"}

def api_submit_lottery_entries(name: str, pin: str, games: list[list[int]]):
    student_doc = fs_auth_student(name, pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}

    normalized_games = []
    for g in (games or []):
        nums = _normalize_lottery_numbers(g)
        if len(nums) != 4:
            return {"ok": False, "error": "각 게임은 1~20 숫자 중 중복 없이 4개여야 합니다."}
        normalized_games.append(nums)

    if not normalized_games:
        return {"ok": False, "error": "구매할 게임이 없습니다."}

    op = api_get_open_lottery_round()
    if not op.get("ok"):
        return {"ok": False, "error": "개시된 복권이 없습니다."}
    rnd = op.get("round", {}) or {}
    rid = str(rnd.get("round_id", "") or "")
    round_no = int(rnd.get("round_no", 0) or 0)
    price = int(rnd.get("ticket_price", 20) or 20)
    if price <= 0:
        return {"ok": False, "error": "복권 가격 설정이 올바르지 않습니다."}

    total_price = int(price * len(normalized_games))
    student_ref = db.collection("students").document(student_doc.id)
    round_ref = db.collection("lottery_rounds").document(rid)
    tx_ref = db.collection("transactions").document()

    @firestore.transactional
    def _do(tx):
        r_snap = round_ref.get(transaction=tx)
        if not r_snap.exists:
            raise ValueError("복권 회차를 찾지 못했습니다.")
        r = r_snap.to_dict() or {}
        if str(r.get("status", "")) != "open":
            raise ValueError("마감된 복권은 구매할 수 없습니다.")

        s_snap = student_ref.get(transaction=tx)
        if not s_snap.exists:
            raise ValueError("학생 계정을 찾지 못했습니다.")
        s = s_snap.to_dict() or {}
        bal = int(s.get("balance", 0) or 0)
        if bal < total_price:
            raise ValueError("잔액이 부족하여 복권을 구매할 수 없습니다.")

        new_bal = int(bal - total_price)
        tx.update(student_ref, {"balance": new_bal})
        tx.set(
            tx_ref,
            {
                "student_id": student_doc.id,
                "type": "withdraw",
                "amount": int(-total_price),
                "balance_after": int(new_bal),
                "memo": f"복권 {int(round_no)}회 {len(normalized_games)}게임 구매",
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )

        for nums in normalized_games:
            entry_ref = db.collection("lottery_entries").document()
            tx.set(
                entry_ref,
                {
                    "round_id": rid,
                    "round_no": int(round_no),
                    "student_id": student_doc.id,
                    "student_no": int(s.get("no", 0) or 0),
                    "student_name": str(s.get("name", "") or name),
                    "numbers": nums,
                    "submitted_at": firestore.SERVER_TIMESTAMP,
                    "ticket_price": int(price),
                },
            )
        return new_bal

    try:
        nb = int(_do(db.transaction()))
        api_list_lottery_entries.clear()
        api_list_lottery_entries_by_student.clear()
        api_get_open_lottery_round.clear()
        return {"ok": True, "balance": nb, "count": len(normalized_games)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"복권 구매 실패: {e}"}

def _generate_admin_lottery_numbers(game_count: int) -> list[list[int]]:
    games = []
    for _ in range(max(int(game_count), 0)):
        nums = sorted(random.sample(range(1, 21), 4))
        games.append(nums)
    return games


def api_submit_admin_lottery_entries(admin_pin: str, game_count: int, apply_treasury: bool = True):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}

    count = int(game_count or 0)
    if count <= 0:
        return {"ok": False, "error": "복권 참여 수는 1 이상이어야 합니다."}

    op = api_get_open_lottery_round()
    if not op.get("ok"):
        return {"ok": False, "error": "개시된 복권이 없습니다."}

    rnd = op.get("round", {}) or {}
    rid = str(rnd.get("round_id", "") or "")
    round_no = int(rnd.get("round_no", 0) or 0)
    price = int(rnd.get("ticket_price", 20) or 20)
    if price <= 0:
        return {"ok": False, "error": "복권 가격 설정이 올바르지 않습니다."}

    numbers_games = _generate_admin_lottery_numbers(count)
    total_cost = int(max(price, 0) * count)

    round_ref = db.collection("lottery_rounds").document(rid)

    @firestore.transactional
    def _do(tx):
        r_snap = round_ref.get(transaction=tx)
        if not r_snap.exists:
            raise ValueError("복권 회차를 찾지 못했습니다.")
        r = r_snap.to_dict() or {}
        if str(r.get("status", "")) != "open":
            raise ValueError("마감된 복권은 구매할 수 없습니다.")

        if bool(apply_treasury) and total_cost > 0:
            _treasury_apply_in_transaction(
                tx,
                memo=f"복권 {int(round_no)}회 관리자 참여금",
                signed_amount=int(-total_cost),
                actor="lottery_admin",
            )
        
        for nums in numbers_games:
            entry_ref = db.collection("lottery_entries").document()
            tx.set(
                entry_ref,
                {
                    "round_id": rid,
                    "round_no": int(round_no),
                    "student_id": "",
                    "student_no": 0,
                    "student_name": ADMIN_NAME,
                    "numbers": nums,
                    "submitted_at": firestore.SERVER_TIMESTAMP,
                    "ticket_price": int(price),
                    "is_admin": True,
                    "treasury_applied": bool(apply_treasury),
                },
            )

    try:
        _do(db.transaction())
        api_get_treasury_state_cached.clear()
        api_list_treasury_ledger_cached.clear()
        api_list_lottery_entries.clear()
        api_list_lottery_entries_by_student.clear()
        api_get_open_lottery_round.clear()
        return {
            "ok": True,
            "count": count,
            "numbers": numbers_games,
            "total_cost": int(total_cost),
            "treasury_applied": bool(apply_treasury),
        }
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"관리자 복권 참여 실패: {e}"}
        

def api_draw_lottery(admin_pin: str, round_id: str, winning_numbers: list[int]):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    rid = str(round_id or "").strip()
    if not rid:
        return {"ok": False, "error": "round_id가 없습니다."}

    win_nums = _normalize_lottery_numbers(winning_numbers)
    if len(win_nums) != 4:
        return {"ok": False, "error": "당첨번호는 1~20 숫자 중 중복 없이 4개여야 합니다."}

    r_ref = db.collection("lottery_rounds").document(rid)
    r_snap = r_ref.get()
    if not r_snap.exists:
        return {"ok": False, "error": "복권 회차를 찾지 못했습니다."}
    rnd = r_snap.to_dict() or {}
    if str(rnd.get("status", "")) not in ("closed", "drawn"):
        return {"ok": False, "error": "마감된 복권만 추첨할 수 있습니다."}

    entries = api_list_lottery_entries(rid).get("rows", [])
    ticket_price = int(rnd.get("ticket_price", 20) or 20)
    tax_rate = int(rnd.get("tax_rate", 40) or 40)
    first_pct = int(rnd.get("first_pct", 80) or 80)
    second_pct = int(rnd.get("second_pct", 20) or 20)
    third_prize = int(rnd.get("third_prize", 20) or 20)

    total_sales = int(ticket_price * len(entries))
    winners3 = []
    winners2 = []
    winners1 = []
    for e in entries:
        nums = _normalize_lottery_numbers(e.get("numbers", []))
        match = len(set(nums) & set(win_nums))
        row = {
            "student_id": str(e.get("student_id", "") or ""),
            "student_no": int(e.get("student_no", 0) or 0),
            "student_name": str(e.get("student_name", "") or ""),
            "is_admin": bool(e.get("is_admin", False)),
            "numbers": nums,
            "match_count": int(match),
            "submitted_at": e.get("submitted_at"),
            "submitted_at_text": str(e.get("submitted_at_text", "") or ""),
        }
        if match == 2:
            winners3.append(row)
        elif match == 3:
            winners2.append(row)
        elif match == 4:
            winners1.append(row)

    third_total = int(len(winners3) * third_prize)
    base_pool = max(int(total_sales - third_total), 0)

    first_gross_total = int(round(base_pool * (first_pct / 100.0), 0))
    second_gross_total = int(round(base_pool * (second_pct / 100.0), 0))

    first_net_total = int(round(first_gross_total * (1.0 - (tax_rate / 100.0)), 0))
    second_net_total = int(round(second_gross_total * (1.0 - (tax_rate / 100.0)), 0))

    first_each = int(round(first_net_total / len(winners1), 0)) if winners1 else 0
    second_each = int(round(second_net_total / len(winners2), 0)) if winners2 else 0

    winner_rows = []
    for x in winners1:
        winner_rows.append({**x, "rank": 1, "prize": int(first_each)})
    for x in winners2:
        winner_rows.append({**x, "rank": 2, "prize": int(second_each)})
    for x in winners3:
        winner_rows.append({**x, "rank": 3, "prize": int(third_prize)})
    winner_rows.sort(key=lambda x: (int(x.get("rank", 9) or 9), int(x.get("student_no", 0) or 0)))

    payout_total = int(sum(int(x.get("prize", 0) or 0) for x in winner_rows))
    # 세금 계산식(요청사항):
    # (총액-3등총액)*1등백분율*0.01*(세금백분율*0.01)
    # +(총액-3등총액)*2등백분율*0.01*(세금백분율*0.01)
    first_tax_total = int(round(base_pool * (first_pct / 100.0) * (tax_rate / 100.0), 0)) if winners1 else 0
    second_tax_total = int(round(base_pool * (second_pct / 100.0) * (tax_rate / 100.0), 0)) if winners2 else 0
    tax_total = int(first_tax_total + second_tax_total)

    participant_keys = set()
    for e in entries:
        sid = str(e.get("student_id", "") or "").strip()
        if sid:
            participant_keys.add(f"sid:{sid}")
            continue
        sno = int(e.get("student_no", 0) or 0)
        sname = str(e.get("student_name", "") or "").strip()
        if sno > 0:
            participant_keys.add(f"sno:{sno}")
        elif sname:
            participant_keys.add(f"name:{sname}")
    participant_count = int(len(participant_keys))
    r_ref.set(
        {
            "status": "drawn",
            "winning_numbers": win_nums,
            "winners": winner_rows,
            "total_sales": int(total_sales),
            "participants": int(participant_count),
            "ticket_count": int(len(entries)),
            "payout_total": int(payout_total),
            "tax_total": int(tax_total),
            "drawn_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    api_list_lottery_entries.clear()
    api_get_open_lottery_round.clear()
    return {"ok": True, "winners": winner_rows}

def api_pay_lottery_prizes(admin_pin: str, round_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    rid = str(round_id or "").strip()
    if not rid:
        return {"ok": False, "error": "round_id가 없습니다."}

    r_ref = db.collection("lottery_rounds").document(rid)
    snap = r_ref.get()
    if not snap.exists:
        return {"ok": False, "error": "복권 회차를 찾지 못했습니다."}
    r = snap.to_dict() or {}
    if str(r.get("status", "")) != "drawn":
        return {"ok": False, "error": "당첨번호 제출 후에 당첨금 지급이 가능합니다."}
    if bool(r.get("payout_done", False)):
        return {"ok": False, "error": "이미 당첨금 지급이 완료된 회차입니다."}

    winners = list(r.get("winners", []) or [])
    paid_total = 0
    for w in winners:
        sid = str(w.get("student_id", "") or "")
        prize = int(w.get("prize", 0) or 0)
        rank = int(w.get("rank", 0) or 0)
        if (not sid) or prize <= 0:
            continue
        res = api_admin_add_tx_by_student_id(
            ADMIN_PIN,
            sid,
            memo=f"복권 {int(r.get('round_no', 0) or 0)}회 {rank}등 당첨금",
            deposit=int(prize),
            withdraw=0,
        )
        if not res.get("ok"):
            return {"ok": False, "error": f"당첨금 지급 실패: {res.get('error', 'unknown')}"}
        paid_total += int(prize)

    r_ref.set(
        {
            "payout_done": True,
            "payout_done_at": firestore.SERVER_TIMESTAMP,
            "payout_total": int(paid_total),
        },
        merge=True,
    )
    api_list_lottery_entries.clear()
    api_list_lottery_entries_by_student.clear()
    return {"ok": True, "paid_total": int(paid_total)}

def _calc_lottery_financials(round_row: dict) -> dict:
    r = round_row or {}
    winners = list(r.get("winners", []) or [])
    total_sales = int(r.get("total_sales", 0) or 0)

    payout_total = int(sum(int(w.get("prize", 0) or 0) for w in winners))
    admin_winning_total = int(
        sum(
            int(w.get("prize", 0) or 0)
            for w in winners
            if bool(w.get("is_admin", False))
            or (
                not str(w.get("student_id", "") or "").strip()
                and str(w.get("student_name", "") or "").strip() == ADMIN_NAME
            )
        )
    )

    tax_rate = int(r.get("tax_rate", 40) or 40)
    first_pct = int(r.get("first_pct", 80) or 80)
    second_pct = int(r.get("second_pct", 20) or 20)
    third_prize = int(r.get("third_prize", 20) or 20)

    third_winner_count = int(sum(1 for w in winners if int(w.get("rank", 0) or 0) == 3))
    third_total = int(third_prize * third_winner_count)
    base_pool = max(int(total_sales - third_total), 0)

    first_winner_count = int(sum(1 for w in winners if int(w.get("rank", 0) or 0) == 1))
    second_winner_count = int(sum(1 for w in winners if int(w.get("rank", 0) or 0) == 2))

    first_tax_total = int(round(base_pool * (first_pct / 100.0) * (tax_rate / 100.0), 0)) if first_winner_count > 0 else 0
    second_tax_total = int(round(base_pool * (second_pct / 100.0) * (tax_rate / 100.0), 0)) if second_winner_count > 0 else 0
    tax_total = int(first_tax_total + second_tax_total)
    national_amount = int(total_sales - payout_total)

    return {
        "payout_total": int(payout_total),
        "tax_total": int(tax_total),
        "national_amount": int(national_amount),
        "admin_winning_total": int(admin_winning_total),
    }


def api_apply_lottery_ledger(admin_pin: str, round_id: str):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    rid = str(round_id or "").strip()
    if not rid:
        return {"ok": False, "error": "round_id가 없습니다."}

    r_ref = db.collection("lottery_rounds").document(rid)
    snap = r_ref.get()
    if not snap.exists:
        return {"ok": False, "error": "복권 회차를 찾지 못했습니다."}
    r = snap.to_dict() or {}

    if bool(r.get("ledger_applied", False)):
        return {"ok": False, "error": "이미 장부 반영된 회차입니다."}

    round_no = int(r.get("round_no", 0) or 0)
    participants = int(r.get("participants", 0) or 0)
    ticket_count = int(r.get("ticket_count", participants) or participants)
    total_sales = int(r.get("total_sales", 0) or 0)

    financials = _calc_lottery_financials(r)
    payout_total = int(financials.get("payout_total", 0) or 0)
    tax_total = int(financials.get("tax_total", 0) or 0)
    national_amount = int(financials.get("national_amount", 0) or 0)
    admin_winning_total = int(financials.get("admin_winning_total", 0) or 0)
    
    # 레거시 회차 보정: 참여자 수는 "복권 수"가 아닌 "실제 참여 학생 수"로 유지
    if participants <= 0:
        entries = api_list_lottery_entries(rid).get("rows", [])
        participant_keys = set()
        for e in entries:
            sid = str(e.get("student_id", "") or "").strip()
            if sid:
                participant_keys.add(f"sid:{sid}")
                continue
            sno = int(e.get("student_no", 0) or 0)
            sname = str(e.get("student_name", "") or "").strip()
            if sno > 0:
                participant_keys.add(f"sno:{sno}")
            elif sname:
                participant_keys.add(f"name:{sname}")
        participants = int(len(participant_keys))

    if national_amount > 0:
        tre_res = api_add_treasury_tx(ADMIN_PIN, f"복권 {round_no}회 국고 반영", income=national_amount, expense=0, actor="lottery")
        if not tre_res.get("ok"):
            return {"ok": False, "error": f"국고 반영 실패: {tre_res.get('error', 'unknown')}"}

    if admin_winning_total > 0:
        admin_win_res = api_add_treasury_tx(
            ADMIN_PIN,
            f"복권 {round_no}회 관리자 당첨금 총액",
            income=admin_winning_total,
            expense=0,
            actor="lottery_admin",
        )
        if not admin_win_res.get("ok"):
            return {"ok": False, "error": f"관리자 당첨금 국고 반영 실패: {admin_win_res.get('error', 'unknown')}"}
            
    db.collection("lottery_admin_ledger").document().set(
        {
            "round_id": rid,
            "round_no": round_no,
            "participants": int(participants),
            "ticket_count": int(ticket_count),
            "total_sales": int(total_sales),
            "payout_total": int(payout_total),
            "tax_total": int(tax_total),
            "national_amount": int(national_amount),
            "admin_winning_total": int(admin_winning_total),
            "drawn_at": r.get("drawn_at"),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    r_ref.set({"ledger_applied": True, "ledger_applied_at": firestore.SERVER_TIMESTAMP}, merge=True)
    return {"ok": True}


def api_list_lottery_admin_ledger(limit=200):
    q = db.collection("lottery_admin_ledger").order_by("round_no", direction=firestore.Query.DESCENDING).limit(int(limit)).stream()
    rows = []
    for d in q:
        x = d.to_dict() or {}
        rid = str(x.get("round_id", "") or "").strip()
        
        payout_total = int(x.get("payout_total", 0) or 0)
        tax_total = int(x.get("tax_total", 0) or 0)
        national_amount = int(x.get("national_amount", 0) or 0)
        admin_winning_total = int(x.get("admin_winning_total", 0) or 0)

        if rid:
            r_snap = db.collection("lottery_rounds").document(rid).get()
            if r_snap.exists:
                r = r_snap.to_dict() or {}
                financials = _calc_lottery_financials(r)
                payout_total = int(financials.get("payout_total", payout_total) or payout_total)
                tax_total = int(financials.get("tax_total", tax_total) or tax_total)
                national_amount = int(financials.get("national_amount", national_amount) or national_amount)
                admin_winning_total = int(financials.get("admin_winning_total", admin_winning_total) or admin_winning_total)
                
                # 기존 장부 데이터가 잘못 저장된 경우 조회 시 자동 보정
                if (
                    payout_total != int(x.get("payout_total", 0) or 0)
                    or tax_total != int(x.get("tax_total", 0) or 0)
                    or national_amount != int(x.get("national_amount", 0) or 0)
                    or admin_winning_total != int(x.get("admin_winning_total", 0) or 0)
                ):
                    d.reference.set(
                        {
                            "payout_total": int(payout_total),
                            "tax_total": int(tax_total),
                            "national_amount": int(national_amount),
                            "admin_winning_total": int(admin_winning_total),
                            "updated_at": firestore.SERVER_TIMESTAMP,
                        },
                        merge=True,
                    )
                    
        rows.append(
            {
                "회차": int(x.get("round_no", 0) or 0),
                "복권추첨일": _fmt_lottery_draw_date(x.get("drawn_at") or x.get("created_at")),
                "참여자 수": int(x.get("participants", 0) or 0),
                "참여 복권 수": int(x.get("ticket_count", 0) or 0),
                "총 액수": int(x.get("total_sales", 0) or 0),
                "당첨금 지급 총액": ("-" if payout_total <= 0 else payout_total),
                "세금": ("-" if tax_total <= 0 else tax_total),
                "국고 반영액": int(national_amount),
            }
        )
    return {"ok": True, "rows": rows}

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
    """로그인 계정의 최종 권한 집합을 반환합니다.
    - 관리자: admin_all
    - 학생: roles 기반 permissions + students.extra_permissions(개별 추가 권한)
    """
    if is_admin:
        return {"admin_all"}
    if not student_id:
        return set()

    snap = db.collection("students").document(student_id).get()
    if not snap.exists:
        return set()

    sd = snap.to_dict() or {}

    # 1) 역할(role) 기반 권한
    perms = set()
    role_id = str(sd.get("role_id", "") or "")
    if role_id:
        rdoc = db.collection("roles").document(role_id).get()
        if rdoc.exists:
            perms |= set((rdoc.to_dict() or {}).get("permissions", []) or [])

    # 2) 학생 개별 추가 권한 (A안)
    extra = sd.get("extra_permissions", []) or []
    if isinstance(extra, list):
        perms |= set([str(x) for x in extra if str(x).strip()])

    return perms

def can(perms: set, need: str) -> bool:
    return ("admin_all" in perms) or (need in perms)


def has_tab_access(perms: set, tab_name: str, is_admin: bool) -> bool:
    """탭(화면) 접근 권한: 관리자이거나 students.extra_permissions에 tab::<탭이름>이 있으면 True"""
    if is_admin:
        return True
    return f"tab::{tab_name}" in perms

def has_admin_feature_access(perms: set, tab_name: str, is_admin: bool) -> bool:
    """탭은 기본으로 보여도, '관리자 기능(관리 UI)'을 열어줄 때 쓰는 권한.
    - 관리자: True
    - 학생: students.extra_permissions에 admin::<탭이름>이 있으면 True
    """
    if is_admin:
        return True
    return f"admin::{tab_name}" in perms


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

    stu_name = st.text_input("이름(계정)", key="sb_stu_pw_name").strip()
    old_pin = st.text_input("기존 비밀번호(4자리)", type="password", key="sb_stu_pw_old").strip()
    new_pin1 = st.text_input("새 비밀번호(4자리)", type="password", key="sb_stu_pw_new1").strip()
    new_pin2 = st.text_input("새 비밀번호(확인)", type="password", key="sb_stu_pw_new2").strip()

    if st.button("비밀번호 변경(학생)", key="sb_stu_pw_change_btn", use_container_width=True):
        if not stu_name:
            st.error("이름(계정)을 입력해 주세요.")
        elif not pin_ok(old_pin):
            st.error("기존 비밀번호는 4자리여야 해요.")
        elif not pin_ok(new_pin1) or not pin_ok(new_pin2):
            st.error("새 비밀번호는 4자리여야 해요.")
        elif new_pin1 != new_pin2:
            st.error("새 비밀번호와 확인이 일치하지 않습니다.")
        elif old_pin == new_pin1:
            st.error("새 비밀번호는 기존 비밀번호와 달라야 합니다.")
        else:
            res = api_change_pin_student(stu_name, old_pin, new_pin1)
            if res.get("ok"):
                toast("비밀번호 변경 완료!", icon="✅")
                st.session_state.pop("sb_stu_pw_name", None)
                st.session_state.pop("sb_stu_pw_old", None)
                st.session_state.pop("sb_stu_pw_new1", None)
                st.session_state.pop("sb_stu_pw_new2", None)
                st.rerun()
            else:
                st.error(res.get("error", "비밀번호 변경 실패"))

    st.divider()

    
    st.header("🔐 [관리자] 계정생성 / PIN변경 / 삭제")

    # ✅ 공통 입력(한 블록으로 통합)
    admin_manage_pin = st.text_input("관리자 비밀번호", type="password", key="admin_manage_pin").strip()
    manage_name = st.text_input("이름(계정)", key="manage_name").strip()
    manage_pin = st.text_input("비밀번호(4자리)", type="password", key="manage_pin").strip()
    
    # ✅ 공통 체크(관리자 비번)
    def _admin_guard():
        if not admin_manage_pin:
            st.error("관리자 비밀번호를 입력해 주세요.")
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
            return {"ok": False, "error": "새 비밀번호는 4자리여야 합니다."}

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
                st.error("비밀번호는 4자리여야 해요. (예: ab7@)")
            else:
                # ✅ 새 계정은 '마지막 번호 + 1'로 저장 (students.no 사용)
                if fs_get_student_doc_by_name(manage_name):
                    st.error("이미 존재하는 계정입니다.")
                else:
                    # 현재 활성 계정 중 최대 번호 찾기
                    max_no = 0
                    for x in _list_active_students_full_cached():
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
                    _list_active_students_full_cached.clear()
                    st.rerun()

    with c2:
        if st.button("PIN 변경", key="btn_pin_change", use_container_width=True):
            if not _admin_guard():
                st.stop()
            if not manage_name:
                st.error("이름을 입력해 주세요.")
            elif not pin_ok(manage_pin):
                st.error("새 비밀번호는 4자리여야 해요.")
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
                    st.error("비밀번호는 4자리여야 해요.")
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


# =========================
# Main: 로그인 (너 코드 방식 유지: form)
# =========================
# =========================
# Main: 로그인 (너 코드 방식 유지: form)
# =========================
if st.session_state.get("logged_in", False):
    _who = str(st.session_state.get("login_name", "") or "").strip()
    st.subheader(f"🔐 로그인({_who})" if _who else "🔐 로그인")
else:
    st.subheader("🔐 로그인")

if not st.session_state.logged_in:
    # ✅ 이름 저장(체크 시 URL에 저장되어 다음에도 자동 입력)
    _saved_name = ""
    _remember_default = False
    try:
        _saved_name = str(st.query_params.get("saved_name", "") or "")
        _remember_default = bool(str(st.query_params.get("remember", "") or "") == "1" and _saved_name)
    except Exception:
        _saved_name = ""
        _remember_default = False

    if _saved_name and not str(st.session_state.get("login_name_input", "") or "").strip():
        st.session_state["login_name_input"] = _saved_name

    with st.form("login_form", clear_on_submit=False):
        login_c1, login_c2, login_c3 = st.columns([2, 2, 1])
        with login_c1:
            login_name = st.text_input("이름", key="login_name_input").strip()
        with login_c2:
            login_pin = st.text_input("비밀번호", type="password", key="login_pin_input").strip()
        with login_c3:
            login_btn = st.form_submit_button("로그인", use_container_width=True)

    if login_btn:
        if not login_name:
            st.error("이름을 입력해 주세요.")
        elif is_admin_login(login_name, login_pin):
            st.session_state.admin_ok = True
            st.session_state.logged_in = True
            st.session_state.login_name = ADMIN_NAME
            st.session_state.login_pin = ADMIN_PIN
            st.session_state["login_student_ctx"] = {}
            # ✅ 이름 저장 처리
            try:
                if bool(st.session_state.get("remember_name_check", False)):
                    st.query_params["saved_name"] = login_name
                    st.query_params["remember"] = "1"
                else:
                    st.query_params.pop("saved_name", None)
                    st.query_params.pop("remember", None)
            except Exception:
                pass
            toast("관리자 모드 ON", icon="🔓")
            st.rerun()
        elif not pin_ok(login_pin):
            st.error("학생 비밀번호는 4자리여야 해요.")
        else:
            doc = fs_auth_student(login_name, login_pin)
            if not doc:
                st.error("이름 또는 비밀번호가 틀립니다.")
            else:
                st.session_state.admin_ok = False
                st.session_state.logged_in = True
                st.session_state.login_name = login_name
                st.session_state.login_pin = login_pin
                _set_login_student_context_from_doc(doc)
            # ✅ 이름 저장 처리
            try:
                if bool(st.session_state.get("remember_name_check", False)):
                    st.query_params["saved_name"] = login_name
                    st.query_params["remember"] = "1"
                else:
                    st.query_params.pop("saved_name", None)
                    st.query_params.pop("remember", None)
            except Exception:
                pass
            toast("로그인 완료!", icon="✅")
            st.rerun()

else:
    if st.button("로그아웃", key="logout_btn", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.admin_ok = False
        st.session_state.login_name = ""
        st.session_state.login_pin = ""
        st.session_state.undo_mode = False
        st.session_state["login_student_ctx"] = {}

        # ✅ (PATCH) 개별조회 지연로딩 상태 완전 초기화 (로그아웃 후 재로그인 시 자동 로드 방지)
        st.session_state.pop("admin_ind_view_loaded", None)

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
student_ctx = _get_login_student_context()
if not is_admin:
    my_student_id = str(student_ctx.get("student_id", "") or "")

my_perms = _get_my_permissions_from_ctx(student_ctx, is_admin=is_admin)

# =========================
# (관리자) 학급 시스템 탭 + (학생) 접근 가능한 탭만
# =========================
ALL_TABS = [
    "🏦 내 통장",
    "🔎 개별조회",
    "💼 직업/월급",
    "🏛️ 국세청(국고)",
    "📊 통계청",
    "💳 신용등급",
    "🏦 은행(적금)",
    "📈 투자",
    "👥 계정 정보/활성화",
    "🏷️ 경매",
    "🍀 복권",
]

def tab_visible(tab_name: str):
    # 관리자: 전부 표시
    if is_admin:
        return True

    # 학생 기본 탭(항상 표시)
    if tab_name in ("🏦 내 통장", "🏦 은행(적금)", "📈 투자", "🏷️ 경매", "🍀 복권"):
        return True

    # ✅ 학생에게 '탭 권한(tab::<탭이름>)'이 부여된 경우 표시
    if has_tab_access(my_perms, tab_name, is_admin=False):
        return True

    # ✅ 기존 permission 기반 표시(역할/권한 시스템 유지)
    if tab_name == "🏛️ 국세청(국고)":
        return can(my_perms, "treasury_read") or can(my_perms, "treasury_write")
    if tab_name == "📊 통계청":
        return can(my_perms, "stats_write")
    if tab_name == "💳 신용등급":
        return can(my_perms, "credit_write")
    if tab_name == "🏦 은행(적금)":
        return can(my_perms, "bank_read") or can(my_perms, "bank_write")
    if tab_name == "💼 직업/월급":
        return can(my_perms, "jobs_write")
    if tab_name == "🗓️ 일정":
        return can(my_perms, "schedule_write") or can(my_perms, "schedule_read")

    # 계정 정보/활성화는 학생에게 기본 숨김(권한 관리 UI가 있어서)
    if tab_name == "👥 계정 정보/활성화":
        return False

    return False

    return False

# -------------------------
# ✅ 탭 구성
# - 관리자: 기존 ALL_TABS(tab_visible) 그대로
# - 학생(개별로그인): "거래/투자/적금/목표" (투자 비활성화면 투자 탭 숨김)
# -------------------------
if is_admin:
    tabs = [t for t in ALL_TABS if tab_visible(t)]
    # ✅ 관리자 탭에서만 '🏦 내 통장' 탭 이름을 변경(학생 탭에는 영향 없음)
    tabs_display = [("💰보상/벌금" if t == "🏦 내 통장" else t) for t in tabs]
    tab_objs = st.tabs(tabs_display)
    tab_map = {name: tab_objs[i] for i, name in enumerate(tabs)}
else:
    # ✅ 투자 탭 노출 여부(계정 정보/활성화에서 '투자활성화' 꺼진 학생은 숨김)
    inv_ok = True
    try:
        if my_student_id:
            snap = db.collection("students").document(str(my_student_id)).get()
            if snap.exists:
                inv_ok = bool((snap.to_dict() or {}).get("invest_enabled", True))
    except Exception:
        inv_ok = True

    # -------------------------
    # ✅ 학생 기본 탭(거래/적금/투자/목표)
    # -------------------------
    base_labels = ["📝 거래", "🏦 적금", "📊 통계/신용"]
    if inv_ok:
        base_labels.append("📈 투자")
    base_labels.append("🎯 목표")
    base_labels.append("🏷️ 경매")
    base_labels.append("🍀 복권")

    # -------------------------
    # ✅ (추가) 관리자 권한 탭들
    # - tab::<탭이름>  : '관리자 전용 탭'을 학생에게 추가로 열어줌
    # - admin::<탭이름>: 기존 탭 안의 '관리자 기능 UI'를 열어줌
    # -------------------------
    extra_admin_tabs = []

    # 1) 관리자 기능(같은 탭 안에 있던 관리자 UI)을 별도 탭으로 빼서 제공
    #    ※ 이 탭을 만들면, 원래 탭(📝 거래/🏦 적금/📈 투자)에서는 학생에게 관리자 UI를 숨깁니다.
    def _append_extra_tab(label: str, key_internal: str):
        # 사용자 기본 탭과 중복 라벨이 생기지 않도록 방지
        if label in base_labels:
            return
        if any(str(label) == str(lab) for (lab, _k) in extra_admin_tabs):
            return
        extra_admin_tabs.append((label, key_internal))

    if has_admin_feature_access(my_perms, "🏦 내 통장", is_admin=False):
        _append_extra_tab("💰보상/벌금(관리자)", "admin::🏦 내 통장")

    if has_admin_feature_access(my_perms, "🏦 은행(적금)", is_admin=False):
        _append_extra_tab("🏦 은행(적금)(관리자)", "admin::🏦 은행(적금)")

    if inv_ok and has_admin_feature_access(my_perms, "📈 투자", is_admin=False):
        _append_extra_tab("📈 투자(관리자)", "admin::📈 투자")

    # 2) 관리자 전용 탭(계정 정보/활성화 제외) — tab_visible() = tab::<탭이름> 권한 기반
    for t in ALL_TABS:
        if t in ("👥 계정 정보/활성화",):
            continue
        # 이미 기본 탭(거래/적금/투자)으로 구현된 것들은 제외
        if t in ("🏦 내 통장", "🏦 은행(적금)", "📈 투자", "🏷️ 경매", "🍀 복권"):
            continue
        if tab_visible(t):
            _append_extra_tab(t, t)  # (표시라벨, 내부키)
            
    user_tab_labels = base_labels + [lab for (lab, _k) in extra_admin_tabs]

    # ✅ (PATCH) 사용자 모드: 탭 위에 통장/정보 요약 표시

    _render_user_bank_header(my_student_id)

    tab_objs = st.tabs(user_tab_labels)

    # -------------------------------------------------
    # tab_map: "내부키" -> tab object
    # -------------------------------------------------
    tab_map = {}

    # 기본 탭(내부키는 기존 로직 재사용)
    idx = 0
    tab_map["🏦 내 통장"] = tab_objs[idx]; idx += 1
    tab_map["🏦 은행(적금)"] = tab_objs[idx]; idx += 1
    tab_map["📊 통계/신용"] = tab_objs[idx]; idx += 1
    if inv_ok:
        tab_map["📈 투자"] = tab_objs[idx]
        idx += 1
    tab_map["🎯 목표"] = tab_objs[idx]
    idx += 1
    tab_map["🏷️ 경매"] = tab_objs[idx]
    idx += 1
    tab_map["🍀 복권"] = tab_objs[idx]
    idx += 1
    extra_start = idx

    # 추가 관리자 탭 매핑
    for i, (_lab, key_internal) in enumerate(extra_admin_tabs):
        tab_map[key_internal] = tab_objs[extra_start + i]


tabs = list(tab_map.keys())

# =========================
# (PATCH) 공용: 신용점수/등급 계산 (내 통장 상단 요약에서 먼저 필요)
# - 탭 실행 순서 때문에 내 통장에서 0등급(0점)으로 뜨는 문제 방지
# =========================
def _score_to_grade(score: int) -> int:
    s = int(score or 0)
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

def _get_credit_cfg():
    ref = db.collection("config").document("credit_scoring")
    snap = ref.get()
    if not snap.exists:
        return {"base": 50, "o": 1, "x": -3, "tri": 0}
    d = snap.to_dict() or {}
    return {
        "base": int(d.get("base", 50) if d.get("base", None) is not None else 50),
        "o": int(d.get("o", 1) if d.get("o", None) is not None else 1),
        "x": int(d.get("x", -3) if d.get("x", None) is not None else -3),
        "tri": int(d.get("tri", 0) if d.get("tri", None) is not None else 0),
    }

def _norm_status(v) -> str:
    v = str(v or "").strip().upper()
    if v in ("O", "○"):
        return "O"
    if v in ("△", "▲", "Δ"):
        return "△"
    return "X"

def _calc_credit_score_for_student(student_id: str):
    credit_cfg = _get_credit_cfg()
    base = int(credit_cfg.get("base", 50) if credit_cfg.get("base", None) is not None else 50)
    o_pt = int(credit_cfg.get("o", 1) if credit_cfg.get("o", None) is not None else 1)
    x_pt = int(credit_cfg.get("x", -3) if credit_cfg.get("x", None) is not None else -3)
    tri_pt = int(credit_cfg.get("tri", 0) if credit_cfg.get("tri", None) is not None else 0)

    def _delta(v) -> int:
        v = _norm_status(v)
        if v == "O":
            return o_pt
        if v == "△":
            return tri_pt
        return x_pt

    res = api_list_stat_submissions_cached(limit_cols=200)
    rows_desc = list(res.get("rows", []) or []) if res.get("ok") else []

    score = int(base)
    # rows_desc는 최신→과거 / 누적은 과거→최신으로
    for sub in reversed(rows_desc):
        statuses = dict(sub.get("statuses", {}) or {})
        v_raw = statuses.get(str(student_id), "X")
        score = int(score + _delta(v_raw))
        if score > 100:
            score = 100
        if score < 0:
            score = 0

    grade = _score_to_grade(score)
    return score, grade


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
    credit_grade = int(bal_res.get("credit_grade", DEFAULT_CREDIT_GRADE) or DEFAULT_CREDIT_GRADE)
    
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
        trade_admin_ok = bool(is_admin)  # ✅ 학생은 여기서 관리자 UI를 숨기고, 별도 관리자 탭(admin::🏦 내 통장)에서만 표시
        if trade_admin_ok:

            # ✅ (보상/벌금) 내부 작은 탭
            sub_tab_all, sub_tab_personal = st.tabs(["전체", "개인"])

            # =================================================
            # [전체] : 기존 화면 그대로
            # =================================================
            with sub_tab_all:
                # -------------------------------------------------
                # 1) 전체 일괄 지급/벌금
                # -------------------------------------------------
                st.markdown("### 🎁 전체 일괄 지급/벌금")

                tpl_res3 = api_list_templates_cached()
                templates3 = tpl_res3.get("templates", []) if tpl_res3.get("ok") else []
                tpl_by_display3 = {template_display_for_trade(t): t for t in templates3}

                memo_bulk, dep_bulk, wd_bulk = render_admin_trade_ui(
                    prefix="admin_bulk_reward",
                    templates_list=templates3,
                    template_by_display=tpl_by_display3,
                )

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("저장", key="admin_bulk_reward_save", use_container_width=True):
                        if (dep_bulk > 0 and wd_bulk > 0) or (dep_bulk == 0 and wd_bulk == 0):
                            st.error("입금/출금은 둘 중 하나만 입력해 주세요.")
                        elif not memo_bulk:
                            st.error("내역(메모)을 입력해 주세요.")
                        else:
                            tre_apply_bulk = bool(st.session_state.get("admin_bulk_reward_treasury_apply", False))

                            if dep_bulk > 0:
                                res = api_admin_bulk_deposit(ADMIN_PIN, dep_bulk, memo_bulk)
                                if res.get("ok"):
                                    toast(f"일괄 지급 완료! ({res.get('count')}명)", icon="🎉")
                                    # ✅ 국고 반영(체크 시): 전체 지급 → 국고 세출(합산)
                                    if tre_apply_bulk:
                                        cnt = int(res.get("count", 0) or 0)
                                        if cnt > 0:
                                            api_treasury_auto_bulk_adjust(
                                                memo=f"전체 {memo_bulk}".strip(),
                                                signed_amount=-(int(dep_bulk) * cnt),
                                                actor="전체",
                                            )
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "일괄 지급 실패"))
                            else:
                                res = api_admin_bulk_withdraw(ADMIN_PIN, wd_bulk, memo_bulk)
                                if res.get("ok"):
                                    toast(f"벌금 완료! (적용 {res.get('count')}명)", icon="⚠️")
                                    # ✅ 국고 반영(체크 시): 전체 벌금 → 국고 세입(합산)
                                    if tre_apply_bulk:
                                        cnt = int(res.get("count", 0) or 0)
                                        if cnt > 0:
                                            api_treasury_auto_bulk_adjust(
                                                memo=f"전체 {memo_bulk}".strip(),
                                                signed_amount=(int(wd_bulk) * cnt),
                                                actor="전체",
                                            )
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "일괄 벌금 실패"))

                with b2:
                    if st.button("되돌리기(관리자)", key="admin_bulk_reward_undo_toggle", use_container_width=True):
                        st.session_state["admin_bulk_reward_undo_mode"] = not st.session_state.get(
                            "admin_bulk_reward_undo_mode", False
                        )

                # ✅ 되돌리기(관리자)
                if st.session_state.get("admin_bulk_reward_undo_mode", False):
                    st.subheader("↩️ 선택 되돌리기(관리자)")

                    admin_pin_rb = st.text_input(
                        "관리자 PIN 입력",
                        type="password",
                        key="admin_bulk_reward_undo_pin",
                    ).strip()

                    accounts_for_rb = api_list_accounts_cached().get("accounts", [])
                    name_map = {a.get("name", ""): a.get("student_id", "") for a in (accounts_for_rb or []) if a.get("name")}
                    pick_name = st.selectbox(
                        "되돌릴 학생 선택",
                        ["(선택)"] + list(name_map.keys()),
                        key="admin_bulk_reward_undo_pick_name",
                    )

                    if pick_name != "(선택)":
                        sid_rb = name_map.get(pick_name, "")
                        txr_rb = api_get_txs_by_student_id(sid_rb, limit=120)
                        df_rb = pd.DataFrame(txr_rb.get("rows", [])) if txr_rb.get("ok") else pd.DataFrame()

                        if not df_rb.empty:
                            view_df = df_rb.head(50).copy()

                            def _can_rollback_row(row):
                                if str(row.get("type", "")) == "rollback":
                                    return False
                                memo = str(row.get("memo", "") or "")
                                if _is_savings_memo(memo) or str(row.get("type", "")) in ("maturity",):
                                    return False
                                # ✅ 투자 내역은 되돌리기 비활성화
                                if _is_invest_memo(memo):
                                    return False
                                return True

                            view_df["가능"] = view_df.apply(_can_rollback_row, axis=1)

                            selected_ids = []
                            for _, r in view_df.iterrows():
                                tx_id = r["tx_id"]
                                label = f"{r['created_at_kr']} | {r['memo']} | +{int(r['deposit'])} / -{int(r['withdraw'])}"
                                ck = st.checkbox(
                                    label,
                                    key=f"admin_bulk_reward_rb_ck_{sid_rb}_{tx_id}",
                                    disabled=(not r["가능"]),
                                )
                                if ck and r["가능"]:
                                    selected_ids.append(tx_id)

                            if st.button("선택 항목 되돌리기", key="admin_bulk_reward_do_rb", use_container_width=True):
                                if not is_admin_pin(admin_pin_rb):
                                    st.error("관리자 PIN이 틀립니다.")
                                elif not selected_ids:
                                    st.warning("체크된 항목이 없어요.")
                                else:
                                    res2 = api_admin_rollback_selected(admin_pin_rb, sid_rb, selected_ids)
                                    if res2.get("ok"):
                                        toast(f"선택 {res2.get('undone')}건 되돌림 완료", icon="↩️")
                                        api_list_accounts_cached.clear()
                                        st.rerun()
                                    else:
                                        st.error(res2.get("error", "되돌리기 실패"))


                # -------------------------------------------------
                # 2) 내역 템플릿 순서 정렬
                # -------------------------------------------------
                h1, h2 = st.columns([0.35, 9.65], vertical_alignment="center")
                with h1:
                    if st.button(
                        "▸" if not st.session_state.get("bank_tpl_sort_panel_open", False) else "▾",
                        key="bank_tpl_sort_panel_toggle",
                        use_container_width=True,
                    ):
                        st.session_state["bank_tpl_sort_panel_open"] = not st.session_state.get("bank_tpl_sort_panel_open", False)
                        st.rerun()
                with h2:
                    st.markdown("### ↕️ 내역 템플릿 순서 정렬")

                if not st.session_state.get("bank_tpl_sort_panel_open", False):
                    st.caption("펼치려면 왼쪽 화살표(▸)를 눌러주세요.")
                else:
                    tpl_res2 = api_list_templates_cached()
                    templates = tpl_res2.get("templates", []) if tpl_res2.get("ok") else []
                    templates = sorted(
                        templates,
                        key=lambda t: (int(t.get("order", 999999) or 999999), str(t.get("label", ""))),
                    )
                    tpl_by_id = {t["template_id"]: t for t in templates}

                    st.session_state.setdefault("bank_tpl_sort_mode", False)
                    st.session_state.setdefault("bank_tpl_work_ids", [])
                    st.session_state.setdefault("bank_tpl_mobile_sort_ui", False)

                    if not st.session_state["bank_tpl_sort_mode"]:
                        st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                    else:
                        cur_ids = [t["template_id"] for t in templates]
                        if (not st.session_state["bank_tpl_work_ids"]) or (set(st.session_state["bank_tpl_work_ids"]) != set(cur_ids)):
                            st.session_state["bank_tpl_work_ids"] = cur_ids

                    topA, topB, topC, topD = st.columns([1.1, 1.1, 1.4, 1.6])
                    with topA:
                        if st.button(
                            "정렬모드 ON" if not st.session_state["bank_tpl_sort_mode"] else "정렬모드 OFF",
                            key="bank_tpl_sort_toggle",
                            use_container_width=True,
                        ):
                            st.session_state["bank_tpl_sort_mode"] = not st.session_state["bank_tpl_sort_mode"]
                            if not st.session_state["bank_tpl_sort_mode"]:
                                st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                            st.rerun()
                    with topB:
                        if st.button("order 채우기(1회)", key="bank_tpl_backfill_btn", use_container_width=True):
                            res = api_admin_backfill_template_order(ADMIN_PIN)
                            if res.get("ok"):
                                toast("order 초기화 완료!", icon="🧷")
                                api_list_templates_cached.clear()
                                st.session_state["bank_tpl_work_ids"] = []
                                st.rerun()
                            else:
                                st.error(res.get("error", "실패"))
                    with topC:
                        if st.button("order 전체 재정렬", key="bank_tpl_normalize_btn", use_container_width=True):
                            res = api_admin_normalize_template_order(ADMIN_PIN)
                            if res.get("ok"):
                                toast("order 재정렬 완료!", icon="🧹")
                                api_list_templates_cached.clear()
                                st.session_state["bank_tpl_work_ids"] = []
                                st.rerun()
                            else:
                                st.error(res.get("error", "실패"))
                    with topD:
                        st.session_state["bank_tpl_mobile_sort_ui"] = st.checkbox(
                            "간단 모드(모바일용)",
                            value=bool(st.session_state["bank_tpl_mobile_sort_ui"]),
                            key="bank_tpl_mobile_sort_ui_chk",
                            help="모바일에서 표가 세로로 쌓여 보이는 문제를 피하기 위한 정렬 UI입니다.",
                        )

                    if st.session_state["bank_tpl_sort_mode"]:
                        st.caption("✅ 이동은 화면에서만 즉시 반영 → 마지막에 ‘저장(한 번에)’ 1번 누르면 DB 반영")

                    work_ids = st.session_state["bank_tpl_work_ids"]
                    if not work_ids:
                        st.info("템플릿이 아직 없어요.")
                    else:
                        if st.session_state["bank_tpl_mobile_sort_ui"]:
                            options = list(range(len(work_ids)))

                            def _opt_label(i: int):
                                tid = work_ids[i]
                                t = tpl_by_id.get(tid, {})
                                kind_kr = "입금" if t.get("kind") == "deposit" else "출금"
                                amt = int(t.get("amount", 0) or 0)
                                return f"{i+1}. {t.get('label','')} ({kind_kr} {amt})"

                            pick_i = st.selectbox(
                                "이동할 항목 선택",
                                options,
                                format_func=_opt_label,
                                key="bank_tpl_simple_pick",
                            )

                            b1, b2, b3 = st.columns([1, 1, 2])
                            with b1:
                                if st.button(
                                    "위로 ▲",
                                    key="bank_tpl_simple_up",
                                    disabled=(not st.session_state["bank_tpl_sort_mode"]) or pick_i == 0,
                                    use_container_width=True,
                                ):
                                    work_ids[pick_i - 1], work_ids[pick_i] = work_ids[pick_i], work_ids[pick_i - 1]
                                    st.session_state["bank_tpl_work_ids"] = work_ids
                                    st.session_state["bank_tpl_simple_pick"] = max(0, pick_i - 1)
                                    st.rerun()
                            with b2:
                                if st.button(
                                    "아래로 ▼",
                                    key="bank_tpl_simple_dn",
                                    disabled=(not st.session_state["bank_tpl_sort_mode"]) or pick_i == (len(work_ids) - 1),
                                    use_container_width=True,
                                ):
                                    work_ids[pick_i + 1], work_ids[pick_i] = work_ids[pick_i], work_ids[pick_i + 1]
                                    st.session_state["bank_tpl_work_ids"] = work_ids
                                    st.session_state["bank_tpl_simple_pick"] = min(len(work_ids) - 1, pick_i + 1)
                                    st.rerun()
                            with b3:
                                st.caption("정렬모드 ON일 때만 이동 가능")

                            html = ["<div class='tpl-simple'>"]
                            for idx, tid in enumerate(work_ids, start=1):
                                t = tpl_by_id.get(tid, {})
                                kind_kr = "입금" if t.get("kind") == "deposit" else "출금"
                                amt = int(t.get("amount", 0) or 0)
                                lab = str(t.get("label", "") or "")
                                html.append(
                                    f"<div class='item'>"
                                    f"<span class='idx'>{idx}</span>"
                                    f"<span class='lab'>{lab}</span>"
                                    f"<div class='meta'>{kind_kr} · {amt}</div>"
                                    f"</div>"
                                )
                            html.append("</div>")
                            st.markdown("\n".join(html), unsafe_allow_html=True)

                            if st.session_state["bank_tpl_sort_mode"]:
                                s1, s2 = st.columns([1.2, 1.2])
                                with s1:
                                    if st.button("저장(한 번에)", key="bank_tpl_save_orders_btn_simple", use_container_width=True):
                                        res = api_admin_save_template_orders(ADMIN_PIN, st.session_state["bank_tpl_work_ids"])
                                        if res.get("ok"):
                                            toast(f"순서 저장 완료! ({res.get('count', 0)}개)", icon="💾")
                                            st.session_state["bank_tpl_sort_mode"] = False
                                            api_list_templates_cached.clear()
                                            st.session_state["bank_tpl_work_ids"] = []
                                            st.rerun()
                                        else:
                                            st.error(res.get("error", "저장 실패"))
                                with s2:
                                    if st.button("취소(원복)", key="bank_tpl_cancel_orders_btn_simple", use_container_width=True):
                                        st.session_state["bank_tpl_sort_mode"] = False
                                        st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                                        toast("변경 취소(원복)!", icon="↩️")
                                        st.rerun()
                        else:
                            head = st.columns([0.7, 5.2, 2.2, 1.4], vertical_alignment="center")
                            head[0].markdown("<div class='tpl-head'>순서</div>", unsafe_allow_html=True)
                            head[1].markdown("<div class='tpl-head'>내역</div>", unsafe_allow_html=True)
                            head[2].markdown("<div class='tpl-head'>종류·금액</div>", unsafe_allow_html=True)
                            head[3].markdown("<div class='tpl-head'>이동</div>", unsafe_allow_html=True)

                            for idx, tid in enumerate(work_ids):
                                t = tpl_by_id.get(tid, {})
                                label = t.get("label", "")
                                kind_kr = "입금" if t.get("kind") == "deposit" else "출금"
                                amt = int(t.get("amount", 0) or 0)

                                row = st.columns([0.7, 5.2, 2.2, 0.7, 0.7], vertical_alignment="center")
                                row[0].markdown(f"<div class='tpl-cell'>{idx+1}</div>", unsafe_allow_html=True)
                                row[1].markdown(
                                    f"<div class='tpl-cell'><div class='tpl-label'>{label}</div></div>",
                                    unsafe_allow_html=True,
                                )
                                row[2].markdown(
                                    f"<div class='tpl-cell'><div class='tpl-sub'>{kind_kr} · {amt}</div></div>",
                                    unsafe_allow_html=True,
                                )

                                if st.session_state["bank_tpl_sort_mode"]:
                                    up_disabled = (idx == 0)
                                    down_disabled = (idx == len(work_ids) - 1)

                                    if row[3].button("⬆", key=f"bank_tpl_up_fast_{tid}", disabled=up_disabled, use_container_width=True):
                                        work_ids[idx - 1], work_ids[idx] = work_ids[idx], work_ids[idx - 1]
                                        st.session_state["bank_tpl_work_ids"] = work_ids
                                        st.rerun()

                                    if row[4].button("⬇", key=f"bank_tpl_dn_fast_{tid}", disabled=down_disabled, use_container_width=True):
                                        work_ids[idx + 1], work_ids[idx] = work_ids[idx], work_ids[idx + 1]
                                        st.session_state["bank_tpl_work_ids"] = work_ids
                                        st.rerun()
                                else:
                                    row[3].markdown("<div class='tpl-cell'></div>", unsafe_allow_html=True)
                                    row[4].markdown("<div class='tpl-cell'></div>", unsafe_allow_html=True)

                            if st.session_state["bank_tpl_sort_mode"]:
                                s1, s2 = st.columns([1.2, 1.2])
                                with s1:
                                    if st.button("저장(한 번에)", key="bank_tpl_save_orders_btn", use_container_width=True):
                                        res = api_admin_save_template_orders(ADMIN_PIN, st.session_state["bank_tpl_work_ids"])
                                        if res.get("ok"):
                                            toast(f"순서 저장 완료! ({res.get('count', 0)}개)", icon="💾")
                                            st.session_state["bank_tpl_sort_mode"] = False
                                            api_list_templates_cached.clear()
                                            st.session_state["bank_tpl_work_ids"] = []
                                            st.rerun()
                                        else:
                                            st.error(res.get("error", "저장 실패"))
                                with s2:
                                    if st.button("취소(원복)", key="bank_tpl_cancel_orders_btn", use_container_width=True):
                                        st.session_state["bank_tpl_sort_mode"] = False
                                        st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                                        toast("변경 취소(원복)!", icon="↩️")
                                        st.rerun()


                # -------------------------------------------------
                # 3) 템플릿 추가/수정/삭제
                # -------------------------------------------------
                st.markdown("### 🧩 템플릿 추가/수정/삭제")

                KIND_TO_KR = {"deposit": "입금", "withdraw": "출금"}
                KR_TO_KIND = {"입금": "deposit", "출금": "withdraw"}

                templates_now = api_list_templates_cached().get("templates", [])
                mode = st.radio("작업", ["추가", "수정"], horizontal=True, key="bank_tpl_mode")

                st.session_state.setdefault("bank_tpl_edit_id", "")
                st.session_state.setdefault("bank_tpl_pick_prev", None)

                # ✅ 기존 bank_tpl_label 대신: base_label + category(구분)로 분리
                st.session_state.setdefault("bank_tpl_base_label", "")
                st.session_state.setdefault("bank_tpl_category_kr", "없음")

                st.session_state.setdefault("bank_tpl_kind_setting_kr", "입금")
                st.session_state.setdefault("bank_tpl_amount", 10)
                st.session_state.setdefault("bank_tpl_order", 1)

                CATEGORY_CHOICES = ["없음", "보상", "구입", "벌금"]

                def tpl_display(t):
                    kind_kr = "입금" if t["kind"] == "deposit" else "출금"
                    return f"{t['label']}[{kind_kr} {int(t['amount'])}]"

                def _fill_tpl_form(t):
                    st.session_state["bank_tpl_edit_id"] = t["template_id"]

                    # ✅ category/base_label이 있으면 우선 사용, 없으면 label에서 파싱
                    cat = str(t.get("category", "") or "").strip()
                    base = str(t.get("base_label", "") or "").strip()

                    if (not cat) and (not base):
                        cat2, base2 = _parse_template_label(t.get("label", ""))
                        cat = str(cat2 or "").strip()
                        base = str(base2 or "").strip()

                    st.session_state["bank_tpl_base_label"] = base
                    st.session_state["bank_tpl_category_kr"] = cat if cat else "없음"

                    st.session_state["bank_tpl_kind_setting_kr"] = KIND_TO_KR.get(t.get("kind", "deposit"), "입금")
                    st.session_state["bank_tpl_amount"] = int(t.get("amount", 10) or 10)
                    st.session_state["bank_tpl_order"] = int(t.get("order", 1) or 1)

                if mode == "수정" and templates_now:
                    labels = [tpl_display(t) for t in templates_now]
                    pick = st.selectbox(
                        "수정할 템플릿 선택",
                        list(range(len(templates_now))),
                        format_func=lambda idx: labels[idx],
                        key="bank_tpl_pick",
                    )
                    if st.session_state["bank_tpl_pick_prev"] != pick:
                        st.session_state["bank_tpl_pick_prev"] = pick
                        _fill_tpl_form(templates_now[pick])
                elif mode == "추가":
                    st.session_state["bank_tpl_edit_id"] = ""
                    st.session_state["bank_tpl_pick_prev"] = None

                # ✅ 컬럼: 내역이름 / 구분 / 종류 / 금액
                tcol1, tcol_mid, tcol2, tcol3 = st.columns([2, 1.2, 1, 1])
                with tcol1:
                    tpl_base_label = st.text_input("내역 이름", key="bank_tpl_base_label").strip()
                with tcol_mid:
                    tpl_category_kr = st.selectbox("구분", CATEGORY_CHOICES, key="bank_tpl_category_kr")
                with tcol2:
                    tpl_kind_kr = st.selectbox("종류", ["입금", "출금"], key="bank_tpl_kind_setting_kr")
                with tcol3:
                    tpl_amount = st.number_input("금액", min_value=1, step=1, key="bank_tpl_amount")

                tpl_order = st.number_input("순서(order)", min_value=1, step=1, key="bank_tpl_order")

                if st.button("저장(추가/수정)", key="bank_tpl_save", use_container_width=True):
                    if not tpl_base_label:
                        st.error("내역 이름이 필요합니다.")
                    else:
                        kind_eng = KR_TO_KIND[tpl_kind_kr]
                        tid = st.session_state.get("bank_tpl_edit_id", "") if mode == "수정" else ""

                        # ✅ "없음"이면 category는 빈 문자열로 저장
                        cat = "" if str(tpl_category_kr) == "없음" else str(tpl_category_kr).strip()

                        res = api_admin_upsert_template(
                            ADMIN_PIN,
                            tid,
                            tpl_base_label,
                            cat,
                            kind_eng,
                            int(tpl_amount),
                            int(tpl_order),
                        )
                        if res.get("ok"):
                            toast("템플릿 저장 완료!", icon="🧩")
                            api_list_templates_cached.clear()
                            st.rerun()
                        else:
                            st.error(res.get("error", "템플릿 저장 실패"))

                st.caption("삭제")
                if templates_now:
                    del_labels = [tpl_display(t) for t in templates_now]
                    del_pick = st.selectbox(
                        "삭제할 템플릿 선택",
                        list(range(len(templates_now))),
                        format_func=lambda idx: del_labels[idx],
                        key="bank_tpl_del_pick",
                    )
                    del_id = templates_now[del_pick]["template_id"]

                    if st.button("삭제", key="bank_tpl_del_btn", use_container_width=True):
                        st.session_state["bank_tpl_del_confirm"] = True

                    if st.session_state.get("bank_tpl_del_confirm", False):
                        st.warning("정말로 삭제하시겠습니까?")
                        y, n = st.columns(2)
                        with y:
                            if st.button("예", key="bank_tpl_del_yes", use_container_width=True):
                                res = api_admin_delete_template(ADMIN_PIN, del_id)
                                if res.get("ok"):
                                    toast("삭제 완료!", icon="🗑️")
                                    st.session_state["bank_tpl_del_confirm"] = False
                                    api_list_templates_cached.clear()
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "삭제 실패"))
                        with n:
                            if st.button("아니오", key="bank_tpl_del_no", use_container_width=True):
                                st.session_state["bank_tpl_del_confirm"] = False
                                st.rerun()

                st.markdown("### 📥 템플릿 엑셀로 일괄 추가")

                import io

                # -------------------------
                # 1) 샘플 엑셀 다운로드
                # -------------------------
                sample_df = pd.DataFrame(
                    [
                        {"내역이름": "대여료", "구분": "구입", "종류": "출금", "금액": 100, "순서": 1},
                        {"내역이름": "발표", "구분": "보상", "종류": "입금", "금액": 10, "순서": 2},
                        {"내역이름": "지각", "구분": "벌금", "종류": "출금", "금액": 20, "순서": 3},
                        {"내역이름": "기타", "구분": "없음", "종류": "입금", "금액": 5, "순서": 4},
                    ],
                    columns=["내역이름", "구분", "종류", "금액", "순서"],
                )

                bio = io.BytesIO()
                with pd.ExcelWriter(bio, engine="openpyxl") as writer:
                    sample_df.to_excel(writer, index=False, sheet_name="templates")
                bio.seek(0)

                st.download_button(
                    "📄 샘플 엑셀 다운로드",
                    data=bio.getvalue(),
                    file_name="템플릿_샘플.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="bank_tpl_sample_xlsx_download",
                )

                st.caption("• 샘플 형식: 내역이름 | 구분(없음/보상/구입/벌금) | 종류(입금/출금) | 금액 | 순서")
                st.caption("• 엑셀을 올린 뒤, 아래의 **저장** 버튼을 눌러야 실제 반영됩니다.")

                # -------------------------
                # 2) 엑셀 업로드 + 미리보기
                # -------------------------
                upl = st.file_uploader(
                    "엑셀 업로드(.xlsx)",
                    type=["xlsx"],
                    key="bank_tpl_bulk_xlsx",
                    help="샘플 형식 그대로 업로드하세요. 업로드만으로는 반영되지 않고, 아래 '저장' 버튼을 눌러야 반영됩니다.",
                )

                st.session_state.setdefault("bank_tpl_bulk_df", None)

                if upl is not None:
                    try:
                        df = pd.read_excel(upl)
                        df = df.copy()

                        # 공백 컬럼명 정리
                        df.columns = [str(c).strip() for c in df.columns]

                        need_cols = ["내역이름", "구분", "종류", "금액", "순서"]
                        miss = [c for c in need_cols if c not in df.columns]
                        if miss:
                            st.error(f"필수 컬럼이 없습니다: {miss}")
                            st.session_state["bank_tpl_bulk_df"] = None
                        else:
                            # 문자열/정수 정리
                            df["내역이름"] = df["내역이름"].astype(str).str.strip()
                            df["구분"] = df["구분"].astype(str).str.strip()
                            df["종류"] = df["종류"].astype(str).str.strip()
                            df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
                            df["순서"] = pd.to_numeric(df["순서"], errors="coerce").fillna(999999).astype(int)

                            # 기본값 보정
                            df.loc[df["구분"].isin(["nan", "None", ""]), "구분"] = "없음"

                            # 검증
                            bad_cat = df[~df["구분"].isin(["없음", "보상", "구입", "벌금"])]
                            bad_kind = df[~df["종류"].isin(["입금", "출금"])]
                            bad_label = df[df["내역이름"].str.len() == 0]
                            bad_amt = df[df["금액"] <= 0]

                            if (not bad_cat.empty) or (not bad_kind.empty) or (not bad_label.empty) or (not bad_amt.empty):
                                if not bad_label.empty:
                                    st.error("❌ 내역이름이 비어있는 행이 있습니다.")
                                if not bad_cat.empty:
                                    st.error("❌ 구분 값이 잘못된 행이 있습니다. (없음/보상/구입/벌금만 가능)")
                                if not bad_kind.empty:
                                    st.error("❌ 종류 값이 잘못된 행이 있습니다. (입금/출금만 가능)")
                                if not bad_amt.empty:
                                    st.error("❌ 금액은 1 이상이어야 합니다.")
                                st.session_state["bank_tpl_bulk_df"] = None
                            else:
                                st.session_state["bank_tpl_bulk_df"] = df
                                st.success(f"업로드 완료! ({len(df)}행) 아래 미리보기 확인 후 저장을 누르세요.")
                                st.dataframe(df, use_container_width=True, hide_index=True)

                    except Exception as e:
                        st.error(f"엑셀 읽기 실패: {e}")
                        st.session_state["bank_tpl_bulk_df"] = None

                # -------------------------
                # 3) 저장(반영) 버튼 + (옵션) 기존 리스트 삭제
                # -------------------------
                del_old = st.checkbox(
                    "저장 시 기존 템플릿 리스트를 모두 삭제하고 새로 올린 엑셀로 덮어쓰기",
                    value=False,
                    key="bank_tpl_bulk_delete_old",
                )

                if st.button("✅ 엑셀 내용 저장(반영)", use_container_width=True, key="bank_tpl_bulk_save_btn"):
                    df2 = st.session_state.get("bank_tpl_bulk_df", None)
                    if df2 is None or df2.empty:
                        st.error("먼저 올바른 엑셀을 업로드하세요.")
                    else:
                        try:
                            # 1) 기존 삭제(옵션)
                            if del_old:
                                docs = list(db.collection("templates").stream())
                                batch = db.batch()
                                for d in docs:
                                    batch.delete(d.reference)
                                if docs:
                                    batch.commit()

                            # 2) 엑셀 행들을 upsert(신규로 저장)
                            saved = 0
                            for _, r in df2.iterrows():
                                base_label = str(r["내역이름"]).strip()
                                cat_kr = str(r["구분"]).strip()
                                kind_kr = str(r["종류"]).strip()
                                amt = int(r["금액"])
                                order = int(r["순서"])

                                category = "" if cat_kr == "없음" else cat_kr
                                kind = KR_TO_KIND.get(kind_kr, "deposit")

                                res = api_admin_upsert_template(
                                    ADMIN_PIN,
                                    "",  # ✅ 일괄은 신규로 추가(기존과 매칭/수정은 하지 않음)
                                    base_label,
                                    category,
                                    kind,
                                    amt,
                                    order,
                                )
                                if res.get("ok"):
                                    saved += 1

                            api_list_templates_cached.clear()
                            toast(f"엑셀 저장 완료! ({saved}개 반영)", icon="📥")
                            st.session_state["bank_tpl_bulk_df"] = None
                            st.rerun()

                        except Exception as e:
                            st.error(f"저장 실패: {e}")
            
            # =================================================
            # [개인] : 체크된 학생만 “일괄 지급/벌금” 적용
            # =================================================
            with sub_tab_personal:
                st.markdown("### 👥 대상 학생 선택 (체크한 학생만 적용)")
                accounts_now = api_list_accounts_cached().get("accounts", [])
                import re

                def _num_key(acc):
                    name = str(acc.get("name", ""))
                    m = re.search(r"\d+", name)
                    if m:
                        return int(m.group())   # 1~9 → 01~09처럼 숫자 기준 정렬
                    return 9999                # 번호 없으면 맨 뒤

                accounts_now = sorted(accounts_now, key=_num_key)

                if not accounts_now:
                    st.info("활성 계정이 없습니다.")
                else:
                    selected_ids = []
                    selected_names = []

                    # ✅ 5명씩 한 줄
                    for base in range(0, len(accounts_now), 5):
                        cols = st.columns(5)
                        chunk = accounts_now[base : base + 5]
                        for j in range(5):
                            with cols[j]:
                                if j < len(chunk):
                                    a = chunk[j]
                                    nm = str(a.get("name", "") or "")
                                    sid = str(a.get("student_id", "") or "")
                                    import re
                                    m = re.search(r"\d+", nm)
                                    num = m.group() if m else "?"

                                    label = f"{num}번 {nm}"
                                    ck = st.checkbox(label, key=f"admin_personal_pick_{sid}")
                                    if ck:
                                        selected_ids.append(sid)
                                        selected_names.append(nm)
                                else:
                                    st.write("")

                    if selected_names:
                        st.caption("선택됨: " + " · ".join(selected_names))

                    st.markdown("### 🎁 개인 지급/벌금")

                    tpl_res_p = api_list_templates_cached()
                    templates_p = tpl_res_p.get("templates", []) if tpl_res_p.get("ok") else []
                    tpl_by_display_p = {template_display_for_trade(t): t for t in templates_p}

                    memo_p, dep_p, wd_p = render_admin_trade_ui(
                        prefix="admin_personal_reward",
                        templates_list=templates_p,
                        template_by_display=tpl_by_display_p,
                    )

                    if st.button("저장", key="admin_personal_reward_save", use_container_width=True):
                        if not selected_ids:
                            st.warning("먼저 적용할 학생을 체크해 주세요.")
                        elif (dep_p > 0 and wd_p > 0) or (dep_p == 0 and wd_p == 0):
                            st.error("입금/출금은 둘 중 하나만 입력해 주세요.")
                        elif not memo_p:
                            st.error("내역(메모)을 입력해 주세요.")
                        else:
                            ok_cnt = 0
                            fail = []

                            tre_apply_personal = bool(st.session_state.get("admin_personal_reward_treasury_apply", False))
                            sid_to_disp = {}
                            try:
                                for _a in (accounts_now or []):
                                    _sid = str(_a.get("student_id", "") or "")
                                    if _sid:
                                        _no = int(_a.get("no", 0) or 0)
                                        _nm = str(_a.get("name", "") or "")
                                        if _no > 0:
                                            sid_to_disp[_sid] = f"{_no}번 {_nm}"
                                        else:
                                            sid_to_disp[_sid] = _nm
                            except Exception:
                                sid_to_disp = {}

                            for sid in selected_ids:
                                # ✅ 체크된 학생만 적용 (관리자 출금은 음수 허용)
                                disp_name = sid_to_disp.get(str(sid), str(sid))
                                tre_memo = f"{disp_name} {memo_p}".strip()

                                res = api_admin_add_tx_by_student_id_with_treasury(
                                    ADMIN_PIN,
                                    sid,
                                    memo_p,
                                    int(dep_p),
                                    int(wd_p),
                                    tre_apply_personal,
                                    tre_memo,
                                    actor=disp_name,
                                )
                                if res.get("ok"):
                                    ok_cnt += 1
                                else:
                                    fail.append(res.get("error", "저장 실패"))

                            if ok_cnt > 0:
                                toast(f"개인 적용 완료! ({ok_cnt}명)", icon="✅")
                                api_list_accounts_cached.clear()
                                st.rerun()
                            else:
                                st.error("적용 실패: " + (fail[0] if fail else "알 수 없는 오류"))

        else:
            refresh_account_data_light(login_name, login_pin, force=True)
            slot = st.session_state.data.get(login_name, {})
            if slot.get("error"):
                st.error(slot["error"])
                st.stop()

            df_tx = slot["df_tx"]
            balance = int(slot.get("balance", 0) or 0)
            student_id = slot.get("student_id")

            # ✅ student_id 없으면 여기서 중단(이게 None이면 적금/직업/신용도 전부 못 가져옴)
            if not student_id:
                st.error("학생 ID를 불러오지 못했어요. (로그인/잔액 조회 확인 필요)")
                st.stop()

            # ✅ 거래 기록 (DuplicateElementKey 방지: prefix를 탭 전용으로 변경)
            st.subheader("📝 통장 기록하기")
            _tpl_state = _get_trade_templates_state()
            memo_u, dep_u, wd_u = render_admin_trade_ui(
                prefix=f"bank_trade_{login_name}",
                templates_list=_tpl_state["templates"],
                template_by_display=_tpl_state["by_display"],
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
                        # ✅ 국고 반영(체크 값은 '신청 시점'에 저장해두고,
                        #    실제 국고/통장 반영은 '승인 시점'에 처리합니다.
                        tre_apply = bool(st.session_state.get(f"bank_trade_{login_name}_treasury_apply", False))

                        disp_name = str(login_name or "")
                        try:
                            if student_id:
                                _s = db.collection("students").document(str(student_id)).get()
                                if _s.exists:
                                    _d = _s.to_dict() or {}
                                    _no = int(_d.get("no", 0) or 0)
                                    _nm = str(_d.get("name", "") or disp_name)
                                    if _no > 0:
                                        disp_name = f"{_no}번 {_nm}"
                                    else:
                                        disp_name = _nm
                        except Exception:
                            pass

                        tre_memo = f"{disp_name} {memo}".strip()

                        # -------------------------
                        # ✅ 입금은 '승인 대기'로 전환
                        # -------------------------
                        if deposit > 0 and withdraw == 0:
                            res = api_create_deposit_request(
                                login_name,
                                login_pin,
                                memo=memo,
                                amount=int(deposit),
                                apply_treasury=bool(tre_apply),
                                treasury_memo=tre_memo,
                            )
                            if res.get("ok"):
                                toast("입금 신청 완료! (관리자 승인 후 반영됩니다)", icon="🧾")
                                pfx = f"bank_trade_{login_name}"
                                st.session_state[f"{pfx}_reset_request"] = True
                                st.rerun()
                            else:
                                st.error(res.get("error", "입금 신청 실패"))

                        # -------------------------
                        # ✅ 출금은 기존대로 즉시 반영
                        # -------------------------
                        else:
                            res = api_add_tx_with_treasury(
                                login_name,
                                login_pin,
                                memo,
                                deposit,
                                withdraw,
                                tre_apply,
                                tre_memo,
                                actor=disp_name,
                            )
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

                                pfx = f"bank_trade_{login_name}"
                                st.session_state[f"{pfx}_reset_request"] = True
                                st.rerun()
                            else:
                                st.error(res.get("error", "저장 실패"))

            with col_btn2:
                if st.button("되돌리기(관리자)", key=f"undo_btn_{login_name}", use_container_width=True):
                    st.session_state.undo_mode = not st.session_state.undo_mode

            if st.session_state.undo_mode:
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

            st.subheader("📒 통장 내역(최신순)")
            render_tx_table(df_tx)

# =========================
# 📈 투자
# =========================

# =========================
# (관리자) 🔎 개별조회 - 번호순 expander 요약 + 상세
# =========================

# =========================
# (학생) 💰보상/벌금(관리자) — 별도 탭 (admin::🏦 내 통장)
# =========================
if "admin::🏦 내 통장" in tabs:
    with tab_map["admin::🏦 내 통장"]:
        st.subheader("💰보상/벌금 부여")
        if is_admin:
            st.info("관리자 모드에서는 상단 '💰보상/벌금' 탭에서 사용합니다.")
        else:

            # ✅ (보상/벌금) 내부 작은 탭
            sub_tab_all, sub_tab_personal = st.tabs(["전체", "개인"])

            # =================================================
            # [전체] : 기존 화면 그대로
            # =================================================
            with sub_tab_all:
                # -------------------------------------------------
                # 1) 전체 일괄 지급/벌금
                # -------------------------------------------------
                st.markdown("### 🎁 전체 일괄 지급/벌금")

                tpl_res3 = api_list_templates_cached()
                templates3 = tpl_res3.get("templates", []) if tpl_res3.get("ok") else []
                tpl_by_display3 = {template_display_for_trade(t): t for t in templates3}

                memo_bulk, dep_bulk, wd_bulk = render_admin_trade_ui(
                    prefix="admin_bulk_reward",
                    templates_list=templates3,
                    template_by_display=tpl_by_display3,
                )

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("저장", key="admin_bulk_reward_save", use_container_width=True):
                        if (dep_bulk > 0 and wd_bulk > 0) or (dep_bulk == 0 and wd_bulk == 0):
                            st.error("입금/출금은 둘 중 하나만 입력해 주세요.")
                        elif not memo_bulk:
                            st.error("내역(메모)을 입력해 주세요.")
                        else:
                            tre_apply_bulk = bool(st.session_state.get("admin_bulk_reward_treasury_apply", False))

                            if dep_bulk > 0:
                                res = api_admin_bulk_deposit(ADMIN_PIN, dep_bulk, memo_bulk)
                                if res.get("ok"):
                                    toast(f"일괄 지급 완료! ({res.get('count')}명)", icon="🎉")
                                    # ✅ 국고 반영(체크 시): 전체 지급 → 국고 세출(합산)
                                    if tre_apply_bulk:
                                        cnt = int(res.get("count", 0) or 0)
                                        if cnt > 0:
                                            api_treasury_auto_bulk_adjust(
                                                memo=f"전체 {memo_bulk}".strip(),
                                                signed_amount=-(int(dep_bulk) * cnt),
                                                actor="전체",
                                            )
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "일괄 지급 실패"))
                            else:
                                res = api_admin_bulk_withdraw(ADMIN_PIN, wd_bulk, memo_bulk)
                                if res.get("ok"):
                                    toast(f"벌금 완료! (적용 {res.get('count')}명)", icon="⚠️")
                                    # ✅ 국고 반영(체크 시): 전체 벌금 → 국고 세입(합산)
                                    if tre_apply_bulk:
                                        cnt = int(res.get("count", 0) or 0)
                                        if cnt > 0:
                                            api_treasury_auto_bulk_adjust(
                                                memo=f"전체 {memo_bulk}".strip(),
                                                signed_amount=(int(wd_bulk) * cnt),
                                                actor="전체",
                                            )
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "일괄 벌금 실패"))

                with b2:
                    if st.button("되돌리기(관리자)", key="admin_bulk_reward_undo_toggle", use_container_width=True):
                        st.session_state["admin_bulk_reward_undo_mode"] = not st.session_state.get(
                            "admin_bulk_reward_undo_mode", False
                        )

                # ✅ 되돌리기(관리자)
                if st.session_state.get("admin_bulk_reward_undo_mode", False):
                    st.subheader("↩️ 선택 되돌리기(관리자)")

                    admin_pin_rb = st.text_input(
                        "관리자 PIN 입력",
                        type="password",
                        key="admin_bulk_reward_undo_pin",
                    ).strip()

                    accounts_for_rb = api_list_accounts_cached().get("accounts", [])
                    name_map = {a.get("name", ""): a.get("student_id", "") for a in (accounts_for_rb or []) if a.get("name")}
                    pick_name = st.selectbox(
                        "되돌릴 학생 선택",
                        ["(선택)"] + list(name_map.keys()),
                        key="admin_bulk_reward_undo_pick_name",
                    )

                    if pick_name != "(선택)":
                        sid_rb = name_map.get(pick_name, "")
                        txr_rb = api_get_txs_by_student_id(sid_rb, limit=120)
                        df_rb = pd.DataFrame(txr_rb.get("rows", [])) if txr_rb.get("ok") else pd.DataFrame()

                        if not df_rb.empty:
                            view_df = df_rb.head(50).copy()

                            def _can_rollback_row(row):
                                if str(row.get("type", "")) == "rollback":
                                    return False
                                memo = str(row.get("memo", "") or "")
                                if _is_savings_memo(memo) or str(row.get("type", "")) in ("maturity",):
                                    return False
                                # ✅ 투자 내역은 되돌리기 비활성화
                                if _is_invest_memo(memo):
                                    return False
                                return True

                            view_df["가능"] = view_df.apply(_can_rollback_row, axis=1)

                            selected_ids = []
                            for _, r in view_df.iterrows():
                                tx_id = r["tx_id"]
                                label = f"{r['created_at_kr']} | {r['memo']} | +{int(r['deposit'])} / -{int(r['withdraw'])}"
                                ck = st.checkbox(
                                    label,
                                    key=f"admin_bulk_reward_rb_ck_{sid_rb}_{tx_id}",
                                    disabled=(not r["가능"]),
                                )
                                if ck and r["가능"]:
                                    selected_ids.append(tx_id)

                            if st.button("선택 항목 되돌리기", key="admin_bulk_reward_do_rb", use_container_width=True):
                                if not is_admin_pin(admin_pin_rb):
                                    st.error("관리자 PIN이 틀립니다.")
                                elif not selected_ids:
                                    st.warning("체크된 항목이 없어요.")
                                else:
                                    res2 = api_admin_rollback_selected(admin_pin_rb, sid_rb, selected_ids)
                                    if res2.get("ok"):
                                        toast(f"선택 {res2.get('undone')}건 되돌림 완료", icon="↩️")
                                        api_list_accounts_cached.clear()
                                        st.rerun()
                                    else:
                                        st.error(res2.get("error", "되돌리기 실패"))


                # -------------------------------------------------
                # 2) 내역 템플릿 순서 정렬
                # -------------------------------------------------
                h1, h2 = st.columns([0.35, 9.65], vertical_alignment="center")
                with h1:
                    if st.button(
                        "▸" if not st.session_state.get("bank_tpl_sort_panel_open", False) else "▾",
                        key="bank_tpl_sort_panel_toggle",
                        use_container_width=True,
                    ):
                        st.session_state["bank_tpl_sort_panel_open"] = not st.session_state.get("bank_tpl_sort_panel_open", False)
                        st.rerun()
                with h2:
                    st.markdown("### 🧩 내역 템플릿 순서 정렬")

                if not st.session_state.get("bank_tpl_sort_panel_open", False):
                    st.caption("펼치려면 왼쪽 화살표(▸)를 눌러주세요.")
                else:
                    tpl_res2 = api_list_templates_cached()
                    templates = tpl_res2.get("templates", []) if tpl_res2.get("ok") else []
                    templates = sorted(
                        templates,
                        key=lambda t: (int(t.get("order", 999999) or 999999), str(t.get("label", ""))),
                    )
                    tpl_by_id = {t["template_id"]: t for t in templates}

                    st.session_state.setdefault("bank_tpl_sort_mode", False)
                    st.session_state.setdefault("bank_tpl_work_ids", [])
                    st.session_state.setdefault("bank_tpl_mobile_sort_ui", False)

                    if not st.session_state["bank_tpl_sort_mode"]:
                        st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                    else:
                        cur_ids = [t["template_id"] for t in templates]
                        if (not st.session_state["bank_tpl_work_ids"]) or (set(st.session_state["bank_tpl_work_ids"]) != set(cur_ids)):
                            st.session_state["bank_tpl_work_ids"] = cur_ids

                    topA, topB, topC, topD = st.columns([1.1, 1.1, 1.4, 1.6])
                    with topA:
                        if st.button(
                            "정렬모드 ON" if not st.session_state["bank_tpl_sort_mode"] else "정렬모드 OFF",
                            key="bank_tpl_sort_toggle",
                            use_container_width=True,
                        ):
                            st.session_state["bank_tpl_sort_mode"] = not st.session_state["bank_tpl_sort_mode"]
                            if not st.session_state["bank_tpl_sort_mode"]:
                                st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                            st.rerun()
                    with topB:
                        if st.button("order 채우기(1회)", key="bank_tpl_backfill_btn", use_container_width=True):
                            res = api_admin_backfill_template_order(ADMIN_PIN)
                            if res.get("ok"):
                                toast("order 초기화 완료!", icon="🧷")
                                api_list_templates_cached.clear()
                                st.session_state["bank_tpl_work_ids"] = []
                                st.rerun()
                            else:
                                st.error(res.get("error", "실패"))
                    with topC:
                        if st.button("order 전체 재정렬", key="bank_tpl_normalize_btn", use_container_width=True):
                            res = api_admin_normalize_template_order(ADMIN_PIN)
                            if res.get("ok"):
                                toast("order 재정렬 완료!", icon="🧹")
                                api_list_templates_cached.clear()
                                st.session_state["bank_tpl_work_ids"] = []
                                st.rerun()
                            else:
                                st.error(res.get("error", "실패"))
                    with topD:
                        st.session_state["bank_tpl_mobile_sort_ui"] = st.checkbox(
                            "간단 모드(모바일용)",
                            value=bool(st.session_state["bank_tpl_mobile_sort_ui"]),
                            key="bank_tpl_mobile_sort_ui_chk",
                            help="모바일에서 표가 세로로 쌓여 보이는 문제를 피하기 위한 정렬 UI입니다.",
                        )

                    if st.session_state["bank_tpl_sort_mode"]:
                        st.caption("✅ 이동은 화면에서만 즉시 반영 → 마지막에 ‘저장(한 번에)’ 1번 누르면 DB 반영")

                    work_ids = st.session_state["bank_tpl_work_ids"]
                    if not work_ids:
                        st.info("템플릿이 아직 없어요.")
                    else:
                        if st.session_state["bank_tpl_mobile_sort_ui"]:
                            options = list(range(len(work_ids)))

                            def _opt_label(i: int):
                                tid = work_ids[i]
                                t = tpl_by_id.get(tid, {})
                                kind_kr = "입금" if t.get("kind") == "deposit" else "출금"
                                amt = int(t.get("amount", 0) or 0)
                                return f"{i+1}. {t.get('label','')} ({kind_kr} {amt})"

                            pick_i = st.selectbox(
                                "이동할 항목 선택",
                                options,
                                format_func=_opt_label,
                                key="bank_tpl_simple_pick",
                            )

                            b1, b2, b3 = st.columns([1, 1, 2])
                            with b1:
                                if st.button(
                                    "위로 ▲",
                                    key="bank_tpl_simple_up",
                                    disabled=(not st.session_state["bank_tpl_sort_mode"]) or pick_i == 0,
                                    use_container_width=True,
                                ):
                                    work_ids[pick_i - 1], work_ids[pick_i] = work_ids[pick_i], work_ids[pick_i - 1]
                                    st.session_state["bank_tpl_work_ids"] = work_ids
                                    st.session_state["bank_tpl_simple_pick"] = max(0, pick_i - 1)
                                    st.rerun()
                            with b2:
                                if st.button(
                                    "아래로 ▼",
                                    key="bank_tpl_simple_dn",
                                    disabled=(not st.session_state["bank_tpl_sort_mode"]) or pick_i == (len(work_ids) - 1),
                                    use_container_width=True,
                                ):
                                    work_ids[pick_i + 1], work_ids[pick_i] = work_ids[pick_i], work_ids[pick_i + 1]
                                    st.session_state["bank_tpl_work_ids"] = work_ids
                                    st.session_state["bank_tpl_simple_pick"] = min(len(work_ids) - 1, pick_i + 1)
                                    st.rerun()
                            with b3:
                                st.caption("정렬모드 ON일 때만 이동 가능")

                            html = ["<div class='tpl-simple'>"]
                            for idx, tid in enumerate(work_ids, start=1):
                                t = tpl_by_id.get(tid, {})
                                kind_kr = "입금" if t.get("kind") == "deposit" else "출금"
                                amt = int(t.get("amount", 0) or 0)
                                lab = str(t.get("label", "") or "")
                                html.append(
                                    f"<div class='item'>"
                                    f"<span class='idx'>{idx}</span>"
                                    f"<span class='lab'>{lab}</span>"
                                    f"<div class='meta'>{kind_kr} · {amt}</div>"
                                    f"</div>"
                                )
                            html.append("</div>")
                            st.markdown("\n".join(html), unsafe_allow_html=True)

                            if st.session_state["bank_tpl_sort_mode"]:
                                s1, s2 = st.columns([1.2, 1.2])
                                with s1:
                                    if st.button("저장(한 번에)", key="bank_tpl_save_orders_btn_simple", use_container_width=True):
                                        res = api_admin_save_template_orders(ADMIN_PIN, st.session_state["bank_tpl_work_ids"])
                                        if res.get("ok"):
                                            toast(f"순서 저장 완료! ({res.get('count', 0)}개)", icon="💾")
                                            st.session_state["bank_tpl_sort_mode"] = False
                                            api_list_templates_cached.clear()
                                            st.session_state["bank_tpl_work_ids"] = []
                                            st.rerun()
                                        else:
                                            st.error(res.get("error", "저장 실패"))
                                with s2:
                                    if st.button("취소(원복)", key="bank_tpl_cancel_orders_btn_simple", use_container_width=True):
                                        st.session_state["bank_tpl_sort_mode"] = False
                                        st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                                        toast("변경 취소(원복)!", icon="↩️")
                                        st.rerun()
                        else:
                            head = st.columns([0.7, 5.2, 2.2, 1.4], vertical_alignment="center")
                            head[0].markdown("<div class='tpl-head'>순서</div>", unsafe_allow_html=True)
                            head[1].markdown("<div class='tpl-head'>내역</div>", unsafe_allow_html=True)
                            head[2].markdown("<div class='tpl-head'>종류·금액</div>", unsafe_allow_html=True)
                            head[3].markdown("<div class='tpl-head'>이동</div>", unsafe_allow_html=True)

                            for idx, tid in enumerate(work_ids):
                                t = tpl_by_id.get(tid, {})
                                label = t.get("label", "")
                                kind_kr = "입금" if t.get("kind") == "deposit" else "출금"
                                amt = int(t.get("amount", 0) or 0)

                                row = st.columns([0.7, 5.2, 2.2, 0.7, 0.7], vertical_alignment="center")
                                row[0].markdown(f"<div class='tpl-cell'>{idx+1}</div>", unsafe_allow_html=True)
                                row[1].markdown(
                                    f"<div class='tpl-cell'><div class='tpl-label'>{label}</div></div>",
                                    unsafe_allow_html=True,
                                )
                                row[2].markdown(
                                    f"<div class='tpl-cell'><div class='tpl-sub'>{kind_kr} · {amt}</div></div>",
                                    unsafe_allow_html=True,
                                )

                                if st.session_state["bank_tpl_sort_mode"]:
                                    up_disabled = (idx == 0)
                                    down_disabled = (idx == len(work_ids) - 1)

                                    if row[3].button("⬆", key=f"bank_tpl_up_fast_{tid}", disabled=up_disabled, use_container_width=True):
                                        work_ids[idx - 1], work_ids[idx] = work_ids[idx], work_ids[idx - 1]
                                        st.session_state["bank_tpl_work_ids"] = work_ids
                                        st.rerun()

                                    if row[4].button("⬇", key=f"bank_tpl_dn_fast_{tid}", disabled=down_disabled, use_container_width=True):
                                        work_ids[idx + 1], work_ids[idx] = work_ids[idx], work_ids[idx + 1]
                                        st.session_state["bank_tpl_work_ids"] = work_ids
                                        st.rerun()
                                else:
                                    row[3].markdown("<div class='tpl-cell'></div>", unsafe_allow_html=True)
                                    row[4].markdown("<div class='tpl-cell'></div>", unsafe_allow_html=True)

                            if st.session_state["bank_tpl_sort_mode"]:
                                s1, s2 = st.columns([1.2, 1.2])
                                with s1:
                                    if st.button("저장(한 번에)", key="bank_tpl_save_orders_btn", use_container_width=True):
                                        res = api_admin_save_template_orders(ADMIN_PIN, st.session_state["bank_tpl_work_ids"])
                                        if res.get("ok"):
                                            toast(f"순서 저장 완료! ({res.get('count', 0)}개)", icon="💾")
                                            st.session_state["bank_tpl_sort_mode"] = False
                                            api_list_templates_cached.clear()
                                            st.session_state["bank_tpl_work_ids"] = []
                                            st.rerun()
                                        else:
                                            st.error(res.get("error", "저장 실패"))
                                with s2:
                                    if st.button("취소(원복)", key="bank_tpl_cancel_orders_btn", use_container_width=True):
                                        st.session_state["bank_tpl_sort_mode"] = False
                                        st.session_state["bank_tpl_work_ids"] = [t["template_id"] for t in templates]
                                        toast("변경 취소(원복)!", icon="↩️")
                                        st.rerun()


                # -------------------------------------------------
                # 3) 템플릿 추가/수정/삭제
                # -------------------------------------------------
                st.markdown("### 🧩 템플릿 추가/수정/삭제")

                KIND_TO_KR = {"deposit": "입금", "withdraw": "출금"}
                KR_TO_KIND = {"입금": "deposit", "출금": "withdraw"}

                templates_now = api_list_templates_cached().get("templates", [])
                mode = st.radio("작업", ["추가", "수정"], horizontal=True, key="bank_tpl_mode")

                st.session_state.setdefault("bank_tpl_edit_id", "")
                st.session_state.setdefault("bank_tpl_pick_prev", None)

                # ✅ 기존 bank_tpl_label 대신: base_label + category(구분)로 분리
                st.session_state.setdefault("bank_tpl_base_label", "")
                st.session_state.setdefault("bank_tpl_category_kr", "없음")

                st.session_state.setdefault("bank_tpl_kind_setting_kr", "입금")
                st.session_state.setdefault("bank_tpl_amount", 10)
                st.session_state.setdefault("bank_tpl_order", 1)

                CATEGORY_CHOICES = ["없음", "보상", "구입", "벌금"]

                def tpl_display(t):
                    kind_kr = "입금" if t["kind"] == "deposit" else "출금"
                    return f"{t['label']}[{kind_kr} {int(t['amount'])}]"

                def _fill_tpl_form(t):
                    st.session_state["bank_tpl_edit_id"] = t["template_id"]

                    # ✅ category/base_label이 있으면 우선 사용, 없으면 label에서 파싱
                    cat = str(t.get("category", "") or "").strip()
                    base = str(t.get("base_label", "") or "").strip()

                    if (not cat) and (not base):
                        cat2, base2 = _parse_template_label(t.get("label", ""))
                        cat = str(cat2 or "").strip()
                        base = str(base2 or "").strip()

                    st.session_state["bank_tpl_base_label"] = base
                    st.session_state["bank_tpl_category_kr"] = cat if cat else "없음"

                    st.session_state["bank_tpl_kind_setting_kr"] = KIND_TO_KR.get(t.get("kind", "deposit"), "입금")
                    st.session_state["bank_tpl_amount"] = int(t.get("amount", 10) or 10)
                    st.session_state["bank_tpl_order"] = int(t.get("order", 1) or 1)

                if mode == "수정" and templates_now:
                    labels = [tpl_display(t) for t in templates_now]
                    pick = st.selectbox(
                        "수정할 템플릿 선택",
                        list(range(len(templates_now))),
                        format_func=lambda idx: labels[idx],
                        key="bank_tpl_pick",
                    )
                    if st.session_state["bank_tpl_pick_prev"] != pick:
                        st.session_state["bank_tpl_pick_prev"] = pick
                        _fill_tpl_form(templates_now[pick])
                elif mode == "추가":
                    st.session_state["bank_tpl_edit_id"] = ""
                    st.session_state["bank_tpl_pick_prev"] = None

                # ✅ 컬럼: 내역이름 / 구분 / 종류 / 금액
                tcol1, tcol_mid, tcol2, tcol3 = st.columns([2, 1.2, 1, 1])
                with tcol1:
                    tpl_base_label = st.text_input("내역 이름", key="bank_tpl_base_label").strip()
                with tcol_mid:
                    tpl_category_kr = st.selectbox("구분", CATEGORY_CHOICES, key="bank_tpl_category_kr")
                with tcol2:
                    tpl_kind_kr = st.selectbox("종류", ["입금", "출금"], key="bank_tpl_kind_setting_kr")
                with tcol3:
                    tpl_amount = st.number_input("금액", min_value=1, step=1, key="bank_tpl_amount")

                tpl_order = st.number_input("순서(order)", min_value=1, step=1, key="bank_tpl_order")

                if st.button("저장(추가/수정)", key="bank_tpl_save", use_container_width=True):
                    if not tpl_base_label:
                        st.error("내역 이름이 필요합니다.")
                    else:
                        kind_eng = KR_TO_KIND[tpl_kind_kr]
                        tid = st.session_state.get("bank_tpl_edit_id", "") if mode == "수정" else ""

                        # ✅ "없음"이면 category는 빈 문자열로 저장
                        cat = "" if str(tpl_category_kr) == "없음" else str(tpl_category_kr).strip()

                        res = api_admin_upsert_template(
                            ADMIN_PIN,
                            tid,
                            tpl_base_label,
                            cat,
                            kind_eng,
                            int(tpl_amount),
                            int(tpl_order),
                        )
                        if res.get("ok"):
                            toast("템플릿 저장 완료!", icon="🧩")
                            api_list_templates_cached.clear()
                            st.rerun()
                        else:
                            st.error(res.get("error", "템플릿 저장 실패"))

                st.caption("삭제")
                if templates_now:
                    del_labels = [tpl_display(t) for t in templates_now]
                    del_pick = st.selectbox(
                        "삭제할 템플릿 선택",
                        list(range(len(templates_now))),
                        format_func=lambda idx: del_labels[idx],
                        key="bank_tpl_del_pick",
                    )
                    del_id = templates_now[del_pick]["template_id"]

                    if st.button("삭제", key="bank_tpl_del_btn", use_container_width=True):
                        st.session_state["bank_tpl_del_confirm"] = True

                    if st.session_state.get("bank_tpl_del_confirm", False):
                        st.warning("정말로 삭제하시겠습니까?")
                        y, n = st.columns(2)
                        with y:
                            if st.button("예", key="bank_tpl_del_yes", use_container_width=True):
                                res = api_admin_delete_template(ADMIN_PIN, del_id)
                                if res.get("ok"):
                                    toast("삭제 완료!", icon="🗑️")
                                    st.session_state["bank_tpl_del_confirm"] = False
                                    api_list_templates_cached.clear()
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "삭제 실패"))
                        with n:
                            if st.button("아니오", key="bank_tpl_del_no", use_container_width=True):
                                st.session_state["bank_tpl_del_confirm"] = False
                                st.rerun()

                st.markdown("### 📥 템플릿 엑셀로 일괄 추가")

                import io

                # -------------------------
                # 1) 샘플 엑셀 다운로드
                # -------------------------
                sample_df = pd.DataFrame(
                    [
                        {"내역이름": "대여료", "구분": "구입", "종류": "출금", "금액": 100, "순서": 1},
                        {"내역이름": "발표", "구분": "보상", "종류": "입금", "금액": 10, "순서": 2},
                        {"내역이름": "지각", "구분": "벌금", "종류": "출금", "금액": 20, "순서": 3},
                        {"내역이름": "기타", "구분": "없음", "종류": "입금", "금액": 5, "순서": 4},
                    ],
                    columns=["내역이름", "구분", "종류", "금액", "순서"],
                )

                bio = io.BytesIO()
                with pd.ExcelWriter(bio, engine="openpyxl") as writer:
                    sample_df.to_excel(writer, index=False, sheet_name="templates")
                bio.seek(0)

                st.download_button(
                    "📄 샘플 엑셀 다운로드",
                    data=bio.getvalue(),
                    file_name="템플릿_샘플.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="bank_tpl_sample_xlsx_download",
                )

                st.caption("• 샘플 형식: 내역이름 | 구분(없음/보상/구입/벌금) | 종류(입금/출금) | 금액 | 순서")
                st.caption("• 엑셀을 올린 뒤, 아래의 **저장** 버튼을 눌러야 실제 반영됩니다.")

                # -------------------------
                # 2) 엑셀 업로드 + 미리보기
                # -------------------------
                upl = st.file_uploader(
                    "엑셀 업로드(.xlsx)",
                    type=["xlsx"],
                    key="bank_tpl_bulk_xlsx",
                    help="샘플 형식 그대로 업로드하세요. 업로드만으로는 반영되지 않고, 아래 '저장' 버튼을 눌러야 반영됩니다.",
                )

                st.session_state.setdefault("bank_tpl_bulk_df", None)

                if upl is not None:
                    try:
                        df = pd.read_excel(upl)
                        df = df.copy()

                        # 공백 컬럼명 정리
                        df.columns = [str(c).strip() for c in df.columns]

                        need_cols = ["내역이름", "구분", "종류", "금액", "순서"]
                        miss = [c for c in need_cols if c not in df.columns]
                        if miss:
                            st.error(f"필수 컬럼이 없습니다: {miss}")
                            st.session_state["bank_tpl_bulk_df"] = None
                        else:
                            # 문자열/정수 정리
                            df["내역이름"] = df["내역이름"].astype(str).str.strip()
                            df["구분"] = df["구분"].astype(str).str.strip()
                            df["종류"] = df["종류"].astype(str).str.strip()
                            df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
                            df["순서"] = pd.to_numeric(df["순서"], errors="coerce").fillna(999999).astype(int)

                            # 기본값 보정
                            df.loc[df["구분"].isin(["nan", "None", ""]), "구분"] = "없음"

                            # 검증
                            bad_cat = df[~df["구분"].isin(["없음", "보상", "구입", "벌금"])]
                            bad_kind = df[~df["종류"].isin(["입금", "출금"])]
                            bad_label = df[df["내역이름"].str.len() == 0]
                            bad_amt = df[df["금액"] <= 0]

                            if (not bad_cat.empty) or (not bad_kind.empty) or (not bad_label.empty) or (not bad_amt.empty):
                                if not bad_label.empty:
                                    st.error("❌ 내역이름이 비어있는 행이 있습니다.")
                                if not bad_cat.empty:
                                    st.error("❌ 구분 값이 잘못된 행이 있습니다. (없음/보상/구입/벌금만 가능)")
                                if not bad_kind.empty:
                                    st.error("❌ 종류 값이 잘못된 행이 있습니다. (입금/출금만 가능)")
                                if not bad_amt.empty:
                                    st.error("❌ 금액은 1 이상이어야 합니다.")
                                st.session_state["bank_tpl_bulk_df"] = None
                            else:
                                st.session_state["bank_tpl_bulk_df"] = df
                                st.success(f"업로드 완료! ({len(df)}행) 아래 미리보기 확인 후 저장을 누르세요.")
                                st.dataframe(df, use_container_width=True, hide_index=True)

                    except Exception as e:
                        st.error(f"엑셀 읽기 실패: {e}")
                        st.session_state["bank_tpl_bulk_df"] = None

                # -------------------------
                # 3) 저장(반영) 버튼 + (옵션) 기존 리스트 삭제
                # -------------------------
                del_old = st.checkbox(
                    "저장 시 기존 템플릿 리스트를 모두 삭제하고 새로 올린 엑셀로 덮어쓰기",
                    value=False,
                    key="bank_tpl_bulk_delete_old",
                )

                if st.button("✅ 엑셀 내용 저장(반영)", use_container_width=True, key="bank_tpl_bulk_save_btn"):
                    df2 = st.session_state.get("bank_tpl_bulk_df", None)
                    if df2 is None or df2.empty:
                        st.error("먼저 올바른 엑셀을 업로드하세요.")
                    else:
                        try:
                            # 1) 기존 삭제(옵션)
                            if del_old:
                                docs = list(db.collection("templates").stream())
                                batch = db.batch()
                                for d in docs:
                                    batch.delete(d.reference)
                                if docs:
                                    batch.commit()

                            # 2) 엑셀 행들을 upsert(신규로 저장)
                            saved = 0
                            for _, r in df2.iterrows():
                                base_label = str(r["내역이름"]).strip()
                                cat_kr = str(r["구분"]).strip()
                                kind_kr = str(r["종류"]).strip()
                                amt = int(r["금액"])
                                order = int(r["순서"])

                                category = "" if cat_kr == "없음" else cat_kr
                                kind = KR_TO_KIND.get(kind_kr, "deposit")

                                res = api_admin_upsert_template(
                                    ADMIN_PIN,
                                    "",  # ✅ 일괄은 신규로 추가(기존과 매칭/수정은 하지 않음)
                                    base_label,
                                    category,
                                    kind,
                                    amt,
                                    order,
                                )
                                if res.get("ok"):
                                    saved += 1

                            api_list_templates_cached.clear()
                            toast(f"엑셀 저장 완료! ({saved}개 반영)", icon="📥")
                            st.session_state["bank_tpl_bulk_df"] = None
                            st.rerun()

                        except Exception as e:
                            st.error(f"저장 실패: {e}")
            
            # =================================================
            # [개인] : 체크된 학생만 “일괄 지급/벌금” 적용
            # =================================================
            with sub_tab_personal:
                st.markdown("### 👥 대상 학생 선택 (체크한 학생만 적용)")
                accounts_now = api_list_accounts_cached().get("accounts", [])
                import re

                def _num_key(acc):
                    name = str(acc.get("name", ""))
                    m = re.search(r"\d+", name)
                    if m:
                        return int(m.group())   # 1~9 → 01~09처럼 숫자 기준 정렬
                    return 9999                # 번호 없으면 맨 뒤

                accounts_now = sorted(accounts_now, key=_num_key)

                if not accounts_now:
                    st.info("활성 계정이 없습니다.")
                else:
                    selected_ids = []
                    selected_names = []

                    # ✅ 5명씩 한 줄
                    for base in range(0, len(accounts_now), 5):
                        cols = st.columns(5)
                        chunk = accounts_now[base : base + 5]
                        for j in range(5):
                            with cols[j]:
                                if j < len(chunk):
                                    a = chunk[j]
                                    nm = str(a.get("name", "") or "")
                                    sid = str(a.get("student_id", "") or "")
                                    import re
                                    m = re.search(r"\d+", nm)
                                    num = m.group() if m else "?"

                                    label = f"{num}번 {nm}"
                                    ck = st.checkbox(label, key=f"admin_personal_pick_{sid}")
                                    if ck:
                                        selected_ids.append(sid)
                                        selected_names.append(nm)
                                else:
                                    st.write("")

                    if selected_names:
                        st.caption("선택됨: " + " · ".join(selected_names))

                    st.markdown("### 🎁 개인 지급/벌금")

                    tpl_res_p = api_list_templates_cached()
                    templates_p = tpl_res_p.get("templates", []) if tpl_res_p.get("ok") else []
                    tpl_by_display_p = {template_display_for_trade(t): t for t in templates_p}

                    memo_p, dep_p, wd_p = render_admin_trade_ui(
                        prefix="admin_personal_reward",
                        templates_list=templates_p,
                        template_by_display=tpl_by_display_p,
                    )

                    if st.button("저장", key="admin_personal_reward_save", use_container_width=True):
                        if not selected_ids:
                            st.warning("먼저 적용할 학생을 체크해 주세요.")
                        elif (dep_p > 0 and wd_p > 0) or (dep_p == 0 and wd_p == 0):
                            st.error("입금/출금은 둘 중 하나만 입력해 주세요.")
                        elif not memo_p:
                            st.error("내역(메모)을 입력해 주세요.")
                        else:
                            ok_cnt = 0
                            fail = []

                            tre_apply_personal = bool(st.session_state.get("admin_personal_reward_treasury_apply", False))
                            sid_to_disp = {}
                            try:
                                for _a in (accounts_now or []):
                                    _sid = str(_a.get("student_id", "") or "")
                                    if _sid:
                                        _no = int(_a.get("no", 0) or 0)
                                        _nm = str(_a.get("name", "") or "")
                                        if _no > 0:
                                            sid_to_disp[_sid] = f"{_no}번 {_nm}"
                                        else:
                                            sid_to_disp[_sid] = _nm
                            except Exception:
                                sid_to_disp = {}

                            for sid in selected_ids:
                                # ✅ 체크된 학생만 적용 (관리자 출금은 음수 허용)
                                disp_name = sid_to_disp.get(str(sid), str(sid))
                                tre_memo = f"{disp_name} {memo_p}".strip()

                                res = api_admin_add_tx_by_student_id_with_treasury(
                                    ADMIN_PIN,
                                    sid,
                                    memo_p,
                                    int(dep_p),
                                    int(wd_p),
                                    tre_apply_personal,
                                    tre_memo,
                                    actor=disp_name,
                                )
                                if res.get("ok"):
                                    ok_cnt += 1
                                else:
                                    fail.append(res.get("error", "저장 실패"))

                            if ok_cnt > 0:
                                toast(f"개인 적용 완료! ({ok_cnt}명)", icon="✅")
                                api_list_accounts_cached.clear()
                                st.rerun()
                            else:
                                st.error("적용 실패: " + (fail[0] if fail else "알 수 없는 오류"))


# =========================
# 📈 투자 (공용 렌더: 관리자 탭과 투자(관리자) 탭을 동일 코드로 처리)
# =========================
# =========================
# 📈 투자 (공용 렌더: 관리자 탭과 투자(관리자) 탭을 동일 코드로 처리)
# =========================
def _render_invest_admin_like(*, inv_admin_ok_flag: bool, force_is_admin: bool, my_student_id, login_name, login_pin):
    """관리자 투자 화면을 동일하게 렌더링(권한 학생의 투자(관리자) 탭에서도 동일 UI/기능)."""
    # ✅ 이 함수 내부에서는 is_admin 값을 force_is_admin으로 "가상" 설정해서
    #    관리자 화면 분기(학생용 UI 숨김 등)가 관리자와 동일하게 동작하게 한다.
    is_admin = bool(force_is_admin)
    inv_admin_ok = bool(inv_admin_ok_flag)  # ✅ 관리자 기능 실행 허용 여부(권한)
    
    INV_PROD_COL = "invest_products"
    INV_HIST_COL = "invest_price_history"
    INV_LEDGER_COL = "invest_ledger"
    
    
    # ✅ (PATCH) 투자 탭 - 종목별 '주가 변동 내역' 표 글자/패딩 축소 전용 CSS
    st.markdown(
        """
        <style>
        table.inv_hist_table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            line-height: 1.15;
        }
        table.inv_hist_table th, table.inv_hist_table td {
            padding: 6px 8px;
            border: 1px solid rgba(0,0,0,0.08);
            vertical-align: middle;
        }
        table.inv_hist_table th {
            font-weight: 700;
            background: rgba(0,0,0,0.03);
            text-align: center;  /* ✅ 제목셀만 중앙정렬 */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
    # 유틸(함수 대신 안전하게 inline)
    # -------------------------
    days_ko = ["월", "화", "수", "목", "금", "토", "일"]
    
    def _as_price1(v):
        try:
            return float(f"{float(v):.1f}")
        except Exception:
            return 0.0
    
    def _ts_to_dt(v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        try:
            if hasattr(v, "to_datetime"):
                out = v.to_datetime()
                if isinstance(out, datetime):
                    return out
        except Exception:
            pass
        return None
    
    def _fmt_kor_date_md(dt_obj):
        if not dt_obj:
            return "-"
        try:
            dt_kst = dt_obj.astimezone(KST)
        except Exception:
            dt_kst = dt_obj
        try:
            wd = days_ko[int(dt_kst.weekday())]
        except Exception:
            wd = ""
        return f"{dt_kst.month}월 {dt_kst.day}일({wd})"
    
    # -------------------------
    # 권한: 지급(회수) 가능?
    # - 관리자 or 직업 '투자증권'
    # -------------------------
    def _can_redeem(actor_student_id: str) -> bool:
        if inv_admin_ok:
            return True
        try:
            if not actor_student_id:
                return False
            snap = db.collection("students").document(str(actor_student_id)).get()
            if not snap.exists:
                return False
            rid = str((snap.to_dict() or {}).get("role_id", "") or "")
            if not rid:
                return False
            roles = api_list_roles_cached()
            for r in roles:
                if str(r.get("role_id")) == rid:
                    return str(r.get("role_name", "") or "") == "투자증권"
            return False
        except Exception:
            return False
    
    # -------------------------
    # 장부 로드
    # -------------------------
    def _load_ledger(for_student_id: str | None):
        try:
            q = (
                db.collection(INV_LEDGER_COL)
                .order_by("buy_at", direction=firestore.Query.DESCENDING)
                .limit(400)
                .stream()
            )
            rows = []
            for d in q:
                x = d.to_dict() or {}
                if for_student_id and str(x.get("student_id")) != str(for_student_id):
                    continue
                rows.append({**x, "_doc_id": d.id})
            return rows
        except Exception:
            # fallback(인덱스 등)
            try:
                q = db.collection(INV_LEDGER_COL).limit(400).stream()
                rows = []
                for d in q:
                    x = d.to_dict() or {}
                    if for_student_id and str(x.get("student_id")) != str(for_student_id):
                        continue
                    rows.append({**x, "_doc_id": d.id})
                return rows
            except Exception:
                return []
    
    # -------------------------
    # 주가 변동 내역 로드 (표용)
    # -------------------------
    def _get_history(product_id: str, limit=120):
        pid = str(product_id)
        out = []
        # 1) 인덱스 OK일 때
        try:
            q = (
                db.collection(INV_HIST_COL)
                .where(filter=FieldFilter("product_id", "==", pid))
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(int(limit))
                .stream()
            )
            for d in q:
                x = d.to_dict() or {}
                out.append(
                    {
                        "created_at": x.get("created_at"),
                        "reason": str(x.get("reason", "") or "").strip(),
                        "price_before": _as_price1(x.get("price_before", x.get("price", 0.0))),
                        "price_after": _as_price1(x.get("price_after", x.get("price", 0.0))),
                    }
                )
            return out
        except Exception:
            pass
    
        # 2) fallback
        try:
            q = (
                db.collection(INV_HIST_COL)
                .where(filter=FieldFilter("product_id", "==", pid))
                .limit(int(limit))
                .stream()
            )
            for d in q:
                x = d.to_dict() or {}
                out.append(
                    {
                        "created_at": x.get("created_at"),
                        "reason": str(x.get("reason", "") or "").strip(),
                        "price_before": _as_price1(x.get("price_before", x.get("price", 0.0))),
                        "price_after": _as_price1(x.get("price_after", x.get("price", 0.0))),
                    }
                )
            out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
            return out
        except Exception:
            return []
    
    # -------------------------
    # 종목 로드
    # -------------------------
    def _get_products(active_only=True):
        try:
            q = db.collection(INV_PROD_COL)
            if active_only:
                q = q.where(filter=FieldFilter("is_active", "==", True))
            docs = q.stream()
            out = []
            for d in docs:
                x = d.to_dict() or {}
                nm = str(x.get("name", "") or "").strip()
                if not nm:
                    continue
                out.append(
                    {
                        "product_id": d.id,
                        "name": nm,
                        "current_price": _as_price1(x.get("current_price", 0.0)),
                        "is_active": bool(x.get("is_active", True)),
                    }
                )
            out.sort(key=lambda r: r["name"])
            return out
        except Exception:
            return []
    
    # -------------------------
    # 회수 계산(÷10)
    # -------------------------
    def _calc_redeem_amount(invest_amount: int, buy_price: float, sell_price: float):
        return _calc_invest_redeem_projection(invest_amount, buy_price, sell_price)
    
    # -------------------------------------------------
    # 1) (상단) 종목 및 주가 변동
    # -------------------------------------------------
    st.markdown("### 📈 종목 및 주가 변동")
    
    # (사용자) 상단 요약: 통장 잔액 / 투자 원금 / 현재 평가
    if not is_admin:
        # 1) 통장 잔액
        cur_bal = 0
        try:
            if my_student_id:
                s = db.collection("students").document(str(my_student_id)).get()
                if s.exists:
                    cur_bal = int((s.to_dict() or {}).get("balance", 0) or 0)
        except Exception:
            cur_bal = 0

        # 2) 투자 원금 / 현재 평가
        principal_total = 0
        eval_total = 0
        principal_by_name = {}
        eval_by_name = {}

        def _add_sum(d, k, v):
            d[k] = int(d.get(k, 0) or 0) + int(v or 0)

        def _fmt_breakdown(d):
            items = []
            for k in sorted(d.keys()):
                v = int(d.get(k, 0) or 0)
                if v > 0:
                    items.append(f"{k} {v}드림")
            return ", ".join(items) if items else "없음"

        try:
            prods_now = _get_products(active_only=True)
            price_by_id = {str(p["product_id"]): float(p.get("current_price", 0.0) or 0.0) for p in prods_now}
            name_by_id = {str(p["product_id"]): str(p.get("name", "") or "") for p in prods_now}

            my_rows = _load_ledger(my_student_id)

            for r in my_rows:
                if bool(r.get("redeemed", False)):
                    continue

                amt = int(r.get("invest_amount", 0) or 0)
                if amt <= 0:
                    continue

                pid = str(r.get("product_id", "") or "")
                nm = str(r.get("product_name", "") or "").strip()
                if not nm:
                    nm = str(name_by_id.get(pid, "") or "").strip()
                if not nm:
                    nm = "미지정"

                buy_price = float(r.get("buy_price", 0.0) or 0.0)
                cur_price = float(price_by_id.get(pid, 0.0) or 0.0)

                # ✅ 현재 평가는 투자 회수(지급) 계산과 동일 규칙 적용
                _, _, cur_val = _calc_invest_redeem_projection(amt, buy_price, cur_price)

                _add_sum(principal_by_name, nm, amt)
                _add_sum(eval_by_name, nm, int(round(cur_val)))

            principal_total = sum(principal_by_name.values())
            eval_total = sum(eval_by_name.values())

        except Exception:
            principal_total = 0
            eval_total = 0
            principal_by_name = {}
            eval_by_name = {}
    
    products = _get_products(active_only=True)
    if not products:
        st.info("등록된 투자 종목이 없습니다. 이용을 위해 관리자가 종목을 등록해야 합니다.")
    else:
        for p in products:
            nm = p["name"]
            cur = p["current_price"]
            st.markdown(f"- **{nm}** (현재주가 **{cur:.1f}**)")
    
            if inv_admin_ok:
                with st.expander(f"{nm} 주가 변동 반영", expanded=False):
                    c1, c2, c3 = st.columns([3.2, 2.2, 1.2], gap="small")
                    with c1:
                        reason = st.text_input("변동 사유", key=f"inv_reason_{p['product_id']}")
                    with c2:
                        new_price = st.number_input(
                            "주가",
                            min_value=0.0,
                            max_value=999.9,
                            step=0.1,
                            format="%.1f",
                            value=float(cur),
                            key=f"inv_price_{p['product_id']}",
                        )
                    with c3:
                        save_btn = st.button("저장", use_container_width=True, key=f"inv_save_{p['product_id']}")
    
                    if save_btn:
                        reason2 = str(reason or "").strip()
                        if not reason2:
                            st.warning("변동 사유를 입력해 주세요.")
                        else:
                            try:
                                payload = {
                                    "product_id": p["product_id"],
                                    "reason": reason2,
                                    "price_before": _as_price1(cur),
                                    "price_after": _as_price1(new_price),
                                    "created_at": firestore.SERVER_TIMESTAMP,
                                }
                                db.collection(INV_HIST_COL).document().set(payload)
                                db.collection(INV_PROD_COL).document(p["product_id"]).set(
                                    {"current_price": _as_price1(new_price), "updated_at": firestore.SERVER_TIMESTAMP},
                                    merge=True,
                                )
                                toast("주가가 반영되었습니다.", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"저장 실패: {e}")
    
                    # 변동 내역(표)
                    hist = _get_history(p["product_id"], limit=120)
                    if hist:
                        rows = []
                        for h in hist:
                            dt = _ts_to_dt(h.get("created_at"))
                            pb = float(h.get("price_before", 0.0) or 0.0)
                            pa = float(h.get("price_after", 0.0) or 0.0)
                            diff = round(pa - pb, 1)
    
                            # 변동일시: 0월 0일(요일) 오전/오후 00시 00분
                            def _fmt_kor_datetime(dt_obj):
                                if not dt_obj:
                                    return "-"
                                try:
                                    dt_kst = dt_obj.astimezone(KST)
                                except Exception:
                                    dt_kst = dt_obj
    
                                hour = dt_kst.hour
                                ampm = "오전" if hour < 12 else "오후"
                                hh = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
                                return f"{dt_kst.month}월 {dt_kst.day}일({days_ko[dt_kst.weekday()]}) {ampm} {hh:02d}시 {dt_kst.minute:02d}분"
    
                            # 주가 등락 표시 (요청: 하락은 파란 아이콘+파란 글씨)
                            if diff > 0:
                                diff_view = f"<span style='color:red'>▲ +{diff:.1f}</span>"
                            elif diff < 0:
                                diff_view = f"<span style='color:blue'>▼ {diff:.1f}</span>"
                            else:
                                diff_view = "-"
    
                            rows.append(
                                {
                                    "변동일시": _fmt_kor_datetime(dt),
                                    "변동사유": h.get("reason", "") or "",
                                    "주가": f"{pa:.1f}",          # ✅ '변동 후' → '주가'
                                    "주가 등락": diff_view,
                                }
                            )
    
                        df = pd.DataFrame(rows)
    
                        # ✅ 표(왼쪽) + 꺾은선 그래프(오른쪽)
                        left, right = st.columns([1.7, 2.2], gap="large")
    
                        with left:
                            st.markdown(
                                df.to_html(escape=False, index=False, classes="inv_hist_table"),
                                unsafe_allow_html=True,
                            )
    
                        with right:
                            # 가로: 변동사유 / 세로: 변동 후(주가)
                            chart_rows = []
    
                            # ✅ 초기주가 1점 추가
                            # - 변동 기록이 있으면: 가장 오래된 기록의 price_before가 '초기주가'
                            # - 변동 기록이 없으면: 현재주가를 초기로 표시
                            init_price = None
                            if hist:
                                oldest = hist[-1]  # hist는 최신순이라 마지막이 가장 오래됨
                                init_price = float(oldest.get("price_before", 0.0) or 0.0)
                            if init_price is None:
                                init_price = float(p.get("current_price", 0.0) or 0.0)
    
                            chart_rows.append({"변동사유": "시작주가", "변동 후": round(init_price, 1)})
    
                            # ✅ 이후 변동(오래된→최신)
                            for h2 in reversed(hist):
                                reason2 = str(h2.get("reason", "") or "").strip() or "-"
                                pa2 = float(h2.get("price_after", 0.0) or 0.0)
                                chart_rows.append({"변동사유": reason2, "변동 후": round(pa2, 1)})
    
                            cdf = pd.DataFrame(chart_rows)
    
                            if not cdf.empty:
                                order = cdf["변동사유"].tolist()
    
                                chart_df = cdf.copy().reset_index(drop=True)


    
                                # ✅ (PATCH) 구간별 상승/하락/보합 색상 + 점(회색) 표시

    
                                chart_df["prev_price"] = chart_df["변동 후"].shift(1)


    
                                def _dir(_row):

    
                                    p = _row.get("prev_price")

    
                                    v = _row.get("변동 후")

    
                                    if pd.isna(p) or pd.isna(v):

    
                                        return "same"

    
                                    if v > p:

    
                                        return "up"

    
                                    if v < p:

    
                                        return "down"

    
                                    return "same"


    
                                chart_df["direction"] = chart_df.apply(_dir, axis=1)

    
                                chart_df["x2"] = chart_df["변동사유"].shift(-1)

    
                                chart_df["y2"] = chart_df["변동 후"].shift(-1)

    
                                seg_df = chart_df.dropna(subset=["x2"]).copy()

                                # ✅ 구간(현재→다음) 기준으로 상승/하락/보합 판정
                                def _seg_dir(_r):
                                    y1 = _r.get("변동 후")
                                    y2 = _r.get("y2")
                                    if pd.isna(y1) or pd.isna(y2):
                                        return "same"
                                    if float(y2) > float(y1):
                                        return "up"
                                    if float(y2) < float(y1):
                                        return "down"
                                    return "same"
                                seg_df["direction_seg"] = seg_df.apply(_seg_dir, axis=1)


    
                                seg_chart = alt.Chart(seg_df).mark_rule(strokeWidth=3).encode(

    
                                    x=alt.X(

    
                                        "변동사유:N",

    
                                        sort=order,

    
                                        title=None,

    
                                        axis=alt.Axis(labelAngle=0),

    
                                    ),

    
                                    x2="x2:N",

    
                                    y=alt.Y(

    
                                        "변동 후:Q",

    
                                        title=None,

    
                                        scale=alt.Scale(domain=[50, 100]),

    
                                    ),

    
                                    y2="y2:Q",

    
                                    color=alt.Color(

    
                                        "direction_seg:N",

    
                                        scale=alt.Scale(domain=["up", "down", "same"], range=["red", "blue", "black"]),

    
                                        legend=None,

    
                                    ),

    
                                    tooltip=["변동사유", "변동 후"],

    
                                )


    
                                pt_chart = alt.Chart(chart_df).mark_point(size=55, color="gray").encode(

    
                                    x=alt.X(

    
                                        "변동사유:N",

    
                                        sort=order,

    
                                        title=None,

    
                                        axis=alt.Axis(labelAngle=0),

    
                                    ),

    
                                    y=alt.Y(

    
                                        "변동 후:Q",

    
                                        title=None,

    
                                        scale=alt.Scale(domain=[50, 100]),

    
                                    ),

    
                                    tooltip=["변동사유", "변동 후"],

    
                                )


    
                                chart = (seg_chart + pt_chart).properties(height=260)

    
                                st.altair_chart(chart, use_container_width=True)
                            else:
                                st.caption("그래프 데이터가 없습니다.")
    
                    else:
                        st.caption("아직 주가 변동 기록이 없습니다.")
    
            else:
                with st.expander(f"{nm} 주가 변동 내역", expanded=False):
                    # 변동 내역(표)
                    hist = _get_history(p["product_id"], limit=120)
                    if hist:
                        rows = []
                        for h in hist:
                            dt = _ts_to_dt(h.get("created_at"))
                            pb = float(h.get("price_before", 0.0) or 0.0)
                            pa = float(h.get("price_after", 0.0) or 0.0)
                            diff = round(pa - pb, 1)
    
                            # 변동일시: 0월 0일(요일) 오전/오후 00시 00분
                            def _fmt_kor_datetime(dt_obj):
                                if not dt_obj:
                                    return "-"
                                try:
                                    dt_kst = dt_obj.astimezone(KST)
                                except Exception:
                                    dt_kst = dt_obj
    
                                hour = dt_kst.hour
                                ampm = "오전" if hour < 12 else "오후"
                                hh = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
                                return f"{dt_kst.month}월 {dt_kst.day}일({days_ko[dt_kst.weekday()]}) {ampm} {hh:02d}시 {dt_kst.minute:02d}분"
    
                            # 주가 등락 표시 (요청: 하락은 파란 아이콘+파란 글씨)
                            if diff > 0:
                                diff_view = f"<span style='color:red'>▲ +{diff:.1f}</span>"
                            elif diff < 0:
                                diff_view = f"<span style='color:blue'>▼ {diff:.1f}</span>"
                            else:
                                diff_view = "-"
    
                            rows.append(
                                {
                                    "변동일시": _fmt_kor_datetime(dt),
                                    "변동사유": h.get("reason", "") or "",
                                    "주가": f"{pa:.1f}",          # ✅ '변동 후' → '주가'
                                    "주가 등락": diff_view,
                                }
                            )
    
                        df = pd.DataFrame(rows)
    
                        # ✅ 표(왼쪽) + 꺾은선 그래프(오른쪽)
                        left, right = st.columns([1.7,2.2], gap="large")
    
                        with left:
                            st.markdown(
                                df.to_html(escape=False, index=False, classes="inv_hist_table"),
                                unsafe_allow_html=True,
                            )
    
                        with right:
                            # 가로: 변동사유 / 세로: 변동 후(주가)
                            chart_rows = []
    
                            # ✅ 초기주가 1점 추가
                            # - 변동 기록이 있으면: 가장 오래된 기록의 price_before가 '초기주가'
                            # - 변동 기록이 없으면: 현재주가를 초기로 표시
                            init_price = None
                            if hist:
                                oldest = hist[-1]  # hist는 최신순이라 마지막이 가장 오래됨
                                init_price = float(oldest.get("price_before", 0.0) or 0.0)
                            if init_price is None:
                                init_price = float(p.get("current_price", 0.0) or 0.0)
    
                            chart_rows.append({"변동사유": "시작주가", "변동 후": round(init_price, 1)})
    
                            # ✅ 이후 변동(오래된→최신)
                            for h2 in reversed(hist):
                                reason2 = str(h2.get("reason", "") or "").strip() or "-"
                                pa2 = float(h2.get("price_after", 0.0) or 0.0)
                                chart_rows.append({"변동사유": reason2, "변동 후": round(pa2, 1)})
    
                            cdf = pd.DataFrame(chart_rows)
    
                            if not cdf.empty:
                                order = cdf["변동사유"].tolist()
    
                                chart_df = cdf.copy().reset_index(drop=True)


    
                                # ✅ (PATCH) 구간별 상승/하락/보합 색상 + 점(회색) 표시

    
                                chart_df["prev_price"] = chart_df["변동 후"].shift(1)


    
                                def _dir(_row):

    
                                    p = _row.get("prev_price")

    
                                    v = _row.get("변동 후")

    
                                    if pd.isna(p) or pd.isna(v):

    
                                        return "same"

    
                                    if v > p:

    
                                        return "up"

    
                                    if v < p:

    
                                        return "down"

    
                                    return "same"


    
                                chart_df["direction"] = chart_df.apply(_dir, axis=1)

    
                                chart_df["x2"] = chart_df["변동사유"].shift(-1)

    
                                chart_df["y2"] = chart_df["변동 후"].shift(-1)

    
                                seg_df = chart_df.dropna(subset=["x2"]).copy()

                                # ✅ 구간(현재→다음) 기준으로 상승/하락/보합 판정
                                def _seg_dir(_r):
                                    y1 = _r.get("변동 후")
                                    y2 = _r.get("y2")
                                    if pd.isna(y1) or pd.isna(y2):
                                        return "same"
                                    if float(y2) > float(y1):
                                        return "up"
                                    if float(y2) < float(y1):
                                        return "down"
                                    return "same"
                                seg_df["direction_seg"] = seg_df.apply(_seg_dir, axis=1)


    
                                seg_chart = alt.Chart(seg_df).mark_rule(strokeWidth=3).encode(

    
                                    x=alt.X(

    
                                        "변동사유:N",

    
                                        sort=order,

    
                                        title=None,

    
                                        axis=alt.Axis(labelAngle=0),

    
                                    ),

    
                                    x2="x2:N",

    
                                    y=alt.Y(

    
                                        "변동 후:Q",

    
                                        title=None,

    
                                        scale=alt.Scale(domain=[50, 100]),

    
                                    ),

    
                                    y2="y2:Q",

    
                                    color=alt.Color(

    
                                        "direction_seg:N",

    
                                        scale=alt.Scale(domain=["up", "down", "same"], range=["red", "blue", "black"]),

    
                                        legend=None,

    
                                    ),

    
                                    tooltip=["변동사유", "변동 후"],

    
                                )


    
                                pt_chart = alt.Chart(chart_df).mark_point(size=55, color="gray").encode(

    
                                    x=alt.X(

    
                                        "변동사유:N",

    
                                        sort=order,

    
                                        title=None,

    
                                        axis=alt.Axis(labelAngle=0),

    
                                    ),

    
                                    y=alt.Y(

    
                                        "변동 후:Q",

    
                                        title=None,

    
                                        scale=alt.Scale(domain=[50, 100]),

    
                                    ),

    
                                    tooltip=["변동사유", "변동 후"],

    
                                )


    
                                chart = (seg_chart + pt_chart).properties(height=260)

    
                                st.altair_chart(chart, use_container_width=True)
                            else:
                                st.caption("그래프 데이터가 없습니다.")
    
                    else:
                        st.caption("아직 주가 변동 기록이 없습니다.")
    
    
    # -------------------------------------------------
    # 2) 투자 상품 관리 장부
    # -------------------------------------------------
    st.markdown("### 🧾 투자 상품 관리 장부")
    
    ledger_rows = _load_ledger(None if is_admin else my_student_id)
    
    view_rows = []
    for x in ledger_rows:
        redeemed = bool(x.get("redeemed", False))
        view_rows.append(
            {
                "번호": int(x.get("no", 0) or 0),
                "이름": str(x.get("name", "") or ""),
                "종목": str(x.get("product_name", "") or ""),
                "매입일자": str(x.get("buy_date_label", "") or ""),
                "매입 주가": f"{_as_price1(x.get('buy_price', 0.0)):.1f}",
                "투자 금액": int(x.get("invest_amount", 0) or 0),
                "지급완료": "✅" if redeemed else "",
                "매수일자": str(x.get("sell_date_label", "") or ""),
                "매수 주가": f"{_as_price1(x.get('sell_price', 0.0)):.1f}" if redeemed else "",
                "주가차이": f"{_as_price1(x.get('diff', 0.0)):.1f}" if redeemed else "",
                "수익/손실금": int(round(float(x.get("profit", 0.0) or 0.0))) if redeemed else "",
                "찾을 금액": int(x.get("redeem_amount", 0) or 0) if redeemed else "",
                "_doc_id": x.get("_doc_id"),
                "_student_id": x.get("student_id"),
                "_product_id": x.get("product_id"),
                "_buy_price": x.get("buy_price"),
                "_invest_amount": x.get("invest_amount"),
            }
        )
    
    if view_rows:
        st.dataframe(pd.DataFrame(view_rows).drop(columns=["_doc_id","_student_id","_product_id","_buy_price","_invest_amount"], errors="ignore"),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("투자 내역이 없습니다.")
    
    # -------------------------------------------------
    # 2-1) 지급(회수) 처리
    # -------------------------------------------------
    pending = [x for x in view_rows if not any([x.get("지급완료") == "✅"])]
    if pending:

        st.markdown("#### 💸 투자 회수(지급)")

        # ✅ 사용자 모드에서는 "내 것만" 목록으로 보여주되, 지급 버튼은 표시하지 않음
        #   (지급은 관리자 또는 '투자증권' 직업 학생만 가능 — 문구는 그대로 유지)
        if (not is_admin) and (not inv_admin_ok):
            mine = [x for x in pending if str(x.get("_student_id", "") or "") == str(my_student_id or "")]
            st.info("투자 회수는 관리자 또는 관련 권한을 가진 학생만 할 수 있어요.")
            if not mine:
                st.caption("지급 대기 중인 투자 회수 내역이 없습니다.")
            else:
                for x in mine[:100]:
                    pid = str(x.get("_product_id", "") or "")
                    buy_price = _as_price1(x.get("_buy_price", 0.0))
                    invest_amt = int(x.get("_invest_amount", 0) or 0)
                    prod_name = str(x.get("종목", "") or "")

                    # 현재 주가 찾기
                    cur_price = buy_price
                    for p in products:
                        if str(p["product_id"]) == pid:
                            cur_price = _as_price1(p["current_price"])
                            break

                    diff, profit, redeem_amt = _calc_redeem_amount(invest_amt, buy_price, cur_price)

                    c1, c2, c3, c4 = st.columns([1.2, 2.2, 2.8, 1.2], gap="small")
                    with c1:
                        st.markdown(f"**{x.get('번호','')}**")
                    with c2:
                        st.markdown(f"{x.get('이름','')}")
                        st.caption(prod_name)
                    with c3:
                        st.caption(f"매입 {buy_price:.1f} → 현재 {cur_price:.1f} (차이 {diff:.1f})")
                        st.caption(f"수익/손실 {profit:.1f} | 찾을 금액 {redeem_amt}")
                    with c4:
                        st.markdown("<div style='text-align:center; opacity:0.65; padding-top:8px;'>지급대기</div>", unsafe_allow_html=True)

        # ✅ 관리자/투자증권(권한) 모드: 기존 지급 버튼 로직 유지
        else:
            can_redeem_now = _can_redeem(my_student_id)
            if (not is_admin) and (not can_redeem_now):
                st.info("투자 회수는 관리자 또는 '투자증권' 직업 학생만 할 수 있어요.")
            else:
                for x in pending[:100]:
                    doc_id = str(x.get("_doc_id", "") or "")
                    sid = str(x.get("_student_id", "") or "")
                    pid = str(x.get("_product_id", "") or "")
                    buy_price = _as_price1(x.get("_buy_price", 0.0))
                    invest_amt = int(x.get("_invest_amount", 0) or 0)
                    prod_name = str(x.get("종목", "") or "")

                    # 현재 주가 찾기
                    cur_price = buy_price
                    for p in products:
                        if str(p["product_id"]) == pid:
                            cur_price = _as_price1(p["current_price"])
                            break

                    diff, profit, redeem_amt = _calc_redeem_amount(invest_amt, buy_price, cur_price)

                    c1, c2, c3, c4 = st.columns([1.2, 2.2, 2.8, 1.2], gap="small")
                    with c1:
                        st.markdown(f"**{x.get('번호','')}**")
                    with c2:
                        st.markdown(f"{x.get('이름','')}")
                        st.caption(prod_name)
                    with c3:
                        st.caption(f"매입 {buy_price:.1f} → 현재 {cur_price:.1f} (차이 {diff:.1f})")
                        st.caption(f"수익/손실 {profit:.1f} | 찾을 금액 {redeem_amt}")
                    with c4:
                        if st.button("지급", use_container_width=True, key=f"inv_pay_{doc_id}"):

                            sell_dt = datetime.now(tz=KST)
                            sell_label = _fmt_kor_date_md(sell_dt)
                            memo = f"투자 회수({prod_name})"

                            if inv_admin_ok:
                                res = api_admin_add_tx_by_student_id(
                                    admin_pin=ADMIN_PIN,
                                    student_id=sid,
                                    memo=memo,
                                    deposit=int(redeem_amt),
                                    withdraw=0,
                                )
                            else:
                                res = api_broker_deposit_by_student_id(
                                    actor_student_id=my_student_id,
                                    student_id=sid,
                                    memo=memo,
                                    deposit=int(redeem_amt),
                                    withdraw=0,
                                )

                            if res.get("ok"):
                                # 지급완료 처리 + 지급일 기록
                                try:
                                    db.collection(INV_LEDGER_COL).document(doc_id).update(
                                        {
                                            "redeemed": True,
                                            "redeemed_at": firestore.SERVER_TIMESTAMP,
                                            "redeemed_label": sell_label,
                                            "redeemed_amount": int(redeem_amt),
                                        }
                                    )
                                except Exception:
                                    pass

                                toast("지급 완료!", icon="✅")
                                st.rerun()
                            else:
                                st.error(res.get("error", "지급 실패"))
    
    # -------------------------------------------------
    # 3) (사용자) 투자 실행
    # -------------------------------------------------
    if not is_admin:
        st.markdown("### 💳 투자하기")
    
        inv_ok2 = True
        try:
            snap = db.collection("students").document(str(my_student_id)).get()
            if snap.exists:
                inv_ok2 = bool((snap.to_dict() or {}).get("invest_enabled", True))
        except Exception:
            inv_ok2 = True
    
        if not inv_ok2:
            st.warning("이 계정은 현재 투자 기능이 비활성화되어 있어요.")
        elif not products:
            st.info("투자 종목이 아직 없어요. 관리자에게 종목 추가를 요청해 주세요.")
        else:
            prod_labels = [f"{p['name']} (현재 {p['current_price']:.1f})" for p in products]
            by_label = {lab: p for lab, p in zip(prod_labels, products)}
    
            sel_lab = st.selectbox("투자 종목 선택", prod_labels, key="inv_user_sel_prod")
            sel_prod = by_label.get(sel_lab)
    
            amt = st.number_input("투자 금액", min_value=0, step=10, value=0, key="inv_user_amt")
            if st.button("투자하기 (다음 확인창에서 ‘예’를 눌러야 완료, 신중하게 결정하기)", use_container_width=True, key="inv_user_btn"):
                if int(amt) <= 0:
                    st.warning("투자 금액을 입력해 주세요.")
                else:
                    st.session_state["inv_user_confirm"] = True
    
            if st.session_state.get("inv_user_confirm", False):
                st.warning("정말로 투자할까요?")
                y, n = st.columns(2)
                with y:
                    if st.button("예", use_container_width=True, key="inv_user_yes"):
                        st.session_state["inv_user_confirm"] = False
    
                        memo = f"투자 매입({sel_prod['name']})"
                        res = api_add_tx(login_name, login_pin, memo=memo, deposit=0, withdraw=int(amt))
                        if res.get("ok"):
                            try:
                                sd = fs_auth_student(login_name, login_pin)
                                sdata = sd.to_dict() or {}
                                no = int(sdata.get("no", 0) or 0)
    
                                buy_dt = datetime.now(tz=KST)
                                buy_label = _fmt_kor_date_md(buy_dt)
    
                                db.collection(INV_LEDGER_COL).document().set(
                                    {
                                        "student_id": sd.id,
                                        "no": no,
                                        "name": str(sdata.get("name", "") or ""),
                                        "product_id": sel_prod["product_id"],
                                        "product_name": sel_prod["name"],
                                        "buy_at": firestore.SERVER_TIMESTAMP,
                                        "buy_date_label": buy_label,
                                        "buy_price": _as_price1(sel_prod["current_price"]),
                                        "invest_amount": int(amt),
                                        "redeemed": False,
                                    }
                                )
                                toast("투자 완료! (장부에 반영됨)", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"장부 저장 실패: {e}")
                        else:
                            st.error(res.get("error", "투자 실패"))
                with n:
                    if st.button("아니오", use_container_width=True, key="inv_user_no"):
                        st.session_state["inv_user_confirm"] = False
                        st.rerun()
    
    # -------------------------------------------------
    # 4) (관리자) 투자 종목 추가/수정/삭제
    # -------------------------------------------------
    if inv_admin_ok:
        st.markdown("### 🧰 투자 종목 추가/수정/삭제")
    
        prod_all = _get_products(active_only=False)
    
        # ✅ 드롭다운에는 "활성 종목"만 보이게(삭제=비활성은 숨김)
        prod_active = [p for p in prod_all if bool(p.get("is_active", True))]
    
        labels = ["(신규 추가)"] + [p["name"] for p in prod_active if p["name"]]
    
        sel = st.selectbox("편집 대상", labels, key="inv_admin_edit_sel")
    
        cur_obj = None
        if sel != "(신규 추가)":
            for p in prod_active:
                if p["name"] == sel:
                    cur_obj = p
                    break
    
        name_default = "" if cur_obj is None else cur_obj["name"]
        price_default = 0.0 if cur_obj is None else float(cur_obj["current_price"])
    
        c1, c2 = st.columns([2.2, 1.2], gap="small")
        with c1:
            new_name = st.text_input("투자 종목명", value=name_default, key="inv_admin_name")
        with c2:
            new_price = st.number_input(
                "초기/현재 주가",
                min_value=0.0,
                max_value=999.9,
                step=0.1,
                format="%.1f",
                value=float(price_default),
                key="inv_admin_price",
            )
    
        b1, b2 = st.columns(2)
        with b1:
            if st.button("저장", use_container_width=True, key="inv_admin_save"):
                nm = str(new_name or "").strip()
                if not nm:
                    st.warning("종목명을 입력해 주세요.")
                else:
                    # ✅ 중복 종목명 방지(공백/대소문자 무시)
                    nm_key = nm.replace(" ", "").lower()
                    dup = None
                    for p in prod_all:
                        pnm = str(p.get("name", "") or "").strip()
                        if pnm and pnm.replace(" ", "").lower() == nm_key:
                            dup = p
                            break
    
                    # (신규 추가)인데 이미 존재하면:
                    # - 활성 종목이면: 중복 추가 막기
                    # - 비활성(삭제된) 종목이면: 새로 만들지 말고 "복구(재활성화)" 처리
                    if cur_obj is None and dup is not None:
                        if bool(dup.get("is_active", True)):
                            st.error("이미 같은 종목명이 있어요. (중복 추가 불가)")
                            st.stop()
                        else:
                            # ✅ 비활성 종목 복구
                            try:
                                db.collection(INV_PROD_COL).document(dup["product_id"]).set(
                                    {
                                        "name": nm,
                                        "current_price": _as_price1(new_price),
                                        "is_active": True,
                                        "updated_at": firestore.SERVER_TIMESTAMP,
                                    },
                                    merge=True,
                                )
                                toast("삭제된 종목을 복구했습니다.", icon="♻️")
                                st.rerun()
                            except Exception as e:
                                st.error(f"복구 실패: {e}")
                                st.stop()
    
                    # (수정)인데 다른 문서와 이름이 겹치면 막기
                    if cur_obj is not None and dup is not None and str(dup.get("product_id")) != str(cur_obj.get("product_id")):
                        st.error("이미 같은 종목명이 있어요. (중복 이름 불가)")
                        st.stop()
    
                    try:
                        if cur_obj is None:
                            db.collection(INV_PROD_COL).document().set(
                                {
                                    "name": nm,
                                    "current_price": _as_price1(new_price),
                                    "is_active": True,
                                    "created_at": firestore.SERVER_TIMESTAMP,
                                    "updated_at": firestore.SERVER_TIMESTAMP,
                                }
                            )
                            toast("종목이 추가되었습니다.", icon="✅")
                        else:
                            db.collection(INV_PROD_COL).document(cur_obj["product_id"]).set(
                                {
                                    "name": nm,
                                    "current_price": _as_price1(new_price),
                                    "is_active": True,
                                    "updated_at": firestore.SERVER_TIMESTAMP,
                                },
                                merge=True,
                            )
                            toast("종목이 수정되었습니다.", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
        with b2:
            if st.button("삭제", use_container_width=True, key="inv_admin_del", disabled=(cur_obj is None)):
                if cur_obj is None:
                    st.stop()
                try:
                    db.collection(INV_PROD_COL).document(cur_obj["product_id"]).set(
                        {"is_active": False, "updated_at": firestore.SERVER_TIMESTAMP},
                        merge=True,
                    )
                    toast("삭제(비활성화) 완료", icon="🗑️")
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제 실패: {e}")
    
    # =========================
    # 👥 계정 정보/활성화 (관리자 전용)
    # =========================

# =========================
# (학생) 📈 투자(관리자) — 별도 탭 (admin::📈 투자)
# =========================
if "admin::📈 투자" in tabs:
    with tab_map["admin::📈 투자"]:
        # ✅ 이 탭은 "관리자 기능 접근 권한"을 받은 학생에게만 노출됩니다.
        #    따라서 화면/기능을 관리자 탭과 완전히 동일하게 렌더링합니다.
        _render_invest_admin_like(
            inv_admin_ok_flag=True,
            force_is_admin=True,
            my_student_id=my_student_id,
            login_name=login_name,
            login_pin=login_pin,
        )
if "admin::🏦 은행(적금)" in tabs:
    with tab_map["admin::🏦 은행(적금)"]:
        bank_admin_ok = True
        if is_admin:
            st.info("관리자 모드에서는 상단 '🏦 은행(적금)' 탭에서 사용합니다.")
        else:
            bank_admin_ok = True
            
        render_deposit_approval_ui(ADMIN_PIN, prefix="bank_dep_req", allow=bank_admin_ok)

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
                "base": int(d.get("base", 50) if d.get("base", None) is not None else 50),
                "o": int(d.get("o", 1) if d.get("o", None) is not None else 1),
                "x": int(d.get("x", -3) if d.get("x", None) is not None else -3),
                "tri": int(d.get("tri", 0) if d.get("tri", None) is not None else 0),
            }

        def _calc_credit_score_for_student(student_id: str) -> tuple[int, int]:
            cfg = _get_credit_cfg()
            base = int(cfg.get("base", 50) if cfg.get("base", None) is not None else 50)
            o_pt = int(cfg.get("o", 1) if cfg.get("o", None) is not None else 1)
            x_pt = int(cfg.get("x", -3) if cfg.get("x", None) is not None else -3)
            tri_pt = int(cfg.get("tri", 0) if cfg.get("tri", None) is not None else 0)

            def _delta(v):
                vv = _norm_status(v)
                if vv == "O":
                    return o_pt
                if vv == "△":
                    return tri_pt
                return x_pt

            sub_res = api_list_stat_submissions_cached(limit_cols=200)
            sub_rows_all = sub_res.get("rows", []) if sub_res.get("ok") else []

            # ✅ 오래된→최신 누적 (api_list_stat_submissions_cached는 최신→과거로 오므로 reversed)
            sub_rows_all = list(sub_rows_all or [])

            score = int(base)
            sid = str(student_id)

            for sub in reversed(sub_rows_all):
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
        if bank_admin_ok:
            _ensure_maturity_processing_once()

        # -------------------------------------------------
        # (A) 관리자: 적금 관리 장부 (엑셀형 표 느낌) + 최신순
        # -------------------------------------------------
        if bank_admin_ok:
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

                st.markdown("#### 🛠️ 중도해지 처리(관리자)")
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

        
        # -------------------------------------------------



if "🔎 개별조회" in tabs:
    with tab_map["🔎 개별조회"]:

        if not (is_admin or has_tab_access(my_perms, "🔎 개별조회", is_admin)):
            st.error("접근 권한이 없습니다.")
            st.stop()

        name_search2 = st.text_input(
            "🔎 계정검색(이름 일부)",
            key="admin_ind_view_search"
        ).strip()

        # =================================================
        # (PATCH) 🔎 개별조회 지연 로딩 게이트
        #  - 로그인 시 자동 로딩 ❌
        #  - 버튼 클릭 시에만 무거운 데이터 로드 ⭕
        # =================================================
        if "admin_ind_view_loaded" not in st.session_state:
            st.session_state["admin_ind_view_loaded"] = False

        # ✅ (PATCH) 로그아웃 상태면 이전에 눌렀던 "불러오기" 상태를 무조건 초기화
        if not st.session_state.get("logged_in", False):
            st.session_state.pop("admin_ind_view_loaded", None)

        if not st.session_state["admin_ind_view_loaded"]:
            st.info("개별조회 데이터는 필요할 때만 불러옵니다.")
            if st.button(
                "🔄 개별조회 데이터 불러오기",
                key="admin_ind_view_load",
                use_container_width=True
            ):
                st.session_state["admin_ind_view_loaded"] = True
                st.rerun()
        else:
            # =========================
            # 🔽 개별조회 접기 버튼
            # =========================
            if st.button(
                "🔽 개별조회 접기",
                key="admin_ind_view_close",
                use_container_width=True
            ):
                st.session_state["admin_ind_view_loaded"] = False
                st.rerun()

            # =========================
            # ✅ students에서 번호(no) 포함해서 다시 로드(번호순 정렬)
            # =========================
            docs = (
                db.collection("students")
                .where(filter=FieldFilter("is_active", "==", True))
                .stream()
            )

            acc_rows = []
            for d in docs:
                x = d.to_dict() or {}
                nm = str(x.get("name", "") or "").strip()
                if not nm:
                    continue
                if name_search2 and (name_search2 not in nm):
                    continue
                try:
                    no = int(x.get("no", 999999) or 999999)
                except Exception:
                    no = 999999

                acc_rows.append(
                    {
                        "student_id": d.id,
                        "no": no,
                        "name": nm,
                        "balance": int(x.get("balance", 0) or 0),
                    }
                )

            acc_rows.sort(
                key=lambda r: (
                    int(r.get("no", 999999) or 999999),
                    str(r.get("name", "")),
                )
            )

            if not acc_rows:
                st.info("표시할 계정이 없습니다.")
            else:
                for r in acc_rows:
                    sid = str(r["student_id"])
                    nm = str(r["name"])
                    no = int(r.get("no", 0) or 0)
                    bal_now = int(r.get("balance", 0) or 0)

                    # -------------------------
                    # 적금
                    # -------------------------
                    sres = api_savings_list_by_student_id(sid)
                    savings = sres.get("savings", []) if sres.get("ok") else []

                    # ✅ 적금 탭과 동일한 기준: 만기/해지 제외 원금 합계
                    sv_total = sum(
                        int(s.get("principal", 0) or 0)
                        for s in savings
                        if str(s.get("status", "")).lower().strip()
                        not in ("matured", "canceled", "cancelled")
                    )

                    # -------------------------
                    # 투자 요약
                    # -------------------------
                    inv_text, inv_total = _get_invest_summary_by_student_id(sid)

                    # -------------------------
                    # 직업 / 신용
                    # -------------------------
                    role_name = _get_role_name_by_student_id(sid)
                    credit_score, credit_grade = _safe_credit(sid)

                    # -------------------------
                    # 총자산
                    # -------------------------
                    asset_total = int(bal_now) + int(sv_total) + int(inv_total)

                    collapsed = _fmt_admin_one_line(
                        no=no,
                        name=nm,
                        asset_total=asset_total,
                        bal_now=bal_now,
                        sv_total=sv_total,
                        inv_text=inv_text,
                        inv_total=inv_total,
                        role_name=role_name,
                        credit_score=credit_score,
                        credit_grade=credit_grade,
                    )

                    with st.expander(collapsed, expanded=False):
                        # -------------------------
                        # 통장내역(최신 120)
                        # -------------------------
                        st.markdown("### 📒 통장내역")
                        txr = api_get_txs_by_student_id(sid, limit=120)
                        if not txr.get("ok"):
                            st.error(txr.get("error", "내역을 불러오지 못했어요."))
                        else:
                            df_tx = pd.DataFrame(txr.get("rows", []))
                            if df_tx.empty:
                                st.info("거래 내역이 없어요.")
                            else:
                                df_tx = df_tx.sort_values(
                                    "created_at_utc",
                                    ascending=False
                                )
                                render_tx_table(df_tx)

if "📈 투자" in tabs:
    with tab_map["📈 투자"]:
        _render_invest_admin_like(
            inv_admin_ok_flag=bool(is_admin),
            force_is_admin=bool(is_admin),
            my_student_id=my_student_id,
            login_name=login_name,
            login_pin=login_pin,
        )
if "👥 계정 정보/활성화" in tabs:
    with tab_map["👥 계정 정보/활성화"]:

        if not is_admin:
            st.error("관리자 전용 탭입니다.")
            st.stop()

        # -------------------------------------------------
        # 🔐 학생별 관리자 탭/관리자기능 권한 부여/회수 (관리자만)
        #
        # 1) "tab::<탭이름>"  : 학생에게 '관리자 탭' 자체를 추가로 노출(기본 탭이 아닌 것들)
        # 2) "admin::<탭이름>": 이미 학생에게 기본으로 보이는 탭 안에서 '관리자 기능(관리 UI)'을 열어줌
        #    - 💰보상/벌금(관리자)  -> admin::🏦 내 통장
        #    - 🏦 은행(적금)(관리자)      -> admin::🏦 은행(적금)
        #    - 📈 투자(관리자)            -> admin::📈 투자
        # -------------------------------------------------
        st.markdown("### 🔐 학생별 관리자 탭 권한 부여/회수")
        st.caption("특정 학생에게 '관리자 탭' 또는 '관리자 기능(같은 탭 안)' 권한을 부여합니다. (👥 계정 정보/활성화 탭은 제외)")

        # ✅ 부여 가능한 항목(탭/관리자기능)
        # - (관리자기능) 항목은 학생에게 기본으로 보이는 탭 안에서 관리자 UI를 열어주는 용도입니다.
        GRANT_OPTIONS = [
            ("💰보상/벌금(관리자)", ("admin", "🏦 내 통장")),
            ("🏦 은행(적금)(관리자)", ("admin", "🏦 은행(적금)")),
            ("📈 투자(관리자)", ("admin", "📈 투자")),
        ] + [
            (t, ("tab", t))
            for t in ALL_TABS
            if t not in ("👥 계정 정보/활성화", "🏦 내 통장", "🏦 은행(적금)", "📈 투자")
        ]

        # ✅ 탭별로 함께 부여할 기능 권한(조작 가능하게)
        TAB_BUNDLE = {
            "🏛️ 국세청(국고)": ["treasury_read", "treasury_write"],
            "📊 통계청": ["stats_write"],
            "💳 신용등급": ["credit_write"],
            "💼 직업/월급": ["jobs_write"],
            "🏦 은행(적금)": ["bank_read", "bank_write"],
            "🗓️ 일정": ["schedule_read", "schedule_write"],
        }

        # ✅ 학생 목록(활성 학생)
        stu_list = []
        for x in _list_active_students_full_cached():
            try:
                no = int(x.get("no", 0) or 0)
            except Exception:
                no = 0
            name = str(x.get("name", "") or "")
            extra = x.get("extra_permissions", []) or []
            if not isinstance(extra, list):
                extra = []
            stu_list.append({
                "doc_id": str(x.get("student_id", "") or ""),
                "no": no,
                "name": name,
                "extra": [str(v) for v in extra if str(v).strip()]
            })

        stu_list = sorted(stu_list, key=lambda r: (r.get("no", 9999), r.get("name", "")))

        def _stu_label(r):
            n = int(r.get("no", 0) or 0)
            nm = str(r.get("name", "") or "")
            return f"{n:02d} {nm}".strip()

        by_label = {_stu_label(r): r for r in stu_list}
        opt_labels = [lab for (lab, _v) in GRANT_OPTIONS]
        opt_map = {lab: v for (lab, v) in GRANT_OPTIONS}

        cpa, cpb = st.columns([2, 3])
        with cpa:
            sel_opt_label = st.selectbox("부여할 항목 선택", opt_labels, key="perm_sel_opt_label_v2")
            sel_kind, sel_tab_internal = opt_map.get(sel_opt_label)
        with cpb:
            sel_students = st.multiselect(
                "대상 학생 선택(복수 선택 가능)",
                options=list(by_label.keys()),
                default=[],
                key="perm_sel_students_v2",
            )

        def _keys_for_selection(kind: str, tab_internal: str):
            # kind: "tab" or "admin"
            if kind == "admin":
                base = [f"admin::{tab_internal}"]
            else:
                base = [f"tab::{tab_internal}"]
            base += TAB_BUNDLE.get(tab_internal, [])
            # 중복 제거
            out, seen = [], set()
            for k in base:
                k = str(k)
                if k and (k not in seen):
                    seen.add(k)
                    out.append(k)
            return out

        def _update_student_extra(doc_id: str, add_keys=None, remove_keys=None, clear_all=False):
            add_keys = add_keys or []
            remove_keys = remove_keys or []
            ref = db.collection("students").document(str(doc_id))
            snap = ref.get()
            cur = []
            if snap.exists:
                cur0 = (snap.to_dict() or {}).get("extra_permissions", []) or []
                if isinstance(cur0, list):
                    cur = [str(v) for v in cur0 if str(v).strip()]
            cur_set = set(cur)
            if clear_all:
                cur_set = set()
            for k in add_keys:
                cur_set.add(str(k))
            for k in remove_keys:
                cur_set.discard(str(k))
            ref.update({"extra_permissions": sorted(list(cur_set))})

        g1, g2, g3, g4 = st.columns([1, 1, 1, 2])
        with g1:
            btn_grant = st.button("➕ 권한 부여", use_container_width=True, key="perm_btn_grant_v2")
        with g2:
            btn_revoke = st.button("➖ 권한 회수", use_container_width=True, key="perm_btn_revoke_v2")
        with g3:
            confirm_all = st.checkbox("전체 권한 선택", key="perm_confirm_revoke_all_v2")
        with g4:
            btn_revoke_all = st.button(
                "🔥 전체 권한 회수",
                use_container_width=True,
                disabled=(not confirm_all),
                key="perm_btn_revoke_all_v2",
            )

        if (btn_grant or btn_revoke) and (not sel_students):
            st.warning("먼저 학생을 선택해 주세요.")
        elif btn_grant:
            keys = _keys_for_selection(sel_kind, sel_tab_internal)
            n = 0
            for lab in sel_students:
                r = by_label.get(lab)
                if not r:
                    continue
                _update_student_extra(r["doc_id"], add_keys=keys)
                n += 1
            _list_active_students_full_cached.clear()
            st.success(f"권한 부여 완료: {n}명")
            st.rerun()
        elif btn_revoke:
            keys = _keys_for_selection(sel_kind, sel_tab_internal)
            n = 0
            for lab in sel_students:
                r = by_label.get(lab)
                if not r:
                    continue
                _update_student_extra(r["doc_id"], remove_keys=keys)
                n += 1
            _list_active_students_full_cached.clear()
            st.success(f"권한 회수 완료: {n}명")
            st.rerun()

        if btn_revoke_all and confirm_all:
            docs_perm3 = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
            n = 0
            for x in _list_active_students_full_cached():
                db.collection("students").document(str(x.get("student_id", "") or "")).update({"extra_permissions": []})
                n += 1
            _list_active_students_full_cached.clear()
            st.success(f"전체 학생 권한 전체 회수 완료: {n}명")
            st.rerun()

        # -------------------------------------------------
        # 📌 권한 부여 현황 표
        # -------------------------------------------------
        st.markdown("### 📌 권한 부여 현황")
        st.caption("학생이 기존에 사용하던 유형의 탭(괄호 안 관리자 표기)은 관리자 기능 탭으로 구분됩니다.")

        rows_status = []
        for x in _list_active_students_full_cached():
            extra = x.get("extra_permissions", []) or []
            if not isinstance(extra, list):
                extra = []
            tab_names = [str(k).replace("tab::", "", 1) for k in extra if isinstance(k, str) and k.startswith("tab::")]
            admin_tabs = [str(k).replace("admin::", "", 1) for k in extra if isinstance(k, str) and k.startswith("admin::")]

            # 표시용(관리자기능은 라벨을 보기 좋게 바꿈)
            admin_disp = []
            for t in admin_tabs:
                if t == "🏦 내 통장":
                    admin_disp.append("💰보상/벌금(관리자)")
                elif t == "🏦 은행(적금)":
                    admin_disp.append("🏦 은행(적금)(관리자)")
                elif t == "📈 투자":
                    admin_disp.append("📈 투자(관리자)")
                else:
                    admin_disp.append(f"{t}(관리자)")

            if (not tab_names) and (not admin_disp):
                continue

            try:
                no = int(x.get("no", 0) or 0)
            except Exception:
                no = 0
            nm = str(x.get("name", "") or "")
            rows_status.append({
                "번호": no,
                "이름": nm,
                "추가 탭(tab::)": ", ".join(tab_names) if tab_names else "",
                "관리자 기능(admin::)": ", ".join(admin_disp) if admin_disp else "",
            })

        df_status = pd.DataFrame(rows_status) if rows_status else pd.DataFrame(columns=["번호","이름","추가 탭(tab::)","관리자 기능(admin::)"])
        if not df_status.empty:
            df_status = df_status.sort_values(["번호","이름"]).reset_index(drop=True)

        st.dataframe(df_status, use_container_width=True, hide_index=True)

        # -------------------------------------------------
        # ✅ (탭 상단) 엑셀 일괄 계정 추가 + 샘플 다운로드

        # -------------------------------------------------
        # ✅ (탭 상단) 엑셀 일괄 계정 추가 + 샘플 다운로드
        #   - 사이드바가 아니라 이 탭 본문 최상단에 표시
        # -------------------------------------------------
        st.markdown("### 📥 일괄 엑셀 계정 추가")
        st.caption("엑셀을 올리면 아래 리스트(계정/비번 관리 표)에 바로 반영됩니다.")

        # ✅ 샘플 다운로드
        import io
        sample_df = pd.DataFrame(
            [
                {"번호": 1, "이름": "홍길동", "비밀번호": "12a#"},
                {"번호": 2, "이름": "김철수", "비밀번호": "ab@9"},
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
                    by_no = {}
                    by_name = {}
                    for x in _list_active_students_full_cached():
                        no0 = x.get("no")
                        nm0 = str(x.get("name", "") or "").strip()
                        if isinstance(no0, (int, float)) and str(no0) != "nan":
                            by_no[int(no0)] = str(x.get("student_id", "") or "")
                        if nm0:
                            by_name[nm0] = str(x.get("student_id", "") or "")

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
                    _list_active_students_full_cached.clear()
                    toast(f"엑셀 등록 완료 (신규 {created} / 수정 {updated} / 제외 {skipped})", icon="📥")
                    st.rerun()

                except Exception as e:
                    st.error(f"엑셀 처리 실패: {e}")


        # -------------------------------------------------
        # ✅ 학생 리스트 로드 (번호=엑셀 번호, 그 순서대로 정렬)
        #   - student_id 컬럼은 화면에서 제거(내부로만 유지)
        # -------------------------------------------------
        rows = []
        for x in _list_active_students_full_cached():
            # 엑셀 번호를 의미하는 "no"를 사용 (없으면 큰 값으로 뒤로)
            no = x.get("no", 999999)
            try:
                no = int(no)
            except Exception:
                no = 999999

            rows.append(
                {
                    "_sid": str(x.get("student_id", "") or ""),  # 내부용(삭제할 때만 사용) -> 화면에는 안 보이게 처리
                    "선택": False,
                    "번호": no,
                    "이름": x.get("name", ""),
                    "비밀번호": x.get("pin", ""),
                }
            )

        df_all = pd.DataFrame(rows, columns=["_sid", "선택", "번호", "이름", "비밀번호"])
        if not df_all.empty:
            df_all = df_all.sort_values(["번호", "이름"], ascending=[True, True], kind="mergesort").reset_index(drop=True)

        # ✅ account_df 세션 초기화 (없으면 생성)
        if "account_df" not in st.session_state:
            st.session_state.account_df = df_all.copy()
        
        # -------------------------------------------------
        # ✅ 상단 버튼(2줄): [전체선택/전체해제/계정삭제] + [입출금/투자 일괄]
        # -------------------------------------------------
        st.markdown("#### 👥 계정/비번 관리")

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
        # ✅ (PATCH) 예전 세션에 남아있을 수 있는 컬럼 제거(화면/편집에서 완전히 숨김)
        st.session_state.account_df = st.session_state.account_df.drop(
            columns=["입출금활성화", "투자활성화"], errors="ignore"
        )
        
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
            },
        )


        # ✅ editor 결과를 내부 df에 다시 합치기(_sid 유지)
        #    (행 순서 고정: 번호 기준으로 다시 정렬해서 '체크하면 아래로 내려감' 현상 최소화)
        if not df_all.empty and edited_view is not None:
            tmp = st.session_state.account_df.copy()
            for col in ["선택", "번호", "이름", "비밀번호"]:
                if col in edited_view.columns and col in tmp.columns:
                    tmp[col] = edited_view[col].values
            sort_cols = [c for c in ["번호", "이름"] if c in tmp.columns]
            if sort_cols:
                tmp = tmp.sort_values(
                    sort_cols,
                    ascending=[True] * len(sort_cols),
                    kind="mergesort",
                ).reset_index(drop=True)
            st.session_state.account_df = tmp

# =========================
# 3) 💼 직업/월급 (관리자 중심, 학생은 읽기만)
# =========================
if "💼 직업/월급" in tabs:
    with tab_map["💼 직업/월급"]:
        st.subheader("💼 직업/월급 시스템")

        if not (is_admin or has_tab_access(my_perms, "💼 직업/월급", is_admin)):
            st.info("접근 권한이 없습니다.")
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
                return {"pay_day": 17, "auto_enabled": False}
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

        def _paylog_id(month_key: str, student_id: str, job_id: str = "") -> str:
            # ✅ 월급 지급 로그는 '학생당 1개'가 아니라 '학생+직업당 1개'로 기록
            job_id = str(job_id or "").strip() or "_"
            return f"{month_key}_{student_id}_{job_id}"

        def _already_paid_this_month(month_key: str, student_id: str, job_id: str = "", job_name: str = "") -> bool:
            """이번 달 해당 학생/해당 직업에 대해 이미 월급이 지급되었는지 확인
            - 신규: payroll_log/{YYYY-MM}_{studentId}_{jobId}
            - 레거시(호환): payroll_log/{YYYY-MM}_{studentId} 가 있으면, 저장된 job 이름이 같을 때만 True
            """
            # 1) 신규 키
            snap = db.collection("payroll_log").document(_paylog_id(month_key, student_id, job_id)).get()
            if bool(snap.exists):
                return True

            # 2) 레거시 키(기존 데이터 호환)
            legacy_id = f"{month_key}_{student_id}"
            legacy = db.collection("payroll_log").document(legacy_id).get()
            if legacy.exists:
                ld = legacy.to_dict() or {}
                legacy_job = str(ld.get("job", "") or "")
                # 레거시는 "학생당 1개"로 덮어쓰던 구조였으므로,
                # 현재 지급하려는 직업과 이름이 같을 때만 '지급됨'으로 간주
                if legacy_job and (legacy_job == str(job_name or "")):
                    return True
            return False

        def _write_paylog(month_key: str, student_id: str, amount: int, job_name: str, method: str, job_id: str = ""):
            db.collection("payroll_log").document(_paylog_id(month_key, student_id, job_id)).set(
                {
                    "month": month_key,
                    "student_id": student_id,
                    "amount": int(amount),
                    "job": str(job_name or ""),
                    "job_id": str(job_id or ""),
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
                job_id = str(d.id)
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
                    if _already_paid_this_month(mkey, sid, job_id=job_id, job_name=job_name):
                        skip_cnt += 1
                        continue

                    nm = id_to_name.get(sid, "")
                    memo = f"월급 {job_name}"
                    res = _pay_one_student(sid, net_amt, memo)
                                        # ✅ (국고 세입) 월급 공제액을 국고로 입금
                    deduction = int(max(0, gross - net_amt))
                    if deduction > 0:
                        api_add_treasury_tx(
                            admin_pin=ADMIN_PIN,
                            memo=f"월급 공제 세입({mkey}) {job_name}" + (f" - {nm}" if nm else ""),
                            income=deduction,
                            expense=0,
                            actor="system_salary",
                        )
                    if res.get("ok"):
                        _write_paylog(mkey, sid, net_amt, job_name, method="auto", job_id=job_id)
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
                        targets.append((sid, net_amt, job_name, gross, str(d.id)))
            # ✅ 여러 직업 배정 허용: (학생+직업) 단위로 각각 지급

            already_any = any(_already_paid_this_month(cur_mkey, sid, job_id=jid, job_name=jb) for sid, _, jb, _, jid in targets)

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
                for sid, amt, jb, gross, job_id2 in targets:
                    nm = id_to_name2.get(sid, "")
                    memo = f"월급 {jb}"
                    res = _pay_one_student(sid, int(amt), memo)
                    # ✅ (국고 세입) 월급 공제액을 국고로 입금
                    deduction = int(max(0, int(gross) - int(amt))) if "gross" in locals() else 0
                    if deduction > 0:
                        api_add_treasury_tx(
                            admin_pin=ADMIN_PIN,
                            memo=f"월급 공제 세입({cur_mkey}) {jb}" + (f" - {nm}" if nm else ""),
                            income=deduction,
                            expense=0,
                            actor="system_salary",
                        )

                    if res.get("ok"):
                        # ✅ 수동지급도 이번달 지급 기록 남김(자동 패스 조건 충족)
                        _write_paylog(cur_mkey, sid, int(amt), jb, method="manual", job_id=job_id2)
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
        # ✅ (PATCH) 직업 지정/회수 UI (계정정보/활성화 탭의 권한 부여 방식과 동일 UX)
        #   - 기존 데이터 구조(job_salary.assigned_ids / student_count) 유지
        #   - 기존 월급 자동/수동지급/공제/국고 로직은 그대로 사용됨
        # -------------------------------------------------
        st.markdown("### 🎖️ 직업 지정 / 회수")
        st.caption("직업을 선택한 뒤, 학생을 선택하고 ‘고용/해제’ 버튼을 누르세요.")

        # 직업 선택
        job_pick_labels = [f"{r['order']} | {r['job']} (월급 {int(r['salary'])})" for r in rows]
        job_pick_map = {lab: r["_id"] for lab, r in zip(job_pick_labels, rows)}

        assign_c1, assign_c2 = st.columns([1.2, 2.0])
        with assign_c1:
            sel_job_label = st.selectbox("부여할 직업 선택", job_pick_labels, key="job_assign_pick2") if job_pick_labels else None
        with assign_c2:
            sel_students_labels = st.multiselect("대상 학생 선택(복수 선택 가능)", [lab for lab in acc_options if lab != "(선택 없음)"], key="job_assign_students2")

        btn1, btn2 = st.columns([1, 1])
        with btn1:
            if st.button("➕ 고용", use_container_width=True, key="job_assign_hire_btn2"):
                if not sel_job_label:
                    st.warning("먼저 직업을 선택하세요.")
                elif not sel_students_labels:
                    st.warning("대상 학생을 선택하세요.")
                else:
                    rid = job_pick_map.get(sel_job_label)
                    if rid:
                        ref = db.collection("job_salary").document(rid)
                        snap = ref.get()
                        if snap.exists:
                            x = snap.to_dict() or {}
                            cnt = max(0, int(x.get("student_count", 1) or 1))
                            assigned = list(x.get("assigned_ids", []) or [])

                            # 길이 정규화
                            if cnt == 0:
                                assigned = []
                            else:
                                if len(assigned) < cnt:
                                    assigned = assigned + [""] * (cnt - len(assigned))
                                if len(assigned) > cnt:
                                    assigned = assigned[:cnt]

                            changed = False
                            full = 0
                            for lab in sel_students_labels:
                                sid = label_to_id.get(lab, "")
                                if not sid:
                                    continue
                                # 이미 배정되어 있으면 스킵
                                if sid in assigned:
                                    continue
                                # 빈 자리 찾기
                                try:
                                    k = assigned.index("")
                                except ValueError:
                                    k = -1
                                if k == -1:
                                    full += 1
                                    continue
                                assigned[k] = sid
                                changed = True

                            if changed:
                                ref.update({"assigned_ids": assigned})
                                toast("고용 완료!", icon="✅")
                                if full > 0:
                                    st.warning(f"정원이 가득 차서 {full}명은 배정되지 않았어요. (학생수/정원 증가 후 다시 시도)")
                                st.rerun()
                            else:
                                st.info("변경된 내용이 없습니다. (이미 배정되었거나 정원이 가득 찼을 수 있어요.)")

        with btn2:
            if st.button("➖ 해제", use_container_width=True, key="job_assign_fire_btn2"):
                if not sel_job_label:
                    st.warning("먼저 직업을 선택하세요.")
                elif not sel_students_labels:
                    st.warning("대상 학생을 선택하세요.")
                else:
                    rid = job_pick_map.get(sel_job_label)
                    if rid:
                        ref = db.collection("job_salary").document(rid)
                        snap = ref.get()
                        if snap.exists:
                            x = snap.to_dict() or {}
                            cnt = max(0, int(x.get("student_count", 1) or 1))
                            assigned = list(x.get("assigned_ids", []) or [])

                            # 길이 정규화
                            if cnt == 0:
                                assigned = []
                            else:
                                if len(assigned) < cnt:
                                    assigned = assigned + [""] * (cnt - len(assigned))
                                if len(assigned) > cnt:
                                    assigned = assigned[:cnt]

                            sel_ids = [label_to_id.get(lab, "") for lab in sel_students_labels]
                            sel_ids = [sid for sid in sel_ids if sid]

                            new_assigned = [("" if sid in sel_ids else sid) for sid in assigned]
                            if new_assigned != assigned:
                                ref.update({"assigned_ids": new_assigned})
                                toast("해제 완료!", icon="✅")
                                st.rerun()
                            else:
                                st.info("해제할 배정이 없습니다.")


        # -------------------------------------------------
        # ✅ 전체 직업 해제 (모든 직업에서 배정 학생 전부 해제)
        # -------------------------------------------------
        all_off_cols = st.columns([1.0, 2.0])
        with all_off_cols[0]:
            all_clear_chk = st.checkbox("전체 직업 해제", value=False, key="job_assign_clear_all_chk")
        with all_off_cols[1]:
            if st.button("🔥 전체 직업 해제", use_container_width=True, key="job_assign_clear_all_btn", disabled=(not bool(all_clear_chk))):
                try:
                    _rows2 = _list_job_rows()
                    batch = db.batch()
                    for rr in _rows2:
                        rid2 = rr["_id"]
                        cnt2 = max(0, int(rr.get("student_count", 0) or 0))
                        # 빈 슬롯으로 초기화(정원 유지)
                        empty_ids = [""] * cnt2 if cnt2 > 0 else []
                        batch.update(db.collection("job_salary").document(rid2), {"assigned_ids": empty_ids})
                    batch.commit()
                    toast("전체 직업 해제 완료!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"전체 직업 해제 실패: {e}")


        # -------------------------------------------------
        # ✅ (PATCH) 직업 현황(학생 기준 표) — 학생이 직업 여러 개면 여러 행으로 표시
        # -------------------------------------------------
        st.markdown("### 📋 직업/월급 목록")
        status_rows = []
        # student_id -> (no, name) 빠른 조회
        id_to_no_name = {r["student_id"]: (r["no"], r["name"]) for r in acc_rows}

        for r in rows:
            rid = r["_id"]
            job = r["job"]
            salary = int(r["salary"])
            net = int(_calc_net(salary, cfg) or 0)
            cnt = max(0, int(r.get("student_count", 1) or 1))
            assigned_ids = list(r.get("assigned_ids", []) or [])

            # 길이 정규화
            if cnt == 0:
                assigned_ids = []
            else:
                if len(assigned_ids) < cnt:
                    assigned_ids = assigned_ids + [""] * (cnt - len(assigned_ids))
                if len(assigned_ids) > cnt:
                    assigned_ids = assigned_ids[:cnt]

            for sid in assigned_ids:
                if not sid:
                    continue
                no, nm = id_to_no_name.get(sid, (999999, id_to_label.get(sid, "")))
                status_rows.append(
                    {"번호": int(no) if str(no).isdigit() else no, "이름": nm, "직업": job, "월급": salary, "실수령액": net}
                )

        if status_rows:
            df_status = pd.DataFrame(status_rows)
            # 번호 정렬(문자 섞일 수 있어 안전 처리)
            try:
                df_status["번호_정렬"] = pd.to_numeric(df_status["번호"], errors="coerce").fillna(999999).astype(int)
                df_status = df_status.sort_values(["번호_정렬", "이름", "직업"], kind="mergesort").drop(columns=["번호_정렬"])
            except Exception:
                df_status = df_status.sort_values(["번호", "이름", "직업"], kind="mergesort")
            st.dataframe(df_status[["번호", "이름", "직업", "월급", "실수령액"]], use_container_width=True, hide_index=True)
        else:
            st.info("아직 직업이 배정된 학생이 없습니다.")


        # -------------------------------------------------
        # ✅ (PATCH) [숨김] 직업/월급 '목록 표' + 순서이동/삭제/정원 +/- UI
        #   - 기능은 유지(데이터는 그대로)하되 화면에서는 보이지 않게 처리
        #   - 직업 추가/수정, 직업 지정/회수, 월급 지급(자동/수동)은 그대로 사용
        # -------------------------------------------------
        if False:
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

                hdr = st.columns([1.1, 2.2, 1.1, 1.2, 1.4])
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

                    rowc = st.columns([0.8, 1.0, 2.6, 1.3, 1.3, 1.6])

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
                    st.markdown("<div style='margin:0.35rem 0; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)


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

        # ✅ 입력 초기화 버튼 삭제 (자리만 빈 칸으로 유지)
        with b2:
            st.write("")

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
        # -------------------------------------------------
        # ✅ 직업 엑셀 일괄 업로드 (미리보기 + 저장 버튼 반영)
        # -------------------------------------------------
        st.markdown("### 📥 직업 엑셀 일괄 업로드")
        st.caption("엑셀 업로드 후 미리보기 확인 → '저장(반영)'을 눌러야 실제 반영됩니다.")

        import io

        # ✅ 샘플 엑셀 다운로드  (※ 실수령은 자동 계산이므로 컬럼에서 제거)
        sample_df = pd.DataFrame(
            [
                {"순": 1, "직업": "은행원", "월급": 500, "학생 수": 1},
                {"순": 2, "직업": "통계청", "월급": 300, "학생 수": 2},
            ],
            columns=["순", "직업", "월급", "학생 수"],
        )
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            sample_df.to_excel(writer, index=False, sheet_name="jobs")
        bio.seek(0)

        st.download_button(
            "📄 직업 샘플 엑셀 다운로드",
            data=bio.getvalue(),
            file_name="jobs_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="job_sample_down",
        )

        # ✅ 기존 목록 삭제 여부(저장 시 적용)
        wipe_before = st.checkbox("⚠️ 저장 시 기존 직업 목록 전체 삭제(덮어쓰기)", value=False, key="job_wipe_before")

        up_job = st.file_uploader("📤 직업 엑셀 업로드(xlsx)", type=["xlsx"], key="job_bulk_upl")
        st.session_state.setdefault("job_bulk_df", None)
        st.session_state.setdefault("job_bulk_sig", None)

        # -------------------------
        # 1) 업로드 → 미리보기만 저장
        # -------------------------
        if up_job is not None:
            try:
                file_bytes = up_job.getvalue()
            except Exception:
                file_bytes = None

            sig = None
            if file_bytes is not None:
                sig = (getattr(up_job, "name", ""), len(file_bytes))

            # ✅ 같은 파일을 이미 파싱해서 미리보기로 들고 있으면 재파싱하지 않음
            if sig is not None and st.session_state.get("job_bulk_sig") == sig and st.session_state.get("job_bulk_df") is not None:
                st.info("업로드한 엑셀 미리보기가 준비되어 있습니다. 아래에서 저장(반영)하세요.")
            else:
                try:
                    df = pd.read_excel(up_job)
                    df = df.copy()
                    df.columns = [str(c).strip() for c in df.columns]

                    need_cols = {"순", "직업", "월급", "학생 수"}
                    if not need_cols.issubset(set(df.columns)):
                        st.error("엑셀 컬럼은 반드시: 순 | 직업 | 월급 | 학생 수 여야 합니다.")
                        st.session_state["job_bulk_df"] = None
                        st.session_state["job_bulk_sig"] = None
                    else:
                        # 정리/검증
                        df["순"] = pd.to_numeric(df["순"], errors="coerce").fillna(999999).astype(int)
                        df["직업"] = df["직업"].astype(str).str.strip()
                        df["월급"] = pd.to_numeric(df["월급"], errors="coerce").fillna(0).astype(int)
                        df["학생 수"] = pd.to_numeric(df["학생 수"], errors="coerce").fillna(0).astype(int)

                        bad_job = df[df["직업"].str.len() == 0]
                        bad_sal = df[df["월급"] <= 0]
                        bad_cnt = df[df["학생 수"] <= 0]

                        if (not bad_job.empty) or (not bad_sal.empty) or (not bad_cnt.empty):
                            if not bad_job.empty:
                                st.error("❌ 직업명이 비어있는 행이 있습니다.")
                            if not bad_sal.empty:
                                st.error("❌ 월급은 1 이상이어야 합니다.")
                            if not bad_cnt.empty:
                                st.error("❌ 학생 수는 1 이상이어야 합니다.")
                            st.session_state["job_bulk_df"] = None
                            st.session_state["job_bulk_sig"] = None
                        else:
                            # 보기 좋게 순 정렬
                            df = df.sort_values(["순", "직업"]).reset_index(drop=True)

                            st.session_state["job_bulk_df"] = df
                            st.session_state["job_bulk_sig"] = sig
                            st.success(f"미리보기 준비 완료! ({len(df)}행) 아래에서 저장(반영)을 누르세요.")

                except Exception as e:
                    st.error(f"직업 엑셀 읽기 실패: {e}")
                    st.session_state["job_bulk_df"] = None
                    st.session_state["job_bulk_sig"] = None

        # -------------------------
        # 2) 미리보기 표시
        # -------------------------
        df_preview = st.session_state.get("job_bulk_df")
        if df_preview is not None and not df_preview.empty:
            st.dataframe(df_preview, use_container_width=True, hide_index=True)

        # -------------------------
        # 3) 저장(반영) 버튼: 여기서만 DB 반영
        # -------------------------
        if st.button("✅ 저장(반영)", use_container_width=True, key="job_bulk_save_btn"):
            df2 = st.session_state.get("job_bulk_df")
            if df2 is None or df2.empty:
                st.error("먼저 올바른 엑셀을 업로드해서 미리보기를 만든 뒤 저장하세요.")
            else:
                try:
                    if wipe_before:
                        docs = db.collection("job_salary").stream()
                        for d in docs:
                            db.collection("job_salary").document(d.id).delete()

                    for _, r in df2.iterrows():
                        db.collection("job_salary").document().set(
                            {
                                "order": int(r["순"]),
                                "job": str(r["직업"]),
                                "salary": int(r["월급"]),
                                "student_cnt": int(r["학생 수"]),
                                "assigned_ids": [],
                                "created_at": firestore.SERVER_TIMESTAMP,
                            }
                        )

                    # ✅ 반영 후 세션/업로더 정리 (무한 rerun 방지 + 다음 업로드 준비)
                    st.session_state["job_bulk_df"] = None
                    st.session_state["job_bulk_sig"] = None
                    st.session_state.pop("job_bulk_upl", None)

                    toast("직업 엑셀 저장(반영) 완료!", icon="📥")
                    st.rerun()

                except Exception as e:
                    st.error(f"직업 엑셀 저장 실패: {e}")


# =========================
# 🏛️ 국세청(국고) 탭
# =========================
if "🏛️ 국세청(국고)" in tabs:
    with tab_map["🏛️ 국세청(국고)"]:

        # 관리자만 쓰기 가능 / 학생은 읽기만(원하면 later: treasury_read 권한으로 확장)
        writable = bool(is_admin or has_tab_access(my_perms, "🏛️ 국세청(국고)", is_admin))

        # 1) 상단 잔액 표시: [국고] : 00000드림
        st_res = api_get_treasury_state_cached()
        treasury_bal = int(st_res.get("balance", 0) or 0)
        st.markdown(f"## 🪙국고: **{treasury_bal:,}{TREASURY_UNIT}**")

        st.markdown("### 🧾세입/세출 내역")

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

        if not (is_admin or has_tab_access(my_perms, "📊 통계청", is_admin)):
            st.error("접근 권한이 없습니다.")
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


        # -------------------------
        # (중간) 통계청 통계표
        # - 최신 제출물이 "왼쪽" (created_at DESC)
        # - 클릭은 로컬 변경, [저장] 시 DB 반영
        # -------------------------
        st.markdown("### 📋 통계 관리 장부")

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

        # ✅ 한 줄: [◀] [페이지] [/전체페이지] [▶] | [저장/초기화/삭제]
        row = st.columns([4, 3], gap="small")

        with row[0]:
            nav = st.columns([1, 1, 1, 1], gap="small")

            with nav[0]:
                if st.button("◀", key="stat_nav_left", use_container_width=True, disabled=(cur_page <= 1)):
                    _goto_page(cur_page - 1)

            with nav[1]:
                page_val = st.number_input(
                    "",
                    min_value=1,
                    max_value=total_pages,
                    value=cur_page,
                    step=1,
                    key="stat_page_num",
                    label_visibility="collapsed",
                )
                if int(page_val) != int(cur_page):
                    _goto_page(int(page_val))

            with nav[2]:
                st.markdown(
                    f"<div style='text-align:center; font-weight:700; padding-top:6px;'>/ 전체페이지 {total_pages}</div>",
                    unsafe_allow_html=True,
                )

            with nav[3]:
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

/* ===== (PATCH) 통계표 헤더를 라디오와 같은 기준(왼쪽 정렬)으로 맞추기 ===== */
.stat_hdr_cell{
  display:flex !important;
  justify-content:flex-start !important;  /* ✅ 라디오 그룹이 시작하는 쪽(왼쪽)으로 */
  align-items:center !important;
  width:100% !important;
  padding:0 !important;
  margin:0 !important;
}
.stat_hdr_inner{
  display:inline-block !important;
  text-align:left !important;
  font-weight:700 !important;
  line-height:1.15 !important;
  /* ✅ 라디오 위젯이 가지고 있는 기본 왼쪽 여백과 유사하게 미세 보정 */
  padding-left:2px !important;
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
                        f"<div class='stat_hdr_cell'><div class='stat_hdr_inner'>{date_disp}<br>{label}</div></div>",
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

        if not (is_admin or has_tab_access(my_perms, "💳 신용등급", is_admin)):
            st.info("접근 권한이 없습니다.")
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
        # 2) 점수 계산 설정(기본값)
        # -------------------------
        def _get_credit_cfg():
            ref = db.collection("config").document("credit_scoring")
            snap = ref.get()
            if not snap.exists:
                return {"base": 50, "o": 1, "x": -3, "tri": 0}
            d = snap.to_dict() or {}
            return {
                "base": int(d.get("base", 50) if d.get("base", None) is not None else 50),
                "o": int(d.get("o", 1) if d.get("o", None) is not None else 1),
                "x": int(d.get("x", -3) if d.get("x", None) is not None else -3),
                "tri": int(d.get("tri", 0) if d.get("tri", None) is not None else 0),
            }

        def _save_credit_cfg(cfg: dict):
            db.collection("config").document("credit_scoring").set(
                {
                    "base": int(cfg.get("base", 50) if cfg.get("base", None) is not None else 50),
                    "o": int(cfg.get("o", 1) if cfg.get("o", None) is not None else 1),
                    "x": int(cfg.get("x", -3) if cfg.get("x", None) is not None else -3),
                    "tri": int(cfg.get("tri", 0) if cfg.get("tri", None) is not None else 0),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        credit_cfg = _get_credit_cfg()

        st.markdown("### 📏 신용등급 점수 설정")
        
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

        base = int(credit_cfg.get("base", 50) if credit_cfg.get("base", None) is not None else 50)
        o_pt = int(credit_cfg.get("o", 1) if credit_cfg.get("o", None) is not None else 1)
        x_pt = int(credit_cfg.get("x", -3) if credit_cfg.get("x", None) is not None else -3)
        tri_pt = int(credit_cfg.get("tri", 0) if credit_cfg.get("tri", None) is not None else 0)

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
        st.markdown("### 🌟 신용등급 관리 장부")
        
        nav = st.columns([1, 1, 1, 1], gap="small")

        with nav[0]:
            if st.button(
                "◀",
                key="credit_nav_left",
                use_container_width=True,
                disabled=(cur_page <= 1),
            ):
                _credit_goto_page(cur_page - 1)

        with nav[1]:
            page_val = st.number_input(
                "",
                min_value=1,
                max_value=total_pages,
                value=cur_page,
                step=1,
                key="credit_page_num",
                label_visibility="collapsed",
            )
            if int(page_val) != int(cur_page):
                _credit_goto_page(int(page_val))

        with nav[2]:
            st.markdown(
                f"<div style='text-align:center; font-weight:700; padding-top:6px;'>/ 전체페이지 {total_pages}</div>",
                unsafe_allow_html=True,
            )

        with nav[3]:
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
        hdr_cols = st.columns([0.37, 0.7] + [1.2] * len(sub_rows_view))
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

            row_cols = st.columns([0.37, 0.7] + [1.2] * len(sub_rows_view))
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


# =========================
# 🏦 은행(적금) 탭
# - (관리자) 적금 관리 장부(최신순) + 이자율표
# - (학생) 적금 가입/내 적금 목록/중도해지 + 신용등급 미리보기 + 이자율표
# =========================
if "🏦 은행(적금)" in tabs:
    with tab_map["🏦 은행(적금)"]:

        bank_admin_ok = bool(is_admin)  # ✅ 학생은 여기서 관리자 UI를 숨기고, 별도 관리자 탭(admin::🏦 은행(적금))에서만 표시

        render_deposit_approval_ui(ADMIN_PIN, prefix="bank_dep_req_main", allow=bank_admin_ok)

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
                "base": int(d.get("base", 50) if d.get("base", None) is not None else 50),
                "o": int(d.get("o", 1) if d.get("o", None) is not None else 1),
                "x": int(d.get("x", -3) if d.get("x", None) is not None else -3),
                "tri": int(d.get("tri", 0) if d.get("tri", None) is not None else 0),
            }

        def _calc_credit_score_for_student(student_id: str) -> tuple[int, int]:
            cfg = _get_credit_cfg()
            base = int(cfg.get("base", 50) if cfg.get("base", None) is not None else 50)
            o_pt = int(cfg.get("o", 1) if cfg.get("o", None) is not None else 1)
            x_pt = int(cfg.get("x", -3) if cfg.get("x", None) is not None else -3)
            tri_pt = int(cfg.get("tri", 0) if cfg.get("tri", None) is not None else 0)

            def _delta(v):
                vv = _norm_status(v)
                if vv == "O":
                    return o_pt
                if vv == "△":
                    return tri_pt
                return x_pt

            sub_res = api_list_stat_submissions_cached(limit_cols=200)
            sub_rows_all = sub_res.get("rows", []) if sub_res.get("ok") else []

            # ✅ 오래된→최신 누적 (api_list_stat_submissions_cached는 최신→과거로 오므로 reversed)
            sub_rows_all = list(sub_rows_all or [])

            score = int(base)
            sid = str(student_id)

            for sub in reversed(sub_rows_all):
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
        if bank_admin_ok:
            _ensure_maturity_processing_once()

        # -------------------------------------------------
        # (A) 관리자: 적금 관리 장부 (엑셀형 표 느낌) + 최신순
        # -------------------------------------------------
        if bank_admin_ok:
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

                st.markdown("#### 🛠️ 중도해지 처리(관리자)")
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

            # ✅ (FIX) 적금 총액(진행중) 계산: NameError 방지
            total_savings_principal = 0
            try:
                if my_student_id:
                    sres = api_savings_list_by_student_id(str(my_student_id))
                    if sres.get("ok"):
                        total_savings_principal = savings_active_total(sres.get("savings", []))
            except Exception:
                total_savings_principal = 0

            if my_student_id:
                sc, gr = _calc_credit_score_for_student(my_student_id)

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


            st.markdown("### 📒 내 적금 내역")
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
                    st.markdown("#### ⚠️ 중도 해지(원금만 지급)")
                    opts = ["(선택 없음)"] + [
                        f"{r['적금기간']} | {r['적금 날짜']} | {int(r['적금 금액'])}P"
                        for _, r in running_ids.head(30).iterrows()
                    ]
                    lab_to_id = {opts[i+1]: running_ids.iloc[i]["_id"] for i in range(len(running_ids.head(30)))}
                    pick2 = st.selectbox("중도 해지할 적금 선택", opts, key="stu_bank_cancel_pick")
                    if pick2 != "(선택 없음)":
                        if st.button("중도해지 실행", use_container_width=True, key="stu_bank_cancel_do"):
                            rid = str(lab_to_id.get(pick2))
                            res = _cancel_savings(rid)
                            if res.get("ok"):
                                toast("중도해지 완료", icon="✅")
                                st.rerun()
                            else:
                                st.error(res.get("error", "중도해지 실패"))


        # -------------------------------------------------
        # (C) 이자율 표(캡쳐 표 위치): 장부 아래 / 학생 화면 맨 아래
        #   ✅ 항상 보이게 하지 말고, 필요할 때만 펼치기
        # -------------------------------------------------

        st.markdown("#### 📶 신용등급·기간별 이자율표")        
        with st.expander("📌 신용등급 × 적금기간 이자율(%) 표 보기", expanded=False):

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

# =========================
# 🏷️ 경매 탭
# =========================
if "🏷️ 경매" in tabs:
    with tab_map["🏷️ 경매"]:

        open_res = api_get_open_auction_round()
        open_round = (open_res.get("round", {}) or {}) if open_res.get("ok") else {}

        if is_admin:
            st.markdown("### 📢 경매 개시")
            c1, c2 = st.columns(2)
            with c1:
                a_bid_name = st.text_input("입찰 내역", key="auc_admin_bid_name").strip()
            with c2:
                a_aff = st.text_input("소속", key="auc_admin_affiliation").strip()

            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button("개시", key="auc_admin_open_btn", use_container_width=True):
                    res = api_open_auction(ADMIN_PIN, a_bid_name, a_aff)
                    if res.get("ok"):
                        toast(f"경매 {int(res.get('round_no', 0) or 0):02d}회 개시", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "경매 개시 실패"))

            with btn_c2:
                if st.button("마감", key="auc_admin_close_btn", use_container_width=True):
                    res = api_close_auction(ADMIN_PIN)
                    if res.get("ok"):
                        toast("경매 마감 완료", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "경매 마감 실패"))

            if open_round:
                st.success(
                    f"진행 중: 입찰번호 {int(open_round.get('round_no', 0) or 0):02d} | "
                    f"입찰이름 {str(open_round.get('bid_name', '') or '')} | "
                    f"소속 {str(open_round.get('affiliation', '') or '')}"
                )
            else:
                st.info("개시된 경매가 없습니다.")

            st.markdown("### 📊 경매 결과")

            # ✅ 경매 결과는 '진행 중 경매가 없을 때(=마감 후)'에만 노출
            if open_round:
                st.info("경매 마감 버튼을 눌러야 경매 결과가 표시됩니다.")
            else:
                closed_res = api_get_latest_closed_auction_round()
                if not closed_res.get("ok"):
                    st.info("마감된 경매가 없습니다.")
                else:
                    cl_round = closed_res.get("round", {}) or {}
                    cl_round_id = str(cl_round.get("round_id", "") or "")

                    # 장부 반영이 완료된 경매는 결과 표를 숨기고 기본 안내 문구를 유지
                    if bool(cl_round.get("ledger_applied", False)):
                        st.info("경매 마감 버튼을 눌러야 경매 결과가 표시됩니다.")
                    else:
                        bid_res = api_list_auction_bids(cl_round_id)
                        bid_rows = list(bid_res.get("rows", []) or [])
                        view_rows = []
                        for r in bid_rows:
                            view_rows.append(
                                {
                                    "입찰 가격": int(r.get("amount", 0) or 0),
                                    "입찰일시": str(r.get("submitted_at_text", "") or ""),
                                    "번호": int(r.get("student_no", 0) or 0),
                                    "이름": str(r.get("student_name", "") or ""),
                                }
                            )

                        st.caption(
                            f"최근 마감 경매: {int(cl_round.get('round_no', 0) or 0):02d}회 | "
                            f"입찰이름: {str(cl_round.get('bid_name', '') or '')}"
                        )
                        
                        def _auc_toggle_no_refund():
                            if st.session_state.get("auc_refund_non_winners_no", False):
                                st.session_state["auc_refund_non_winners_yes"] = False

                        def _auc_toggle_yes_refund():
                            if st.session_state.get("auc_refund_non_winners_yes", False):
                                st.session_state["auc_refund_non_winners_no"] = False
                        already = bool(cl_round.get("ledger_applied", False))
                        apply_clicked = False
                             
                        if view_rows:
                            df_auc = pd.DataFrame(view_rows)
                            st.dataframe(df_auc, use_container_width=True, hide_index=True)

                            xbuf = BytesIO()
                            with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                                df_auc.to_excel(writer, index=False, sheet_name="경매결과")
                            xbuf.seek(0)

                            ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.2, 0.9, 1.2, 1.2])
                            with ctrl1:
                                st.download_button(
                                    "엑셀저장",
                                    data=xbuf.getvalue(),
                                    file_name=f"auction_result_{int(cl_round.get('round_no', 0) or 0):02d}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    key="auc_excel_download",
                                )
                            with ctrl2:
                                no_refund_checked = st.checkbox(
                                    "낙찰금 미반환",
                                    value=bool(st.session_state.get("auc_refund_non_winners_no", False)),
                                    key="auc_refund_non_winners_no",
                                    on_change=_auc_toggle_no_refund,
                                )
                            with ctrl3:
                                yes_refund_checked = st.checkbox(
                                    "낙찰금 반환(반환액 90%)",
                                    value=bool(st.session_state.get("auc_refund_non_winners_yes", False)),
                                    key="auc_refund_non_winners_yes",
                                    on_change=_auc_toggle_yes_refund,
                                )
                            with ctrl4:
                                apply_clicked = st.button("장부반영", key="auc_apply_ledger_btn", use_container_width=True, disabled=already)
                        else:
                            st.info("제출된 입찰표가 없습니다.")

                        if already:
                            st.caption("이미 장부 반영된 경매입니다.")
                            
                        if apply_clicked:
                            if (not no_refund_checked) and (not yes_refund_checked):
                                st.warning("낙찰금 반환 여부를 선택 후 장부 반영 버튼을 눌러 주세요")
                            else:
                                refund_non_winners = bool(yes_refund_checked)
                                res = api_apply_auction_ledger(ADMIN_PIN, cl_round_id, refund_non_winners=refund_non_winners)
                                if res.get("ok"):
                                    toast("경매 관리장부 + 국고 세입 반영 완료", icon="✅")
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "장부 반영 실패"))
                                    
            st.markdown("### 📚 경매 관리 장부")
            led = api_list_auction_admin_ledger(limit=100)
            led_rows = list(led.get("rows", []) or [])
            if led_rows:
                st.dataframe(pd.DataFrame(led_rows), use_container_width=True, hide_index=True)
            else:
                st.info("아직 반영된 경매 관리 장부가 없습니다.")

        else:
            st.markdown("### 📝 입찰표")
            if not open_round:
                st.info("개시된 경매가 없습니다.")
            else:
                sid = str(my_student_id or "")
                me_snap = db.collection("students").document(sid).get() if sid else None
                me = me_snap.to_dict() if (me_snap and me_snap.exists) else {}
                my_no_v = int((me or {}).get("no", 0) or 0)
                my_name_v = str((me or {}).get("name", login_name) or login_name)

                st.write(f"- 입찰기일: {_fmt_auction_dt(open_round.get('opened_at'))}")
                st.write(f"- 입찰번호: {int(open_round.get('round_no', 0) or 0):02d}")
                st.write(f"- 입찰이름: {str(open_round.get('bid_name', '') or '')}")
                st.write(f"- 입찰자 정보: 번호 {my_no_v} / 이름 {my_name_v} / 소속 {str(open_round.get('affiliation', '') or '')}")

            st.markdown("### ✋경매 참여하기")
            if not open_round:
                st.info("개시된 경매가 없습니다.")
            else:
                bid_doc_id = f"{str(open_round.get('round_id', '') or '')}_{sid}"
                prev_bid = db.collection("auction_bids").document(bid_doc_id).get() if sid else None
                if prev_bid and prev_bid.exists:
                    pb = prev_bid.to_dict() or {}
                    st.success(
                        f"입찰표 제출 완료: {int(pb.get('amount', 0) or 0):,} 드림 | "
                        f"제출시각 {_fmt_auction_dt(pb.get('submitted_at'))}"
                    )
                else:
                    amt = st.number_input("입찰 가격(드림)", min_value=0, step=1, key="auc_user_amount")
                    confirm = st.radio("입찰표를 제출하시겠습니까?", ["아니오", "예"], horizontal=True, key="auc_user_confirm")
                    if st.button("입찰표 제출", use_container_width=True, key="auc_user_submit_btn"):
                        if confirm != "예":
                            st.warning("제출 전 확인에서 '예'를 선택해 주세요.")
                        else:
                            res = api_submit_auction_bid(login_name, login_pin, int(amt))
                            if res.get("ok"):
                                toast("입찰표 제출 완료! 제출 즉시 통장에서 차감되었습니다.", icon="✅")
                                st.rerun()
                            else:
                                st.error(res.get("error", "입찰표 제출 실패"))

# =========================
# 🍀 복권 탭
# =========================
if "🍀 복권" in tabs:
    with tab_map["🍀 복권"]:

        open_lot_res = api_get_open_lottery_round()
        open_round = (open_lot_res.get("round", {}) or {}) if open_lot_res.get("ok") else {}

        if is_admin:
            st.markdown("### 🛠️ 복권 설정 및 개시")
            l1, l2, l3 = st.columns(3)
            with l1:
                lot_price = st.number_input("복권 가격 설정", min_value=2, step=1, value=20, key="lot_admin_price")
                lot_first = st.number_input("1등 당첨 백분율(%)", min_value=0, max_value=100, step=1, value=80, key="lot_admin_first_pct")
            with l2:
                lot_tax = st.number_input("세금(%)", min_value=1, max_value=100, step=1, value=40, key="lot_admin_tax")
                lot_second = st.number_input("2등 당첨 백분율(%)", min_value=0, max_value=100, step=1, value=20, key="lot_admin_second_pct")
            with l3:
                lot_third = st.number_input("3등 당첨금", min_value=0, step=1, value=20, key="lot_admin_third")

            if int(lot_first) + int(lot_second) != 100:
                st.warning("1등 + 2등 당첨 백분율의 합은 반드시 100이어야 합니다.")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("개시", key="lot_admin_open_btn", use_container_width=True):
                    res = api_open_lottery(
                        ADMIN_PIN,
                        {
                            "ticket_price": int(lot_price),
                            "tax_rate": int(lot_tax),
                            "first_pct": int(lot_first),
                            "second_pct": int(lot_second),
                            "third_prize": int(lot_third),
                        },
                    )
                    if res.get("ok"):
                        toast(f"복권 {int(res.get('round_no', 0) or 0)}회 개시", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "복권 개시 실패"))
            with b2:
                if st.button("마감", key="lot_admin_close_btn", use_container_width=True):
                    res = api_close_lottery(ADMIN_PIN)
                    if res.get("ok"):
                        toast("복권 마감 완료", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "복권 마감 실패"))

            if open_round:
                st.success(
                    f"진행 중 복권: {int(open_round.get('round_no', 0) or 0)}회 | 가격 {int(open_round.get('ticket_price', 0) or 0)}"
                )
            else:
                st.info("개시된 복권이 없습니다.")

            st.markdown("### 👑 관리자 복권 참여")
            if open_round:
                ap1, ap2, ap3 = st.columns([2, 1, 1])
                with ap1:
                    admin_lot_count = st.number_input("복권 참여 수", min_value=1, step=1, value=1, key="lot_admin_join_count")
                with ap2:
                    st.write("")
                    lot_apply_treasury = st.checkbox("국고반영", value=True, key="lot_admin_join_apply_treasury")
                with ap3:
                    st.write("")
                    if st.button("복권 참여", key="lot_admin_join_btn", use_container_width=True):
                        ares = api_submit_admin_lottery_entries(
                            ADMIN_PIN,
                            int(admin_lot_count),
                            apply_treasury=bool(lot_apply_treasury),
                        )
                        if ares.get("ok"):
                            toast(f"관리자 복권 {int(ares.get('count', 0) or 0)}게임 참여 완료", icon="✅")
                            st.rerun()
                        else:
                            st.error(ares.get("error", "관리자 복권 참여 실패"))

                current_round_entries = api_list_lottery_entries(str(open_round.get("round_id", "") or "")).get("rows", [])
                ticket_price = int(open_round.get("ticket_price", 0) or 0)
                admin_with_treasury_count = 0
                admin_without_treasury_count = 0
                student_count = 0
                for row in current_round_entries:
                    is_admin_entry = bool(row.get("is_admin", False))
                    if is_admin_entry:
                        if bool(row.get("treasury_applied", False)):
                            admin_with_treasury_count += 1
                        else:
                            admin_without_treasury_count += 1
                    else:
                        student_count += 1

                if admin_with_treasury_count > 0:
                    st.caption(
                        "관리자 참여 현황 : "
                        f"복권 참여수 {int(admin_with_treasury_count):02d}  |  "
                        f"총액 {int(admin_with_treasury_count * ticket_price)}  |  "
                        "국고반영여부 O"
                    )
                if admin_without_treasury_count > 0:
                    st.caption(
                        "관리자 참여 현황 : "
                        f"복권 참여수 {int(admin_without_treasury_count):02d}  |  "
                        f"총액 {int(admin_without_treasury_count * ticket_price)}  |  "
                        "국고반영여부 X"
                    )

                st.caption(
                    "학생 참여 현황 : "
                    f"복권 참여수 {int(student_count):02d}  |  "
                    f"총액 {int(student_count * ticket_price):03d}"
                )
            else:
                st.info("개시된 복권이 없습니다.")
            
            current_round_id = str(open_round.get("round_id", "") or "")
            current_round = dict(open_round)
            if not current_round_id:
                try:
                    cq = db.collection("lottery_rounds").order_by("round_no", direction=firestore.Query.DESCENDING).limit(1).stream()
                    for d in cq:
                        current_round = d.to_dict() or {}
                        current_round["round_id"] = d.id
                        current_round_id = d.id
                        break
                except Exception:
                    current_round_id = ""

            st.markdown("### 📝 복권 참여 결과")
            lot_result_gate_msg = "복권 마감 버튼을 눌러야 결과가 표시됩니다."
            if current_round_id:
                ent_res = api_list_lottery_entries(current_round_id)
                ent_rows = list(ent_res.get("rows", []) or [])
                is_lottery_closed = str(current_round.get("status", "")) in ("closed", "drawn")
                payout_done = bool(current_round.get("payout_done", False))

                # 복권 참여 결과는 "복권 마감" 이후에만 보이고,
                # 당첨금 지급/장부 반영 완료 후에는 다시 안내 문구로 전환.
                show_entry_result = bool(ent_rows) and is_lottery_closed and (not payout_done)

                if show_entry_result:
                    ticket_price = int(current_round.get("ticket_price", 0) or 0)
                    participant_keys = set()
                    for r in ent_rows:
                        sid = str(r.get("student_id", "") or "").strip()
                        if sid:
                            participant_keys.add(f"sid:{sid}")
                            continue
                        sno = int(r.get("student_no", 0) or 0)
                        sname = str(r.get("student_name", "") or "").strip()
                        if sno > 0:
                            participant_keys.add(f"sno:{sno}")
                        elif sname:
                            participant_keys.add(f"name:{sname}")

                    summary_rows = [{
                        "참여자수": int(len(participant_keys)),
                        "참여 복권수": int(len(ent_rows)),
                        "총 액수": int(len(ent_rows) * ticket_price),
                    }]
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

                    view_rows = [
                        {
                            "참여 일시": str(r.get("submitted_at_text", "") or ""),
                            "번호": int(r.get("student_no", 0) or 0),
                            "이름": str(r.get("student_name", "") or ""),
                            "복권 참여 번호": str(r.get("numbers_text", "") or ""),
                        }
                        for r in ent_rows
                    ]
                    st.dataframe(pd.DataFrame(view_rows), use_container_width=True, hide_index=True)
                else:
                    st.info(lot_result_gate_msg)
            else:
                st.info(lot_result_gate_msg)
                
            st.markdown("### 🎰 복권 추첨하기")
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                wn1 = st.number_input("첫 번째 당첨번호", min_value=1, max_value=20, step=1, value=1, key="lot_wn1")
            with d2:
                wn2 = st.number_input("두 번째 당첨번호", min_value=1, max_value=20, step=1, value=2, key="lot_wn2")
            with d3:
                wn3 = st.number_input("세 번째 당첨번호", min_value=1, max_value=20, step=1, value=3, key="lot_wn3")
            with d4:
                wn4 = st.number_input("네 번째 당첨번호", min_value=1, max_value=20, step=1, value=4, key="lot_wn4")

            draw_nums = [int(wn1), int(wn2), int(wn3), int(wn4)]
            if len(set(draw_nums)) != 4:
                st.warning("당첨번호 4개는 서로 중복될 수 없습니다.")

            if st.button("당첨번호 제출", key="lot_draw_btn", use_container_width=True):
                if not current_round_id:
                    st.error("대상 복권 회차가 없습니다.")
                elif len(set(draw_nums)) != 4:
                    st.error("당첨번호 4개는 중복 없이 입력해 주세요.")
                else:
                    res = api_draw_lottery(ADMIN_PIN, current_round_id, draw_nums)
                    if res.get("ok"):
                        st.session_state["lottery_winners_visible_round_id"] = str(current_round_id)
                        toast("복권 추첨 완료", icon="✅")
                        st.rerun()
                    else:
                        st.error(res.get("error", "복권 추첨 실패"))

            st.markdown("### 🎉 당첨자 확인")
            if current_round_id:
                current_round_id_str = str(current_round_id)
                submitted_round_id = str(st.session_state.get("lottery_winners_visible_round_id", "") or "")
                show_winner_result = submitted_round_id == current_round_id_str
                
                r_snap = db.collection("lottery_rounds").document(current_round_id).get()
                r_dat = r_snap.to_dict() if r_snap.exists else {}
                winners = list((r_dat or {}).get("winners", []) or [])
                win_nums = _normalize_lottery_numbers((r_dat or {}).get("winning_numbers", []))
                draw_submitted = str((r_dat or {}).get("status", "") or "") == "drawn"

                if show_winner_result and draw_submitted:
                    st.caption(f"회차 {int((r_dat or {}).get('round_no', 0) or 0)} | 당첨번호: {', '.join([f'{n:02d}' for n in win_nums])}")
                else:
                    st.info("당첨 번호 제출 버튼을 눌러야 당첨 결과가 표시됩니다.")
                    
                if show_winner_result and winners:
                    def _render_nums(nums, wset):
                        out = []
                        for n in nums:
                            if int(n) in wset:
                                out.append(f"<span style='color:#d90429;font-weight:700'>{int(n):02d}</span>")
                            else:
                                out.append(f"{int(n):02d}")
                        return ", ".join(out)

                    html = [
                        "<table style='width:100%;border-collapse:collapse'>",
                        "<thead><tr><th style='text-align:left;border-bottom:1px solid #ddd'>등수</th><th style='text-align:left;border-bottom:1px solid #ddd'>번호</th><th style='text-align:left;border-bottom:1px solid #ddd'>이름</th><th style='text-align:left;border-bottom:1px solid #ddd'>복권 참여 번호</th><th style='text-align:left;border-bottom:1px solid #ddd'>당첨금</th></tr></thead><tbody>",
                    ]
                    for w in winners:
                        html.append(
                            "<tr>"
                            f"<td>{int(w.get('rank', 0) or 0)}등</td>"
                            f"<td>{int(w.get('student_no', 0) or 0)}</td>"
                            f"<td>{str(w.get('student_name', '') or '')}</td>"
                            f"<td>{_render_nums(_normalize_lottery_numbers(w.get('numbers', [])), set(win_nums))}</td>"
                            f"<td>{int(w.get('prize', 0) or 0)}</td>"
                            "</tr>"
                        )
                    html.append("</tbody></table>")
                    st.markdown("".join(html), unsafe_allow_html=True)

                else:
                    if show_winner_result and draw_submitted:
                        st.info("당첨자가 없습니다.")

                if show_winner_result and draw_submitted:
                    payout_done = bool((r_dat or {}).get("payout_done", False))
                    led_done = bool((r_dat or {}).get("ledger_applied", False))
                    action_done = payout_done and led_done

                    if st.button(
                        "당첨금 지급 및 장부 반영",
                        key="lot_finalize_btn",
                        use_container_width=True,
                        disabled=action_done,
                    ):
                        finalize_ok = True
                        if not payout_done:
                            pay_res = api_pay_lottery_prizes(ADMIN_PIN, current_round_id)
                            if not pay_res.get("ok"):
                                st.error(pay_res.get("error", "당첨금 지급 실패"))
                                finalize_ok = False

                        if finalize_ok and (not led_done):
                            led_res = api_apply_lottery_ledger(ADMIN_PIN, current_round_id)
                            if not led_res.get("ok"):
                                st.error(led_res.get("error", "장부 반영 실패"))
                                finalize_ok = False

                        if finalize_ok:
                            st.session_state["lottery_winners_visible_round_id"] = ""
                            toast("당첨금 지급 및 장부 반영 완료", icon="✅")
                            st.rerun()

                    if payout_done:
                        st.caption("당첨금 지급: 완료")
                    if led_done:
                        st.caption("장부 반영: 완료")

            st.markdown("### 📒 복권 관리 장부")
            led_res = api_list_lottery_admin_ledger(limit=200)
            led_rows = list(led_res.get("rows", []) or [])
            if led_rows:
                st.dataframe(pd.DataFrame(led_rows), use_container_width=True, hide_index=True)
            else:
                st.info("아직 반영된 복권 관리 장부가 없습니다.")

        else:
            st.markdown("### 🎟️ 복권 구매하기")
            if not open_round:
                st.info("개시된 복권이 없습니다.")
            else:
                st.markdown(
                    f"🔔 {int(open_round.get('round_no', 0) or 0)}회차 | 복권 가격 {int(open_round.get('ticket_price', 0) or 0):02d}"
                )
                st.caption("※ 한 게임(한 줄)에는 4개의 숫자를 입력해야 합니다.")
                st.caption("※ 각 칸에는 1~20 사이의 숫자만 입력할 수 있으며, 한 줄 안에서는 숫자가 중복될 수 없습니다.")
                st.caption("※ 구매할 게임 수만큼 숫자를 입력한 후, 구매 버튼을 눌러주세요.")
                
                game_count = 5
                nums_per_game = 4
                games_raw = []

                def _clear_lottery_input_fields():
                    for gi in range(game_count):
                        for ni in range(nums_per_game):
                            key = f"lot_in_{gi}_{ni}"
                            st.session_state[key] = ""
                            st.session_state.pop(f"{key}__backup", None)

                # 구매 성공 후 다음 렌더에서 입력칸 자동 초기화
                if st.session_state.pop("lottery_clear_after_buy", False):
                    _clear_lottery_input_fields()
                    
                with st.form("lottery_user_form", clear_on_submit=False):
                    for gi in range(game_count):
                        row_cols = st.columns([0.8, 1, 1, 1, 1])
                        with row_cols[0]:
                            st.markdown(f"**{gi + 1}게임:**")
                        row_vals = []
                        for ni in range(nums_per_game):
                            k = f"lot_in_{gi}_{ni}"
                            raw = row_cols[ni + 1].text_input(
                                label=f"{gi + 1}게임 {ni + 1}칸",
                                key=k,
                                placeholder="(숫자 입력칸)",
                                label_visibility="collapsed",
                            )
                            row_vals.append(str(raw).strip())
                        games_raw.append(row_vals)

                    c1, c2 = st.columns(2)
                    with c1:
                        clear_clicked = st.form_submit_button("숫자 초기화", use_container_width=True)
                    with c2:
                        buy_clicked = st.form_submit_button("복권 구입", use_container_width=True)

                if clear_clicked:
                    st.session_state["lottery_clear_after_buy"] = True
                    st.rerun()

                if buy_clicked:
                    valid_games = []
                    has_error = False

                    for idx, game in enumerate(games_raw):
                        vals = [str(x).strip() for x in (game or [])]
                        filled = [v for v in vals if v != ""]
                        if not filled:
                            continue
                        if len(filled) != nums_per_game:
                            st.error(f"{idx + 1}게임: 숫자 4개를 모두 입력해 주세요.")
                            has_error = True
                            continue

                        parsed = []
                        for v in vals:
                            if not v.isdigit():
                                st.error(f"{idx + 1}게임: 숫자만 입력해 주세요.")
                                has_error = True
                                parsed = []
                                break
                            n = int(v)
                            if n < 1 or n > 20:
                                st.error(f"{idx + 1}게임: 숫자는 1~20 사이여야 합니다.")
                                has_error = True
                                parsed = []
                                break
                            parsed.append(n)

                        if not parsed:
                            continue
                        if len(set(parsed)) != nums_per_game:
                            st.error(f"{idx + 1}게임: 같은 숫자를 중복 입력할 수 없습니다.")
                            has_error = True
                            continue
                            
                        valid_games.append(parsed)

                    if not has_error:
                        if not valid_games:
                            st.error("입력된 게임이 없습니다. 최소 1게임 이상 입력해 주세요.")
                        else:
                            res = api_submit_lottery_entries(login_name, login_pin, valid_games)
                            if res.get("ok"):
                                toast(f"복권 {int(res.get('count', 0) or 0)}게임 구매 완료! 통장에서 금액이 차감되었습니다.", icon="✅")
                                st.session_state["lottery_clear_after_buy"] = True
                                st.rerun()
                            else:
                                st.error(res.get("error", "복권 구매 실패"))
                                    
            st.markdown("### 📜 복권 구매 내역")
            my_sid = str(my_student_id or "")
            hist_rows = []
            open_round_id = str(open_round.get("round_id", "") or "").strip()
            if (not open_round_id) or (not my_sid):
                st.info("개시된 복권이 없습니다.")
            else:
                hres = api_list_lottery_entries_by_student(my_sid, round_id=open_round_id)
                hist_rows = list(hres.get("rows", []) or []) if hres.get("ok") else []
                if hist_rows:
                    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("복권 구매 내역이 없습니다.")
                    
# =========================
# 📊 통계/신용 (학생 전용 · 읽기 전용)
# - 통계청 통계표(본인) + 신용등급 변동표(본인)
# - 저장/초기화/삭제/수정 기능 없음
# =========================
if "📊 통계/신용" in tabs and (not is_admin):
    with tab_map["📊 통계/신용"]:

        if not my_student_id:
            st.info("로그인 후 확인할 수 있어요.")
            st.stop()

        # 내 번호/이름
        my_no = ""
        my_nm = ""
        try:
            ss = db.collection("students").document(str(my_student_id)).get()
            if ss.exists:
                d0 = ss.to_dict() or {}
                my_no = str(d0.get("no", "") or "")
                my_nm = str(d0.get("name", "") or "").strip()
        except Exception:
            pass

        # -------------------------------------------------
        # 1) 통계표(내 기록)
        # -------------------------------------------------
        st.markdown("### 📋 통계표(내 기록)")

        sub_res_u = api_list_stat_submissions_cached(limit_cols=50)
        sub_rows_all_u = sub_res_u.get("rows", []) if sub_res_u.get("ok") else []
        if not sub_rows_all_u:
            st.info("아직 제출물 내역이 없어요.")
        else:
            import math

            VISIBLE_COLS = 7
            total_cols = len(sub_rows_all_u)
            total_pages = max(1, int(math.ceil(total_cols / VISIBLE_COLS)))

            if "user_stat_page_idx" not in st.session_state:
                st.session_state["user_stat_page_idx"] = 0  # 0=최신

            st.session_state["user_stat_page_idx"] = max(
                0, min(int(st.session_state["user_stat_page_idx"]), total_pages - 1)
            )
            page_idx = int(st.session_state["user_stat_page_idx"])
            cur_page = page_idx + 1

            def _goto_user_stat_page(p: int):
                p = max(1, min(int(p), total_pages))
                st.session_state["user_stat_page_idx"] = p - 1
                st.rerun()

            # 네비게이션(저장/초기화/삭제 없음) — ✅ 1줄 고정(사용자 모드 전용)
            nav = st.columns([1, 1, 1, 1], gap="small")
            with nav[0]:
                if st.button("◀", key="user_stat_prev", use_container_width=True, disabled=(cur_page <= 1)):
                    _goto_user_stat_page(cur_page - 1)
            with nav[1]:
                # ✅ 페이지 번호 입력(1줄)
                page_val = st.number_input(
                    "",
                    min_value=1,
                    max_value=total_pages,
                    value=cur_page,
                    step=1,
                    key="user_stat_page_num",
                    label_visibility="collapsed",
                )
                if int(page_val) != int(cur_page):
                    _goto_user_stat_page(int(page_val))
            with nav[2]:
                st.markdown(
                    f"""<div style="text-align:center; padding-top:0.45rem;">/ 전체페이지 {total_pages}</div>""",
                    unsafe_allow_html=True,
                )
            with nav[3]:
                if st.button("▶", key="user_stat_next", use_container_width=True, disabled=(cur_page >= total_pages)):
                    _goto_user_stat_page(cur_page + 1)

            # 최신이 왼쪽이 되도록(내부는 DESC 기준 유지)
            sub_rows_desc = list(sub_rows_all_u)  # created_at DESC
            start = page_idx * VISIBLE_COLS
            end = start + VISIBLE_COLS
            sub_rows_view = sub_rows_desc[start:end]

            # ---- 헤더 ----
            hdr_cols = st.columns([0.37, 0.7] + [1.2] * len(sub_rows_view))
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
                        f"<div class='stat_hdr_cell'><div class='stat_hdr_inner'>{date_disp}<br>{lab}</div></div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            # ---- 본문(내 것 1줄) ----
            row_cols = st.columns([0.37, 0.7] + [1.2] * len(sub_rows_view))
            with row_cols[0]:
                st.markdown(my_no if my_no else "-")
            with row_cols[1]:
                st.markdown(my_nm if my_nm else "-")

            for j, sub in enumerate(sub_rows_view):
                statuses = dict(sub.get("statuses", {}) or {})
                stv = _norm_status(statuses.get(str(my_student_id), "X"))
                opt = ["O", "X", "△"]
                idx0 = 0 if stv == "O" else (1 if stv == "X" else 2)
                with row_cols[j + 2]:
                    st.radio(
                        "상태",
                        opt,
                        index=idx0,
                        key=f"user_stat_cell_{str(my_student_id)}_{str(sub.get('submission_id') or '')}",
                        horizontal=True,
                        label_visibility="collapsed",
                        disabled=True,
                    )


        # -------------------------------------------------
        # 2) 신용등급 변동표(내 기록)
        # -------------------------------------------------
        st.divider()
        st.markdown("### 💳 신용등급 변동표(내 기록)")

        sub_res_c = api_list_stat_submissions_cached(limit_cols=50)
        sub_rows_all_c = sub_res_c.get("rows", []) if sub_res_c.get("ok") else []
        if not sub_rows_all_c:
            st.info("표시할 기록이 없어요.")
        else:
            import math

            cfg = _get_credit_cfg()
            base = int(cfg.get("base", 50) or 50)

            def _delta(v: str) -> int:
                v = _norm_status(v)
                if v == "O":
                    return int(cfg.get("o", 1) or 1)
                if v == "△":
                    return int(cfg.get("tri", 0) or 0)
                return int(cfg.get("x", -3) or -3)

            # 누적 점수(오래된→최신 순으로 계산)
            sub_rows_desc = list(sub_rows_all_c)
            sub_rows_asc = list(reversed(sub_rows_desc))

            cur = base
            score_at_sub = {}
            for s in sub_rows_asc:
                sid = str(s.get("submission_id") or "")
                statuses = dict(s.get("statuses", {}) or {})
                v = statuses.get(str(my_student_id), "X")
                cur = int(cur) + int(_delta(v))
                score_at_sub[sid] = int(cur)

            VISIBLE_COLS2 = 7
            total_cols2 = len(sub_rows_desc)
            total_pages2 = max(1, int(math.ceil(total_cols2 / VISIBLE_COLS2)))

            if "user_credit_page_idx" not in st.session_state:
                st.session_state["user_credit_page_idx"] = 0

            st.session_state["user_credit_page_idx"] = max(
                0, min(int(st.session_state["user_credit_page_idx"]), total_pages2 - 1)
            )
            page_idx2 = int(st.session_state["user_credit_page_idx"])
            cur_page2 = page_idx2 + 1

            def _goto_user_credit_page(p: int):
                p = max(1, min(int(p), total_pages2))
                st.session_state["user_credit_page_idx"] = p - 1
                st.rerun()

            # 네비게이션 — ✅ 1줄 고정(사용자 모드 전용)
            nav2 = st.columns([1, 1, 1, 1], gap="small")
            with nav2[0]:
                if st.button("◀", key="user_credit_prev", use_container_width=True, disabled=(cur_page2 <= 1)):
                    _goto_user_credit_page(cur_page2 - 1)
            with nav2[1]:
                page_val2 = st.number_input(
                    "",
                    min_value=1,
                    max_value=total_pages2,
                    value=cur_page2,
                    step=1,
                    key="user_credit_page_num",
                    label_visibility="collapsed",
                )
                if int(page_val2) != int(cur_page2):
                    _goto_user_credit_page(int(page_val2))
            with nav2[2]:
                st.markdown(
                    f"""<div style="text-align:center; padding-top:0.45rem;">/ 전체페이지 {total_pages2}</div>""",
                    unsafe_allow_html=True,
                )
            with nav2[3]:
                if st.button("▶", key="user_credit_next", use_container_width=True, disabled=(cur_page2 >= total_pages2)):
                    _goto_user_credit_page(cur_page2 + 1)

            start2 = page_idx2 * VISIBLE_COLS2
            end2 = start2 + VISIBLE_COLS2
            sub_rows_view2 = sub_rows_desc[start2:end2]

            hdr_cols2 = st.columns([0.55, 1.2] + [1.9] * len(sub_rows_view2))
            with hdr_cols2[0]:
                st.markdown("**번호**")
            with hdr_cols2[1]:
                st.markdown("**이름**")

            for j, s in enumerate(sub_rows_view2):
                with hdr_cols2[j + 2]:
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

            row_cols2 = st.columns([0.55, 1.2] + [1.9] * len(sub_rows_view2))
            with row_cols2[0]:
                st.markdown(my_no if my_no else "-")
            with row_cols2[1]:
                st.markdown(my_nm if my_nm else "-")

            for j, sub in enumerate(sub_rows_view2):
                sid = str(sub.get("submission_id") or "")
                sc = int(score_at_sub.get(sid, base))
                gr = _score_to_grade(sc)
                with row_cols2[j + 2]:
                    st.markdown(
                        f"<div style='text-align:center; font-weight:900;'>{sc}점/{gr}등급</div>",
                        unsafe_allow_html=True,
                    )


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
        # ✅ 타이틀(DDay) 자리
        title_ph = st.empty()

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
                    default_date = datetime.fromisoformat(cur_goal_date).date()
                except Exception:
                    pass
            g_date = st.date_input("목표 날짜", value=default_date, key=f"goal_date_{login_name}")
            # ✅ D-Day 표시 (목표 날짜 기준 남은 일수)
            try:
                _dday = int((g_date - date.today()).days)
            except Exception:
                _dday = 0
            if _dday >= 0:
                dday_text = f"(D-{_dday:02d}일)"
            else:
                dday_text = f"(D+{abs(_dday):02d}일)"
            title_ph.markdown(
                f"## 🎯 나의 목표 자산 <span style='font-size:0.75em;color:#777;'>{dday_text}</span>",
                unsafe_allow_html=True,
            )

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

                mdt = _to_utc_datetime(s.get("maturity_date") or s.get("maturity_utc"))
                if isinstance(mdt, datetime):
                    m_date = mdt.astimezone(KST).date()
                    if m_date <= g_date:
                        interest_before_goal += interest
        except Exception:
            # 로드 실패해도 목표 UI는 동작
            pass

        goal_amount = int(g_amt)
        # ✅ 투자 현재 평가금(거래 탭 기준) 포함
        inv_eval_total = 0
        try:
            _inv_text, _inv_total = _get_invest_summary_by_student_id(sid)
            inv_eval_total = int(_inv_total or 0)
        except Exception:
            inv_eval_total = 0

        expected_amount = bal_now + principal_all_running + interest_before_goal + inv_eval_total

        now_ratio = clamp01(bal_now / goal_amount if goal_amount > 0 else 0)
        exp_ratio = clamp01(expected_amount / goal_amount if goal_amount > 0 else 0)

        st.progress(exp_ratio)
        st.write(f"총 자산 기준 예상 달성률: **{exp_ratio*100:.1f}%** (예상 {expected_amount} / 목표 {goal_amount})")

        if principal_all_running > 0:
            msg = f"📌 진행 중 적금 원금 **+{principal_all_running}** 포함"

            if interest_before_goal > 0:
                msg += f", 목표일({g_date.isoformat()}) 이전 만기 적금 이자 **+{interest_before_goal}** 포함"
            else:
                msg += " (목표일 이전 만기 적금은 원금만 반영)"

            # ✅ 투자 현재평가 포함 추가
            if inv_eval_total > 0:
                msg += f", 투자 현재평가 +{inv_eval_total} 포함"

            st.info(msg)

        if principal_all_running == 0 and interest_before_goal == 0:
            st.caption("진행 중 적금이 없어 예상 금액은 통장 잔액과 같아요.")

