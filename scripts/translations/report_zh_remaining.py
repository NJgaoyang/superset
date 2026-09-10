# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file distributed
# with this work for additional information regarding copyright ownership.
# The ASF licenses this file to you under the Apache License, Version 2.0.

"""Report high-risk remaining Simplified Chinese translation entries."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PO_PATH = ROOT / "superset/translations/zh/LC_MESSAGES/messages.po"

# Product/UI English words that normally should not remain in a Chinese sentence.
# Technical terms intentionally allowed in Chinese UI are excluded from this list.
UI_ENGLISH = re.compile(
    r"\b(?:Select|Choose|Loading|Loaded|Failed|Failure|Success|Successful|"
    r"Create|Created|Delete|Deleted|Edit|Edited|Save|Saved|Cancel|Apply|Clear|"
    r"Search|Refresh|Run|Stop|Open|Close|Copy|Copied|Download|Upload|Import|Export|"
    r"User|Users|Role|Roles|Permission|Permissions|Chart|Charts|Dashboard|Dashboards|"
    r"Dataset|Datasets|Datasource|Datasources|Filter|Filters|Metric|Metrics|"
    r"Dimension|Dimensions|Column|Columns|Alert|Alerts|Report|Reports)\b",
    re.IGNORECASE,
)

TECHNICAL_EXACT = re.compile(
    r"^(?:SQL|JSON|CSV|Jinja|ECharts|MySQL|PostgreSQL|ClickHouse|Trino|Presto|"
    r"StarRocks|Hive|API|URL|URI|UUID|ID|DDL|DML|CTAS|CVAS|SELECT|FROM|WHERE|"
    r"GROUP BY|ORDER BY|LIMIT|NULL|TRUE|FALSE|OAuth2|GeoJSON|YAML|ZIP|PDF|PNG|JPG|"
    r"VARCHAR|BIGINT|INT|INTEGER|FLOAT|DOUBLE|DECIMAL|DATE|DATETIME|TIMESTAMP)(?:\b.*)?$",
    re.IGNORECASE,
)


def decode(token: str) -> str:
    return ast.literal_eval(token.strip())


def field(lines: list[str], name: str) -> str | None:
    prefix = f"{name} "
    for i, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        pieces = [decode(line[len(prefix):].rstrip("\r\n"))]
        i += 1
        while i < len(lines) and lines[i].startswith('"'):
            pieces.append(decode(lines[i].rstrip("\r\n")))
            i += 1
        return "".join(pieces)
    return None


def translations(lines: list[str]) -> list[str]:
    values: list[str] = []
    for key in ("msgstr", "msgstr[0]"):
        value = field(lines, key)
        if value is not None:
            values.append(value)
    return values


def is_fuzzy(lines: list[str]) -> bool:
    return any(line.startswith("#,") and "fuzzy" in line for line in lines)


def short(value: str, limit: int = 180) -> str:
    value = value.replace("\n", "\\n")
    return value if len(value) <= limit else value[: limit - 3] + "..."


def main() -> int:
    text = PO_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"\n{2,}", text)
    findings: dict[str, list[tuple[str, str]]] = {
        "fuzzy": [],
        "english_equal": [],
        "ui_english_in_zh": [],
        "empty": [],
    }

    for block in blocks:
        lines = block.splitlines(keepends=True)
        msgid = field(lines, "msgid")
        if not msgid:
            continue
        vals = translations(lines)
        if not vals:
            continue
        msgstr = vals[0]

        if is_fuzzy(lines):
            findings["fuzzy"].append((msgid, msgstr))

        if not msgstr.strip():
            findings["empty"].append((msgid, msgstr))
            continue

        if msgstr.strip() == msgid.strip() and re.search(r"[A-Za-z]", msgid):
            if not TECHNICAL_EXACT.match(msgid.strip()):
                findings["english_equal"].append((msgid, msgstr))

        if re.search(r"[\u4e00-\u9fff]", msgstr) and UI_ENGLISH.search(msgstr):
            findings["ui_english_in_zh"].append((msgid, msgstr))

    print("ZH_REMAINING_SUMMARY")
    for category, items in findings.items():
        print(f"{category}={len(items)}")

    # Print bounded, reviewable samples. Fuzzy is numerous, so prioritize entries
    # that also look suspicious (English-only/equal or short UI labels).
    for category in ("english_equal", "ui_english_in_zh", "empty"):
        print(f"\n[{category}]")
        for msgid, msgstr in findings[category][:200]:
            print(f"ID: {short(msgid)}")
            print(f"ZH: {short(msgstr)}")

    fuzzy_priority = [
        pair for pair in findings["fuzzy"]
        if len(pair[0]) <= 120 or pair in findings["english_equal"] or pair in findings["ui_english_in_zh"]
    ]
    print("\n[fuzzy_priority]")
    for msgid, msgstr in fuzzy_priority[:250]:
        print(f"ID: {short(msgid)}")
        print(f"ZH: {short(msgstr)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
