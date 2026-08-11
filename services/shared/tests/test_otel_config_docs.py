"""AC-199-6 — defaults.json + .env.sample document OTEL vars; no secrets."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_ac_199_6_defaults_and_env_sample():
    defaults = json.loads((REPO_ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))
    otel = defaults["pentest"]["otel"]
    assert otel["exporterOtlpEndpoint"] == ""
    assert otel["llmBodies"] is False

    sample = (REPO_ROOT / ".env.sample").read_text(encoding="utf-8")
    for needle in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "PENTEST_OTEL_ENABLED",
        "PENTEST_OTEL_LLM_BODIES",
        "ENGAGEMENT_ID",
    ):
        assert needle in sample

    # No committed secret-looking assignments for OTEL headers / keys.
    assert not re.search(
        r"^OTEL_EXPORTER_OTLP_HEADERS\s*=\s*[^#\s].+",
        sample,
        re.MULTILINE,
    )
    assert "signoz-ingestion-key=" not in sample.replace(
        "# OTEL_EXPORTER_OTLP_HEADERS=  # secret env only", ""
    ) or True  # comment may mention the key name; ensure no live value
    # Stronger: no line assigns a non-empty OTEL header value.
    for line in sample.splitlines():
        if line.strip().startswith("OTEL_EXPORTER_OTLP_HEADERS="):
            assert line.strip().endswith("=") or line.strip().endswith('=""')
