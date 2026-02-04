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
# Sidebar: 계정 만들기/삭제 + (관리자) 학생 엑셀 일괄 업로드
# =========================
with st.sidebar:
    st.header("➕ 계정 만들기 / 삭제")

    new_name = st.text_input("이름(계정)", key="new_name").strip()
    new_pin = st.text_input("비밀번호(4자리 숫자)", type="password", key="new_pin").strip()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("계정 생성"):
            if not new_name:
                st.error("이름을 입력해 주세요.")
            elif not pin_ok(new_pin):
                st.error("비밀번호는 4자리 숫자여야 해요. (예: 0123)")
            else:
                res = api_create_account(new_name, new_pin)
                if res.get("ok"):
                    toast("계정 생성 완료!")
                    st.session_state.pop("new_name", None)
                    st.session_state.pop("new_pin", None)
                    api_list_accounts_cached.clear()
                    st.rerun()
                else:
                    st.error(res.get("error", "계정 생성 실패"))

    with c2:
        if st.button("삭제"):
            st.session_state.delete_confirm = True

    if st.session_state.delete_confirm:
        st.warning("정말로 삭제하시겠습니까?")
        y, n = st.columns(2)
        with y:
            if st.button("예", key="delete_yes"):
                if not new_name:
                    st.error("삭제할 이름(계정)을 입력해 주세요.")
                elif not pin_ok(new_pin):
                    st.error("비밀번호는 4자리 숫자여야 해요.")
                else:
                    res = api_delete_account(new_name, new_pin)
                    if res.get("ok"):
                        toast("삭제 완료!", icon="🗑️")
                        st.session_state.delete_confirm = False
                        st.session_state.data.pop(new_name, None)
                        api_list_accounts_cached.clear()
                        st.rerun()
                    else:
                        st.error(res.get("error", "삭제 실패"))
        with n:
            if st.button("아니오", key="delete_no"):
                st.session_state.delete_confirm = False
                st.rerun()

    st.divider()
    st.subheader("📥 (관리자) 학생 명단 엑셀 업로드")
    st.caption("엑셀에 name, pin 컬럼이 있으면 일괄 생성합니다.")
    up = st.file_uploader("학생 명단 엑셀(xlsx)", type=["xlsx"], key="upload_students_xlsx")
    if st.button("엑셀로 학생 일괄 생성(관리자)", use_container_width=True):
        if not st.session_state.get("admin_ok", False):
            st.error("관리자 로그인 후 사용하세요.")
        elif up is None:
            st.error("엑셀 파일을 올려주세요.")
        else:
            try:
                df = pd.read_excel(up)
                cols = [c.lower().strip() for c in df.columns.astype(str)]
                df.columns = cols
                if "name" not in df.columns or "pin" not in df.columns:
                    st.error("엑셀에 name, pin 컬럼이 필요합니다.")
                else:
                    created = 0
                    for _, r in df.iterrows():
                        nm = str(r.get("name", "") or "").strip()
                        pn = str(r.get("pin", "") or "").strip()
                        if nm and pn.isdigit() and len(pn) == 4:
                            if not fs_get_student_doc_by_name(nm):
                                api_create_account(nm, pn)
                                created += 1
                    toast(f"일괄 생성 완료! (+{created})", icon="📥")
                    api_list_accounts_cached.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"업로드 실패: {e}")

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
    "👥 학생/계정",
    "💼 직업/월급",
    "🏛️ 국세청(국고)",
    "📊 통계청",
    "💳 신용등급",
    "🏦 은행(예금)",
    "📈 투자",
    "🛒 구입/벌금",
    "🗓️ 일정",
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
        return True  # 투자 참여는 전원 가능(원하면 권한으로 제한 가능)
    if tab_name == "🛒 구입/벌금":
        return True
    if tab_name in ("👥 학생/계정", "💼 직업/월급"):
        return False
    return False

tabs = [t for t in ALL_TABS if tab_visible(t)]
tab_objs = st.tabs(tabs)

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

# 탭 렌더
idx = 0

with tab_objs[idx]:
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

# 다음 탭 인덱스
idx += 1

# =========================
# 2) 👥 학생/계정 (관리자 전용)
# =========================
if "👥 학생/계정" in tabs:
    with tab_objs[idx]:
        st.subheader("👥 학생/계정 관리(관리자)")
        accounts = api_list_accounts_cached().get("accounts", [])

        # 역할 목록
        roles_res = api_list_roles_cached()
        roles = roles_res.get("roles", []) if roles_res.get("ok") else []
        role_options = ["(없음)"] + [r["role_id"] for r in roles]  # role_id가 직업명(문서ID)
        role_label = {r["role_id"]: r["role_name"] for r in roles}

        st.caption("학생을 선택해 직업(역할)을 부여하세요. 직업별 권한이 탭 수정 권한이 됩니다.")
        for a in accounts:
            cols = st.columns([2.2, 1.2, 2.6])
            cols[0].write(f"👤 {a['name']} (잔액 {a['balance']})")
            cur = a.get("role_id", "") or ""
            pick = cols[1].selectbox(
                "직업",
                role_options,
                index=role_options.index(cur) if cur in role_options else 0,
                key=f"role_pick_{a['student_id']}",
                format_func=lambda x: "(없음)" if x == "(없음)" else f"{role_label.get(x,x)}",
                label_visibility="collapsed",
            )
            if cols[2].button("직업 저장", key=f"role_save_{a['student_id']}", use_container_width=True):
                rid = "" if pick == "(없음)" else pick
                res = api_admin_set_role(ADMIN_PIN, a["student_id"], rid)
                if res.get("ok"):
                    toast(f"{a['name']} 직업 저장 완료", icon="💼")
                    api_list_accounts_cached.clear()
                    st.rerun()
                else:
                    st.error(res.get("error", "저장 실패"))

        st.divider()
        st.subheader("📥 초기 데이터 업로드(관리자)")
        st.caption("1) 직업표/월급(xlsx) → roles 생성, 2) 은행 금리표(pdf 텍스트) → bank_rates 저장")

        up_jobs = st.file_uploader("직업표 및 월급 명세서(xlsx)", type=["xlsx"], key="up_jobs_pay")
        if st.button("직업/월급 업로드 → 직업(roles) 생성", use_container_width=True):
            if up_jobs is None:
                st.error("xlsx 파일을 올려주세요.")
            else:
                try:
                    jobs_df, pay_df = parse_jobs_xlsx(up_jobs)
                    res = upsert_roles_from_paytable(ADMIN_PIN, pay_df)
                    if res.get("ok"):
                        toast("직업(roles) 생성 완료!", icon="💼")
                        st.dataframe(pay_df, use_container_width=True, hide_index=True)
                        st.rerun()
                    else:
                        st.error(res.get("error", "실패"))
                except Exception as e:
                    st.error(f"처리 실패: {e}")

        up_rate_pdf = st.file_uploader("은행 금리표(pdf)", type=["pdf"], key="up_bank_rate_pdf")
        if st.button("금리표 업로드 → bank_products_rates 저장", use_container_width=True):
            if up_rate_pdf is None:
                st.error("pdf 파일을 올려주세요.")
            else:
                try:
                    # Streamlit 업로드 파일은 bytes -> 텍스트 간단 추출: PyMuPDF 없이 '문자열'만 필요하면 한계가 있어
                    # 여기서는 매우 단순하게: pdf가 텍스트 레이어를 가진 경우만 처리(너 pdf는 텍스트가 잡히는 편)
                    import fitz
                    doc = fitz.open(stream=up_rate_pdf.read(), filetype="pdf")
                    text = ""
                    for p in range(min(2, doc.page_count)):
                        text += doc.load_page(p).get_text("text") + "\n"
                    rows = parse_bank_rate_pdf_text(text)
                    res = upsert_bank_rates(ADMIN_PIN, rows)
                    if res.get("ok"):
                        toast("금리표 저장 완료!", icon="🏦")
                        st.write(rows)
                    else:
                        st.error(res.get("error", "실패"))
                except Exception as e:
                    st.error(f"처리 실패: {e}")
    idx += 1

# =========================
# 3) 💼 직업/월급 (관리자 중심, 학생은 읽기만)
# =========================
if "💼 직업/월급" in tabs:
    with tab_objs[idx]:
        st.subheader("💼 직업/월급 시스템")

        roles = api_list_roles_cached().get("roles", [])
        if not roles:
            st.warning("roles(직업)이 아직 없습니다. 먼저 ‘학생/계정’ 탭에서 직업/월급 xlsx를 업로드하세요.")
        else:
            df_roles = pd.DataFrame(roles)[["role_id","role_name","salary_gross","tax_rate","desk_rent","electric_fee","health_fee","permissions"]]
            st.dataframe(df_roles, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("💸 월급 지급(관리자)")
        st.caption("학생별 role_id(직업)에 있는 급여/세금/공과금을 적용해 자동 지급/징수합니다.")

        accounts = api_list_accounts_cached().get("accounts", [])
        name_map = {a["name"]: a for a in accounts}
        pick = st.selectbox("지급 대상", ["(전체)"] + list(name_map.keys()))
        pay_date = st.date_input("지급 날짜", value=date.today())

        if st.button("월급 실행(관리자)", use_container_width=True):
            if not is_admin:
                st.error("관리자만 가능합니다.")
            else:
                targets = accounts if pick == "(전체)" else [name_map[pick]]
                role_dict = {r["role_id"]: r for r in roles}

                done = 0
                for a in targets:
                    sid = a["student_id"]
                    rid = str(a.get("role_id","") or "")
                    if not rid or rid not in role_dict:
                        continue
                    r = role_dict[rid]
                    gross = int(r.get("salary_gross",0) or 0)
                    tax = int(round(gross * float(r.get("tax_rate",0.1) or 0.1)))
                    desk = int(r.get("desk_rent",50) or 50)
                    elec = int(r.get("electric_fee",10) or 10)
                    health = int(r.get("health_fee",10) or 10)
                    net = gross - tax - desk - elec - health

                    memo = f"월급({rid}) {pay_date.isoformat()}"

                    # 지급은 +net (단, 0 이하도 가능하게 하고 싶으면 관리자 tx로 처리)
                    if net != 0:
                        if net > 0:
                            api_admin_add_tx_by_student_id(ADMIN_PIN, sid, memo, net, 0)
                        else:
                            api_admin_add_tx_by_student_id(ADMIN_PIN, sid, memo, 0, abs(net))

                    # 국세청(국고)에도 세금 수입 반영
                    if tax > 0:
                        add_treasury_income(ADMIN_PIN, pay_date, f"{a['name']} 세금(월급)", tax)

                    done += 1

                api_list_accounts_cached.clear()
                toast(f"월급 처리 완료 ({done}명)", icon="💸")
                st.rerun()
    idx += 1

# =========================
# 국세청(국고): ledger helper
# =========================
def get_latest_treasury_balance() -> int:
    q = db.collection("treasury_ledger").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).stream()
    docs = list(q)
    if not docs:
        return 0
    return int((docs[0].to_dict() or {}).get("balance_after", 0) or 0)

def add_treasury_income(admin_pin: str, d: date, memo: str, income: int):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    income = int(income or 0)
    if income <= 0:
        return {"ok": False, "error": "수입은 1 이상"}
    bal = get_latest_treasury_balance()
    new_bal = bal + income
    db.collection("treasury_ledger").document().set(
        {
            "date": str(d.isoformat()),
            "memo": str(memo or ""),
            "income": income,
            "expense": 0,
            "balance_after": new_bal,
            "created_by": "admin",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return {"ok": True, "balance": new_bal}

def add_treasury_expense(admin_pin: str, d: date, memo: str, expense: int):
    if not is_admin_pin(admin_pin):
        return {"ok": False, "error": "관리자 PIN이 틀립니다."}
    expense = int(expense or 0)
    if expense <= 0:
        return {"ok": False, "error": "지출은 1 이상"}
    bal = get_latest_treasury_balance()
    new_bal = bal - expense
    db.collection("treasury_ledger").document().set(
        {
            "date": str(d.isoformat()),
            "memo": str(memo or ""),
            "income": 0,
            "expense": expense,
            "balance_after": new_bal,
            "created_by": "admin",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return {"ok": True, "balance": new_bal}

def list_treasury(limit=200):
    q = db.collection("treasury_ledger").order_by("created_at", direction=firestore.Query.DESCENDING).limit(int(limit)).stream()
    rows = []
    for d in q:
        x = d.to_dict() or {}
        rows.append(
            {
                "date": x.get("date",""),
                "memo": x.get("memo",""),
                "income": int(x.get("income",0) or 0),
                "expense": int(x.get("expense",0) or 0),
                "balance_after": int(x.get("balance_after",0) or 0),
            }
        )
    return rows

# =========================
# 4) 🏛️ 국세청(국고)
# =========================
if "🏛️ 국세청(국고)" in tabs:
    with tab_objs[idx]:
        st.subheader("🏛️ 국세청(국고 장부)")
        bal = get_latest_treasury_balance()
        st.metric("현재 국고 잔액", f"{bal}")

        writable = can(my_perms, "treasury_write") or is_admin

        c1, c2 = st.columns(2)
        with c1:
            d = st.date_input("날짜", value=date.today(), key="treasury_date")
            memo = st.text_input("내용", key="treasury_memo")
        with c2:
            t = st.radio("구분", ["수입", "지출"], horizontal=True, key="treasury_type")
            amt = st.number_input("금액", min_value=1, step=1, key="treasury_amt")

        if st.button("국고 기록 저장", use_container_width=True, disabled=(not writable)):
            if not memo.strip():
                st.error("내용을 입력하세요.")
            else:
                if t == "수입":
                    res = add_treasury_income(ADMIN_PIN if is_admin else ADMIN_PIN, d, memo, int(amt))
                else:
                    res = add_treasury_expense(ADMIN_PIN if is_admin else ADMIN_PIN, d, memo, int(amt))
                if res.get("ok"):
                    toast("국고 기록 저장 완료", icon="🏛️")
                    st.rerun()
                else:
                    st.error(res.get("error","실패"))

        st.divider()
        df = pd.DataFrame(list_treasury(200))
        st.dataframe(df, use_container_width=True, hide_index=True)
    idx += 1

# =========================
# 5) 📊 통계청
# =========================
def upsert_stats_sheet(d: date, title: str, marks: dict, created_by: str):
    db.collection("stats_submissions").document(f"{d.isoformat()}__{title}").set(
        {
            "date": d.isoformat(),
            "title": title,
            "marks": marks,
            "created_by": created_by,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return {"ok": True}

def list_stats(limit=50):
    q = db.collection("stats_submissions").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(int(limit)).stream()
    rows = []
    for d in q:
        x = d.to_dict() or {}
        rows.append(x)
    return rows

if "📊 통계청" in tabs:
    with tab_objs[idx]:
        st.subheader("📊 통계청(제출 통계)")
        writable = can(my_perms, "stats_write") or is_admin
        accounts = api_list_accounts_cached().get("accounts", [])

        d = st.date_input("제출 날짜", value=date.today(), key="stats_date")
        title = st.text_input("제출물 이름(가정통신문/배움공책 등)", key="stats_title").strip()

        st.caption("O / X / (빈칸=사유결석 등)")
        marks = {}
        for a in accounts:
            cols = st.columns([2, 2])
            cols[0].write(a["name"])
            pick = cols[1].selectbox(
                "제출",
                ["", "O", "X"],
                key=f"stats_{d.isoformat()}_{title}_{a['student_id']}",
                label_visibility="collapsed",
            )
            marks[a["student_id"]] = pick

        if st.button("통계 저장", use_container_width=True, disabled=(not writable)):
            if not title:
                st.error("제출물 이름을 입력하세요.")
            else:
                upsert_stats_sheet(d, title, marks, created_by=("admin" if is_admin else login_name))
                toast("통계 저장 완료", icon="📊")
                st.rerun()

        st.divider()
        st.subheader("최근 통계")
        rows = list_stats(20)
        if rows:
            st.write(pd.DataFrame([{"date":r["date"],"title":r["title"],"updated_at":str(r.get("updated_at",""))} for r in rows]))
        else:
            st.info("저장된 통계가 없습니다.")
    idx += 1

# =========================
# 6) 💳 신용등급 (통계청 marks 기반 +1/-3)
# =========================
def calc_credit_from_marks(marks_list: list[dict], student_ids: list[str]):
    score = {sid: 0 for sid in student_ids}
    for sheet in marks_list:
        marks = sheet.get("marks", {}) or {}
        for sid in student_ids:
            v = str(marks.get(sid, "") or "")
            if v == "O":
                score[sid] += 1
            elif v == "X":
                score[sid] -= 3
    # clamp 0~100
    for sid in score:
        score[sid] = max(0, min(100, int(score[sid])))
    return score

def grade_from_score(s: int) -> int:
    # pdf 하단 기준(대략): 90이상=1등급 ... 0~19=10등급
    s = int(s or 0)
    if s >= 90: return 1
    if s >= 80: return 2
    if s >= 70: return 3
    if s >= 60: return 4
    if s >= 50: return 5
    if s >= 40: return 6
    if s >= 30: return 7
    if s >= 20: return 8
    if s >= 10: return 9
    return 10

def save_credit_week(week_date: date, scores: dict, grades: dict, created_by: str):
    db.collection("credit_weekly").document(str(week_date.isoformat())).set(
        {
            "week_date": week_date.isoformat(),
            "scores": scores,
            "grades": grades,
            "created_by": created_by,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return {"ok": True}

def get_latest_credit_grades():
    q = db.collection("credit_weekly").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(1).stream()
    docs = list(q)
    if not docs:
        return {}
    return (docs[0].to_dict() or {}).get("grades", {}) or {}

if "💳 신용등급" in tabs:
    with tab_objs[idx]:
        st.subheader("💳 신용등급")
        writable = can(my_perms, "credit_write") or is_admin
        accounts = api_list_accounts_cached().get("accounts", [])
        student_ids = [a["student_id"] for a in accounts]

        week_date = st.date_input("기록 날짜(월요일 권장)", value=date.today(), key="credit_week_date")

        st.caption("최근 통계청 기록을 가져와 점수(+1/-3)를 자동 계산합니다.")
        recent_stats = list_stats(10)
        scores = calc_credit_from_marks(recent_stats, student_ids)
        grades = {sid: grade_from_score(scores[sid]) for sid in student_ids}

        df = pd.DataFrame(
            [
                {"이름": a["name"], "점수": scores[a["student_id"]], "등급": grades[a["student_id"]]}
                for a in accounts
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("이번 주 신용등급 저장", use_container_width=True, disabled=(not writable)):
            save_credit_week(week_date, scores, grades, created_by=("admin" if is_admin else login_name))
            toast("신용등급 저장 완료", icon="💳")
            st.rerun()
    idx += 1

# =========================
# 7) 🏦 은행(예금) - 금리표 + 예금장부(별도)
# =========================
def create_bank_deposit(student_id: str, principal: int, weeks: int, credit_grade: int):
    principal = int(principal or 0)
    weeks = int(weeks or 0)
    if principal <= 0 or principal % 100 != 0:
        return {"ok": False, "error": "예금은 100 단위만 가능합니다."}
    if weeks not in (2,4,6,8,10):
        return {"ok": False, "error": "기간은 2/4/6/8/10주만 가능합니다."}

    rate = get_bank_rate(weeks, credit_grade)  # %
    if rate <= 0:
        return {"ok": False, "error": "금리표가 없습니다. 관리자 탭에서 금리표를 업로드하세요."}

    # (중요) 예금은 "내 통장"에서 돈이 빠져나가야 함 => 기존 입출금 시스템 사용(그대로)
    # 학생 출금은 잔액 부족이면 막히므로, 예금 가입은 학생이 스스로 할 때만 가능
    # 여기서는 관리자/은행원이 대신 처리하려면 api_admin_add_tx_by_student_id를 쓰면 됨
    # → 정책은 원하면 바꿀 수 있지만, 여기선 “학생 본인 가입”을 기본으로 둠.
    return {"ok": True, "rate": rate}

def upsert_bank_deposit_record(student_id: str, weeks: int, principal: int, rate: int, start: date):
    start_dt = datetime.now(timezone.utc)
    due_dt = (datetime.now(timezone.utc) + timedelta(days=weeks*7))
    interest = int(round(principal * (rate/100)))
    payout = principal + interest

    ref = db.collection("bank_deposits").document()
    ref.set(
        {
            "student_id": student_id,
            "weeks": weeks,
            "principal": principal,
            "rate": rate,
            "start_at": start_dt,
            "due_at": due_dt,
            "interest": interest,
            "payout": payout,
            "status": "active",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return {"ok": True, "deposit_id": ref.id, "payout": payout, "interest": interest, "due_at": due_dt}

def list_bank_deposits(student_id: str, limit=50):
    q = (
        db.collection("bank_deposits")
        .where(filter=FieldFilter("student_id", "==", student_id))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(int(limit))
        .stream()
    )
    out = []
    for d in q:
        x = d.to_dict() or {}
        out.append(
            {
                "id": d.id,
                "weeks": int(x.get("weeks",0) or 0),
                "principal": int(x.get("principal",0) or 0),
                "rate": int(x.get("rate",0) or 0),
                "interest": int(x.get("interest",0) or 0),
                "payout": int(x.get("payout",0) or 0),
                "status": x.get("status",""),
                "due_at": _to_utc_datetime(x.get("due_at")),
            }
        )
    return out

def bank_close_as_mature(student_id: str, dep_id: str, name: str, pin: str):
    # 만기: payout 입금 + 장부 status 변경
    snap = db.collection("bank_deposits").document(dep_id).get()
    if not snap.exists:
        return {"ok": False, "error": "예금 기록이 없습니다."}
    d = snap.to_dict() or {}
    if d.get("student_id") != student_id:
        return {"ok": False, "error": "권한이 없습니다."}
    if d.get("status") != "active":
        return {"ok": False, "error": "이미 처리된 예금입니다."}

    payout = int(d.get("payout",0) or 0)

    # 기존 입금/출금 시스템 그대로 사용: payout 입금
    res = api_add_tx(name, pin, f"은행 예금 만기({d.get('weeks')}주)", payout, 0)
    if not res.get("ok"):
        return res

    db.collection("bank_deposits").document(dep_id).update({"status":"matured", "closed_at": firestore.SERVER_TIMESTAMP})
    return {"ok": True}

if "🏦 은행(예금)" in tabs:
    with tab_objs[idx]:
        st.subheader("🏦 은행(예금)")
        st.caption("예금은 100 단위, 기간은 2/4/6/8/10주(금리표 필요). 신용등급에 따라 금리 적용.")

        accounts = api_list_accounts_cached().get("accounts", [])
        latest_grades = get_latest_credit_grades()

        # 은행원/관리자는 다른 학생 처리 가능, 그 외는 본인만
        if is_admin or can(my_perms, "bank_write"):
            pick_name = st.selectbox("대상 학생", [a["name"] for a in accounts], key="bank_pick_student")
        else:
            pick_name = login_name

        target_doc = fs_get_student_doc_by_name(pick_name)
        if not target_doc:
            st.error("대상 학생을 찾지 못했습니다.")
        else:
            sid = target_doc.id
            target_pin_needed = (pick_name == login_name and not is_admin)

            grade = int(latest_grades.get(sid, 10) or 10)
            st.write(f"현재 신용등급(최근 기록 기준): **{grade}등급**")

            principal = st.number_input("예금 금액(100단위)", min_value=100, step=100, value=200, key="bank_principal")
            weeks = st.selectbox("기간(주)", [2,4,6,8,10], key="bank_weeks")

            rate = get_bank_rate(int(weeks), int(grade))
            st.info(f"적용 금리(%) : **{rate}%**  → 이자 = 금리×예금금액/100")

            if st.button("예금 가입", use_container_width=True):
                # 1) 내 통장에서 출금 (학생 본인일 때는 api_add_tx 사용)
                if pick_name == login_name and not is_admin:
                    # 학생 본인 PIN으로 출금
                    out = api_add_tx(login_name, login_pin, f"은행 예금 가입({weeks}주)", 0, int(principal))
                    if not out.get("ok"):
                        st.error(out.get("error","가입 실패"))
                    else:
                        up = upsert_bank_deposit_record(sid, int(weeks), int(principal), int(rate), date.today())
                        toast("예금 가입 완료!", icon="🏦")
                        st.rerun()
                else:
                    # 은행원/관리자가 대신 처리: 관리자 tx로 출금(벌금처럼 음수 허용이 아니라 출금)
                    out = api_admin_add_tx_by_student_id(ADMIN_PIN, sid, f"은행 예금 가입({weeks}주)", 0, int(principal))
                    if not out.get("ok"):
                        st.error(out.get("error","가입 실패"))
                    else:
                        up = upsert_bank_deposit_record(sid, int(weeks), int(principal), int(rate), date.today())
                        toast("예금 가입(대리) 완료!", icon="🏦")
                        st.rerun()

            st.divider()
            st.subheader("예금 장부")
            deposits = list_bank_deposits(sid)
            if deposits:
                df = pd.DataFrame(
                    [
                        {
                            "상태": x["status"],
                            "원금": x["principal"],
                            "기간(주)": x["weeks"],
                            "금리%": x["rate"],
                            "이자": x["interest"],
                            "만기수령": x["payout"],
                            "만기일": format_kr_datetime(x["due_at"].astimezone(KST)) if x["due_at"] else "",
                            "id": x["id"],
                        }
                        for x in deposits
                    ]
                )
                st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

                # 만기 처리(본인 또는 은행권한자)
                active_ids = [x["id"] for x in deposits if x["status"] == "active"]
                if active_ids:
                    sel = st.selectbox("만기/해지 처리할 예금", active_ids, key="bank_close_pick")
                    if st.button("만기 처리(수령)", use_container_width=True):
                        if pick_name == login_name and not is_admin:
                            res = bank_close_as_mature(sid, sel, login_name, login_pin)
                        else:
                            # 대리 만기 지급: 관리자 tx로 지급
                            snap = db.collection("bank_deposits").document(sel).get()
                            d0 = snap.to_dict() or {}
                            payout = int(d0.get("payout",0) or 0)
                            api_admin_add_tx_by_student_id(ADMIN_PIN, sid, f"은행 예금 만기({d0.get('weeks')}주)", payout, 0)
                            db.collection("bank_deposits").document(sel).update({"status":"matured", "closed_at": firestore.SERVER_TIMESTAMP})
                            res = {"ok": True}

                        if res.get("ok"):
                            toast("만기 처리 완료", icon="✅")
                            st.rerun()
                        else:
                            st.error(res.get("error","실패"))
            else:
                st.info("예금 기록이 없습니다.")
    idx += 1

# =========================
# 8) 📈 투자(뼈대)
# =========================
if "📈 투자" in tabs:
    with tab_objs[idx]:
        st.subheader("📈 투자")
        st.caption("투자 장부/주가 그래프(ppt)는 ‘참고자료’. 여기서는 거래 기록(구매/환수) 저장 뼈대만 제공합니다.")
        st.info("다음 단계에서: ‘국어/수학/사회’ 주가(%)를 교사가 입력 → 학생 포지션의 손익 자동 계산으로 확장하면 됩니다.")
    idx += 1

# =========================
# 9) 🛒 구입/벌금(뼈대)
# =========================
if "🛒 구입/벌금" in tabs:
    with tab_objs[idx]:
        st.subheader("🛒 구입/벌금")
        st.caption("구입표/벌금표를 Firestore에 규칙으로 저장해두고, 버튼으로 자동 적용하는 구조가 좋습니다.")
        st.info("다음 단계에서: store_items / fine_rules 업로드 + 적용 버튼(= 관리자 지급/출금) 연결하면 완성됩니다.")
    idx += 1

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
    # area 별 권한 키 규칙
    if area == "bank":
        return "schedule_bank_write" in perms
    if area == "treasury":
        return "schedule_treasury_write" in perms
    if area == "env":
        return "schedule_env_write" in perms
    return False

if "🗓️ 일정" in tabs:
    with tab_objs[idx]:
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
