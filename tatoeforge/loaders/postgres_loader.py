"""PostgreSQL database loader."""

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import pandas as pd

try:
    import psycopg2
    from psycopg2.extensions import connection
except ImportError:  # pragma: no cover - exercised only when optional dep is missing
    psycopg2 = None
    connection = Any

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


class PostgresLoader:
    """Load data into PostgreSQL database."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "tatoeba",
        user: str = "postgres",
        password: str = "",
        num_processes: Optional[int] = None,
    ):
        """Initialize PostgreSQL loader."""
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        self.num_processes = num_processes or 1

    def _get_connection(self) -> connection:
        """Get database connection."""
        if psycopg2 is None:
            raise ImportError(
                "psycopg2-binary is required for PostgreSQL loading. "
                "Install project requirements before using PostgresLoader."
            )
        return psycopg2.connect(**self.connection_params)

    def create_tables(self) -> None:
        """Create database tables for Tatoeba data."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            self._create_tables(cursor)
            conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating tables: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def reset_tables(self) -> None:
        """Drop and recreate all managed tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            for table_name in [
                "sentence_grammar_patterns",
                "grammar_patterns",
                "sentence_audio",
                "sentence_tokens",
                "tags",
                "links",
                "sentences",
            ]:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

            self._create_tables(cursor)
            conn.commit()
            logger.info("Database tables rebuilt successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error rebuilding tables: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _create_tables(self, cursor: Any) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sentences (
                sentence_id INTEGER PRIMARY KEY,
                language VARCHAR(10) NOT NULL,
                text TEXT NOT NULL,
                username VARCHAR(100),
                date_added TIMESTAMP,
                date_modified TIMESTAMP
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
                language VARCHAR(10) NOT NULL,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                sentence_id INTEGER NOT NULL,
                tag_name VARCHAR(100) NOT NULL,
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
                language VARCHAR(10) NOT NULL,
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
                confidence DOUBLE PRECISION,
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
                downloaded_at TIMESTAMP,
                status VARCHAR(50) NOT NULL DEFAULT 'metadata',
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

    def _engine(self):
        if psycopg2 is None:
            raise ImportError(
                "psycopg2-binary is required for PostgreSQL loading. "
                "Install project requirements before using PostgresLoader."
            )

        from sqlalchemy import create_engine
        from sqlalchemy.engine import URL

        url = URL.create(
            "postgresql+psycopg2",
            username=self.connection_params["user"],
            password=self.connection_params["password"],
            host=self.connection_params["host"],
            port=self.connection_params["port"],
            database=self.connection_params["database"],
        )
        return create_engine(url)

    def load_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
        chunksize: int = 10000,
    ) -> None:
        """Load DataFrame into PostgreSQL table."""
        if df.empty:
            logger.info("No records to load into table '%s'", table_name)
            return

        logger.info(f"Loading {len(df)} records into table '{table_name}'")
        engine = self._engine()

        try:
            df.to_sql(
                table_name,
                engine,
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
            engine.dispose()

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
        conn = self._get_connection()
        try:
            if params:
                df = pd.read_sql_query(sql, conn, params=params)
            else:
                df = pd.read_sql_query(sql, conn)
            return df
        finally:
            conn.close()

    def _fetch_dicts(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, tuple(params))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def get_sentences_by_language(self, language: str) -> pd.DataFrame:
        """Get all sentences for a specific language."""
        sql = "SELECT * FROM sentences WHERE language = %s"
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

        token_placeholders = ",".join(["%s"] * len(tokens))
        params: List[Any] = list(tokens)
        where_clauses = [f"st.normalized_token IN ({token_placeholders})"]

        if language:
            where_clauses.append("s.language = %s")
            params.append(language)

        having_clause = ""
        if match_all:
            having_clause = "HAVING COUNT(DISTINCT st.normalized_token) = %s"
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
            LIMIT %s OFFSET %s
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
        placeholders = ",".join(["%s"] * len(unique_ids))
        params: List[Any] = list(unique_ids)
        language_clause = ""

        if target_language:
            language_clause = "AND s.language = %s"
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
        placeholders = ",".join(["%s"] * len(unique_ids))
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
        placeholders = ",".join(["%s"] * len(unique_ids))
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
            WHERE sentence_id = %s
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
        conn = self._get_connection()
        conn.set_isolation_level(0)
        cursor = conn.cursor()
        try:
            cursor.execute("VACUUM ANALYZE")
            logger.info("Database optimization complete")
        finally:
            cursor.close()
            conn.close()
