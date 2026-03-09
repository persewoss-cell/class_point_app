from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

import streamlit as st
from postgrest.exceptions import APIError
from supabase import create_client


class FailedPrecondition(Exception):
    pass


@dataclass
class FieldFilter:
    field: str
    op: str
    value: Any


class Query:
    ASCENDING = "asc"
    DESCENDING = "desc"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVER_TIMESTAMP = _now_iso


class _FirestoreCompat:
    SERVER_TIMESTAMP = SERVER_TIMESTAMP
    Query = Query

    @staticmethod
    def transactional(fn: Callable):
        return fn


firestore = _FirestoreCompat()


class DocumentSnapshot:
    def __init__(self, table: str, doc_id: str, data: dict[str, Any] | None):
        self._table = table
        self.id = str(doc_id)
        self._data = data
        self.exists = data is not None
        self.reference = DocumentReference(table, doc_id)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data or {})


class _DocStreamItem(DocumentSnapshot):
    pass


class DocumentReference:
    def __init__(self, table: str, doc_id: str):
        self.table_name = table
        self.doc_id = str(doc_id)

    def get(self, transaction=None) -> DocumentSnapshot:
        q = _supabase().table(self.table_name).select("*").eq("id", self.doc_id).limit(1).execute()
        rows = q.data or []
        return DocumentSnapshot(self.table_name, self.doc_id, rows[0] if rows else None)

    def set(self, data: dict[str, Any], merge: bool = False):
        payload = dict(data)
        if payload.get("id") is None:
            payload["id"] = self.doc_id
        if merge:
            existing = self.get()
            if existing.exists:
                merged = existing.to_dict()
                merged.update(payload)
                payload = merged
        return _supabase().table(self.table_name).upsert(payload).execute()

    def update(self, data: dict[str, Any]):
        return _supabase().table(self.table_name).update(dict(data)).eq("id", self.doc_id).execute()

    def delete(self):
        return _supabase().table(self.table_name).delete().eq("id", self.doc_id).execute()


class QueryRef:
    def __init__(self, table: str):
        self.table_name = table
        self._filters: list[FieldFilter] = []
        self._order_by: tuple[str, str] | None = None
        self._limit: int | None = None

    def document(self, doc_id: str | None = None) -> DocumentReference:
        import uuid

        return DocumentReference(self.table_name, str(doc_id or uuid.uuid4()))

    def where(self, filter: FieldFilter):
        self._filters.append(filter)
        return self

    def order_by(self, field: str, direction: str = Query.ASCENDING):
        self._order_by = (field, direction)
        return self

    def limit(self, n: int):
        self._limit = int(n)
        return self

        def _apply_filters_python(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = rows
        for f in self._filters:
            if f.op == "==":
                out = [r for r in out if r.get(f.field) == f.value]
            elif f.op == ">=":
                out = [r for r in out if r.get(f.field) is not None and r.get(f.field) >= f.value]
            elif f.op == "<=":
                out = [r for r in out if r.get(f.field) is not None and r.get(f.field) <= f.value]
            elif f.op == ">":
                out = [r for r in out if r.get(f.field) is not None and r.get(f.field) > f.value]
            elif f.op == "<":
                out = [r for r in out if r.get(f.field) is not None and r.get(f.field) < f.value]
            elif f.op == "in":
                values = list(f.value or [])
                out = [r for r in out if r.get(f.field) in values]
        return out

    def _apply_order_limit_python(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = list(rows)
        if self._order_by:
            field, direction = self._order_by
            out.sort(key=lambda r: (r.get(field) is None, r.get(field)), reverse=(direction == Query.DESCENDING))
        if self._limit is not None:
            out = out[: self._limit]
        return out
        
    def stream(self) -> Iterable[_DocStreamItem]:
        qb = _supabase().table(self.table_name).select("*")
        for f in self._filters:
            if f.op == "==":
                qb = qb.eq(f.field, f.value)
            elif f.op == ">=":
                qb = qb.gte(f.field, f.value)
            elif f.op == "<=":
                qb = qb.lte(f.field, f.value)
            elif f.op == ">":
                qb = qb.gt(f.field, f.value)
            elif f.op == "<":
                qb = qb.lt(f.field, f.value)
            elif f.op == "in":
                qb = qb.in_(f.field, f.value)
        if self._order_by:
            field, direction = self._order_by
            qb = qb.order(field, desc=(direction == Query.DESCENDING))
        if self._limit is not None:
            qb = qb.limit(self._limit)
            
        try:
            rows = qb.execute().data or []
        except APIError:
            # Firestore에서는 스키마가 느슨하지만, Supabase/PostgREST는
            # 존재하지 않는 컬럼 필터/정렬에서 즉시 오류를 발생시킨다.
            # 이 경우 전체 조회 후 Python에서 동일 조건을 적용해 호환성을 유지한다.
            raw_rows = _supabase().table(self.table_name).select("*").execute().data or []
            rows = self._apply_order_limit_python(self._apply_filters_python(raw_rows))
            
            return [_DocStreamItem(self.table_name, str(r.get("id", "")), r) for r in rows]

    def get(self):
        return list(self.stream())


class Batch:
    def __init__(self):
        self.ops: list[tuple[str, Any]] = []

    def set(self, ref: DocumentReference, data: dict[str, Any], merge: bool = False):
        self.ops.append(("set", (ref, data, merge)))

    def update(self, ref: DocumentReference, data: dict[str, Any]):
        self.ops.append(("update", (ref, data)))

    def delete(self, ref: DocumentReference):
        self.ops.append(("delete", (ref,)))

    def commit(self):
        for op, args in self.ops:
            getattr(self, f"_exec_{op}")(*args)

    def _exec_set(self, ref, data, merge):
        ref.set(data, merge=merge)

    def _exec_update(self, ref, data):
        ref.update(data)

    def _exec_delete(self, ref):
        ref.delete()


class Transaction(Batch):
    pass


class DB:
    def table(self, name: str) -> QueryRef:
        return QueryRef(name)

    def batch(self) -> Batch:
        return Batch()

    def transaction(self) -> Transaction:
        return Transaction()


def get_db() -> DB:
    return DB()


def _supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# helpers requested

def get_students():
    return _supabase().table("students").select("*").execute().data or []


def insert_student(data: dict[str, Any]):
    return _supabase().table("students").insert(data).execute()
