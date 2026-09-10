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

"""Audit the zh-CN catalog for the BI terminology contract used by this fork."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PO_PATH = ROOT / "superset/translations/zh/LC_MESSAGES/messages.po"

CONTEXT_FORBIDDEN: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dashboard", ("看板", "仪表板")),
    ("sql lab", ("SQL工具箱", "SQL 工具箱", "SQL实验室", "SQL 实验室", "SQL Lab")),
    ("filter", ("过滤器", "过滤")),
    ("alert", ("警报",)),
    ("report", ("报告",)),
)

EXPECTED: dict[str, str] = {
    "Database": "数据库",
    "Databases": "数据库",
    "Database Connections": "数据库连接",
    "Datasource": "数据源",
    "Datasources": "数据源",
    "Dataset": "数据集",
    "Datasets": "数据集",
    "Chart": "图表",
    "Charts": "图表",
    "Dashboard": "仪表盘",
    "Dashboards": "仪表盘",
    "Explore": "图表编辑",
    "SQL Lab": "SQL 工作台",
    "Filter": "筛选器",
    "Filters": "筛选器",
    "Alert": "告警",
    "Alerts": "告警",
    "Reports": "报表",
    "Security": "权限管理",
    "List Users": "用户管理",
    "List Roles": "角色管理",
    "%s hr ago": "%s 小时前",
    "%s record...": "%s 条记录...",
}


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


def translation_value(lines: list[str]) -> str | None:
    if field_value(lines, "msgid_plural") is not None:
        return field_value(lines, "msgstr[0]")
    return field_value(lines, "msgstr")


def main() -> int:
    text = PO_PATH.read_text(encoding="utf-8")
    parts = re.split(r"\n{2,}", text)
    failures: list[str] = []
    seen_expected: set[str] = set()

    for block in parts:
        lines = block.splitlines(keepends=True)
        msgid = field_value(lines, "msgid")
        if not msgid:
            continue
        plural = field_value(lines, "msgid_plural") or ""
        translation = translation_value(lines)
        if translation is None:
            continue

        context = f"{msgid}\n{plural}".lower()
        for trigger, forbidden_terms in CONTEXT_FORBIDDEN:
            if trigger not in context:
                continue
            for forbidden in forbidden_terms:
                if forbidden in translation:
                    failures.append(
                        f"{msgid!r}: contains legacy term {forbidden!r} in {translation!r}"
                    )

        expected = EXPECTED.get(msgid)
        if expected is not None:
            seen_expected.add(msgid)
            if translation != expected:
                failures.append(
                    f"{msgid!r}: expected {expected!r}, found {translation!r}"
                )

        if "select一个" in translation or "select 一个" in translation:
            failures.append(f"{msgid!r}: contains mixed-language select wording")

    missing = sorted(set(EXPECTED) - seen_expected)
    # Some strings are version-dependent. Missing entries are informational;
    # mismatched entries that do exist are the contract violation.
    if missing:
        print("BI audit: version-dependent expected msgids not present:")
        for msgid in missing:
            print(f"  - {msgid}")

    if failures:
        print("BI terminology audit failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("BI terminology audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
