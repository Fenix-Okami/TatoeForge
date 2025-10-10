"""Transform and save data to Parquet format with indexing."""

import logging
from pathlib import Path
from typing import Optional, List
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from multiprocessing import Pool, cpu_count
from functools import partial

logger = logging.getLogger(__name__)


class ParquetTransformer:
    """Transform data and save to Parquet format indexed by language and sentence ID."""

    def __init__(self, output_dir: str = "output", num_processes: Optional[int] = None):
        """Initialize Parquet transformer.
        
        Args:
            output_dir: Directory to save Parquet files
            num_processes: Number of processes for parallel processing (None = cpu_count)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.num_processes = num_processes or cpu_count()
        
    def save_by_language(self, df: pd.DataFrame, dataset_name: str = "sentences") -> None:
        """Save DataFrame to Parquet files partitioned by language.
        
        Args:
            df: DataFrame containing data with 'language' column
            dataset_name: Name of the dataset (used for directory naming)
        """
        if 'language' not in df.columns:
            logger.error("DataFrame must contain 'language' column")
            raise ValueError("DataFrame must contain 'language' column")
            
        output_path = self.output_dir / dataset_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving {len(df)} records to Parquet files in {output_path}")
        
        # Get unique languages
        languages = df['language'].unique()
        logger.info(f"Found {len(languages)} languages to process")
        
        # Process languages in parallel
        if self.num_processes > 1:
            with Pool(self.num_processes) as pool:
                partial_save = partial(self._save_language_partition, df=df, output_path=output_path)
                pool.map(partial_save, languages)
        else:
            for lang in languages:
                self._save_language_partition(lang, df, output_path)
                
        logger.info(f"Successfully saved data for {len(languages)} languages")
    
    def _save_language_partition(self, language: str, df: pd.DataFrame, output_path: Path) -> None:
        """Save data for a single language to Parquet file.
        
        Args:
            language: Language code
            df: Full DataFrame
            output_path: Base output path
        """
        try:
            lang_df = df[df['language'] == language].copy()
            
            # Sort by sentence_id for better indexing
            if 'sentence_id' in lang_df.columns:
                lang_df = lang_df.sort_values('sentence_id')
            
            # Save to Parquet with appropriate compression
            file_path = output_path / f"{language}.parquet"
            
            # Create PyArrow table with index
            table = pa.Table.from_pandas(lang_df, preserve_index=False)
            
            # Write with Snappy compression for good balance of speed and size
            pq.write_table(
                table,
                file_path,
                compression='snappy',
                use_dictionary=True,
                write_statistics=True
            )
            
            logger.info(f"Saved {len(lang_df)} records for language '{language}' to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving language partition '{language}': {e}")
    
    def save_with_partitioning(self, df: pd.DataFrame, dataset_name: str = "sentences",
                               partition_cols: Optional[List[str]] = None) -> None:
        """Save DataFrame with partitioning using PyArrow dataset.
        
        Args:
            df: DataFrame to save
            dataset_name: Name of the dataset
            partition_cols: Columns to use for partitioning (default: ['language'])
        """
        if partition_cols is None:
            partition_cols = ['language']
            
        output_path = self.output_dir / dataset_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving data with partitioning by {partition_cols}")
        
        # Sort by sentence_id if present
        if 'sentence_id' in df.columns:
            df = df.sort_values('sentence_id')
        
        # Create PyArrow table
        table = pa.Table.from_pandas(df, preserve_index=False)
        
        # Write dataset with partitioning
        pq.write_to_dataset(
            table,
            root_path=str(output_path),
            partition_cols=partition_cols,
            compression='snappy',
            use_dictionary=True,
            existing_data_behavior='overwrite_or_ignore'
        )
        
        logger.info(f"Dataset saved to {output_path} with partitioning")
    
    def load_parquet(self, dataset_name: str = "sentences", 
                     language: Optional[str] = None) -> pd.DataFrame:
        """Load data from Parquet files.
        
        Args:
            dataset_name: Name of the dataset to load
            language: Specific language to load (None = load all)
            
        Returns:
            DataFrame with loaded data
        """
        dataset_path = self.output_dir / dataset_name
        
        if not dataset_path.exists():
            logger.error(f"Dataset not found: {dataset_path}")
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        if language:
            # Load specific language file
            file_path = dataset_path / f"{language}.parquet"
            if not file_path.exists():
                logger.error(f"Language file not found: {file_path}")
                raise FileNotFoundError(f"Language file not found: {file_path}")
            
            logger.info(f"Loading data for language '{language}' from {file_path}")
            return pd.read_parquet(file_path)
        else:
            # Load all Parquet files in directory
            logger.info(f"Loading all data from {dataset_path}")
            parquet_files = list(dataset_path.glob("*.parquet"))
            
            if not parquet_files:
                # Try loading partitioned dataset
                try:
                    dataset = pq.ParquetDataset(str(dataset_path))
                    return dataset.read().to_pandas()
                except Exception as e:
                    logger.error(f"No Parquet files found in {dataset_path}")
                    raise FileNotFoundError(f"No Parquet files found in {dataset_path}")
            
            dfs = []
            for file_path in parquet_files:
                dfs.append(pd.read_parquet(file_path))
            
            return pd.concat(dfs, ignore_index=True)
    
    def get_languages(self, dataset_name: str = "sentences") -> List[str]:
        """Get list of available languages in the dataset.
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            List of language codes
        """
        dataset_path = self.output_dir / dataset_name
        
        if not dataset_path.exists():
            logger.warning(f"Dataset not found: {dataset_path}")
            return []
        
        # Get all Parquet files
        parquet_files = list(dataset_path.glob("*.parquet"))
        languages = [f.stem for f in parquet_files]
        
        logger.info(f"Found {len(languages)} languages in dataset '{dataset_name}'")
        return languages
