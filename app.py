import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.title("🔥 Class Bank Connected to Firebase")

# Firebase 연결
if not firebase_admin._apps:
    firebase_dict = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 테스트로 데이터 저장
if st.button("테스트 데이터 저장"):
    db.collection("test").add({"msg": "파이어베이스 연결 성공!"})
    st.success("Firestore에 저장 완료!")
