"""
Downloads the real, public "Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016"
(Furberg, Brinton, Keating, Ortiz — RTI International), hosted on Zenodo under
CC-BY-4.0, no login required.

Source record: https://zenodo.org/records/53894

This script:
  1. Downloads both export zips.
  2. Verifies their published MD5 checksums.
  3. Extracts the small per-user/per-day/per-hour CSVs into data/raw/ (these
     are committed to git — a few KB to ~9MB each).
  4. Leaves the large minute/second-level files in data/raw_large/ (gitignored,
     tens/hundreds of MB) for scripts/aggregate_heartrate.py to consume.

Nothing here is synthetic. Every row in data/raw/ came from this download.
"""
import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW_LARGE = ROOT / "data" / "raw_large"
DOWNLOAD_DIR = RAW / "_download"

FILES = {
    "export1.zip": (
        "https://zenodo.org/records/53894/files/mturkfitbit_export_3.12.16-4.11.16.zip?download=1",
        "88a4396c5ff706b7eaed030de4c53588",
    ),
    "export2.zip": (
        "https://zenodo.org/records/53894/files/mturkfitbit_export_4.12.16-5.12.16.zip?download=1",
        "7afbecdce29814e1be2e9a7c94f8f165",
    ),
}

SMALL_FILES = [
    "dailyActivity_merged.csv",
    "hourlyCalories_merged.csv",
    "hourlyIntensities_merged.csv",
    "hourlySteps_merged.csv",
    "minuteSleep_merged.csv",
    "weightLogInfo_merged.csv",
    "sleepDay_merged.csv",  # only present in export2
]


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RAW_LARGE.mkdir(parents=True, exist_ok=True)

    for prefix, (zip_name, (url, expected_md5)) in zip(("p1", "p2"), FILES.items()):
        zip_path = DOWNLOAD_DIR / zip_name
        if not zip_path.exists():
            print(f"Downloading {url} ...")
            urllib.request.urlretrieve(url, zip_path)
        actual_md5 = md5sum(zip_path)
        assert actual_md5 == expected_md5, f"Checksum mismatch for {zip_name}: {actual_md5} != {expected_md5}"
        print(f"{zip_name}: MD5 verified ({actual_md5})")

        extract_dir = DOWNLOAD_DIR / prefix
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        inner_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        assert len(inner_dirs) == 1, f"Unexpected zip layout in {zip_name}"
        inner = inner_dirs[0]

        for fname in SMALL_FILES:
            src = inner / fname
            if src.exists():
                dst = RAW / f"{prefix}_{fname}"
                shutil.copyfile(src, dst)
                print(f"  -> {dst.relative_to(ROOT)}")

        hr_src = inner / "heartrate_seconds_merged.csv"
        if hr_src.exists():
            hr_dst = RAW_LARGE / f"heartrate_seconds_{prefix}.csv"
            shutil.copyfile(hr_src, hr_dst)
            print(f"  -> {hr_dst.relative_to(ROOT)} (large, gitignored)")

    print("\nDone. Run scripts/aggregate_heartrate.py next.")


if __name__ == "__main__":
    main()
