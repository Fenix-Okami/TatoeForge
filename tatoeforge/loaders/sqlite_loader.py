"""SQLite database loader."""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import pandas as pd

from tatoeforge.extractors.tatoeba_audio import AUDIO_COLUMNS
from tatoeforge.utils.tokenizer import normalize_query_tokens, tokenize_text

logger = logging.getLogger(__name__)


SENTENCE_COLUMNS = [
    "sentence_id",
    "language",
    "text",
    "username",
    "date_added",
    "date_modified",
]
LINK_COLUMNS = ["sentence_id", "translation_id"]
TAG_COLUMNS = ["sentence_id", "tag_name"]
TOKEN_COLUMNS = ["sentence_id", "language", "token", "normalized_token", "position"]
GRAMMAR_PATTERN_COLUMNS = [
    "pattern_id",
    "language",
    "name",
    "description",
    "pattern_text",
    "source",
    "metadata_json",
]
SENTENCE_GRAMMAR_COLUMNS = [
    "sentence_id",
    "pattern_id",
    "evidence_text",
    "confidence",
    "source",
]


class SQLiteLoader:
    """Load data into SQLite database."""

    def __init__(self, database_path: str = "tatoeba.db", num_processes: Optional[int] = None):
        """Initialize SQLite loader.

        Args:
            database_path: Path to SQLite database file
            num_processes: Number of processes for parallel loading (reserved)
        """
        self.database_path = Path(database_path)
        self.num_processes = num_processes or 1
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Ensure database file and directory exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self, row_factory: bool = False) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        if row_factory:
            conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self) -> None:
        """Create database tables for Tatoeba data."""
        conn = self._connect()
        try:
            self._create_tables(conn)
            conn.commit()
        finally:
            conn.close()

        logger.info("Database tables created successfully")

    def reset_tables(self) -> None:
        """Drop and recreate all managed tables."""
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            for table_name in [
                "sentence_grammar_patterns",
                "grammar_patterns",
                "sentence_audio",
                "sentence_tokens",
                "tags",
                "links",
                "sentences",
            ]:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
        finally:
            conn.close()

        self.create_tables()

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sentences (
                sentence_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL,
                text TEXT NOT NULL,
                username TEXT,
                date_added TEXT,
                date_modified TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sentences_language
            ON sentences(language)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sentence_tokens (
                sentence_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                token TEXT NOT NULL,
                normalized_token TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sentence_tokens_lookup
            ON sentence_tokens(language, normalized_token, sentence_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sentence_tokens_sentence_id
            ON sentence_tokens(sentence_id)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                translation_id INTEGER NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
                FOREIGN KEY (translation_id) REFERENCES sentences(sentence_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_links_sentence_id
            ON links(sentence_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_links_translation_id
            ON links(translation_id)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tags_sentence_id
            ON tags(sentence_id)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS grammar_patterns (
                pattern_id TEXT PRIMARY KEY,
                language TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                pattern_text TEXT,
                source TEXT,
                metadata_json TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_grammar_patterns_language
            ON grammar_patterns(language)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sentence_grammar_patterns (
                sentence_id INTEGER NOT NULL,
                pattern_id TEXT NOT NULL,
                evidence_text TEXT,
                confidence REAL,
                source TEXT,
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
                FOREIGN KEY (pattern_id) REFERENCES grammar_patterns(pattern_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sentence_grammar_sentence_id
            ON sentence_grammar_patterns(sentence_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sentence_grammar_pattern_id
            ON sentence_grammar_patterns(pattern_id)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sentence_audio (
                source TEXT NOT NULL,
                audio_id TEXT NOT NULL,
                sentence_id INTEGER NOT NULL,
                username TEXT,
                license TEXT,
                attribution_url TEXT,
                download_url TEXT,
                local_path TEXT,
                downloaded_at TEXT,
                status TEXT NOT NULL DEFAULT 'metadata',
                PRIMARY KEY (source, audio_id),
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sentence_audio_sentence_id
            ON sentence_audio(sentence_id)
            """
        )

    def _prepare_dataframe(
        self,
        df: pd.DataFrame,
        columns: Sequence[str],
        defaults: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        defaults = defaults or {}
        prepared = df.copy()

        for column in columns:
            if column not in prepared.columns:
                prepared[column] = defaults.get(column)

        for column, default in defaults.items():
            if column in prepared.columns:
                prepared[column] = prepared[column].where(pd.notnull(prepared[column]), default)

        prepared = prepared[list(columns)]
        return prepared.where(pd.notnull(prepared), None)

    def load_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
        chunksize: int = 1000,
    ) -> None:
        """Load DataFrame into SQLite table."""
        if df.empty:
            logger.info("No records to load into table '%s'", table_name)
            return

        logger.info(f"Loading {len(df)} records into table '{table_name}'")

        conn = self._connect()
        try:
            df.to_sql(
                table_name,
                conn,
                if_exists=if_exists,
                index=False,
                chunksize=chunksize,
                method="multi",
            )
            logger.info(f"Successfully loaded data into '{table_name}'")
        except Exception as e:
            logger.error(f"Error loading data into '{table_name}': {e}")
            raise
        finally:
            conn.close()

    def load_sentences(self, sentences_df: pd.DataFrame, rebuild: bool = True) -> None:
        """Load sentences and regenerate exact-token lookup rows."""
        logger.info(f"Loading {len(sentences_df)} sentences")
        if rebuild:
            self.reset_tables()
        else:
            self.create_tables()

        sentences = self._prepare_dataframe(sentences_df, SENTENCE_COLUMNS)
        self.load_dataframe(sentences, "sentences")
        self._load_sentence_tokens(sentences)

    def _load_sentence_tokens(self, sentences_df: pd.DataFrame, batch_size: int = 100000) -> None:
        records: List[Dict[str, Any]] = []

        for row in sentences_df[["sentence_id", "language", "text"]].itertuples(index=False):
            for token in tokenize_text(str(row.text)):
                records.append(
                    {
                        "sentence_id": int(row.sentence_id),
                        "language": row.language,
                        "token": token.token,
                        "normalized_token": token.normalized_token,
                        "position": token.position,
                    }
                )

            if len(records) >= batch_size:
                self.load_dataframe(pd.DataFrame(records, columns=TOKEN_COLUMNS), "sentence_tokens")
                records.clear()

        if records:
            self.load_dataframe(pd.DataFrame(records, columns=TOKEN_COLUMNS), "sentence_tokens")

    def load_links(self, links_df: pd.DataFrame) -> None:
        """Load translation links into database."""
        logger.info(f"Loading {len(links_df)} translation links")
        self.create_tables()
        links = self._prepare_dataframe(links_df, LINK_COLUMNS)
        self.load_dataframe(links, "links")

    def load_tags(self, tags_df: pd.DataFrame) -> None:
        """Load sentence tags into database."""
        logger.info(f"Loading {len(tags_df)} tags")
        self.create_tables()
        tags = self._prepare_dataframe(tags_df, TAG_COLUMNS)
        self.load_dataframe(tags, "tags")

    def load_sentence_audio(self, audio_df: pd.DataFrame) -> None:
        """Load sentence audio metadata into database."""
        logger.info(f"Loading {len(audio_df)} audio metadata rows")
        self.create_tables()
        audio = self._prepare_dataframe(audio_df, AUDIO_COLUMNS, {"source": "tatoeba", "status": "metadata"})
        self.load_dataframe(audio, "sentence_audio")

    def load_grammar_patterns(self, grammar_patterns_df: pd.DataFrame) -> None:
        """Load grammar pattern definitions."""
        logger.info(f"Loading {len(grammar_patterns_df)} grammar patterns")
        self.create_tables()
        patterns = self._prepare_dataframe(grammar_patterns_df, GRAMMAR_PATTERN_COLUMNS)
        self.load_dataframe(patterns, "grammar_patterns")

    def load_sentence_grammar_patterns(self, sentence_grammar_df: pd.DataFrame) -> None:
        """Load sentence-to-grammar annotations."""
        logger.info(f"Loading {len(sentence_grammar_df)} sentence grammar annotations")
        self.create_tables()
        annotations = self._prepare_dataframe(sentence_grammar_df, SENTENCE_GRAMMAR_COLUMNS)
        self.load_dataframe(annotations, "sentence_grammar_patterns")

    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        conn = self._connect()
        try:
            if params:
                df = pd.read_sql_query(sql, conn, params=params)
            else:
                df = pd.read_sql_query(sql, conn)
            return df
        finally:
            conn.close()

    def _fetch_dicts(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        conn = self._connect(row_factory=True)
        try:
            cursor = conn.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_sentences_by_language(self, language: str) -> pd.DataFrame:
        """Get all sentences for a specific language."""
        sql = "SELECT * FROM sentences WHERE language = ?"
        return self.query(sql, (language,))

    def get_sentences_by_vocabulary(
        self,
        words: Union[str, Sequence[str], Iterable[str]],
        language: Optional[str] = None,
        target_language: Optional[str] = None,
        match_all: bool = True,
        include_translations: bool = True,
        include_audio: bool = True,
        include_grammar: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return sentences containing exact normalized vocabulary tokens."""
        tokens = normalize_query_tokens(words)
        if not tokens:
            return []

        token_placeholders = ",".join(["?"] * len(tokens))
        params: List[Any] = list(tokens)
        where_clauses = [f"st.normalized_token IN ({token_placeholders})"]

        if language:
            where_clauses.append("s.language = ?")
            params.append(language)

        having_clause = ""
        if match_all:
            having_clause = "HAVING COUNT(DISTINCT st.normalized_token) = ?"
            params.append(len(tokens))

        params.extend([int(limit), int(offset)])
        sql = f"""
            SELECT s.sentence_id, s.language, s.text, s.username, s.date_added, s.date_modified
            FROM sentences s
            JOIN sentence_tokens st ON s.sentence_id = st.sentence_id
            WHERE {' AND '.join(where_clauses)}
            GROUP BY s.sentence_id, s.language, s.text, s.username, s.date_added, s.date_modified
            {having_clause}
            ORDER BY s.sentence_id
            LIMIT ? OFFSET ?
        """

        sentences = self._fetch_dicts(sql, params)
        sentence_ids = [int(sentence["sentence_id"]) for sentence in sentences]

        translations = (
            self.get_translations_for_sentences(sentence_ids, target_language=target_language)
            if include_translations
            else {}
        )
        audio = self.get_audio_for_sentences(sentence_ids) if include_audio else {}
        grammar = self.get_grammar_patterns_for_sentences(sentence_ids) if include_grammar else {}

        return [
            {
                "sentence": sentence,
                "translations": translations.get(int(sentence["sentence_id"]), []),
                "audio": audio.get(int(sentence["sentence_id"]), []),
                "grammar_patterns": grammar.get(int(sentence["sentence_id"]), []),
            }
            for sentence in sentences
        ]

    def get_translations(
        self,
        sentence_id: int,
        target_language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get direct translations for a sentence."""
        return self.get_translations_for_sentences([sentence_id], target_language).get(sentence_id, [])

    def get_translations_for_sentences(
        self,
        sentence_ids: Sequence[int],
        target_language: Optional[str] = None,
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get direct translations grouped by source sentence id."""
        if not sentence_ids:
            return {}

        unique_ids = list(dict.fromkeys(int(sentence_id) for sentence_id in sentence_ids))
        placeholders = ",".join(["?"] * len(unique_ids))
        params: List[Any] = list(unique_ids)
        language_clause = ""

        if target_language:
            language_clause = "AND s.language = ?"
            params.append(target_language)

        rows = self._fetch_dicts(
            f"""
            SELECT l.sentence_id AS source_sentence_id,
                   s.sentence_id, s.language, s.text, s.username, s.date_added, s.date_modified
            FROM links l
            JOIN sentences s ON s.sentence_id = l.translation_id
            WHERE l.sentence_id IN ({placeholders})
            {language_clause}
            ORDER BY l.sentence_id, s.language, s.sentence_id
            """,
            params,
        )

        grouped = {sentence_id: [] for sentence_id in unique_ids}
        for row in rows:
            source_sentence_id = int(row.pop("source_sentence_id"))
            grouped.setdefault(source_sentence_id, []).append(row)

        return grouped

    def get_audio_for_sentence(self, sentence_id: int) -> List[Dict[str, Any]]:
        """Get audio metadata for a sentence."""
        return self.get_audio_for_sentences([sentence_id]).get(sentence_id, [])

    def get_audio_for_sentences(self, sentence_ids: Sequence[int]) -> Dict[int, List[Dict[str, Any]]]:
        """Get audio metadata grouped by sentence id."""
        if not sentence_ids:
            return {}

        unique_ids = list(dict.fromkeys(int(sentence_id) for sentence_id in sentence_ids))
        placeholders = ",".join(["?"] * len(unique_ids))
        rows = self._fetch_dicts(
            f"""
            SELECT source, audio_id, sentence_id, username, license, attribution_url,
                   download_url, local_path, downloaded_at, status
            FROM sentence_audio
            WHERE sentence_id IN ({placeholders})
            ORDER BY sentence_id, source, audio_id
            """,
            unique_ids,
        )

        grouped = {sentence_id: [] for sentence_id in unique_ids}
        for row in rows:
            grouped.setdefault(int(row["sentence_id"]), []).append(row)

        return grouped

    def get_grammar_patterns_for_sentence(self, sentence_id: int) -> List[Dict[str, Any]]:
        """Get grammar annotations for a sentence."""
        return self.get_grammar_patterns_for_sentences([sentence_id]).get(sentence_id, [])

    def get_grammar_patterns_for_sentences(
        self,
        sentence_ids: Sequence[int],
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get grammar annotations grouped by sentence id."""
        if not sentence_ids:
            return {}

        unique_ids = list(dict.fromkeys(int(sentence_id) for sentence_id in sentence_ids))
        placeholders = ",".join(["?"] * len(unique_ids))
        rows = self._fetch_dicts(
            f"""
            SELECT sgp.sentence_id, gp.pattern_id, gp.language, gp.name, gp.description,
                   gp.pattern_text, gp.source AS pattern_source, gp.metadata_json,
                   sgp.evidence_text, sgp.confidence, sgp.source AS annotation_source
            FROM sentence_grammar_patterns sgp
            JOIN grammar_patterns gp ON gp.pattern_id = sgp.pattern_id
            WHERE sgp.sentence_id IN ({placeholders})
            ORDER BY sgp.sentence_id, gp.pattern_id
            """,
            unique_ids,
        )

        grouped = {sentence_id: [] for sentence_id in unique_ids}
        for row in rows:
            grouped.setdefault(int(row["sentence_id"]), []).append(row)

        return grouped

    def get_sentence_with_translations(self, sentence_id: int) -> Dict[str, Any]:
        """Get a sentence with its direct translations."""
        rows = self._fetch_dicts(
            """
            SELECT sentence_id, language, text, username, date_added, date_modified
            FROM sentences
            WHERE sentence_id = ?
            """,
            [sentence_id],
        )

        if not rows:
            return {}

        return {
            "sentence": rows[0],
            "translations": self.get_translations(sentence_id),
        }

    def vacuum(self) -> None:
        """Optimize database (VACUUM command)."""
        logger.info("Running VACUUM to optimize database")
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()
        logger.info("Database optimization complete")
