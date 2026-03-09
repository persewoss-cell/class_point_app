import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def db_select_all(table):
    res = supabase.table(table).select("*").execute()
    return res.data


def db_select_one(table, column, value):
    res = supabase.table(table).select("*").eq(column, value).execute()
    return res.data[0] if res.data else None


def db_insert(table, data):
    return supabase.table(table).insert(data).execute()


def db_update(table, column, value, data):
    return supabase.table(table).update(data).eq(column, value).execute()


def db_delete(table, column, value):
    return supabase.table(table).delete().eq(column, value).execute()
