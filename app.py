
# app_quota_fix_v5.py
# 핵심: Firestore 429 Quota exceeded 시 무한 retry(300초) 방지
# - retry=None, timeout=10
# - try/except로 앱 크래시 방지
# - templates / accounts 조회 보호

import streamlit as st
from firebase_admin import firestore

# db는 기존 초기화 로직을 그대로 사용한다고 가정
# from your existing code: db = firestore.client()

# =========================
# Templates (안전 조회)
# =========================
@st.cache_data(ttl=300, show_spinner=False)
def api_list_templates_cached():
    try:
        templates = []
        docs = db.collection("templates").stream(retry=None, timeout=10)
        for d in docs:
            t = d.to_dict() or {}
            if t.get("label"):
                templates.append({
                    "template_id": d.id,
                    "label": t.get("label"),
                    "kind": str(t.get("kind", "deposit") or "deposit"),
                    "amount": int(t.get("amount", 0) or 0),
                    "order": int(t.get("order", 999999) or 999999),
                })
        templates.sort(key=lambda x: (x["order"], x["label"]))
        return {"ok": True, "templates": templates}
    except Exception as e:
        return {"ok": False, "templates": [], "error": f"{type(e).__name__}: {e}"}


# =========================
# Accounts (안전 조회)
# =========================
@st.cache_data(ttl=30, show_spinner=False)
def api_list_accounts_cached():
    try:
        accounts = []
        docs = db.collection("accounts").stream(retry=None, timeout=10)
        for d in docs:
            a = d.to_dict() or {}
            a["id"] = d.id
            if a.get("name"):
                accounts.append(a)
        accounts = sorted(accounts, key=lambda x: str(x.get("name", "")))
        return {"ok": True, "accounts": accounts}
    except Exception as e:
        return {"ok": False, "accounts": [], "error": f"{type(e).__name__}: {e}"}


# =========================
# 사용 예 (기존 코드에서 이 패턴으로 교체)
# =========================
def safe_load_accounts():
    res = api_list_accounts_cached()
    if not res.get("ok"):
        st.warning(f"계정 목록을 불러오지 못했어요: {res.get('error','')}")
        return []
    return res.get("accounts", [])
