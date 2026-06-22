"""Tests for vocabulary tokenization."""

import unittest

from tatoeforge.utils.tokenizer import normalize_query_tokens, normalize_token, tokenize_text


class TestTokenizer(unittest.TestCase):
    """Test exact-token lookup normalization."""

    def test_tokenize_punctuation_and_case(self):
        tokens = tokenize_text("Hello, brave WORLD!")
        self.assertEqual([token.token for token in tokens], ["Hello", "brave", "WORLD"])
        self.assertEqual(
            [token.normalized_token for token in tokens],
            ["hello", "brave", "world"],
        )

    def test_nfkc_normalization(self):
        self.assertEqual(normalize_token("ＡＢＣ"), "abc")
        tokens = tokenize_text("ＡＢＣ test")
        self.assertEqual([token.normalized_token for token in tokens], ["abc", "test"])

    def test_normalize_query_tokens_flattens_multiword_input(self):
        tokens = normalize_query_tokens(["Hello, WORLD", "hello"])
        self.assertEqual(tokens, ["hello", "world"])


if __name__ == "__main__":
    unittest.main()
