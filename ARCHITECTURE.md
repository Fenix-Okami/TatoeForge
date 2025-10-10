# TatoeForge Architecture

This document describes the architecture and design of TatoeForge.

## Overview

TatoeForge is an ETL (Extract, Transform, Load) pipeline for processing Tatoeba sentence data. It follows a modular architecture with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        TatoeForge ETL                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐      ┌──────────────┐      ┌──────────────┐│
│  │           │      │              │      │              ││
│  │  Extract  │─────▶│  Transform   │─────▶│     Load     ││
│  │           │      │              │      │              ││
│  └───────────┘      └──────────────┘      └──────────────┘│
│       │                    │                      │        │
│       │                    │                      │        │
│  ┌────▼─────────┐   ┌─────▼──────────┐   ┌──────▼───────┐│
│  │ Tatoeba API  │   │    Parquet     │   │   SQLite /   ││
│  │(tatoebatools)│   │   Files w/     │   │  PostgreSQL  ││
│  │              │   │   Indexing     │   │              ││
│  └──────────────┘   └────────────────┘   └──────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           Supporting Components                     │  │
│  │  • Configuration (JSON-based)                       │  │
│  │  • Quality Filter (Sentence ID filtering)           │  │
│  │  • Multiprocessing (Parallel processing)            │  │
│  │  • CLI Interface (Command-line tool)                │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Extractors (`tatoeforge/extractors/`)

**Purpose**: Extract data from Tatoeba using the tatoebatools library.

**Key Classes**:
- `TatoebaExtractor`: Main extractor class
  - `extract_sentences()`: Extract sentence data
  - `extract_links()`: Extract translation links
  - `extract_tags()`: Extract sentence tags
  - `extract_detailed_sentences()`: Extract with metadata

**Features**:
- Language filtering (specific languages or all)
- Progress logging
- Handles large datasets efficiently
- Returns pandas DataFrames

### 2. Transformers (`tatoeforge/transformers/`)

**Purpose**: Transform data and save to Parquet format with efficient indexing.

**Key Classes**:
- `ParquetTransformer`: Transform and save data
  - `save_by_language()`: Save with language partitioning
  - `save_with_partitioning()`: Save with custom partitioning
  - `load_parquet()`: Load Parquet data
  - `get_languages()`: List available languages

**Features**:
- Language-based partitioning for fast access
- Multiprocessing support for parallel processing
- Snappy compression for optimal size/speed
- Automatic indexing by sentence_id
- Dictionary encoding for string columns
- Statistics collection for query optimization

### 3. Loaders (`tatoeforge/loaders/`)

**Purpose**: Load data into databases (SQLite or PostgreSQL).

**Key Classes**:
- `SQLiteLoader`: SQLite database operations
  - `create_tables()`: Create schema with indexes
  - `load_sentences()`: Load sentence data
  - `load_links()`: Load translation links
  - `load_tags()`: Load sentence tags
  - `query()`: Execute SQL queries
  - `vacuum()`: Optimize database

- `PostgresLoader`: PostgreSQL database operations
  - Same interface as SQLiteLoader
  - Uses psycopg2 and SQLAlchemy
  - Supports connection pooling

**Features**:
- Automatic schema creation
- Batch loading with configurable chunk sizes
- Foreign key constraints
- Indexed columns for fast queries
- Database optimization (VACUUM)

### 4. Utilities (`tatoeforge/utils/`)

**Purpose**: Supporting utilities for configuration and data filtering.

**Key Classes**:
- `Config`: Configuration management
  - JSON-based configuration
  - Dot-notation for nested keys
  - Property accessors for common settings
  - Default values

- `QualityFilter`: Quality sentence filtering
  - Filter by sentence ID sets
  - Load from files
  - DataFrame filtering
  - Add/update quality IDs

### 5. ETL Pipeline (`tatoeforge/etl.py`)

**Purpose**: Orchestrate the complete ETL process.

**Key Class**:
- `ETLPipeline`: Main pipeline orchestrator
  - `extract()`: Run extraction step
  - `transform()`: Run transformation step
  - `load()`: Run loading step
  - `run()`: Run complete pipeline

**Features**:
- Configurable via Config object
- Automatic component initialization
- Error handling and logging
- Progress tracking

### 6. CLI (`tatoeforge/cli.py`)

**Purpose**: Command-line interface for easy usage.

**Commands**:
- `run`: Execute full ETL pipeline
- `extract`: Extract data only
- `load`: Load existing data

**Features**:
- Argument parsing
- Configuration file support
- CLI argument overrides
- Logging setup
- Error handling

## Data Flow

### Extract Phase
1. User specifies languages (or all)
2. TatoebaExtractor downloads data using tatoebatools
3. Data converted to pandas DataFrames
4. Optional: Apply quality filter
5. Return structured data

### Transform Phase
1. Receive DataFrames from extraction
2. Sort by sentence_id for indexing
3. Partition by language
4. Convert to PyArrow tables
5. Save as Parquet files with:
   - Snappy compression
   - Dictionary encoding
   - Statistics for optimization
6. Multiprocessing for parallel language processing

### Load Phase
1. Read Parquet files (by language or all)
2. Create database tables and indexes
3. Load data in batches (configurable chunk size)
4. Optimize database (VACUUM)

## Configuration

### Configuration Format

```json
{
  "languages": ["eng", "fra"],
  "data_dir": "data",
  "output_dir": "output",
  "num_processes": 4,
  "extract_links": true,
  "extract_tags": true,
  "quality_filter": {
    "enabled": true,
    "file": "quality_ids.txt"
  },
  "database": {
    "type": "sqlite",
    "path": "tatoeba.db"
  }
}
```

### Configuration Priority

1. Default values (hardcoded)
2. Configuration file values
3. CLI argument values (highest priority)

## Multiprocessing Strategy

TatoeForge uses Python's `multiprocessing` module for parallel processing:

1. **Transform Phase**: Process multiple languages in parallel
   - Each language processed independently
   - Number of processes configurable
   - Default: CPU count

2. **Process Pool**: Uses `multiprocessing.Pool`
   - Shared across language processing
   - Efficient resource utilization

3. **Memory Management**:
   - Process data in chunks
   - Clear memory after each language
   - Configurable chunk sizes for loading

## Database Schema

### Sentences Table
```sql
CREATE TABLE sentences (
    sentence_id INTEGER PRIMARY KEY,
    language VARCHAR(10) NOT NULL,
    text TEXT NOT NULL,
    username VARCHAR(100),
    date_added TIMESTAMP,
    date_modified TIMESTAMP
);
CREATE INDEX idx_sentences_language ON sentences(language);
```

### Links Table
```sql
CREATE TABLE links (
    id INTEGER/SERIAL PRIMARY KEY,
    sentence_id INTEGER NOT NULL,
    translation_id INTEGER NOT NULL,
    FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
    FOREIGN KEY (translation_id) REFERENCES sentences(sentence_id)
);
CREATE INDEX idx_links_sentence_id ON links(sentence_id);
CREATE INDEX idx_links_translation_id ON links(translation_id);
```

### Tags Table
```sql
CREATE TABLE tags (
    id INTEGER/SERIAL PRIMARY KEY,
    sentence_id INTEGER NOT NULL,
    tag_name VARCHAR(100) NOT NULL,
    FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id)
);
CREATE INDEX idx_tags_sentence_id ON tags(sentence_id);
```

## Parquet Format

### Directory Structure
```
output/
├── sentences/
│   ├── eng.parquet
│   ├── fra.parquet
│   └── deu.parquet
├── links/
│   └── ...
└── tags/
    └── ...
```

### Parquet File Properties
- **Compression**: Snappy (good balance of speed/size)
- **Encoding**: Dictionary for string columns
- **Statistics**: Enabled for query optimization
- **Index**: Sorted by sentence_id

## Error Handling

### Extraction Errors
- Network issues: Retry with exponential backoff
- Invalid data: Log and skip
- Missing languages: Warning only

### Transform Errors
- Disk space issues: Check before write
- Invalid data: Validate before save
- Multiprocessing errors: Log and continue with remaining

### Load Errors
- Connection failures: Retry with backoff
- Duplicate data: Use upsert or skip
- Schema mismatches: Recreate tables if needed

## Performance Considerations

### Extraction
- Download speed depends on network and Tatoeba server
- Cache downloaded data in data_dir
- Process languages incrementally

### Transform
- Multiprocessing speeds up language partitioning
- Parquet compression reduces disk usage
- Indexing improves query performance

### Load
- Batch loading faster than row-by-row
- Indexes created after load (faster than during)
- VACUUM optimizes database after load

### Memory
- Process languages independently
- Use chunked loading
- Clear intermediate data

### Disk
- Parquet compression ~70% of CSV size
- Database indexes increase size ~20%
- Plan for 2-3x raw data size

## Extension Points

### Adding New Extractors
1. Create new class in `extractors/`
2. Implement extraction methods returning DataFrames
3. Register in `__init__.py`

### Adding New Loaders
1. Create new class in `loaders/`
2. Implement `load_sentences()`, `load_links()`, `load_tags()`
3. Register in `__init__.py`

### Custom Transformers
1. Create new class in `transformers/`
2. Implement transformation logic
3. Integrate into ETL pipeline

### Custom Filters
1. Create new filter class
2. Implement `filter_dataframe()` method
3. Integrate into extraction phase

## Testing Strategy

### Unit Tests
- Config management
- Quality filtering
- Data validation

### Integration Tests
- End-to-end pipeline (small dataset)
- Database operations
- Parquet operations

### Performance Tests
- Large dataset handling
- Memory usage profiling
- Multiprocessing efficiency

## Future Enhancements

1. **Incremental Updates**: Update only changed data
2. **Data Validation**: Schema validation with Pydantic
3. **More Databases**: MySQL, MongoDB support
4. **Cloud Storage**: S3, GCS for Parquet files
5. **Streaming**: Process data in streaming mode
6. **Web UI**: Web interface for monitoring
7. **API**: REST API for programmatic access
8. **Caching**: Redis for query caching

## Dependencies

### Core Dependencies
- `tatoebatools`: Data extraction from Tatoeba
- `pandas`: Data manipulation
- `pyarrow`: Parquet file operations
- `sqlalchemy`: Database abstraction
- `psycopg2-binary`: PostgreSQL driver
- `tqdm`: Progress bars

### Development Dependencies
- `pytest`: Testing framework
- `black`: Code formatting
- `flake8`: Linting
- `mypy`: Type checking

## License

Apache License 2.0 - See LICENSE file for details.
