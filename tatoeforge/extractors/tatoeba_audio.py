"""Tatoeba audio metadata parsing and optional download helpers."""

import csv
from datetime import datetime, timezone
import io
from pathlib import Path
import tarfile
from typing import Callable, Iterable, Optional, Set
import urllib.request

import pandas as pd


AUDIO_EXPORT_FILENAME = "sentences_with_audio.tar.bz2"
AUDIO_EXPORT_URL = f"https://downloads.tatoeba.org/exports/{AUDIO_EXPORT_FILENAME}"
AUDIO_DOWNLOAD_URL_TEMPLATE = "https://tatoeba.org/audio/download/{audio_id}"
AUDIO_COLUMNS = [
    "source",
    "audio_id",
    "sentence_id",
    "username",
    "license",
    "attribution_url",
    "download_url",
    "local_path",
    "downloaded_at",
    "status",
]


def is_reusable_audio_license(license_value: object) -> bool:
    """Return whether the Tatoeba license field permits reuse outside Tatoeba."""
    if pd.isna(license_value):
        return False
    value = "" if license_value is None else str(license_value).strip()
    return bool(value and value != r"\N")


def parse_audio_export(
    export_path: str,
    sentence_ids: Optional[Iterable[int]] = None,
) -> pd.DataFrame:
    """Parse Tatoeba's sentences_with_audio export into a DataFrame."""
    allowed_ids: Optional[Set[int]] = None
    if sentence_ids is not None:
        allowed_ids = {int(sentence_id) for sentence_id in sentence_ids}

    rows = []
    with tarfile.open(export_path, "r:bz2") as tar:
        members = [member for member in tar.getmembers() if member.isfile()]
        if not members:
            return pd.DataFrame(columns=AUDIO_COLUMNS)

        extracted = tar.extractfile(members[0])
        if extracted is None:
            return pd.DataFrame(columns=AUDIO_COLUMNS)

        text_stream = io.TextIOWrapper(extracted, encoding="utf-8", newline="")
        reader = csv.reader(text_stream, delimiter="\t")

        for row in reader:
            if not row or len(row) < 2:
                continue

            try:
                sentence_id = int(row[0])
            except ValueError:
                continue

            if allowed_ids is not None and sentence_id not in allowed_ids:
                continue

            audio_id = str(row[1]).strip()
            username = row[2].strip() if len(row) > 2 else ""
            license_value = row[3].strip() if len(row) > 3 else ""
            attribution_url = row[4].strip() if len(row) > 4 else ""

            rows.append(
                {
                    "source": "tatoeba",
                    "audio_id": audio_id,
                    "sentence_id": sentence_id,
                    "username": username or None,
                    "license": license_value or None,
                    "attribution_url": attribution_url or None,
                    "download_url": AUDIO_DOWNLOAD_URL_TEMPLATE.format(audio_id=audio_id),
                    "local_path": None,
                    "downloaded_at": None,
                    "status": "metadata",
                }
            )

    return pd.DataFrame(rows, columns=AUDIO_COLUMNS)


def download_audio_files(
    audio_df: pd.DataFrame,
    audio_dir: str,
    reusable_only: bool = True,
    urlretrieve: Callable[[str, str], object] = urllib.request.urlretrieve,
) -> pd.DataFrame:
    """Download audio files referenced by metadata rows."""
    result = audio_df.copy()
    if result.empty:
        return result

    base_dir = Path(audio_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    for index, row in result.iterrows():
        if reusable_only and not is_reusable_audio_license(row.get("license")):
            result.at[index, "status"] = "skipped_license"
            continue

        source = str(row.get("source") or "tatoeba")
        audio_id = str(row["audio_id"])
        target_dir = base_dir / source
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{audio_id}.mp3"

        try:
            if not target_path.exists():
                urlretrieve(str(row["download_url"]), str(target_path))
            result.at[index, "local_path"] = str(target_path)
            result.at[index, "downloaded_at"] = datetime.now(timezone.utc).isoformat()
            result.at[index, "status"] = "downloaded"
        except Exception:
            result.at[index, "local_path"] = None
            result.at[index, "downloaded_at"] = None
            result.at[index, "status"] = "download_error"

    return result
