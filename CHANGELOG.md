# Changelog

All notable changes to TatoeForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-10

### Added
- Initial release of TatoeForge
- ETL pipeline for Tatoeba data extraction, transformation, and loading
- Support for tatoebatools library integration
- Parquet format output with language-based indexing
- SQLite database loader with automatic schema creation
- PostgreSQL database loader with connection pooling
- Quality filtering based on trusted sentence ID lists
- Language selection (specific languages or all)
- Multiprocessing support for parallel data transformation
- JSON-based configuration system with CLI overrides
- Command-line interface with three modes:
  - `run`: Full ETL pipeline
  - `extract`: Extract data only
  - `load`: Load existing data
- Configuration file support (JSON format)
- Comprehensive documentation:
  - README with installation and usage
  - GETTING_STARTED guide with examples
  - ARCHITECTURE document with design details
  - QUICK_REFERENCE for common operations
- Example configuration files for SQLite and PostgreSQL
- Unit tests for configuration and quality filtering
- Example Python scripts demonstrating API usage
- Logging support with file and console output

### Features
- Extract sentences, translation links, and tags from Tatoeba
- Transform data to optimized Parquet format
- Load data into SQLite or PostgreSQL databases
- Filter by language codes (ISO 639-3)
- Filter by quality sentence IDs
- Parallel processing with configurable worker count
- Batch loading with configurable chunk sizes
- Automatic database optimization (VACUUM)
- Progress tracking and logging
- Error handling and recovery

### Technical Details
- Python 3.8+ support
- PyArrow for efficient Parquet operations
- Pandas for data manipulation
- psycopg2-binary for PostgreSQL support
- SQLAlchemy for database abstraction
- Multiprocessing module for parallel processing
- Snappy compression for Parquet files
- Dictionary encoding for string columns
- Indexed Parquet files for fast queries
- Foreign key constraints in database
- Indexed columns for optimized queries

[0.1.0]: https://github.com/Fenix-Okami/TatoeForge/releases/tag/v0.1.0
