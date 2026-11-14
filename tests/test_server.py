from __future__ import annotations

import json
import threading
import time
from http.server import HTTPServer
import httpx

from veridex.server import VeridexStudioHandler


def test_studio_server_endpoints():
    server = HTTPServer(("127.0.0.1", 0), VeridexStudioHandler)
    port = server.server_port

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        base_url = f"http://127.0.0.1:{port}"

        # 1. Test GET /
        resp = httpx.get(f"{base_url}/")
        assert resp.status_code == 200
        assert "Veridex Live Evaluation Studio" in resp.text

        # 2. Test GET /api/status
        status_resp = httpx.get(f"{base_url}/api/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data.get("status") == "ok"

        # 3. Test POST /api/run
        run_resp = httpx.post(
            f"{base_url}/api/run",
            json={
                "suite": "examples/01_structured_extraction/suite.yaml",
                "simulate_success": True,
            },
        )
        assert run_resp.status_code == 200
        res_data = run_resp.json()
        assert res_data.get("suite_id") == "structured_extraction_benchmark"
        assert res_data.get("pass_rate") == 1.0

    finally:
        server.shutdown()
        server.server_close()
