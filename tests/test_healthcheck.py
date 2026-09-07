"""
Unit test for healthcheck.py HTTP server.
"""

import json
import urllib.request
from healthcheck import start_health_server


def test_health_server_endpoint():
    # Start server on a test port
    test_port = 19876
    server = start_health_server(port=test_port)
    assert server is not None

    try:
        # Request /health
        url = f"http://127.0.0.1:{test_port}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "healthy"
            assert data["service"] == "Reddit Survey Scout"
            assert "uptime_seconds" in data
    finally:
        server.shutdown()
        server.server_close()
