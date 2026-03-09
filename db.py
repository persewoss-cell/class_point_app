diff --git a/db.py b/db.py
new file mode 100644
index 0000000000000000000000000000000000000000..fa7f53445da69fca21141f54e931cb3a51848aaa
--- /dev/null
+++ b/db.py
@@ -0,0 +1,211 @@
+from __future__ import annotations
+
+from dataclasses import dataclass
+from datetime import datetime, timezone
+from typing import Any, Dict, Iterable, List, Optional
+
+from pymongo import ASCENDING, DESCENDING, MongoClient
+from pymongo.collection import Collection
+from pymongo.database import Database
+
+
+class FailedPrecondition(Exception):
+    """Firestore 호환 예외 자리표시자."""
+
+
+@dataclass
+class FieldFilter:
+    field_path: str
+    op_string: str
+    value: Any
+
+
+class _ServerTimestamp:
+    pass
+
+
+class Query:
+    ASCENDING = "ASCENDING"
+    DESCENDING = "DESCENDING"
+
+
+SERVER_TIMESTAMP = _ServerTimestamp()
+
+
+class DocumentSnapshot:
+    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
+        self.id = str(doc_id)
+        self._data = data
+
+    @property
+    def exists(self) -> bool:
+        return self._data is not None
+
+    def to_dict(self) -> Optional[Dict[str, Any]]:
+        if self._data is None:
+            return None
+        data = dict(self._data)
+        data.pop("_id", None)
+        return data
+
+
+class DocumentReference:
+    def __init__(self, collection: "CollectionReference", doc_id: str):
+        self._collection = collection
+        self.id = str(doc_id)
+
+    def get(self, transaction: "Transaction" = None) -> DocumentSnapshot:
+        data = self._collection._col.find_one({"_id": self.id})
+        return DocumentSnapshot(self.id, data)
+
+    def set(self, data: Dict[str, Any], merge: bool = False):
+        payload = _normalize_payload(data)
+        if merge:
+            self._collection._col.update_one({"_id": self.id}, {"$set": payload}, upsert=True)
+        else:
+            payload["_id"] = self.id
+            self._collection._col.replace_one({"_id": self.id}, payload, upsert=True)
+
+    def update(self, data: Dict[str, Any]):
+        payload = _normalize_payload(data)
+        self._collection._col.update_one({"_id": self.id}, {"$set": payload}, upsert=False)
+
+    def delete(self):
+        self._collection._col.delete_one({"_id": self.id})
+
+
+class QueryReference:
+    def __init__(self, col: Collection):
+        self._col = col
+        self._filters: List[FieldFilter] = []
+        self._sort: List[tuple] = []
+        self._limit: Optional[int] = None
+
+    def where(self, *args, filter: FieldFilter = None):
+        if filter is not None:
+            self._filters.append(filter)
+        elif len(args) == 3:
+            self._filters.append(FieldFilter(args[0], args[1], args[2]))
+        else:
+            raise ValueError("where requires FieldFilter or (field, op, value)")
+        return self
+
+    def order_by(self, field: str, direction: str = Query.ASCENDING):
+        sort_dir = DESCENDING if direction == Query.DESCENDING else ASCENDING
+        self._sort.append((field, sort_dir))
+        return self
+
+    def limit(self, n: int):
+        self._limit = int(n)
+        return self
+
+    def stream(self) -> Iterable[DocumentSnapshot]:
+        cur = self._col.find(_filters_to_mongo(self._filters))
+        if self._sort:
+            cur = cur.sort(self._sort)
+        if self._limit is not None:
+            cur = cur.limit(self._limit)
+        return [DocumentSnapshot(str(doc.get("_id")), doc) for doc in cur]
+
+
+class CollectionReference(QueryReference):
+    def __init__(self, db: Database, name: str):
+        self._db = db
+        self._name = name
+        super().__init__(db[name])
+
+    def document(self, doc_id: str = None) -> DocumentReference:
+        if doc_id is None:
+            from bson import ObjectId
+
+            doc_id = str(ObjectId())
+        return DocumentReference(self, str(doc_id))
+
+    def add(self, data: Dict[str, Any]):
+        ref = self.document()
+        ref.set(data)
+        return None, ref
+
+
+class Transaction:
+    def __init__(self, client: "FirestoreCompatClient"):
+        self._client = client
+
+    def get(self, doc_ref: DocumentReference):
+        return doc_ref.get(transaction=self)
+
+    def set(self, doc_ref: DocumentReference, data: Dict[str, Any], merge: bool = False):
+        doc_ref.set(data, merge=merge)
+
+    def update(self, doc_ref: DocumentReference, data: Dict[str, Any]):
+        doc_ref.update(data)
+
+    def delete(self, doc_ref: DocumentReference):
+        doc_ref.delete()
+
+
+class FirestoreCompatClient:
+    def __init__(self, db: Database):
+        self._db = db
+
+    def collection(self, name: str) -> CollectionReference:
+        return CollectionReference(self._db, name)
+
+    def transaction(self) -> Transaction:
+        return Transaction(self)
+
+
+def transactional(fn):
+    def wrapper(transaction: Transaction, *args, **kwargs):
+        return fn(transaction, *args, **kwargs)
+
+    return wrapper
+
+
+class _FirestoreNamespace:
+    Query = Query
+    SERVER_TIMESTAMP = SERVER_TIMESTAMP
+    transactional = staticmethod(transactional)
+
+
+firestore = _FirestoreNamespace()
+
+
+def init_db(uri: str, db_name: str) -> FirestoreCompatClient:
+    client = MongoClient(uri)
+    return FirestoreCompatClient(client[db_name])
+
+
+def _filters_to_mongo(filters: List[FieldFilter]) -> Dict[str, Any]:
+    query: Dict[str, Any] = {}
+    for f in filters:
+        field, op, value = f.field_path, f.op_string, _normalize_value(f.value)
+        if op == "==":
+            query[field] = value
+        else:
+            mongo_op = {
+                ">": "$gt",
+                ">=": "$gte",
+                "<": "$lt",
+                "<=": "$lte",
+                "!=": "$ne",
+                "in": "$in",
+            }.get(op)
+            if not mongo_op:
+                raise ValueError(f"Unsupported operator: {op}")
+            query.setdefault(field, {})[mongo_op] = value
+    return query
+
+
+def _normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
+    return {k: _normalize_value(v) for k, v in data.items()}
+
+
+def _normalize_value(value: Any) -> Any:
+    if value is SERVER_TIMESTAMP:
+        return datetime.now(timezone.utc)
+    if isinstance(value, dict):
+        return {k: _normalize_value(v) for k, v in value.items()}
+    if isinstance(value, list):
+        return [_normalize_value(v) for v in value]
+    return value
