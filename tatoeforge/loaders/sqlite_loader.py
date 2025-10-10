"""SQLite database loader."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from multiprocessing import Pool
from functools import partial

logger = logging.getLogger(__name__)


class SQLiteLoader:
    """Load data into SQLite database."""

    def __init__(self, database_path: str = "tatoeba.db", num_processes: Optional[int] = None):
        """Initialize SQLite loader.
        
        Args:
            database_path: Path to SQLite database file
            num_processes: Number of processes for parallel loading (for multiple tables)
        """
        self.database_path = Path(database_path)
        self.num_processes = num_processes or 1
        self._ensure_database()
        
    def _ensure_database(self) -> None:
        """Ensure database file and directory exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
    def create_tables(self) -> None:
        """Create database tables for Tatoeba data."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Sentences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentences (
                sentence_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL,
                text TEXT NOT NULL,
                username TEXT,
                date_added TEXT,
                date_modified TEXT
            )
        """)
        
        # Create index on language for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentences_language 
            ON sentences(language)
        """)
        
        # Links table (translations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                translation_id INTEGER NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
                FOREIGN KEY (translation_id) REFERENCES sentences(sentence_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_sentence_id 
            ON links(sentence_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_translation_id 
            ON links(translation_id)
        """)
        
        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_sentence_id 
            ON tags(sentence_id)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database tables created successfully")
    
    def load_dataframe(self, df: pd.DataFrame, table_name: str, 
                      if_exists: str = "replace", chunksize: int = 10000) -> None:
        """Load DataFrame into SQLite table.
        
        Args:
            df: DataFrame to load
            table_name: Name of the table
            if_exists: How to behave if table exists ('fail', 'replace', 'append')
            chunksize: Number of rows to insert at a time
        """
        logger.info(f"Loading {len(df)} records into table '{table_name}'")
        
        conn = sqlite3.connect(self.database_path)
        
        try:
            df.to_sql(
                table_name,
                conn,
                if_exists=if_exists,
                index=False,
                chunksize=chunksize,
                method='multi'
            )
            logger.info(f"Successfully loaded data into '{table_name}'")
            
        except Exception as e:
            logger.error(f"Error loading data into '{table_name}': {e}")
            raise
        finally:
            conn.close()
    
    def load_sentences(self, sentences_df: pd.DataFrame) -> None:
        """Load sentences data into database.
        
        Args:
            sentences_df: DataFrame with sentence data
        """
        logger.info(f"Loading {len(sentences_df)} sentences")
        self.create_tables()
        self.load_dataframe(sentences_df, 'sentences', if_exists='replace')
    
    def load_links(self, links_df: pd.DataFrame) -> None:
        """Load translation links into database.
        
        Args:
            links_df: DataFrame with link data
        """
        logger.info(f"Loading {len(links_df)} translation links")
        self.create_tables()
        self.load_dataframe(links_df, 'links', if_exists='replace')
    
    def load_tags(self, tags_df: pd.DataFrame) -> None:
        """Load sentence tags into database.
        
        Args:
            tags_df: DataFrame with tag data
        """
        logger.info(f"Loading {len(tags_df)} tags")
        self.create_tables()
        self.load_dataframe(tags_df, 'tags', if_exists='replace')
    
    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            DataFrame with query results
        """
        conn = sqlite3.connect(self.database_path)
        try:
            if params:
                df = pd.read_sql_query(sql, conn, params=params)
            else:
                df = pd.read_sql_query(sql, conn)
            return df
        finally:
            conn.close()
    
    def get_sentences_by_language(self, language: str) -> pd.DataFrame:
        """Get all sentences for a specific language.
        
        Args:
            language: Language code
            
        Returns:
            DataFrame with sentences
        """
        sql = "SELECT * FROM sentences WHERE language = ?"
        return self.query(sql, (language,))
    
    def get_sentence_with_translations(self, sentence_id: int) -> Dict[str, Any]:
        """Get a sentence with its translations.
        
        Args:
            sentence_id: Sentence ID
            
        Returns:
            Dictionary with sentence and translations
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Get main sentence
        cursor.execute("SELECT * FROM sentences WHERE sentence_id = ?", (sentence_id,))
        sentence = cursor.fetchone()
        
        if not sentence:
            conn.close()
            return {}
        
        # Get translations
        cursor.execute("""
            SELECT s.* FROM sentences s
            JOIN links l ON s.sentence_id = l.translation_id
            WHERE l.sentence_id = ?
        """, (sentence_id,))
        translations = cursor.fetchall()
        
        conn.close()
        
        return {
            'sentence': sentence,
            'translations': translations
        }
    
    def vacuum(self) -> None:
        """Optimize database (VACUUM command)."""
        logger.info("Running VACUUM to optimize database")
        conn = sqlite3.connect(self.database_path)
        conn.execute("VACUUM")
        conn.close()
        logger.info("Database optimization complete")
