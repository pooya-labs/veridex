import pytest
from veridex.providers.http_provider import HttpEndpointProvider


def test_http_provider_template_rendering():
    provider = HttpEndpointProvider(
        endpoint_url="https://api.example.com/v1/chat",
        payload_template={
            "query": "{{ prompt }}",
            "context": {"sys": "{{ system_prompt }}"},
        },
    )

    rendered = provider._render_template(
        provider.payload_template,
        prompt="Explain quantum entanglement",
        system_prompt="You are a physicist",
    )

    assert rendered["query"] == "Explain quantum entanglement"
    assert rendered["context"]["sys"] == "You are a physicist"


def test_http_provider_response_extraction():
    data = {
        "status": "ok",
        "result": {
            "output": "Simulated RAG output text",
        },
    }

    text = HttpEndpointProvider._extract_response_text(data, "result.output")
    assert text == "Simulated RAG output text"
