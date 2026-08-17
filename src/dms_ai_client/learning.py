from __future__ import annotations

import json
import os
import re
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dms_ai_client.paths import USER_CONFIG_DIR


_LEARNING_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class Correction:
    heard: str
    replace_with: str


def _local_path(user_dir: Path | None = None) -> Path:
    return (user_dir or USER_CONFIG_DIR) / "voice.local.json"


def _legacy_local_path(user_dir: Path | None = None) -> Path:
    return (user_dir or USER_CONFIG_DIR) / "client.local.json"


def _payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Local client configuration must be a JSON object.")
    return value


def learned_data(user_dir: Path | None = None) -> tuple[tuple[str, ...], tuple[Correction, ...]]:
    with _LEARNING_LOCK:
        path = _local_path(user_dir)
        if path.exists():
            transcription = _payload(path).get("transcription", {})
        else:
            transcription = _payload(_legacy_local_path(user_dir)).get("voice", {}).get("transcription", {})
    if not isinstance(transcription, dict):
        return (), ()
    raw_keywords = transcription.get("learnedKeywords", [])
    keywords = tuple(item.strip() for item in raw_keywords if isinstance(item, str) and item.strip()) if isinstance(raw_keywords, list) else ()
    corrections: list[Correction] = []
    raw_corrections = transcription.get("corrections", [])
    if isinstance(raw_corrections, list):
        for item in raw_corrections:
            if not isinstance(item, dict):
                continue
            heard, replacement = item.get("heard"), item.get("replaceWith")
            if isinstance(heard, str) and heard.strip() and isinstance(replacement, str) and replacement.strip():
                corrections.append(Correction(heard.strip(), replacement.strip()))
    return tuple(dict.fromkeys(keywords)), tuple(corrections)


def apply_corrections(text: str, corrections: tuple[Correction, ...]) -> str:
    result = text
    for correction in corrections:
        pattern = rf"(?<!\w){re.escape(correction.heard)}(?!\w)"
        result = re.sub(pattern, lambda _match, value=correction.replace_with: value, result, flags=re.IGNORECASE)
    return result


def _write(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def learn_correction(
    heard: str,
    replacement: str,
    *,
    max_keywords: int,
    max_corrections: int,
    user_dir: Path | None = None,
) -> None:
    with _LEARNING_LOCK:
        heard, replacement = heard.strip(), replacement.strip()
        if not heard or not replacement or heard.casefold() == replacement.casefold():
            raise ValueError("Learning requires two different non-empty texts.")
        if len(heard) > 300 or len(replacement) > 300 or "\n" in heard or "\n" in replacement:
            raise ValueError("Learned text must be one line up to 300 characters.")
        path = _local_path(user_dir)
        payload = _payload(path)
        transcription = payload.setdefault("transcription", {})
        if not isinstance(transcription, dict):
            raise ValueError("Local transcription configuration must be an object.")
        keywords, corrections = learned_data(user_dir)
        updated_keywords = list(keywords)
        if replacement.casefold() not in {item.casefold() for item in updated_keywords}:
            if len(updated_keywords) >= max_keywords:
                raise ValueError("Maximum number of learned keywords reached.")
            updated_keywords.append(replacement)
        updated_corrections = [item for item in corrections if item.heard.casefold() != heard.casefold()]
        if len(updated_corrections) >= max_corrections:
            raise ValueError("Maximum number of learned corrections reached.")
        updated_corrections.append(Correction(heard, replacement))
        transcription["learnedKeywords"] = updated_keywords
        transcription["corrections"] = [
            {"heard": item.heard, "replaceWith": item.replace_with} for item in updated_corrections
        ]
        _write(payload, path)


def forget_correction(heard: str, *, user_dir: Path | None = None) -> None:
    with _LEARNING_LOCK:
        path = _local_path(user_dir)
        payload = _payload(path)
        if not path.exists():
            legacy = _payload(_legacy_local_path(user_dir)).get("voice", {}).get("transcription", {})
            if isinstance(legacy, dict):
                payload["transcription"] = dict(legacy)
        transcription = payload.get("transcription", {})
        if not isinstance(transcription, dict):
            return
        corrections = transcription.get("corrections", [])
        if isinstance(corrections, list):
            removed_replacements = {
                str(item.get("replaceWith", "")).casefold()
                for item in corrections
                if isinstance(item, dict) and str(item.get("heard", "")).casefold() == heard.strip().casefold()
            }
            transcription["corrections"] = [
                item for item in corrections
                if not isinstance(item, dict) or str(item.get("heard", "")).casefold() != heard.strip().casefold()
            ]
            remaining_replacements = {
                str(item.get("replaceWith", "")).casefold()
                for item in transcription["corrections"]
                if isinstance(item, dict)
            }
            keywords = transcription.get("learnedKeywords", [])
            if isinstance(keywords, list):
                transcription["learnedKeywords"] = [
                    item for item in keywords
                    if not isinstance(item, str) or item.casefold() not in removed_replacements - remaining_replacements
                ]
        _write(payload, path)
