import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google.api_core.exceptions import AlreadyExists
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


class Query:
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


@dataclass
class QueryFilter:
    field_path: str
    op_string: str
    value: Any


def build_filter(field_path: str, op_string: str, value: Any) -> QueryFilter:
    return QueryFilter(field_path=field_path, op_string=op_string, value=value)


class DocumentSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]], reference: "DocumentReference"):
        self.id = str(doc_id)
        self._data = data
        self.reference = reference

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return self._data.copy() if self._data is not None else None


class DocumentReference:
    def __init__(self, collection: "CollectionReference", doc_id: str):
        self._collection = collection
        self.id = str(doc_id)

    def get(self, transaction: "Transaction" = None) -> DocumentSnapshot:
        data = self._collection._col.find_one({"_id": self.id})
        return DocumentSnapshot(self.id, data, self)

    def set(self, data: Dict[str, Any], merge: bool = False):
        payload = _normalize_payload(data)
        if merge:
            self._collection._col.update_one({"_id": self.id}, {"$set": payload}, upsert=True)
        else:
            payload["_id"] = self.id
            self._collection._col.replace_one({"_id": self.id}, payload, upsert=True)

    def create(self, data: Dict[str, Any]):
        payload = _normalize_payload(data)
        payload["_id"] = self.id
        try:
            self._collection._col.insert_one(payload)
        except DuplicateKeyError as exc:
            raise AlreadyExists(f"Document already exists: {self.id}") from exc

    def update(self, data: Dict[str, Any]):
        payload = _normalize_payload(data)
        self._collection._col.update_one({"_id": self.id}, {"$set": payload}, upsert=False)

    def delete(self):
        self._collection._col.delete_one({"_id": self.id})


class QueryReference:
    def __init__(self, col: Collection):
        self._col = col
        self._filters: List[QueryFilter] = []
        self._sort: List[tuple] = []
        self._limit: Optional[int] = None

    def where(self, *args, filter: QueryFilter = None):
        if filter is not None:
            self._filters.append(filter)
        elif len(args) == 3:
            self._filters.append(QueryFilter(args[0], args[1], args[2]))
        else:
            raise ValueError("where requires QueryFilter or (field, op, value)")
        return self

    def order_by(self, field: str, direction: str = Query.ASCENDING):
        sort_dir = DESCENDING if direction == Query.DESCENDING else ASCENDING
        self._sort.append((field, sort_dir))
        return self

    def limit(self, n: int):
        self._limit = int(n)
        return self

    def stream(self):
        cur = self._col.find(_filters_to_mongo(self._filters))
        if self._sort:
            cur = cur.sort(self._sort)
        if self._limit is not None:
            cur = cur.limit(self._limit)

        out = []
        for doc in cur:
            doc_id = str(doc.get("_id"))
            ref = DocumentReference(CollectionReference(self._col.database, self._col.name), doc_id)
            out.append(DocumentSnapshot(doc_id, doc, ref))
        return out


class CollectionReference(QueryReference):
    def __init__(self, db: Database, name: str):
        self._db = db
        self._name = name
        super().__init__(db[name])

    def document(self, doc_id: str = None) -> DocumentReference:
        if doc_id is None:
            from bson import ObjectId

            doc_id = str(ObjectId())
        return DocumentReference(self, str(doc_id))

    def add(self, data: Dict[str, Any]):
        ref = self.document()
        ref.set(data)
        return None, ref


class Transaction:
    def __init__(self, client: "MongoCompatClient"):
        self._client = client

    def get(self, doc_ref: DocumentReference):
        return doc_ref.get(transaction=self)

    def set(self, doc_ref: DocumentReference, data: Dict[str, Any], merge: bool = False):
        doc_ref.set(data, merge=merge)

    def update(self, doc_ref: DocumentReference, data: Dict[str, Any]):
        doc_ref.update(data)

    def delete(self, doc_ref: DocumentReference):
        doc_ref.delete()


class WriteBatch:
    def __init__(self):
        self._ops = []

    def set(self, doc_ref: DocumentReference, data: Dict[str, Any], merge: bool = False):
        self._ops.append(("set", doc_ref, data, merge))

    def update(self, doc_ref: DocumentReference, data: Dict[str, Any]):
        self._ops.append(("update", doc_ref, data, None))

    def delete(self, doc_ref: DocumentReference):
        self._ops.append(("delete", doc_ref, None, None))

    def commit(self):
        for op, ref, data, merge in self._ops:
            if op == "set":
                ref.set(data, merge=bool(merge))
            elif op == "update":
                ref.update(data)
            elif op == "delete":
                ref.delete()
        self._ops = []


class MongoCompatClient:
    def __init__(self, db: Database):
        self._db = db

    def collection(self, name: str) -> CollectionReference:
        return CollectionReference(self._db, name)

    def transaction(self) -> Transaction:
        return Transaction(self)

    def batch(self) -> WriteBatch:
        return WriteBatch()


class _MongoNamespace:
    Query = Query

    @staticmethod
    def transactional(fn):
        def wrapper(transaction: Transaction, *args, **kwargs):
            return fn(transaction, *args, **kwargs)

        return wrapper


mongo = _MongoNamespace()


def init_db(uri: Optional[str] = None, db_name: Optional[str] = None) -> MongoCompatClient:
    global _client, _db
    mongo_uri = uri or os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI is required")

    resolved_db_name = db_name or os.environ.get("MONGO_DB_NAME", "class_point_app")

    if _client is None:
        _client = MongoClient(mongo_uri)
    if _db is None or _db.name != resolved_db_name:
        _db = _client[resolved_db_name]

    return MongoCompatClient(_db)


def get_collection(name: str) -> Collection:
    if _db is None:
        init_db()
    return _db[name]


def insert_document(collection_name: str, data: Dict[str, Any]) -> str:
    col = get_collection(collection_name)
    payload = _normalize_payload(data)
    result = col.insert_one(payload)
    return str(result.inserted_id)


def find_documents(collection_name: str, query: Optional[Dict[str, Any]] = None):
    col = get_collection(collection_name)
    return list(col.find(query or {}))


def update_document(collection_name: str, query: Dict[str, Any], update_data: Dict[str, Any], upsert: bool = False) -> int:
    col = get_collection(collection_name)
    result = col.update_one(query, {"$set": _normalize_payload(update_data)}, upsert=upsert)
    return result.modified_count


def delete_document(collection_name: str, query: Dict[str, Any]) -> int:
    col = get_collection(collection_name)
    result = col.delete_one(query)
    return result.deleted_count


def _filters_to_mongo(filters: List[QueryFilter]) -> Dict[str, Any]:
    query: Dict[str, Any] = {}
    for f in filters:
        field, op, value = f.field_path, f.op_string, _normalize_value(f.value)
        if op == "==":
            query[field] = value
        else:
            mongo_op = {
                ">": "$gt",
                ">=": "$gte",
                "<": "$lt",
                "<=": "$lte",
                "!=": "$ne",
                "in": "$in",
            }.get(op)
            if not mongo_op:
                raise ValueError(f"Unsupported operator: {op}")
            query.setdefault(field, {})[mongo_op] = value
    return query


def _normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _normalize_value(v) for k, v in data.items()}


def _normalize_dict_key(key: Any) -> str:
    """Ensure nested document keys are BSON-safe."""
    safe_key = str(key)
    return safe_key.replace(".", "\uff0e").replace("$", "\uff04").replace("\x00", "\ufffd")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {_normalize_dict_key(k): _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    return value
