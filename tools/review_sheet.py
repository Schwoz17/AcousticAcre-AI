"""Native-speaker review loop for language packs.

  Export a sheet (open in Excel / Google Sheets, fill the "corrected" column, leave blank if fine):
      python tools/review_sheet.py export ha            -> review_ha.csv
  Import it back; marks the pack reviewed and records the reviewer:
      python tools/review_sheet.py import ha review_ha.csv --name "Amina Musa" --role "farmer, native speaker"

The gateway and app only ship packs with "reviewed": true.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "content" / "phrases"
SECTIONS = ("ui", "crops", "questions", "diagnoses", "steps")


def text_of(sec, v):
    return v["name"] if sec == "diagnoses" else v["text"] if sec == "steps" else v


def export(lang, out):
    en = json.loads((ROOT / "en.json").read_text(encoding="utf-8"))
    tr = json.loads((ROOT / f"{lang}.json").read_text(encoding="utf-8"))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel shows accents correctly
        w = csv.writer(f)
        w.writerow(["section", "id", "english", "draft", "corrected", "comment"])
        for sec in SECTIONS:
            for k, v in en[sec].items():
                w.writerow([sec, k, text_of(sec, v), text_of(sec, tr[sec][k]), "", ""])
    print(f"wrote {out}: give it to the {tr['lang_name']} reviewer. Keep {{n}} and {{option}} as they are.")


def import_(lang, sheet, name, role):
    p = ROOT / f"{lang}.json"
    tr = json.loads(p.read_text(encoding="utf-8"))
    changed = 0
    with open(sheet, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            new = (row.get("corrected") or "").strip()
            if not new:
                continue
            sec, k = row["section"], row["id"]
            if sec == "diagnoses":
                tr[sec][k]["name"] = new
            elif sec == "steps":
                tr[sec][k]["text"] = new
            else:
                tr[sec][k] = new
            changed += 1
    if "{n}" not in tr["ui"]["press_option"] or "{option}" not in tr["ui"]["press_option"]:
        raise SystemExit("press_option lost {n} or {option}; fix the sheet and re-import")
    tr.update(reviewed=True, version=tr["version"].replace("-draft", ""),
              reviewer={"name": name, "date": date.today().isoformat(), "role": role})
    tr.pop("draft_note", None)
    p.write_text(json.dumps(tr, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{lang}: {changed} corrections applied; marked reviewed by {name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "import"])
    ap.add_argument("lang")
    ap.add_argument("sheet", nargs="?")
    ap.add_argument("--name", default="")
    ap.add_argument("--role", default="native speaker")
    a = ap.parse_args()
    if a.cmd == "export":
        export(a.lang, a.sheet or f"review_{a.lang}.csv")
    else:
        if not a.sheet or not a.name:
            raise SystemExit("import needs the sheet path and --name of the reviewer")
        import_(a.lang, a.sheet, a.name, a.role)
