"""Quality filtering for Tatoeba sentences."""

import pandas as pd
from typing import Set, Optional
import logging

logger = logging.getLogger(__name__)


class QualityFilter:
    """Filter sentences based on quality indicators."""

    def __init__(self, quality_sentence_ids: Optional[Set[int]] = None):
        """Initialize quality filter.
        
        Args:
            quality_sentence_ids: Set of sentence IDs that are trusted/quality sentences
        """
        self.quality_sentence_ids = quality_sentence_ids or set()
        
    @classmethod
    def from_file(cls, filepath: str) -> "QualityFilter":
        """Load quality sentence IDs from file.
        
        Args:
            filepath: Path to file containing sentence IDs (one per line)
            
        Returns:
            QualityFilter object
        """
        quality_ids = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and line.isdigit():
                        quality_ids.add(int(line))
            logger.info(f"Loaded {len(quality_ids)} quality sentence IDs from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Quality filter file not found: {filepath}")
        except Exception as e:
            logger.error(f"Error loading quality filter: {e}")
            
        return cls(quality_ids)
    
    @classmethod
    def from_tatoeba(cls, sentences_detailed) -> "QualityFilter":
        """Extract quality sentence IDs from Tatoeba sentences_detailed data.
        
        Args:
            sentences_detailed: Iterator of sentence detail objects from tatoebatools
            
        Returns:
            QualityFilter object
        """
        quality_ids = set()
        for sentence in sentences_detailed:
            # Consider sentences with tags like "OK" or rating above threshold as quality
            if hasattr(sentence, 'correctness') and sentence.correctness >= 0:
                quality_ids.add(sentence.sentence_id)
                
        logger.info(f"Extracted {len(quality_ids)} quality sentences from Tatoeba data")
        return cls(quality_ids)
    
    def filter_dataframe(self, df: pd.DataFrame, id_column: str = 'sentence_id') -> pd.DataFrame:
        """Filter a DataFrame to only include quality sentences.
        
        Args:
            df: DataFrame containing sentences
            id_column: Name of the column containing sentence IDs
            
        Returns:
            Filtered DataFrame
        """
        if not self.quality_sentence_ids:
            logger.warning("No quality sentence IDs loaded, returning unfiltered data")
            return df
            
        initial_count = len(df)
        filtered_df = df[df[id_column].isin(self.quality_sentence_ids)]
        filtered_count = len(filtered_df)
        
        logger.info(f"Filtered {initial_count} sentences to {filtered_count} quality sentences "
                   f"({filtered_count/initial_count*100:.1f}%)")
        
        return filtered_df
    
    def is_quality(self, sentence_id: int) -> bool:
        """Check if a sentence ID is marked as quality.
        
        Args:
            sentence_id: Sentence ID to check
            
        Returns:
            True if sentence is quality, False otherwise
        """
        return sentence_id in self.quality_sentence_ids
    
    def add_quality_ids(self, sentence_ids: Set[int]) -> None:
        """Add additional quality sentence IDs.
        
        Args:
            sentence_ids: Set of sentence IDs to add
        """
        self.quality_sentence_ids.update(sentence_ids)
        
    def __len__(self) -> int:
        """Return number of quality sentence IDs."""
        return len(self.quality_sentence_ids)
