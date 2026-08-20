#!/usr/bin/env python3
"""Build dashboard.html by injecting data/analysis.json into dashboard.template.html.

Usage: python3 scripts/build_dashboard.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
template = (ROOT / "dashboard.template.html").read_text()
data = json.loads((ROOT / "data" / "analysis.json").read_text())

# Compact JSON, escaped so it can never terminate the surrounding <script> block.
payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

out = template.replace("__ANALYSIS_DATA__", payload)
(ROOT / "dashboard.html").write_text(out)
print(f"wrote dashboard.html ({len(out):,} bytes, {len(data['symbols'])} symbols)")
