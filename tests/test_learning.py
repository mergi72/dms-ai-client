from __future__ import annotations

import json
from pathlib import Path

import pytest

from dms_ai_client.learning import apply_corrections, forget_correction, learn_correction, learned_data


def test_confirmed_learning_writes_only_user_local_config(tmp_path: Path) -> None:
    machine = tmp_path / "machine"
    user = tmp_path / "user"
    machine.mkdir()
    machine_config = machine / "voice.json"
    machine_config.write_text('{"machine": true}', encoding="utf-8")
    learn_correction("virtualizaci", "v realizaci", max_keywords=5, max_corrections=5, user_dir=user)
    assert json.loads(machine_config.read_text(encoding="utf-8")) == {"machine": True}
    keywords, corrections = learned_data(user)
    assert keywords == ("v realizaci",)
    assert corrections[0].heard == "virtualizaci"
    assert apply_corrections("Najdi ve virtualizaci zakázku", corrections) == "Najdi ve v realizaci zakázku"


def test_learning_requires_a_real_confirmed_change(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        learn_correction("stejné", "stejné", max_keywords=5, max_corrections=5, user_dir=tmp_path)


def test_correction_can_be_forgotten(tmp_path: Path) -> None:
    learn_correction("edo kat", "eDoCat", max_keywords=5, max_corrections=5, user_dir=tmp_path)
    forget_correction("edo kat", user_dir=tmp_path)
    keywords, corrections = learned_data(tmp_path)
    assert keywords == ()
    assert corrections == ()


def test_legacy_learning_is_read_and_migrated_on_forget(tmp_path: Path) -> None:
    (tmp_path / "client.local.json").write_text(
        json.dumps({"voice": {"transcription": {
            "learnedKeywords": ["eDoCat"],
            "corrections": [{"heard": "edo kat", "replaceWith": "eDoCat"}],
        }}}),
        encoding="utf-8",
    )
    assert learned_data(tmp_path)[0] == ("eDoCat",)
    forget_correction("edo kat", user_dir=tmp_path)
    assert (tmp_path / "voice.local.json").exists()
    assert learned_data(tmp_path) == ((), ())
