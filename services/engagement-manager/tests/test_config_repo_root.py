from __future__ import annotations

from app.config import _defaults_images, _repo_root, get_settings


def test_repo_root_and_image_pins_do_not_raise() -> None:
    """Docker image layout is /app/app/config.py — parents[3] must not crash boot."""
    root = _repo_root()
    assert root.is_dir()
    images = _defaults_images()
    assert isinstance(images, dict)
    settings = get_settings()
    assert settings.android_emulator_image
    assert settings.mobsf_image
