# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file distributed
# with this work for additional information regarding copyright ownership.
# The ASF licenses this file to you under the Apache License, Version 2.0.

"""Build a review queue for upstream machine-translated zh-CN entries.

Entries already covered by the frozen fuzzy review snapshot are excluded, so
this queue represents the remaining machine-translated text that still needs an
explicit release-quality review pass.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PO_PATH = ROOT / "superset/translations/zh/LC_MESSAGES/messages.po"
FUZZY_REVIEW_PATH = ROOT / "scripts/translations/zh_release_review_overrides.json"
OUTPUT_PATH = ROOT / "scripts/translations/zh_machine_review_queue.json"
MARKER = "Machine-translated via backfill_po.py"


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


def main() -> int:
    reviewed = {}
    if FUZZY_REVIEW_PATH.exists():
        reviewed = json.loads(FUZZY_REVIEW_PATH.read_text(encoding="utf-8"))

    text = PO_PATH.read_text(encoding="utf-8")
    queue: list[dict[str, str]] = []
    for block in re.split(r"\n{2,}", text):
        if MARKER not in block:
            continue
        lines = block.splitlines(keepends=True)
        msgid = field(lines, "msgid")
        if not msgid or msgid in reviewed:
            continue
        plural = field(lines, "msgid_plural")
        msgstr = field(lines, "msgstr[0]") if plural is not None else field(lines, "msgstr")
        if msgstr is None:
            continue
        queue.append({"msgid": msgid, "msgstr": msgstr})

    OUTPUT_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"machine_review_pending={len(queue)}")
    print(f"machine_review_queue={OUTPUT_PATH.relative_to(ROOT)}")
    for item in queue[:100]:
        print(f"ID: {item['msgid'][:180].replace(chr(10), ' ')}")
        print(f"ZH: {item['msgstr'][:180].replace(chr(10), ' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
