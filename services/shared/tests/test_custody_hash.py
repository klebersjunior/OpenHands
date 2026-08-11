"""AC-199-3 — custody hash chain breaks if a middle event is altered."""

from __future__ import annotations

import sys
from pathlib import Path

SERVICES_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICES_ROOT))

from shared.custody import build_custody_event, verify_chain


def test_ac_199_3_tamper_breaks_chain():
    e1 = build_custody_event(
        engagement_id="11111111-1111-1111-1111-111111111111",
        actor="session:test",
        action="finding.create",
        resource_type="finding",
        resource_id="f1",
        prev_hash=None,
        metadata={"severity": "high"},
    )
    e2 = build_custody_event(
        engagement_id="11111111-1111-1111-1111-111111111111",
        actor="session:test",
        action="finding.triage",
        resource_type="finding",
        resource_id="f1",
        prev_hash=e1.hash,
        metadata={"status": "confirmed"},
    )
    e3 = build_custody_event(
        engagement_id="11111111-1111-1111-1111-111111111111",
        actor="session:test",
        action="finding.export",
        resource_type="finding",
        resource_id="f1",
        prev_hash=e2.hash,
        metadata={"ref": "s3://bucket/e1/evidence.json"},
    )
    assert verify_chain([e1, e2, e3]) is True

    # Tamper middle event metadata without recomputing hash.
    e2.metadata_redacted = {"status": "false_positive", "tampered": True}
    assert verify_chain([e1, e2, e3]) is False
