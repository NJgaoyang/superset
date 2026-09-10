# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file distributed
# with this work for additional information regarding copyright ownership.
# The ASF licenses this file to you under the Apache License, Version 2.0.

"""Freeze one completed human review pass of the zh-CN fuzzy queue.

This is intentionally one-shot: once ``zh_release_review_overrides.json``
exists, future master changes are NOT auto-accepted. New fuzzy entries remain in
``zh_fuzzy_review_queue.json`` until another explicit review pass is performed.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "scripts/translations/zh_fuzzy_review_queue.json"
CORRECTIONS_PATH = ROOT / "scripts/translations/zh_release_review_corrections.json"
OUTPUT_PATH = ROOT / "scripts/translations/zh_release_review_overrides.json"

PRINTF = re.compile(
    r"%\([^)]+\)[#0\- +]?\d*(?:\.\d+)?[a-zA-Z]"
    r"|%(?:\d+\$)?[#0\- +]?\d*(?:\.\d+)?[sdif]"
)


def placeholders(value: str) -> Counter[str]:
    return Counter(PRINTF.findall(value))


def main() -> int:
    if OUTPUT_PATH.exists():
        print(
            "Release review override snapshot already exists; "
            "new fuzzy entries will remain pending review."
        )
        return 0

    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    corrections = json.loads(CORRECTIONS_PATH.read_text(encoding="utf-8"))

    by_id: dict[str, str] = {}
    duplicates: list[str] = []
    for item in queue:
        msgid = item["msgid"]
        msgstr = item["msgstr"]
        if msgid in by_id:
            duplicates.append(msgid)
        by_id[msgid] = msgstr

    if duplicates:
        print("Duplicate msgids in review queue:")
        for msgid in sorted(set(duplicates)):
            print(f"  - {msgid}")
        return 1

    unknown = sorted(set(corrections) - set(by_id))
    if unknown:
        print("Release-review corrections not present in the current fuzzy queue:")
        for msgid in unknown:
            print(f"  - {msgid}")
        return 1

    reviewed = {
        msgid: corrections.get(msgid, msgstr)
        for msgid, msgstr in by_id.items()
    }

    incompatible: list[tuple[str, Counter[str], Counter[str]]] = []
    for msgid, msgstr in reviewed.items():
        expected = placeholders(msgid)
        actual = placeholders(msgstr)
        if expected != actual:
            incompatible.append((msgid, expected, actual))

    if incompatible:
        print("Placeholder incompatibilities found during release review:")
        for msgid, expected, actual in incompatible:
            print(f"  - {msgid}")
            print(f"      source: {dict(expected)}")
            print(f"      target: {dict(actual)}")
        return 1

    OUTPUT_PATH.write_text(
        json.dumps(reviewed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Frozen {len(reviewed)} reviewed fuzzy entries; "
        f"{len(corrections)} received explicit translation corrections."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
