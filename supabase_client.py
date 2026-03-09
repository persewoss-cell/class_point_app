diff --git a/supabase_client.py b/supabase_client.py
new file mode 100644
index 0000000000000000000000000000000000000000..d42c1d4abe2664178a14468b56b1305b0fc66631
--- /dev/null
+++ b/supabase_client.py
@@ -0,0 +1,38 @@
+from supabase import create_client
+import os
+
+SUPABASE_URL = os.environ.get("SUPABASE_URL")
+SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
+
+supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
+
+
+def db_select_one(table, column, value):
+    res = supabase.table(table).select("*").eq(column, value).limit(1).execute()
+    if res.data:
+        return res.data[0]
+    return None
+
+
+def db_select_all(table):
+    res = supabase.table(table).select("*").execute()
+    return res.data or []
+
+
+def db_insert(table, doc_id, data):
+    payload = {
+        "id": doc_id,
+        "data": data
+    }
+    return supabase.table(table).upsert(payload).execute()
+
+
+def db_update(table, doc_id, data):
+    payload = {
+        "data": data
+    }
+    return supabase.table(table).update(payload).eq("id", doc_id).execute()
+
+
+def db_delete(table, doc_id):
+    return supabase.table(table).delete().eq("id", doc_id).execute()
