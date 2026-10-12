"""Build a read-only, self-contained preview from the public snapshot projections."""

import argparse
import json
import re
from pathlib import Path

from apps.api.config import Settings
from packages.data.snapshot import load_snapshot

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "apps/web/static"


def export_sample():
    settings = Settings()
    snapshot = load_snapshot(settings.data_root, settings.manifest_path)
    selected = snapshot.companies[:8]
    records = [
        record for company in selected for record in snapshot.histories[company.id_badan_usaha]
    ]
    info = snapshot.info.model_dump(mode="json")
    info["company_count"] = len(selected)
    info["evidence_record_count"] = len(records)
    sample = {
        "scope": "READ_ONLY_SAMPLE",
        "source_company_count": snapshot.info.company_count,
        "meta": snapshot.ref.model_dump(mode="json"),
        "info": info,
        "companies": [company.model_dump(mode="json") for company in selected],
        "evidence": [record.model_dump(mode="json") for record in records],
    }
    content = json.dumps(sample, ensure_ascii=False, separators=(",", ":"))
    (STATIC / "sample.mjs").write_text("export const SAMPLE = " + content + ";\n", encoding="utf-8")


def bundle():
    modules = ["domain.mjs", "api.mjs", "demo.mjs", "sample.mjs", "views.mjs", "app.mjs"]
    parts = []
    for name in modules:
        text = (STATIC / name).read_text(encoding="utf-8")
        text = re.sub(r"^import .*?;\n", "", text, flags=re.MULTILINE | re.DOTALL)
        text = re.sub(r"^export (?=(const|function|class)\b)", "", text, flags=re.MULTILINE)
        parts.append(text)
    code = "window.JAGA_PREVIEW = true;\n" + "\n".join(parts)
    code = code.replace("</script", "<\\/script")
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    html = html.replace(
        '<link rel="stylesheet" href="/assets/styles.css">', "<style>" + css + "</style>"
    )
    html = re.sub(r'  <link rel="icon"[^>]*>\n', "", html)
    html = html.replace(
        '<script type="module" src="/assets/app.mjs"></script>',
        '<script type="module">\n' + code + "\n</script>",
    )
    out = ROOT / "apps/web/dist/JAGA_JKN_frontend_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-sample", action="store_true")
    args = parser.parse_args()
    if args.refresh_sample:
        export_sample()
    if (STATIC / "views.mjs").exists() and (STATIC / "app.mjs").exists():
        bundle()
