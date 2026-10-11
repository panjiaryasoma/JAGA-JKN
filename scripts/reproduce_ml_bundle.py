"""Replay a frozen handoff in a fresh directory; retain full logs and exact comparisons."""

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    archive = ROOT / "artifacts/jaga-jkn-ml-handoff.zip"
    OUT.mkdir(parents=True, exist_ok=True)
    log_path = OUT / "logs/clean_reproduction.txt"
    log_path.parent.mkdir(exist_ok=True)
    record = {
        "started_utc": datetime.now(UTC).isoformat(),
        "archive_sha256": digest(archive),
        "model_before_sha256": digest(ROOT / "models/best_model.pkl"),
        "settings_changed": False,
        "threshold_retuned": False,
        "commands": [],
    }
    with tempfile.TemporaryDirectory(prefix="jaga-ml-reproduce-", dir=ROOT.parent) as directory:
        folder = Path(directory)
        with zipfile.ZipFile(archive) as handle:
            for name in handle.namelist():
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError("Unsafe archive path")
            handle.extractall(folder)
        checksums = json.loads((folder / "CHECKSUMS.json").read_text())
        for name, expected in checksums.items():
            if digest(folder / name) != expected:
                raise ValueError(f"Archive checksum mismatch: {name}")
        record["verified_archive_files"] = len(checksums)
        commands = [
            [
                "uv",
                "sync",
                "--locked",
                "--group",
                "ml",
                "--python",
                f"{sys.version_info.major}.{sys.version_info.minor}",
            ],
            ["uv", "run", "--no-sync", "python", "-m", "pipelines.training"],
        ]
        with log_path.open("w") as log:
            for command in commands:
                print("Clean reproduction: " + " ".join(command), flush=True)
                log.write("$ " + " ".join(command) + "\n")
                log.flush()
                result = subprocess.run(
                    command, cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=False
                )
                record["commands"].append({"command": command, "exit_code": result.returncode})
                if result.returncode:
                    raise RuntimeError(f"Reproduction failed; see {log_path}")
        compared = [
            "models/best_model.pkl",
            "models/example_output.json",
            "results/benchmarks/group_time.json",
            "results/benchmarks/group_time_predictions.csv",
            "results/benchmarks/company_holdout.json",
            "results/benchmarks/company_holdout_predictions.csv",
        ]
        record["comparisons"] = {
            name: {
                "expected_sha256": digest(ROOT / name),
                "reproduced_sha256": digest(folder / name),
                "exact_bytes_match": (ROOT / name).read_bytes() == (folder / name).read_bytes(),
            }
            for name in compared
        }
        mismatches = {
            name: values
            for name, values in record["comparisons"].items()
            if not values["exact_bytes_match"]
        }
        if mismatches:
            for name, values in mismatches.items():
                print(
                    f"Reproduction mismatch: {name}; expected="
                    f"{values['expected_sha256']}; reproduced="
                    f"{values['reproduced_sha256']}",
                    flush=True,
                )
            raise ValueError(
                "Reproduction mismatch in: " + ", ".join(sorted(mismatches))
            )
    record.update(
        status="PASSED",
        finished_utc=datetime.now(UTC).isoformat(),
        log_sha256=digest(log_path),
        model_after_sha256=digest(ROOT / "models/best_model.pkl"),
    )
    if record["model_before_sha256"] != record["model_after_sha256"]:
        raise ValueError("Frozen model changed")
    (OUT / "clean_reproduction.json").write_text(json.dumps(record, indent=2) + "\n")
    print("PASS: 6 exact file comparisons; frozen model unchanged", flush=True)


if __name__ == "__main__":
    main()
