#!/usr/bin/env python3
"""Simple example of using TatoeForge programmatically."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tatoeforge.utils.config import Config
from tatoeforge import ETLPipeline


def main():
    """Run a simple ETL example."""
    
    # Create configuration
    config = Config({
        'languages': ['eng'],  # Just English for this example
        'data_dir': 'example_data',
        'output_dir': 'example_output',
        'num_processes': 2,
        'database': {
            'type': 'sqlite',
            'path': 'example.db'
        }
    })
    
    print("TatoeForge Simple Example")
    print("=" * 50)
    print(f"Languages: {config.languages}")
    print(f"Output directory: {config.output_dir}")
    print(f"Database: {config.database_config.get('path')}")
    print("=" * 50)
    
    # Initialize pipeline
    print("\nInitializing pipeline...")
    pipeline = ETLPipeline(config)
    
    # Run the pipeline
    print("\nRunning ETL pipeline...")
    print("This will download data from Tatoeba, so it may take a while...")
    
    try:
        pipeline.run(languages=['eng'])
        print("\n✓ Pipeline completed successfully!")
        print(f"\nData has been saved to:")
        print(f"  - Parquet files: {config.output_dir}/sentences/")
        print(f"  - Database: {config.database_config.get('path')}")
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
