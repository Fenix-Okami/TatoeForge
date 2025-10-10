"""Extractor for Tatoeba data using tatoebatools."""

import logging
from pathlib import Path
from typing import Optional, List
from tatoebatools import tatoeba
import pandas as pd

logger = logging.getLogger(__name__)


class TatoebaExtractor:
    """Extract data from Tatoeba using tatoebatools library."""

    def __init__(self, data_dir: str = "data"):
        """Initialize Tatoeba extractor.
        
        Args:
            data_dir: Directory to store downloaded data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_sentences(self, languages: Optional[List[str]] = None) -> pd.DataFrame:
        """Extract sentences from Tatoeba.
        
        Args:
            languages: List of language codes to extract (e.g., ['eng', 'fra', 'deu'])
                      If None, extracts all languages
            
        Returns:
            DataFrame with columns: sentence_id, language, text
        """
        logger.info(f"Extracting sentences for languages: {languages or 'all'}")
        
        sentences = []
        for sentence in tatoeba.sentences():
            # Filter by language if specified
            if languages and sentence.lang not in languages:
                continue
                
            sentences.append({
                'sentence_id': sentence.sentence_id,
                'language': sentence.lang,
                'text': sentence.text
            })
            
            # Log progress periodically
            if len(sentences) % 100000 == 0:
                logger.info(f"Extracted {len(sentences)} sentences...")
        
        logger.info(f"Extraction complete. Total sentences: {len(sentences)}")
        return pd.DataFrame(sentences)
    
    def extract_links(self) -> pd.DataFrame:
        """Extract sentence links (translations) from Tatoeba.
        
        Returns:
            DataFrame with columns: sentence_id, translation_id
        """
        logger.info("Extracting sentence links...")
        
        links = []
        for link in tatoeba.links():
            links.append({
                'sentence_id': link.sentence_id,
                'translation_id': link.translation_id
            })
            
            if len(links) % 100000 == 0:
                logger.info(f"Extracted {len(links)} links...")
        
        logger.info(f"Link extraction complete. Total links: {len(links)}")
        return pd.DataFrame(links)
    
    def extract_tags(self) -> pd.DataFrame:
        """Extract sentence tags from Tatoeba.
        
        Returns:
            DataFrame with columns: sentence_id, tag_name
        """
        logger.info("Extracting sentence tags...")
        
        tags = []
        for tag in tatoeba.tags():
            tags.append({
                'sentence_id': tag.sentence_id,
                'tag_name': tag.tag_name
            })
            
            if len(tags) % 10000 == 0:
                logger.info(f"Extracted {len(tags)} tags...")
        
        logger.info(f"Tag extraction complete. Total tags: {len(tags)}")
        return pd.DataFrame(tags)
    
    def extract_detailed_sentences(self, languages: Optional[List[str]] = None) -> pd.DataFrame:
        """Extract detailed sentence information from Tatoeba.
        
        Args:
            languages: List of language codes to extract
            
        Returns:
            DataFrame with detailed sentence information including metadata
        """
        logger.info(f"Extracting detailed sentences for languages: {languages or 'all'}")
        
        sentences = []
        try:
            for sentence in tatoeba.sentences_detailed():
                if languages and sentence.lang not in languages:
                    continue
                    
                sentence_data = {
                    'sentence_id': sentence.sentence_id,
                    'language': sentence.lang,
                    'text': sentence.text,
                    'username': getattr(sentence, 'username', None),
                    'date_added': getattr(sentence, 'date_added', None),
                    'date_modified': getattr(sentence, 'date_modified', None),
                }
                
                sentences.append(sentence_data)
                
                if len(sentences) % 100000 == 0:
                    logger.info(f"Extracted {len(sentences)} detailed sentences...")
                    
        except Exception as e:
            logger.warning(f"Detailed sentences extraction encountered an error: {e}")
            logger.info("Falling back to basic sentence extraction")
            return self.extract_sentences(languages)
        
        logger.info(f"Detailed extraction complete. Total sentences: {len(sentences)}")
        return pd.DataFrame(sentences)
