"""Message-catalog parity: every locale catalog must mirror en.json.

Guards against the failure mode where a new locale ships a partial catalog:
key sets, interpolation variable names, and rich-text tags must match the
English source of truth for every supported UI locale.

ICU plural *usage* may legitimately differ per language (English often uses a
plain `{count}` while Slavic/Romance locales need `{count, plural, ...}`) —
what must match is the set of variable names so `t('key', {count: n})`
resolves in every locale.
"""
import json
import re
from pathlib import Path

import pytest

from app.schemas.auth import SUPPORTED_UI_LOCALES

MESSAGES_DIR = Path(__file__).resolve().parents[2] / "messages"

# Matches both plain {var} and the variable in {var, plural, ...}
VAR_RE = re.compile(r"\{([a-zA-Z0-9_]+)(?:\s*,|\})")
RICH_TAGS = ("<strong>", "<code>", "<adminLink>", "<settingsLink>", "<feedbackLink>", "<br />")


def _flatten(node, prefix=""):
    flat = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def _load(locale):
    with open(MESSAGES_DIR / f"{locale}.json", encoding="utf-8") as fh:
        return _flatten(json.load(fh))


EN = None


def setup_module():
    global EN
    EN = _load("en")


@pytest.mark.parametrize("locale", sorted(set(SUPPORTED_UI_LOCALES) - {"en"}))
def test_catalog_has_no_missing_or_extra_keys(locale):
    keys = set(_load(locale))
    missing = sorted(set(EN) - keys)
    extra = sorted(keys - set(EN))
    assert not missing, f"{locale}: missing {len(missing)} keys, e.g. {missing[:10]}"
    assert not extra, f"{locale}: extra keys not in en.json, e.g. {extra[:10]}"


@pytest.mark.parametrize("locale", sorted(set(SUPPORTED_UI_LOCALES) - {"en"}))
def test_variables_and_rich_tags_match_en(locale):
    loc = _load(locale)
    problems = []
    for key, en_value in EN.items():
        if not isinstance(en_value, str):
            continue
        loc_value = loc.get(key)
        if not isinstance(loc_value, str):
            continue
        if set(VAR_RE.findall(en_value)) != set(VAR_RE.findall(loc_value)):
            problems.append((key, "variables", set(VAR_RE.findall(en_value)), set(VAR_RE.findall(loc_value))))
        for tag in RICH_TAGS:
            if en_value.count(tag) != loc_value.count(tag):
                problems.append((key, f"rich_tag:{tag}", en_value.count(tag), loc_value.count(tag)))
    assert not problems, f"{locale}: {len(problems)} parity problems, e.g. {problems[:8]}"


def test_arabic_catalog_is_registered():
    assert "ar" in SUPPORTED_UI_LOCALES
    ar = _load("ar")
    # spot-check the sections the review called out as missing
    assert "auth.login.title" in ar
    assert "admin.dashboardBanner.title" in ar
    assert "targetLanguages.es-ES" in ar
    assert "lesson.exerciseTypeMultipleChoice" in ar
