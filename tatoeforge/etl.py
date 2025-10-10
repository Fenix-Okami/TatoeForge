"""Main ETL pipeline orchestrator."""

import logging
from typing import Optional, List
from pathlib import Path

from tatoeforge.extractors.tatoeba_extractor import TatoebaExtractor
from tatoeforge.transformers.parquet_transformer import ParquetTransformer
from tatoeforge.loaders.sqlite_loader import SQLiteLoader
from tatoeforge.loaders.postgres_loader import PostgresLoader
from tatoeforge.utils.config import Config
from tatoeforge.utils.quality_filter import QualityFilter

logger = logging.getLogger(__name__)


class ETLPipeline:
    """Main ETL pipeline for Tatoeba data processing."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize ETL pipeline.
        
        Args:
            config: Configuration object (if None, uses defaults)
        """
        self.config = config or Config()
        
        # Initialize components
        self.extractor = TatoebaExtractor(data_dir=self.config.data_dir)
        self.transformer = ParquetTransformer(
            output_dir=self.config.output_dir,
            num_processes=self.config.num_processes
        )
        
        # Quality filter (optional)
        self.quality_filter: Optional[QualityFilter] = None
        if self.config.use_quality_filter:
            quality_file = self.config.get('quality_filter.file')
            if quality_file:
                self.quality_filter = QualityFilter.from_file(quality_file)
            else:
                logger.warning("Quality filter enabled but no file specified")
        
        # Database loader
        self.loader = self._initialize_loader()
        
    def _initialize_loader(self):
        """Initialize database loader based on configuration.
        
        Returns:
            Database loader (SQLite or PostgreSQL)
        """
        db_type = self.config.database_type.lower()
        db_config = self.config.database_config
        
        if db_type == 'postgres' or db_type == 'postgresql':
            logger.info("Initializing PostgreSQL loader")
            return PostgresLoader(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 5432),
                database=db_config.get('database', 'tatoeba'),
                user=db_config.get('user', 'postgres'),
                password=db_config.get('password', ''),
                num_processes=self.config.num_processes
            )
        else:
            logger.info("Initializing SQLite loader")
            db_path = db_config.get('path', 'tatoeba.db')
            return SQLiteLoader(
                database_path=db_path,
                num_processes=self.config.num_processes
            )
    
    def extract(self, languages: Optional[List[str]] = None) -> None:
        """Extract data from Tatoeba.
        
        Args:
            languages: List of language codes to extract (None = config languages or all)
        """
        if languages is None:
            languages = self.config.languages
            
        logger.info(f"Starting extraction for languages: {languages or 'all'}")
        
        # Extract sentences
        sentences_df = self.extractor.extract_sentences(languages)
        
        # Apply quality filter if enabled
        if self.quality_filter:
            logger.info("Applying quality filter to sentences")
            sentences_df = self.quality_filter.filter_dataframe(sentences_df)
        
        # Save to Parquet
        logger.info("Saving sentences to Parquet format")
        self.transformer.save_by_language(sentences_df, dataset_name="sentences")
        
        # Extract and save links if requested
        if self.config.get('extract_links', False):
            logger.info("Extracting translation links")
            links_df = self.extractor.extract_links()
            
            # Filter links to only include quality sentences if filter enabled
            if self.quality_filter:
                logger.info("Filtering links to quality sentences")
                links_df = links_df[
                    links_df['sentence_id'].isin(self.quality_filter.quality_sentence_ids) &
                    links_df['translation_id'].isin(self.quality_filter.quality_sentence_ids)
                ]
            
            self.transformer.save_by_language(links_df, dataset_name="links")
        
        # Extract and save tags if requested
        if self.config.get('extract_tags', False):
            logger.info("Extracting sentence tags")
            tags_df = self.extractor.extract_tags()
            
            # Filter tags to only quality sentences if filter enabled
            if self.quality_filter:
                logger.info("Filtering tags to quality sentences")
                tags_df = tags_df[
                    tags_df['sentence_id'].isin(self.quality_filter.quality_sentence_ids)
                ]
            
            self.transformer.save_by_language(tags_df, dataset_name="tags")
        
        logger.info("Extraction complete")
    
    def transform(self) -> None:
        """Transform data (already done during extraction with Parquet save)."""
        logger.info("Transform step - data already transformed during extraction")
    
    def load(self, languages: Optional[List[str]] = None) -> None:
        """Load data into database.
        
        Args:
            languages: List of language codes to load (None = load all available)
        """
        logger.info("Starting data load into database")
        
        # Get available languages if not specified
        if languages is None:
            languages = self.config.languages
            if not languages:
                languages = self.transformer.get_languages("sentences")
        
        logger.info(f"Loading data for languages: {languages or 'all'}")
        
        # Load sentences
        if languages:
            sentences_dfs = []
            for lang in languages:
                try:
                    df = self.transformer.load_parquet("sentences", language=lang)
                    sentences_dfs.append(df)
                except FileNotFoundError:
                    logger.warning(f"No data found for language '{lang}'")
            
            if sentences_dfs:
                import pandas as pd
                sentences_df = pd.concat(sentences_dfs, ignore_index=True)
                self.loader.load_sentences(sentences_df)
        else:
            sentences_df = self.transformer.load_parquet("sentences")
            self.loader.load_sentences(sentences_df)
        
        # Load links if available
        try:
            links_df = self.transformer.load_parquet("links")
            self.loader.load_links(links_df)
        except FileNotFoundError:
            logger.info("No links data to load")
        
        # Load tags if available
        try:
            tags_df = self.transformer.load_parquet("tags")
            self.loader.load_tags(tags_df)
        except FileNotFoundError:
            logger.info("No tags data to load")
        
        # Optimize database
        logger.info("Optimizing database")
        self.loader.vacuum()
        
        logger.info("Data load complete")
    
    def run(self, languages: Optional[List[str]] = None) -> None:
        """Run full ETL pipeline.
        
        Args:
            languages: List of language codes to process (None = config languages or all)
        """
        logger.info("=" * 60)
        logger.info("Starting TatoeForge ETL Pipeline")
        logger.info("=" * 60)
        
        try:
            # Extract
            self.extract(languages)
            
            # Transform (implicit in extract step)
            self.transform()
            
            # Load
            self.load(languages)
            
            logger.info("=" * 60)
            logger.info("ETL Pipeline completed successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"ETL Pipeline failed: {e}", exc_info=True)
            raise
