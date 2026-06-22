"""SQLite loader integration tests for retrieval tables."""

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from tatoeforge.loaders.sqlite_loader import SQLiteLoader


class TestSQLiteLoaderRetrieval(unittest.TestCase):
    """Test sentence retrieval, translations, grammar, and audio metadata."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.loader = SQLiteLoader(str(self.db_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def _load_fixture(self):
        sentences = pd.DataFrame(
            [
                {"sentence_id": 1, "language": "eng", "text": "Hello, brave world!"},
                {"sentence_id": 2, "language": "eng", "text": "Hello there."},
                {"sentence_id": 3, "language": "fra", "text": "Bonjour le monde."},
                {"sentence_id": 4, "language": "eng", "text": "Full-width ＡＢＣ test."},
            ]
        )
        self.loader.load_sentences(sentences)

        self.loader.load_links(
            pd.DataFrame(
                [
                    {"sentence_id": 1, "translation_id": 3},
                    {"sentence_id": 3, "translation_id": 1},
                ]
            )
        )
        self.loader.load_sentence_audio(
            pd.DataFrame(
                [
                    {
                        "source": "tatoeba",
                        "audio_id": "123",
                        "sentence_id": 1,
                        "username": "alice",
                        "license": "CC BY 4.0",
                        "attribution_url": "https://example.com/alice",
                        "download_url": "https://tatoeba.org/audio/download/123",
                        "local_path": None,
                        "downloaded_at": None,
                        "status": "metadata",
                    }
                ]
            )
        )
        self.loader.load_grammar_patterns(
            pd.DataFrame(
                [
                    {
                        "pattern_id": "eng-present-simple",
                        "language": "eng",
                        "name": "Present simple",
                        "description": "Placeholder pattern",
                        "pattern_text": "hello",
                        "source": "manual",
                        "metadata_json": "{}",
                    }
                ]
            )
        )
        self.loader.load_sentence_grammar_patterns(
            pd.DataFrame(
                [
                    {
                        "sentence_id": 1,
                        "pattern_id": "eng-present-simple",
                        "evidence_text": "Hello",
                        "confidence": 1.0,
                        "source": "manual",
                    }
                ]
            )
        )

    def test_vocabulary_lookup_returns_sentence_extras(self):
        self._load_fixture()

        results = self.loader.get_sentences_by_vocabulary(
            ["HELLO", "world"],
            language="eng",
            target_language="fra",
        )

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["sentence"]["sentence_id"], 1)
        self.assertEqual(result["translations"][0]["sentence_id"], 3)
        self.assertEqual(result["translations"][0]["text"], "Bonjour le monde.")
        self.assertEqual(result["audio"][0]["audio_id"], "123")
        self.assertEqual(result["grammar_patterns"][0]["pattern_id"], "eng-present-simple")

    def test_match_any_and_nfkc_lookup(self):
        self._load_fixture()

        any_results = self.loader.get_sentences_by_vocabulary(
            ["hello", "world"],
            language="eng",
            match_all=False,
            include_translations=False,
            include_audio=False,
            include_grammar=False,
        )
        self.assertEqual([row["sentence"]["sentence_id"] for row in any_results], [1, 2])

        nfkc_results = self.loader.get_sentences_by_vocabulary(
            "abc",
            language="eng",
            include_translations=False,
            include_audio=False,
            include_grammar=False,
        )
        self.assertEqual([row["sentence"]["sentence_id"] for row in nfkc_results], [4])

    def test_load_sentences_rebuilds_dependent_tables(self):
        self._load_fixture()

        self.loader.load_sentences(
            pd.DataFrame(
                [
                    {"sentence_id": 10, "language": "eng", "text": "Fresh sentence."},
                ]
            )
        )

        self.assertEqual(int(self.loader.query("SELECT COUNT(*) AS count FROM links").iloc[0]["count"]), 0)
        self.assertEqual(
            int(self.loader.query("SELECT COUNT(*) AS count FROM sentence_audio").iloc[0]["count"]),
            0,
        )
        old_results = self.loader.get_sentences_by_vocabulary("hello", language="eng")
        self.assertEqual(old_results, [])


if __name__ == "__main__":
    unittest.main()
