"""Tests for Tatoeba audio metadata parsing."""

from pathlib import Path
import tarfile
import tempfile
import unittest

from tatoeforge.extractors.tatoeba_audio import download_audio_files, parse_audio_export


class TestTatoebaAudio(unittest.TestCase):
    """Test Tatoeba audio metadata helpers."""

    def _write_audio_export(self, directory: str) -> Path:
        export_path = Path(directory) / "sentences_with_audio.tar.bz2"
        content = (
            "1\t123\talice\tCC BY 4.0\thttps://example.com/alice\n"
            "2\t456\tbob\t\t\n"
            "bad\trow\n"
        ).encode("utf-8")

        data_path = Path(directory) / "sentences_with_audio.csv"
        data_path.write_bytes(content)

        with tarfile.open(export_path, "w:bz2") as tar:
            tar.add(data_path, arcname="sentences_with_audio.csv")

        return export_path

    def test_parse_audio_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = self._write_audio_export(temp_dir)
            df = parse_audio_export(str(export_path), sentence_ids={1})

        self.assertEqual(len(df), 1)
        row = df.iloc[0].to_dict()
        self.assertEqual(row["source"], "tatoeba")
        self.assertEqual(row["audio_id"], "123")
        self.assertEqual(row["sentence_id"], 1)
        self.assertEqual(row["license"], "CC BY 4.0")
        self.assertEqual(row["status"], "metadata")
        self.assertEqual(row["download_url"], "https://tatoeba.org/audio/download/123")

    def test_download_audio_files_skips_empty_license_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = self._write_audio_export(temp_dir)
            df = parse_audio_export(str(export_path))
            calls = []

            def fake_urlretrieve(url, filename):
                calls.append((url, filename))
                Path(filename).write_bytes(b"audio")

            downloaded = download_audio_files(
                df,
                audio_dir=str(Path(temp_dir) / "audio"),
                reusable_only=True,
                urlretrieve=fake_urlretrieve,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(downloaded.loc[0, "status"], "downloaded")
            self.assertEqual(downloaded.loc[1, "status"], "skipped_license")
            self.assertTrue(Path(downloaded.loc[0, "local_path"]).exists())


if __name__ == "__main__":
    unittest.main()
