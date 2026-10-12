#!/usr/bin/env python3
"""Build an offline keyboard lexicon from the pinned Apache-2.0 Rime dictionary."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vendor/pinyin-simp"
provenance = json.loads((SOURCE / "UPSTREAM.json").read_text())
data = (SOURCE / "pinyin_simp.dict.yaml").read_bytes()
assert hashlib.sha256(data).hexdigest() == provenance["files_sha256"]["pinyin_simp.dict.yaml"]
entries = {}
for line in data.decode().splitlines():
    parts = line.split("\t")
    if len(parts) != 3:
        continue
    word, syllables, frequency = parts
    code = syllables.replace(" ", "").replace("ü", "v")
    if not re.fullmatch("[a-z]+", code) or len(code) > 32:
        continue
    if not word or not frequency.isdigit():
        continue
    key = (code, word)
    value = (int(frequency), syllables.replace(" ", "'").replace("ü", "v"))
    if key not in entries or entries[key][0] < value[0]:
        entries[key] = value

destination = ROOT / "Keyboard/Resources"
destination.mkdir(parents=True, exist_ok=True)
header = ("# Derived from rime/rime-pinyin-simp; Apache-2.0.\n"
          "# Modified: spaces removed from pinyin; duplicates merged; maximum code length 32.\n"
          f"# Source commit: {provenance['commit']}\n")
(destination / "pinyin.tsv").write_text(header + "".join(
    f"{code}\t{word}\t{weight}\t{spelling}\n" for (code, word), (weight, spelling) in sorted(entries.items())
))
notice = ("Offline Pinyin Dictionary\n\n"
          "Derived from rime/rime-pinyin-simp / Android Open Source Project Pinyin IME.\n"
          f"Source: {provenance['repository']}\nCommit: {provenance['commit']}\n\n"
          "Modified for this project: pinyin separators removed, duplicates merged, "
          "codes longer than 32 characters excluded. The dictionary retains its "
          "Apache License 2.0; the original keyboard engine is not bundled.\n\n"
          + (SOURCE / "AUTHORS").read_text() + "\n" + (SOURCE / "LICENSE").read_text())
(destination / "Pinyin-LICENSE.txt").write_text(notice)
print(f"Built offline Pinyin dictionary: {len(entries):,} entries")
