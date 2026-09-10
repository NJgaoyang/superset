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
changes only the matching ``msgstr`` lines (and removes ``fuzzy`` for those
entries) so Git diffs remain small and future upstream merges stay reviewable.
"""

from __future__ import annotations

import argparse
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


def remove_fuzzy_flag(block: str) -> str:
    lines = block.splitlines(keepends=True)
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
    return "".join(result)


def replace_translation(block: str, translated: str) -> tuple[str, bool]:
    pattern = re.compile(
        r'(?m)^msgstr "(?:\\.|[^"\\])*"(?:\n"(?:\\.|[^"\\])*")*'
    )
    match = pattern.search(block)
    if match is None:
        return block, False

    replacement = f'msgstr "{po_escape(translated)}"'
    updated = block[: match.start()] + replacement + block[match.end() :]
    updated = remove_fuzzy_flag(updated)
    return updated, updated != block


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
        target = f'msgid "{po_escape(msgid)}"'
        matched = False

        for index in range(0, len(parts), 2):
            block = parts[index]
            if not re.search(rf"(?m)^{re.escape(target)}$", block):
                continue

            matched = True
            updated, entry_changed = replace_translation(block, translated)
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
