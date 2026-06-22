"""Configuration management for TatoeForge."""

import json
from typing import Any, Dict, List, Optional


class Config:
    """Configuration handler for ETL pipeline."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize configuration.
        
        Args:
            config_dict: Dictionary containing configuration parameters
        """
        self._config = config_dict or {}
        
    @classmethod
    def from_file(cls, filepath: str) -> "Config":
        """Load configuration from JSON file.
        
        Args:
            filepath: Path to JSON configuration file
            
        Returns:
            Config object
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return cls(config_dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
                
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
    
    @property
    def languages(self) -> Optional[List[str]]:
        """Get list of languages to extract."""
        return self.get('languages')
    
    @property
    def output_dir(self) -> str:
        """Get output directory for parquet files."""
        return self.get('output_dir', 'output')
    
    @property
    def database_type(self) -> str:
        """Get database type (sqlite or postgres)."""
        return self.get('database.type', 'sqlite')
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database connection configuration."""
        return self.get('database', {})
    
    @property
    def use_quality_filter(self) -> bool:
        """Whether to filter by quality sentences."""
        return self.get('quality_filter.enabled', False)
    
    @property
    def num_processes(self) -> int:
        """Number of processes for multiprocessing."""
        return self.get('num_processes', 4)
    
    @property
    def data_dir(self) -> str:
        """Get data directory for downloaded files."""
        return self.get('data_dir', 'data')

    @property
    def extract_audio(self) -> bool:
        """Whether to extract audio metadata."""
        return self.get('extract_audio', False)

    @property
    def download_audio(self) -> bool:
        """Whether to download audio files during audio extraction."""
        return self.get('download_audio', False)

    @property
    def audio_dir(self) -> str:
        """Directory for downloaded audio files."""
        return self.get('audio_dir', 'audio')

    @property
    def audio_reusable_only(self) -> bool:
        """Whether to download only audio rows with a reusable license field."""
        return self.get('audio_reusable_only', True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
