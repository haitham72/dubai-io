"""HTTP surface: no secrets in responses, file import, disabled WhatsApp send."""
import json

from fastapi.testclient import TestClient

from app import main


def test_connector_http_lists_blocks_and_imports(tmp_path):
    client = TestClient(main.app)
    assert client.get("/api/session").status_code == 200
    listed = client.get("/api/connectors")
    assert listed.status_code == 200
    body = listed.json()
    by_id = {row["id"]: row for row in body["connectors"]}
    assert by_id["signal"]["available"] is False and by_id["signal"]["integration"] == "unavailable"
    assert by_id["whatsapp"]["integration"] == "unofficial" and by_id["whatsapp"]["available"] is False
    assert by_id["gmail"]["integration"] == "official_api" and by_id["gmail"]["available"] is True
    assert "ciphertext" not in listed.text

    folder = tmp_path / "box"
    folder.mkdir()
    (folder / "note.txt").write_text("keep this file")
    connected = client.post("/api/connectors/filesystem/connect", json={"credentials": {"root": str(folder)}})
    assert connected.status_code == 200
    assert connected.json()["account_label"] == str(folder)
    synced = client.post("/api/connectors/filesystem/sync")
    assert synced.status_code == 200 and synced.json()["imported"] == 1
    records = client.get("/api/connectors/filesystem/records")
    assert records.json()["items"][0]["provenance"] == "provider_confirmed"
    assert "keep this file" in records.json()["items"][0]["text"]

    imported = client.post("/api/connectors/finance_statements/import", json={
        "filename": "statement.csv",
        "content": "id,date,description,amount,currency\nline-1,2026-11-01,Salik,12.50,AED\n",
    })
    assert imported.status_code == 200
    assert imported.json()["provenance"] == "user_supplied"
    statement = client.get("/api/connectors/finance_statements/records").json()["items"][0]
    assert statement["source_timestamp"] == "2026-11-01"
    assert statement["metadata"]["amount"]["provenance"] == "user_supplied"
    assert statement["provenance"] == "user_supplied"

    blocked = client.post("/api/connectors/signal/sync")
    assert blocked.status_code == 409
    send = client.post("/api/connectors/whatsapp/outbound", json={"action": "send_message", "payload": {"to": "971500000000", "text": "hi"}})
    assert send.status_code == 403
    assert send.json()["detail"]
    deleted = client.delete("/api/connectors/filesystem/data")
    assert deleted.status_code == 200
    assert (folder / "note.txt").read_text() == "keep this file"
    assert client.get("/api/connectors/filesystem/records").json()["items"] == []
    assert "super-secret" not in json.dumps(listed.json())
