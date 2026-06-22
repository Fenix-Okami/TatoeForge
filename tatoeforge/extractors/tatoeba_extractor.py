"""Extractor for Tatoeba data using tatoebatools."""

import logging
from pathlib import Path
from typing import Iterable, Optional, List
import urllib.request

import pandas as pd

from tatoeforge.extractors.tatoeba_audio import (
    AUDIO_EXPORT_FILENAME,
    AUDIO_EXPORT_URL,
    download_audio_files,
    parse_audio_export,
)

logger = logging.getLogger(__name__)


def _get_tatoeba():
    """Import tatoebatools only when extraction actually needs it."""
    try:
        from tatoebatools import tatoeba
    except ImportError as exc:
        raise ImportError(
            "tatoebatools is required for Tatoeba extraction. "
            "Install project requirements before running extract/run commands."
        ) from exc
    return tatoeba


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
        tatoeba = _get_tatoeba()
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
        tatoeba = _get_tatoeba()
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
        tatoeba = _get_tatoeba()
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
            tatoeba = _get_tatoeba()
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

    def extract_audio_metadata(
        self,
        sentence_ids: Optional[Iterable[int]] = None,
        export_path: Optional[str] = None,
        download_audio: bool = False,
        audio_dir: str = "audio",
        reusable_only: bool = True,
    ) -> pd.DataFrame:
        """Extract Tatoeba audio metadata and optionally download reusable audio.

        Args:
            sentence_ids: Optional sentence IDs to keep.
            export_path: Optional local sentences_with_audio.tar.bz2 path.
            download_audio: Whether to download referenced audio files.
            audio_dir: Directory where downloaded audio files are stored.
            reusable_only: Skip empty-license audio when downloading.

        Returns:
            DataFrame matching the sentence_audio table.
        """
        export_file = Path(export_path) if export_path else self.data_dir / AUDIO_EXPORT_FILENAME

        if not export_file.exists():
            logger.info("Downloading Tatoeba audio metadata export to %s", export_file)
            urllib.request.urlretrieve(AUDIO_EXPORT_URL, str(export_file))

        logger.info("Parsing Tatoeba audio metadata from %s", export_file)
        audio_df = parse_audio_export(str(export_file), sentence_ids=sentence_ids)

        if download_audio:
            logger.info("Downloading Tatoeba audio files to %s", audio_dir)
            audio_df = download_audio_files(
                audio_df,
                audio_dir=audio_dir,
                reusable_only=reusable_only,
            )

        logger.info("Audio metadata extraction complete. Total rows: %s", len(audio_df))
        return audio_df
