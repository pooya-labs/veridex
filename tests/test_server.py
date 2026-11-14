from __future__ import annotations

import json
import threading
import time
from http.server import HTTPServer
import httpx

from veridex.server import VeridexStudioHandler


def test_enterprise_studio_server_full_suite():
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
        assert "Veridex Enterprise Studio" in resp.text
        assert "Model Matrix Leaderboard" in resp.text
        assert "YAML Suite Studio" in resp.text

        # 2. Test GET /api/status
        status_resp = httpx.get(f"{base_url}/api/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data.get("status") == "ok"
        assert "platform" in data

        # 3. Test GET /api/suites
        suites_resp = httpx.get(f"{base_url}/api/suites")
        assert suites_resp.status_code == 200
        suites_data = suites_resp.json()
        assert isinstance(suites_data, list)
        assert len(suites_data) >= 1

        # 4. Test POST /api/run with local suite
        run_resp = httpx.post(
            f"{base_url}/api/run",
            json={
                "suite": "examples/01_structured_extraction/suite.yaml",
                "simulate_success": True,
            },
        )
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert run_data.get("suite_id") == "structured_extraction_benchmark"
        assert run_data.get("pass_rate") == 1.0

        # 5. Test POST /api/run with raw_yaml
        raw_yaml_content = """id: inline_test
name: Inline Suite
provider: mock
cases:
  - id: c1
    name: Quick Check
    prompt: "Hello"
    expected_output: "Hello"
    assertions:
      - type: exact_match
"""
        inline_run_resp = httpx.post(
            f"{base_url}/api/run",
            json={"raw_yaml": raw_yaml_content, "simulate_success": True},
        )
        assert inline_run_resp.status_code == 200
        assert inline_run_resp.json()["pass_rate"] == 1.0

        # 6. Test GET /api/history
        history_resp = httpx.get(f"{base_url}/api/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert len(history_data) >= 2

        # 7. Test POST /api/validate
        val_resp = httpx.post(
            f"{base_url}/api/validate",
            json={"content": raw_yaml_content},
        )
        assert val_resp.status_code == 200
        val_data = val_resp.json()
        assert val_data.get("valid") is True
        assert val_data.get("cases_count") == 1

        # 8. Test POST /api/matrix
        matrix_resp = httpx.post(
            f"{base_url}/api/matrix",
            json={
                "suite": "examples/01_structured_extraction/suite.yaml",
                "models": ["mock-fast", "mock-smart"],
            },
        )
        assert matrix_resp.status_code == 200
        matrix_data = matrix_resp.json()
        assert "model_results" in matrix_data

        # 9. Test POST /api/fuzz
        fuzz_resp = httpx.post(
            f"{base_url}/api/fuzz",
            json={
                "suite": "examples/01_structured_extraction/suite.yaml",
                "modes": ["typo"],
            },
        )
        assert fuzz_resp.status_code == 200
        fuzz_data = fuzz_resp.json()
        assert "total_cases" in fuzz_data

    finally:
        server.shutdown()
        server.server_close()
