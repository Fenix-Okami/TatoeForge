"""Tokenization helpers for sentence vocabulary lookup."""

from dataclasses import dataclass
import re
import unicodedata
from typing import Iterable, List, Sequence, Union


_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class Token:
    """A sentence token and its normalized lookup form."""

    token: str
    normalized_token: str
    position: int


def normalize_token(value: str) -> str:
    """Normalize a token for exact vocabulary lookup."""
    return unicodedata.normalize("NFKC", value).casefold()


def tokenize_text(text: str) -> List[Token]:
    """Split text into normalized tokens.

    This intentionally stays simple and portable: it splits on punctuation and
    whitespace, then applies Unicode NFKC normalization and case folding. CJK
    and other languages without word boundaries need language-specific analyzers
    in a later layer.
    """
    normalized_text = unicodedata.normalize("NFKC", text or "")
    tokens: List[Token] = []

    for position, match in enumerate(_TOKEN_RE.finditer(normalized_text)):
        token = match.group(0)
        tokens.append(
            Token(
                token=token,
                normalized_token=normalize_token(token),
                position=position,
            )
        )

    return tokens


def normalize_query_tokens(words: Union[str, Sequence[str], Iterable[str]]) -> List[str]:
    """Normalize one or more query words into unique lookup tokens."""
    if isinstance(words, str):
        values = [words]
    else:
        values = list(words)

    normalized: List[str] = []
    seen = set()

    for value in values:
        for token in tokenize_text(str(value)):
            if token.normalized_token and token.normalized_token not in seen:
                normalized.append(token.normalized_token)
                seen.add(token.normalized_token)

    return normalized
