"""Optional PostgreSQL integration tests."""

import os
import unittest

import pandas as pd

from tatoeforge.loaders.postgres_loader import PostgresLoader


@unittest.skipUnless(
    os.environ.get("TATOEFORGE_TEST_POSTGRES") == "1",
    "Set TATOEFORGE_TEST_POSTGRES=1 to run PostgreSQL integration tests",
)
class TestPostgresLoaderIntegration(unittest.TestCase):
    """Smoke tests for PostgresLoader against an explicit local test database."""

    def setUp(self):
        self.loader = PostgresLoader(
            host=os.environ.get("TATOEFORGE_POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("TATOEFORGE_POSTGRES_PORT", "5432")),
            database=os.environ.get("TATOEFORGE_POSTGRES_DATABASE", "tatoeba_test"),
            user=os.environ.get("TATOEFORGE_POSTGRES_USER", "postgres"),
            password=os.environ.get("TATOEFORGE_POSTGRES_PASSWORD", ""),
        )

    def test_vocabulary_lookup_smoke(self):
        self.loader.load_sentences(
            pd.DataFrame(
                [
                    {"sentence_id": 1, "language": "eng", "text": "Hello world."},
                    {"sentence_id": 2, "language": "fra", "text": "Bonjour le monde."},
                ]
            )
        )
        self.loader.load_links(pd.DataFrame([{"sentence_id": 1, "translation_id": 2}]))

        results = self.loader.get_sentences_by_vocabulary(
            ["hello", "world"],
            language="eng",
            target_language="fra",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["translations"][0]["sentence_id"], 2)


if __name__ == "__main__":
    unittest.main()
