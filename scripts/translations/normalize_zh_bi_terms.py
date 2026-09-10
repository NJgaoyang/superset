# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Normalize legacy Simplified Chinese BI terminology by gettext context.

This is deliberately context-aware: replacements are only applied when the
English msgid identifies the corresponding Superset product concept. It keeps
technical identifiers and unrelated uses untouched while making the visible BI
terminology consistent across the catalog.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PO_PATH = ROOT / "superset/translations/zh/LC_MESSAGES/messages.po"

# Trigger substring in English gettext context -> legacy Chinese replacements.
RULES: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "dashboard",
        (
            ("仪表板", "仪表盘"),
            ("看板", "仪表盘"),
        ),
    ),
    (
        "sql lab",
        (
            ("SQL 工具箱", "SQL 工作台"),
            ("SQL工具箱", "SQL 工作台"),
            ("SQL 实验室", "SQL 工作台"),
            ("SQL实验室", "SQL 工作台"),
            ("SQL Lab", "SQL 工作台"),
        ),
    ),
    (
        "filter",
        (
            ("过滤器", "筛选器"),
            ("过滤", "筛选"),
        ),
    ),
    (
        "alert",
        (("警报", "告警"),),
    ),
    (
        "report",
        (("报告", "报表"),),
    ),
)


def decode_po_string(token: str) -> str:
    return ast.literal_eval(token.strip())


def field_value(lines: list[str], field: str) -> str | None:
    prefix = f"{field} "
    for start, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        pieces = [decode_po_string(line[len(prefix) :].rstrip("\r\n"))]
        index = start + 1
        while index < len(lines) and lines[index].startswith('"'):
            pieces.append(decode_po_string(lines[index].rstrip("\r\n")))
            index += 1
        return "".join(pieces)
    return None


def gettext_context(lines: list[str]) -> str:
    msgid = field_value(lines, "msgid") or ""
    plural = field_value(lines, "msgid_plural") or ""
    return f"{msgid}\n{plural}".lower()


def normalize_translation_lines(
    lines: list[str], replacements: tuple[tuple[str, str], ...]
) -> tuple[list[str], Counter[str]]:
    changed = Counter()
    in_translation = False
    result: list[str] = []

    for line in lines:
        if line.startswith("msgstr ") or line.startswith("msgstr["):
            in_translation = True
        elif in_translation and not line.startswith('"'):
            # A gettext field after msgstr is unusual, but stop defensively.
            if line.startswith("msgid") or line.startswith("msgctxt"):
                in_translation = False

        if in_translation:
            for old, new in replacements:
                occurrences = line.count(old)
                if occurrences:
                    line = line.replace(old, new)
                    changed[f"{old} -> {new}"] += occurrences
        result.append(line)

    return result, changed


def main() -> int:
    text = PO_PATH.read_text(encoding="utf-8")
    parts = re.split(r"(\n{2,})", text)
    total = Counter()
    changed_entries = 0

    for index in range(0, len(parts), 2):
        block = parts[index]
        lines = block.splitlines(keepends=True)
        context = gettext_context(lines)
        replacements: list[tuple[str, str]] = []
        for trigger, trigger_replacements in RULES:
            if trigger in context:
                replacements.extend(trigger_replacements)

        if not replacements:
            continue

        updated_lines, changed = normalize_translation_lines(lines, tuple(replacements))
        if changed:
            parts[index] = "".join(updated_lines)
            total.update(changed)
            changed_entries += 1

    if changed_entries:
        PO_PATH.write_text("".join(parts), encoding="utf-8")

    print(f"Normalized legacy BI terminology in {changed_entries} gettext entrie(s).")
    for rule, count in sorted(total.items()):
        print(f"  {rule}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
