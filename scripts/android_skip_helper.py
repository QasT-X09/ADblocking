#!/usr/bin/env python3
"""ADB helper to find and tap likely "skip" buttons on Android.

This utility is intended for personal automation/testing on your own device.
It uses `adb shell uiautomator dump` and parses UI XML for clickable nodes
that match configurable skip keywords.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable, Sequence

DEFAULT_KEYWORDS = [
    "skip",
    "пропустить",
    "skip ad",
    "skip ads",
    "close",
    "закрыть",
]


@dataclass
class UiNode:
    text: str
    resource_id: str
    clickable: bool
    bounds: str

    @property
    def center(self) -> tuple[int, int]:
        # bounds format: [x1,y1][x2,y2]
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", self.bounds)
        if not m:
            raise ValueError(f"Unexpected bounds: {self.bounds!r}")
        x1, y1, x2, y2 = map(int, m.groups())
        return ((x1 + x2) // 2, (y1 + y2) // 2)


def run_adb(args: Sequence[str], serial: str | None = None) -> str:
    cmd = ["adb"]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ADB command failed ({' '.join(cmd)}):\n{proc.stderr.strip()}"
        )
    return proc.stdout


def load_ui_xml(serial: str | None = None) -> str:
    run_adb(["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], serial=serial)
    return run_adb(["shell", "cat", "/sdcard/window_dump.xml"], serial=serial)


def parse_nodes(xml_text: str) -> Iterable[UiNode]:
    root = ET.fromstring(xml_text)
    for node in root.iter("node"):
        yield UiNode(
            text=(node.attrib.get("text") or "").strip(),
            resource_id=(node.attrib.get("resource-id") or "").strip(),
            clickable=(node.attrib.get("clickable") == "true"),
            bounds=(node.attrib.get("bounds") or ""),
        )


def is_match(node: UiNode, keywords: Sequence[str]) -> bool:
    hay = f"{node.text} {node.resource_id}".lower()
    return node.clickable and any(kw.lower() in hay for kw in keywords)


def tap(serial: str | None, x: int, y: int) -> None:
    run_adb(["shell", "input", "tap", str(x), str(y)], serial=serial)


def run_loop(
    interval_s: float,
    keywords: Sequence[str],
    dry_run: bool,
    serial: str | None,
    max_taps: int,
) -> int:
    taps = 0
    while max_taps <= 0 or taps < max_taps:
        try:
            xml_text = load_ui_xml(serial=serial)
            candidates = [n for n in parse_nodes(xml_text) if is_match(n, keywords)]
            if candidates:
                node = candidates[0]
                x, y = node.center
                if dry_run:
                    print(f"[DRY RUN] Match: text={node.text!r}, id={node.resource_id!r}, tap=({x},{y})")
                else:
                    tap(serial, x, y)
                    print(f"Tapped {x},{y} -> text={node.text!r}, id={node.resource_id!r}")
                taps += 1
            else:
                print("No skip-like button found on current screen")
            time.sleep(interval_s)
        except KeyboardInterrupt:
            print("Stopped by user")
            break
        except Exception as exc:  # keep loop running for transient ADB/UI issues
            print(f"Warning: {exc}", file=sys.stderr)
            time.sleep(interval_s)
    return taps


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ADB UI automation helper for tapping skip/close buttons"
    )
    p.add_argument("--serial", help="ADB device serial (if multiple devices)")
    p.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)",
    )
    p.add_argument(
        "--keyword",
        action="append",
        default=None,
        help="Keyword to match clickable elements. Can be repeated.",
    )
    p.add_argument(
        "--max-taps",
        type=int,
        default=0,
        help="Stop after N taps (0 = infinite until Ctrl+C)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print tap coordinates, do not tap",
    )
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    keywords = args.keyword or DEFAULT_KEYWORDS
    print(f"Using keywords: {keywords}")
    taps = run_loop(
        interval_s=args.interval,
        keywords=keywords,
        dry_run=args.dry_run,
        serial=args.serial,
        max_taps=args.max_taps,
    )
    print(f"Done. taps={taps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
