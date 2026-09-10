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

This keeps the upstream ``messages.po`` catalog as the source of truth while
allowing this fork to maintain a small, reviewable terminology layer.  The
script updates exact msgids only, removes ``fuzzy`` from changed entries, and
fails when an override no longer exists upstream so upgrades cannot silently
lose important terminology.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polib

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


def main() -> int:
    args = parse_args()
    overrides: dict[str, str] = json.loads(args.overrides.read_text(encoding="utf-8"))
    catalog = polib.pofile(args.po)

    changed = 0
    missing: list[str] = []

    for msgid, translated in overrides.items():
        entry = catalog.find(msgid)
        if entry is None:
            missing.append(msgid)
            continue

        entry_changed = entry.msgstr != translated or "fuzzy" in entry.flags
        if entry_changed:
            entry.msgstr = translated
            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
            changed += 1

    if missing:
        print("Missing override msgids:")
        for msgid in missing:
            print(f"  - {msgid}")
        if not args.allow_missing:
            return 1

    if changed:
        catalog.save(args.po)

    print(f"Applied {changed} Chinese BI translation override(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
