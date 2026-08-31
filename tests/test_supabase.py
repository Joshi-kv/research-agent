import uuid

import pytest

from integrations.supabase import get_supabase_client

TABLE = "test_table"


@pytest.mark.integration
def test_supabase_roundtrip():
    """Insert/read/delete against live Supabase.

    Scoped to a unique row so it never deletes data it did not create — the
    previous version wiped the whole table with .neq("id", 0), which also
    compared a uuid column against an integer.
    """
    client = get_supabase_client()
    name = f"pytest-{uuid.uuid4()}"

    inserted = client.table(TABLE).insert({"name": name}).execute().data
    assert len(inserted) == 1
    row_id = inserted[0]["id"]

    try:
        rows = client.table(TABLE).select("*").eq("name", name).execute().data
        assert len(rows) == 1
        assert rows[0]["name"] == name
        assert rows[0]["id"] == row_id
    finally:
        client.table(TABLE).delete().eq("id", row_id).execute()

    assert client.table(TABLE).select("*").eq("name", name).execute().data == []
