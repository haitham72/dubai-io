from fastapi.testclient import TestClient

from app.widgets import app


def test_widget_origin_serves_only_miniapps_with_no_network():
    client = TestClient(app)
    page = client.get("/miniapps/marinaexpress.html")
    assert page.status_code == 200
    csp = page.headers["content-security-policy"]
    assert "connect-src 'none'" in csp and "default-src 'none'" in csp
    assert client.get("/index.html").status_code == 404  # the host app is not on this origin
    assert client.get("/api/health").status_code == 404
