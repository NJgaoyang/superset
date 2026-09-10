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

"""Apply BI-oriented Simplified Chinese terminology overrides.

The upstream ``messages.po`` catalog remains the source of truth. This script
changes only matching translation fields (and removes ``fuzzy`` for changed
entries) so Git diffs remain small and future upstream merges stay reviewable.
It supports both single-line and wrapped/multiline gettext ``msgid`` entries.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PO = ROOT / "superset/translations/zh/LC_MESSAGES/messages.po"
DEFAULT_OVERRIDES = Path(__file__).with_name("zh_bi_overrides.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--po", type=Path, default=DEFAULT_PO)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Do not fail when an override msgid is absent from the catalog.",
    )
    return parser.parse_args()


def po_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\t", "\\t")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def decode_po_string(token: str) -> str:
    """Decode one gettext quoted string using Python-compatible escapes."""
    return ast.literal_eval(token.strip())


def field_value(lines: list[str], field: str) -> tuple[str, int, int] | None:
    """Return decoded field value and [start, end) line span for a PO field."""
    prefix = f"{field} "
    for start, line in enumerate(lines):
        if not line.startswith(prefix):
            continue

        pieces = [decode_po_string(line[len(prefix) :].rstrip("\r\n"))]
        end = start + 1
        while end < len(lines) and lines[end].startswith('"'):
            pieces.append(decode_po_string(lines[end].rstrip("\r\n")))
            end += 1
        return "".join(pieces), start, end
    return None


def remove_fuzzy_flag(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        if not line.startswith("#,"):
            result.append(line)
            continue

        newline = "\n" if line.endswith("\n") else ""
        flags = [flag.strip() for flag in line[2:].strip().split(",") if flag.strip()]
        flags = [flag for flag in flags if flag != "fuzzy"]
        if flags:
            result.append(f"#, {', '.join(flags)}{newline}")
    return result


def patch_entry(block: str, expected_msgid: str, translated: str) -> tuple[str, bool, bool]:
    """Patch one entry, returning (updated, matched_msgid, changed)."""
    lines = block.splitlines(keepends=True)
    msgid_field = field_value(lines, "msgid")
    if msgid_field is None or msgid_field[0] != expected_msgid:
        return block, False, False

    # Avoid plural entries: this override layer intentionally handles ordinary
    # UI strings only so plural rules remain owned by the upstream catalog.
    if field_value(lines, "msgid_plural") is not None:
        return block, True, False

    msgstr_field = field_value(lines, "msgstr")
    if msgstr_field is None:
        return block, True, False

    current, start, end = msgstr_field
    has_fuzzy = any(
        line.startswith("#,") and "fuzzy" in {f.strip() for f in line[2:].split(",")}
        for line in lines
    )
    if current == translated and not has_fuzzy:
        return block, True, False

    newline = "\n" if lines[start].endswith("\n") else ""
    lines[start:end] = [f'msgstr "{po_escape(translated)}"{newline}']
    lines = remove_fuzzy_flag(lines)
    return "".join(lines), True, True


def main() -> int:
    args = parse_args()
    overrides: dict[str, str] = json.loads(args.overrides.read_text(encoding="utf-8"))
    text = args.po.read_text(encoding="utf-8")

    # Keep blank-line separators as independent elements so untouched PO entries
    # remain byte-for-byte identical.
    parts = re.split(r"(\n{2,})", text)
    changed = 0
    missing: list[str] = []

    for msgid, translated in overrides.items():
        matched = False
        for index in range(0, len(parts), 2):
            updated, entry_matched, entry_changed = patch_entry(
                parts[index], msgid, translated
            )
            if not entry_matched:
                continue
            matched = True
            if entry_changed:
                parts[index] = updated
                changed += 1
            break

        if not matched:
            missing.append(msgid)

    if missing:
        print("Missing override msgids:")
        for msgid in missing:
            print(f"  - {msgid}")
        if not args.allow_missing:
            return 1

    if changed:
        args.po.write_text("".join(parts), encoding="utf-8")

    print(f"Applied {changed} Chinese BI translation override(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
