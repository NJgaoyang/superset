# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file distributed
# with this work for additional information regarding copyright ownership.
# The ASF licenses this file to you under the Apache License, Version 2.0.

"""Release-quality checks for the Simplified Chinese gettext catalog."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PO_PATH = ROOT / "superset/translations/zh/LC_MESSAGES/messages.po"

PRINTF = re.compile(
    r"%\([^)]+\)[#0\- +]?\d*(?:\.\d+)?[a-zA-Z]"
    r"|%(?:\d+\$)?[#0\- +]?\d*(?:\.\d+)?[sdif]"
)

# These are legacy/product wording regressions or characteristic machine-
# translation artifacts that must never ship in the release-quality catalog.
BANNED_ZH = (
    "看板",
    "仪表板",
    "SQL工具箱",
    "SQL 工具箱",
    "SQL实验室",
    "过滤器",
    "警报",
    "select一个",
    "other值",
    "超级集",
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


def has_fuzzy(lines: list[str]) -> bool:
    return any(
        line.startswith("#,")
        and "fuzzy" in {flag.strip() for flag in line[2:].split(",")}
        for line in lines
    )


def placeholders(value: str) -> Counter[str]:
    return Counter(PRINTF.findall(value))


def main() -> int:
    text = PO_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"\n{2,}", text)

    fuzzy: list[str] = []
    empty: list[str] = []
    placeholder_errors: list[tuple[str, Counter[str], Counter[str]]] = []
    banned: list[tuple[str, str]] = []

    for block in blocks:
        lines = block.splitlines(keepends=True)
        msgid = field(lines, "msgid")
        if not msgid:
            continue

        plural = field(lines, "msgid_plural")
        msgstr = field(lines, "msgstr[0]") if plural is not None else field(lines, "msgstr")
        if msgstr is None:
            continue

        if has_fuzzy(lines):
            fuzzy.append(msgid)

        if not msgstr.strip():
            empty.append(msgid)

        # Chinese has one plural form. Source singular/plural forms should use
        # the same printf variables in Superset; accept either source form to
        # avoid false positives from grammar-only plural changes.
        target_ph = placeholders(msgstr)
        source_candidates = {tuple(sorted(placeholders(msgid).items()))}
        if plural is not None:
            source_candidates.add(tuple(sorted(placeholders(plural).items())))
        target_tuple = tuple(sorted(target_ph.items()))
        if target_tuple not in source_candidates:
            placeholder_errors.append((msgid, placeholders(msgid), target_ph))

        for bad in BANNED_ZH:
            if bad in msgstr:
                banned.append((msgid, bad))

    problems = len(fuzzy) + len(empty) + len(placeholder_errors) + len(banned)
    print("ZH_RELEASE_QUALITY")
    print(f"fuzzy={len(fuzzy)}")
    print(f"empty={len(empty)}")
    print(f"placeholder_errors={len(placeholder_errors)}")
    print(f"banned_terms={len(banned)}")

    if fuzzy:
        print("\nRemaining fuzzy entries:")
        for msgid in fuzzy[:50]:
            print(f"  - {msgid[:220]}")
    if empty:
        print("\nEmpty translations:")
        for msgid in empty[:50]:
            print(f"  - {msgid[:220]}")
    if placeholder_errors:
        print("\nPlaceholder mismatches:")
        for msgid, expected, actual in placeholder_errors[:50]:
            print(f"  - {msgid[:180]}")
            print(f"      source={dict(expected)} target={dict(actual)}")
    if banned:
        print("\nBanned legacy/machine wording:")
        for msgid, bad in banned[:50]:
            print(f"  - {bad!r} in {msgid[:180]}")

    if problems:
        print(f"\nRelease-quality audit failed with {problems} finding(s).")
        return 1

    print("Release-quality zh-CN audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
