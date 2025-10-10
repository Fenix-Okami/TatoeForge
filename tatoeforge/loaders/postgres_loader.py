"""PostgreSQL database loader."""

import logging
from typing import Optional, Dict, Any
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import connection

logger = logging.getLogger(__name__)


class PostgresLoader:
    """Load data into PostgreSQL database."""

    def __init__(self, host: str = "localhost", port: int = 5432,
                 database: str = "tatoeba", user: str = "postgres",
                 password: str = "", num_processes: Optional[int] = None):
        """Initialize PostgreSQL loader.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            num_processes: Number of processes (for future parallel operations)
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.num_processes = num_processes or 1
        
    def _get_connection(self) -> connection:
        """Get database connection.
        
        Returns:
            PostgreSQL connection
        """
        return psycopg2.connect(**self.connection_params)
    
    def create_tables(self) -> None:
        """Create database tables for Tatoeba data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Sentences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentences (
                    sentence_id INTEGER PRIMARY KEY,
                    language VARCHAR(10) NOT NULL,
                    text TEXT NOT NULL,
                    username VARCHAR(100),
                    date_added TIMESTAMP,
                    date_modified TIMESTAMP
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
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    sentence_id INTEGER NOT NULL,
                    tag_name VARCHAR(100) NOT NULL,
                    FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags_sentence_id 
                ON tags(sentence_id)
            """)
            
            conn.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating tables: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def load_dataframe(self, df: pd.DataFrame, table_name: str,
                      if_exists: str = "replace", chunksize: int = 10000) -> None:
        """Load DataFrame into PostgreSQL table.
        
        Args:
            df: DataFrame to load
            table_name: Name of the table
            if_exists: How to behave if table exists ('fail', 'replace', 'append')
            chunksize: Number of rows to insert at a time
        """
        logger.info(f"Loading {len(df)} records into table '{table_name}'")
        
        from sqlalchemy import create_engine
        
        # Create SQLAlchemy engine
        connection_string = (
            f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}"
            f"@{self.connection_params['host']}:{self.connection_params['port']}"
            f"/{self.connection_params['database']}"
        )
        
        engine = create_engine(connection_string)
        
        try:
            df.to_sql(
                table_name,
                engine,
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
            engine.dispose()
    
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
        conn = self._get_connection()
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
        sql = "SELECT * FROM sentences WHERE language = %s"
        return self.query(sql, (language,))
    
    def get_sentence_with_translations(self, sentence_id: int) -> Dict[str, Any]:
        """Get a sentence with its translations.
        
        Args:
            sentence_id: Sentence ID
            
        Returns:
            Dictionary with sentence and translations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get main sentence
            cursor.execute("SELECT * FROM sentences WHERE sentence_id = %s", (sentence_id,))
            sentence = cursor.fetchone()
            
            if not sentence:
                return {}
            
            # Get translations
            cursor.execute("""
                SELECT s.* FROM sentences s
                JOIN links l ON s.sentence_id = l.translation_id
                WHERE l.sentence_id = %s
            """, (sentence_id,))
            translations = cursor.fetchall()
            
            return {
                'sentence': sentence,
                'translations': translations
            }
        finally:
            cursor.close()
            conn.close()
    
    def vacuum(self) -> None:
        """Optimize database (VACUUM command)."""
        logger.info("Running VACUUM to optimize database")
        conn = self._get_connection()
        conn.set_isolation_level(0)  # Autocommit mode required for VACUUM
        cursor = conn.cursor()
        try:
            cursor.execute("VACUUM ANALYZE")
            logger.info("Database optimization complete")
        finally:
            cursor.close()
            conn.close()
