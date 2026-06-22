"""Command-line interface for TatoeForge."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from tatoeforge.etl import ETLPipeline
from tatoeforge.utils.config import Config


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tatoeforge.log')
        ]
    )


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='TatoeForge - ETL pipeline for Tatoeba data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full ETL with default config
  tatoeforge run
  
  # Run ETL with custom config
  tatoeforge run --config config.json
  
  # Extract only specific languages
  tatoeforge run --languages eng,fra,deu
  
  # Extract data only (no database load)
  tatoeforge extract --languages eng,spa
  
  # Load data into database from existing Parquet files
  tatoeforge load --languages eng,fra
        """
    )
    
    parser.add_argument(
        'command',
        choices=['run', 'extract', 'load'],
        help='Command to execute (run = full ETL, extract = extract only, load = load only)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--languages',
        type=str,
        help='Comma-separated list of language codes (e.g., eng,fra,deu)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for Parquet files'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        help='Directory for downloaded data'
    )
    
    parser.add_argument(
        '--database-type',
        choices=['sqlite', 'postgres'],
        help='Database type (sqlite or postgres)'
    )
    
    parser.add_argument(
        '--database-path',
        type=str,
        help='Path to SQLite database file (for SQLite)'
    )
    
    parser.add_argument(
        '--num-processes',
        type=int,
        help='Number of processes for multiprocessing'
    )
    
    parser.add_argument(
        '--quality-filter',
        type=str,
        help='Path to quality sentence IDs file'
    )
    
    parser.add_argument(
        '--extract-links',
        action='store_true',
        help='Extract translation links'
    )
    
    parser.add_argument(
        '--extract-tags',
        action='store_true',
        help='Extract sentence tags'
    )

    parser.add_argument(
        '--extract-audio',
        action='store_true',
        help='Extract Tatoeba audio metadata'
    )

    parser.add_argument(
        '--download-audio',
        action='store_true',
        help='Download audio files referenced by extracted audio metadata'
    )

    parser.add_argument(
        '--audio-dir',
        type=str,
        help='Directory for downloaded audio files'
    )

    audio_license_group = parser.add_mutually_exclusive_group()
    audio_license_group.add_argument(
        '--audio-reusable-only',
        dest='audio_reusable_only',
        action='store_true',
        default=None,
        help='Download only audio rows with non-empty reusable license metadata'
    )
    audio_license_group.add_argument(
        '--include-unlicensed-audio',
        dest='audio_reusable_only',
        action='store_false',
        help='Allow downloading audio rows with empty license metadata'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        if args.config:
            logger.info(f"Loading configuration from {args.config}")
            config = Config.from_file(args.config)
        else:
            logger.info("Using default configuration")
            config = Config()
        
        # Override config with CLI arguments
        if args.languages:
            languages = [lang.strip() for lang in args.languages.split(',')]
            config.set('languages', languages)
        else:
            languages = None
        
        if args.output_dir:
            config.set('output_dir', args.output_dir)
        
        if args.data_dir:
            config.set('data_dir', args.data_dir)
        
        if args.database_type:
            config.set('database.type', args.database_type)
        
        if args.database_path:
            config.set('database.path', args.database_path)
        
        if args.num_processes:
            config.set('num_processes', args.num_processes)
        
        if args.quality_filter:
            config.set('quality_filter.enabled', True)
            config.set('quality_filter.file', args.quality_filter)
        
        if args.extract_links:
            config.set('extract_links', True)
        
        if args.extract_tags:
            config.set('extract_tags', True)

        if args.extract_audio:
            config.set('extract_audio', True)

        if args.download_audio:
            config.set('extract_audio', True)
            config.set('download_audio', True)

        if args.audio_dir:
            config.set('audio_dir', args.audio_dir)

        if args.audio_reusable_only is not None:
            config.set('audio_reusable_only', args.audio_reusable_only)
        
        # Initialize pipeline
        logger.info("Initializing ETL pipeline")
        pipeline = ETLPipeline(config)
        
        # Execute command
        if args.command == 'run':
            logger.info("Running full ETL pipeline")
            pipeline.run(languages=languages)
            
        elif args.command == 'extract':
            logger.info("Running extraction only")
            pipeline.extract(languages=languages)
            
        elif args.command == 'load':
            logger.info("Running load only")
            pipeline.load(languages=languages)
        
        logger.info("Command completed successfully")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
