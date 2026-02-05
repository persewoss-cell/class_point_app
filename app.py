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
    div[role="radiogroup"] > label {
        background: #f3f4f6;
        padding: 6px 10px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid #ddd;
        font-size: 0.85rem;
    }
    div[role="radiogroup"] > label:has(input:checked) {
        background: #2563eb;
        color: #ffffff;
        border-color: #2563eb;
    }

    [data-testid="stDataFrame"] { overflow-x: auto; }

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
    @media (max-width: 768px) {
        .app-title { font-size: clamp(2.05rem, 7.9vw, 3.3rem); }
    }

    /* ✅ 전체적으로 줄간격 조금 촘촘하게 */
    p, .stMarkdown { margin-bottom: 0.35rem !important; }
    .stCaptionContainer { margin-top: 0.15rem !important; }

    /* ✅ 템플릿 정렬 표(엑셀 느낌) */
    .tpl-head { font-weight: 800; padding: 6px 6px; border-bottom: 2px solid #ddd; margin-bottom: 4px; }
    .tpl-cell { padding: 4px 6px; border-bottom: 1px solid #eee; line-height: 1.15; font-size: 0.95rem; }
    .tpl-label { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    @media (max-width: 768px){
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
    /* =========================
       💼 직업/월급 탭: 학생수(+/-), 순서(⬆️⬇️) 버튼 고정(원형 안 삐져나옴)
       ========================= */
    .jobcnt-wrap div[data-testid="stButton"] > button,
    .joborder-wrap div[data-testid="stButton"] > button{
        width: clamp(2.1rem, 3.6vw, 2.6rem) !important;
        height: clamp(2.1rem, 3.6vw, 2.6rem) !important;
        min-width: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        border-radius: 9999px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
        overflow: hidden !important;
    }
    .jobcnt-num{
        width: clamp(2.1rem, 3.6vw, 2.6rem);
        height: clamp(2.1rem, 3.6vw, 2.6rem);
        display:flex; align-items:center; justify-content:center;
        font-weight: 800;
    }
    .job-empty{
        padding: 0.35rem 0.5rem;
        color: #777;
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
    return sum(
        int(s.get("principal", 0) or 0)
        for s in savings_list
        if str(s.get("status", "")).lower() == "active"
    )

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
# Cached lists (너 코드 유지)
# =========================
@st.cache_data(ttl=30, show_spinner=False)
def api_list_accounts_cached():
    docs = db.collection("students").where(filter=FieldFilter("is_active", "==", True)).stream()
    items = []
    for d in docs:
        s = d.to_dict() or {}
        nm = s.get("name", "")
        if nm:
            items.append(
                {
                    "student_id": d.id,
                    "name": nm,
                    "balance": int(s.get("balance", 0) or 0),
                    "role_id": str(s.get("role_id", "") or ""),
                }
            )
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
    doc = fs_auth_student(name, pin)
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

def api_get_balance(name, pin):
    student_doc = fs_auth_student(name, pin)
    if not student_doc:
        return {"ok": False, "error": "이름 또는 비밀번호가 틀립니다."}
    data = student_doc.to_dict() or {}
    return {"ok": True, "balance": int(data.get("balance", 0) or 0), "student_id": student_doc.id}

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
    "delete_confirm": False,
    "undo_mode": False,
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
    "🏦 은행(예금)",
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
    if tab_name == "🏦 은행(예금)":
        return can(my_perms, "bank_read") or can(my_perms, "bank_write")

    if tab_name == "📈 투자":
        return True
    if tab_name == "🛒 구입/벌금":
        return True

    # 학생에게 숨김
    if tab_name in ("💼 직업/월급", "👥 계정 정보/활성화"):
        return False

    return False

tabs = [t for t in ALL_TABS if tab_visible(t)]
tab_objs = st.tabs(tabs)
tab_map = {name: tab_objs[i] for i, name in enumerate(tabs)}


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

    bal_res = api_get_balance(name, pin)
    if not bal_res.get("ok"):
        st.session_state.data[name] = {"error": bal_res.get("error", "잔액 로드 실패"), "ts": now}
        return

    balance = int(bal_res["balance"])
    student_id = bal_res.get("student_id")

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

            sub1, sub2 = st.tabs(["📝 거래", "📒 내역"])

            with sub1:
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

            with sub2:
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

        st.divider()

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
        # ✅ 표 헤더 + 행 렌더(보기 좋게: 중앙정렬/버튼 안삐져나가게)
        #   - 로직(저장/순서/학생수/드롭다운)은 그대로, UI만 정리
        # -------------------------------------------------
        st.markdown("### 📋 직업/월급 목록")
        st.caption("• 아래에 직업을 추가/수정하면 이 표에 들어갑니다. • 학생 수를 늘리면 ‘이름(계정)’ 드롭다운이 자동으로 늘어납니다.")

        st.markdown(
            """
            <style>
            /* 직업/월급 표용 미세 스타일 */
            .job-table .hdr{
                font-weight: 900;
                text-align: center;
                padding: 8px 6px;
                border-bottom: 2px solid #e5e7eb;
                background: #fafafa;
                border-radius: 10px;
                margin-bottom: 6px;
            }
            .job-table .cell{
                padding: 10px 6px;
                border-bottom: 1px solid #f1f5f9;
            }
            .job-table .center{ text-align:center; }
            .job-table .right{ text-align:right; }
            .job-table .jobname{ font-weight: 800; }
            .job-table .muted{ color:#6b7280; font-size: 0.92rem; }

            /* 행 간격 */
            .job-row{ padding: 6px 0; }

            /* 버튼이 튀어나오지 않게(특히 순서/+-) */
            .job-table div[data-testid="stButton"] > button{
                width: 100% !important;
                border-radius: 12px !important;
            }

            /* selectbox 높이/여백 정리 */
            .job-table div[data-testid="stSelectbox"] > div{
                min-height: 2.55rem;
            }

            /* 번호/금액/실수령을 중앙으로(표 느낌) */
            .job-table .stMarkdown p { margin-bottom: 0.2rem !important; }

            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div class='job-table'>", unsafe_allow_html=True)

        # 헤더(가운데 정렬)
        head = st.columns([0.7, 2.2, 1.2, 1.3, 1.2, 3.6, 1.2])
        head[0].markdown("<div class='hdr'>순</div>", unsafe_allow_html=True)
        head[1].markdown("<div class='hdr'>직업</div>", unsafe_allow_html=True)
        head[2].markdown("<div class='hdr'>월급</div>", unsafe_allow_html=True)
        head[3].markdown("<div class='hdr'>실수령액</div>", unsafe_allow_html=True)
        head[4].markdown("<div class='hdr'>학생 수</div>", unsafe_allow_html=True)
        head[5].markdown("<div class='hdr'>이름(계정)</div>", unsafe_allow_html=True)
        head[6].markdown("<div class='hdr'>순서</div>", unsafe_allow_html=True)

        # -------------------------------------------------
        # ✅ 행 렌더 + 학생수(+/-) + 계정 드롭다운(학생수만큼)
        #   - 기존 로직 유지(저장/순서 바꾸기 동일)
        # -------------------------------------------------
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

            st.markdown("<div class='job-row'>", unsafe_allow_html=True)
            c = st.columns([0.7, 2.2, 1.2, 1.3, 1.2, 3.6, 1.2])

            # 순 / 직업 / 월급 / 실수령액
            c[0].markdown(f"<div class='cell center'><b>{order}</b></div>", unsafe_allow_html=True)
            c[1].markdown(f"<div class='cell jobname'>{job}</div>", unsafe_allow_html=True)
            c[2].markdown(f"<div class='cell center'>{salary}</div>", unsafe_allow_html=True)
            c[3].markdown(f"<div class='cell center'><b>{net}</b></div>", unsafe_allow_html=True)

            # -------------------------
            # 학생 수 +/-
            # -------------------------
            with c[4]:
                st.markdown("<div class='jobcnt-wrap'>", unsafe_allow_html=True)

                a1, a2, a3 = st.columns([1, 1.2, 1])

                with a1:
                    if st.button("−", use_container_width=True, key=f"job_cnt_minus_{rid}"):
                        new_cnt = max(0, cnt - 1)
                        new_assigned = assigned_ids[:new_cnt] if new_cnt > 0 else []
                        db.collection("job_salary").document(rid).update(
                            {
                                "student_count": new_cnt,
                                "assigned_ids": new_assigned,
                            }
                        )
                        st.rerun()

                with a2:
                    st.markdown(f"<div class='jobcnt-num'>{cnt}</div>", unsafe_allow_html=True)

                with a3:
                    if st.button("+", use_container_width=True, key=f"job_cnt_plus_{rid}"):
                        new_cnt = cnt + 1
                        # cnt가 늘어나면 assigned_ids도 1칸 늘려줌
                        new_assigned = assigned_ids + [""]
                        db.collection("job_salary").document(rid).update(
                            {
                                "student_count": new_cnt,
                                "assigned_ids": new_assigned,
                            }
                        )
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

            # -------------------------
            # 이름(계정) 드롭다운 (학생수 0이면 숨김)
            # -------------------------
            with c[5]:
                if cnt <= 0:
                    st.markdown("<div class='job-empty'>-</div>", unsafe_allow_html=True)
                else:
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

            # -------------------------
            # 순서 위/아래
            # -------------------------
            with c[6]:
                st.markdown("<div class='joborder-wrap'>", unsafe_allow_html=True)

                up_disabled = (i == 0)
                dn_disabled = (i == len(rows) - 1)
                b1, b2 = st.columns(2)

                with b1:
                    if st.button("⬆️", use_container_width=True, disabled=up_disabled, key=f"job_up_{rid}"):
                        prev = rows[i - 1]
                        _swap_order(rid, order, prev["_id"], int(prev["order"]))
                        st.rerun()

                with b2:
                    if st.button("⬇️", use_container_width=True, disabled=dn_disabled, key=f"job_dn_{rid}"):
                        nxt = rows[i + 1]
                        _swap_order(rid, order, nxt["_id"], int(nxt["order"]))
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

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

if "🗓️ 일정" in tabs:
    with tab_map["🗓️ 일정"]:
        st.subheader("🗓️ 일정")
        st.caption("예: 은행 담당자는 bank 일정만 수정 가능 / 국세청 담당자는 treasury 일정만 수정 가능")

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
