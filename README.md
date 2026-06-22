# TatoeForge

An ETL (Extract, Transform, Load) pipeline for [Tatoeba](https://tatoeba.org) data with multiprocessing support. TatoeForge uses the `tatoebatools` library to extract sentence data, saves it to Parquet format indexed by language and sentence ID, applies optional quality filtering, and loads it into either SQLite or PostgreSQL databases.

## Features

- **Extract**: Download and extract Tatoeba sentences, links, and tags using `tatoebatools`
- **Transform**: Save data to Parquet format with language-based partitioning and indexing
- **Load**: Load data into SQLite or PostgreSQL databases
- **Vocabulary Retrieval**: Query sentences by normalized exact-token vocabulary matches
- **Translations**: Retrieve direct Tatoeba-linked translations by target language
- **Audio Metadata**: Extract Tatoeba audio metadata and optionally download reusable audio files
- **Grammar Placeholders**: Store curated grammar pattern annotations for later lookup
- **Multiprocessing**: Parallel processing for faster data transformation
- **Quality Filtering**: Optional filtering based on trusted quality sentence lists
- **Language Selection**: Extract and process specific languages
- **Configurable**: JSON-based configuration with CLI overrides

## Installation

### From source

```bash
git clone https://github.com/Fenix-Okami/TatoeForge.git
cd TatoeForge
pip install -e .
```

### Requirements

- Python 3.8+
- tatoebatools
- pandas
- pyarrow
- psycopg2-binary (for PostgreSQL support)
- tqdm

## Quick Start

### Basic Usage

Run the full ETL pipeline with default settings (SQLite database):

```bash
tatoeforge run
```

### Extract Specific Languages

Extract only English, French, and German sentences:

```bash
tatoeforge run --languages eng,fra,deu
```

### Using a Configuration File

Create a configuration file (see `config.example.json`) and run:

```bash
tatoeforge run --config my_config.json
```

## Configuration

### Configuration File

Create a JSON configuration file with the following structure:

```json
{
  "languages": ["eng", "fra", "deu"],
  "data_dir": "data",
  "output_dir": "output",
  "num_processes": 4,
  "extract_links": true,
  "extract_tags": true,
  "extract_audio": false,
  "download_audio": false,
  "audio_dir": "audio",
  "audio_reusable_only": true,
  "quality_filter": {
    "enabled": true,
    "file": "quality_sentences.txt"
  },
  "database": {
    "type": "sqlite",
    "path": "tatoeba.db"
  }
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `languages` | List of language codes to extract | All languages |
| `data_dir` | Directory for downloaded data | `data` |
| `output_dir` | Directory for Parquet files | `output` |
| `num_processes` | Number of parallel processes | CPU count |
| `extract_links` | Extract translation links | `false` |
| `extract_tags` | Extract sentence tags | `false` |
| `extract_audio` | Extract Tatoeba audio metadata | `false` |
| `download_audio` | Download audio files during extraction | `false` |
| `audio_dir` | Directory for downloaded audio files | `audio` |
| `audio_reusable_only` | Download only audio rows with non-empty reusable license metadata | `true` |
| `quality_filter.enabled` | Enable quality filtering | `false` |
| `quality_filter.file` | Path to quality IDs file | - |
| `database.type` | Database type (`sqlite` or `postgres`) | `sqlite` |
| `database.path` | SQLite database path | `tatoeba.db` |
| `database.host` | PostgreSQL host | `localhost` |
| `database.port` | PostgreSQL port | `5432` |
| `database.database` | PostgreSQL database name | `tatoeba` |
| `database.user` | PostgreSQL username | `postgres` |
| `database.password` | PostgreSQL password | - |

### PostgreSQL Configuration

For PostgreSQL, use a configuration like `config.postgres.example.json`:

```json
{
  "database": {
    "type": "postgres",
    "host": "localhost",
    "port": 5432,
    "database": "tatoeba",
    "user": "postgres",
    "password": "your_password"
  }
}
```

## CLI Commands

### Run Full Pipeline

```bash
tatoeforge run [options]
```

### Extract Only

Extract data and save to Parquet (no database loading):

```bash
tatoeforge extract --languages eng,spa,jpn
```

### Load Only

Load existing Parquet files into database:

```bash
tatoeforge load --languages eng,fra
```

### CLI Options

```
--config PATH              Path to JSON configuration file
--languages CODES          Comma-separated language codes
--output-dir DIR          Output directory for Parquet files
--data-dir DIR            Directory for downloaded data
--database-type TYPE      Database type (sqlite or postgres)
--database-path PATH      SQLite database path
--num-processes N         Number of processes
--quality-filter PATH     Path to quality IDs file
--extract-links           Extract translation links
--extract-tags            Extract sentence tags
--extract-audio           Extract Tatoeba audio metadata
--download-audio          Download audio files referenced by metadata
--audio-dir DIR           Directory for downloaded audio files
--audio-reusable-only     Download only rows with reusable license metadata
--include-unlicensed-audio Allow empty-license audio downloads
--verbose                 Enable verbose logging
```

## Quality Filtering

To filter sentences by quality, create a text file with one sentence ID per line:

```
123456
234567
345678
...
```

Then enable it in your configuration:

```json
{
  "quality_filter": {
    "enabled": true,
    "file": "quality_sentences.txt"
  }
}
```

Or via CLI:

```bash
tatoeforge run --quality-filter quality_sentences.txt
```

## Data Structure

### Parquet Format

Data is saved in Parquet format with the following structure:

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

Each Parquet file is:
- Indexed by sentence_id
- Compressed with Snappy
- Optimized for columnar queries

### Database Schema

#### Sentences Table

| Column | Type | Description |
|--------|------|-------------|
| sentence_id | INTEGER | Primary key |
| language | TEXT/VARCHAR | Language code |
| text | TEXT | Sentence text |
| username | TEXT/VARCHAR | Contributor username |
| date_added | TEXT/TIMESTAMP | Date added |
| date_modified | TEXT/TIMESTAMP | Date modified |

#### Links Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| sentence_id | INTEGER | Source sentence |
| translation_id | INTEGER | Translation sentence |

#### Tags Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| sentence_id | INTEGER | Tagged sentence |
| tag_name | TEXT/VARCHAR | Tag name |

#### Sentence Tokens Table

Generated from sentence text for fast exact-token lookup.

| Column | Type | Description |
|--------|------|-------------|
| sentence_id | INTEGER | Source sentence |
| language | TEXT/VARCHAR | Language code |
| token | TEXT | Original normalized-form token text |
| normalized_token | TEXT | NFKC + casefold lookup token |
| position | INTEGER | Token position in the sentence |

#### Grammar Tables

`grammar_patterns` stores curated pattern definitions. `sentence_grammar_patterns` links sentences to patterns with optional evidence text, confidence, and source metadata.

#### Sentence Audio Table

Stores Tatoeba audio metadata by `source` and `audio_id`, including sentence ID, contributor username, license, attribution URL, computed download URL, optional local path, download timestamp, and status.

## Programmatic Usage

### Python API

```python
from tatoeforge import ETLPipeline
from tatoeforge.utils.config import Config

# Create configuration
config = Config.from_file('config.json')

# Initialize pipeline
pipeline = ETLPipeline(config)

# Run full ETL
pipeline.run(languages=['eng', 'fra'])

# Or run steps individually
pipeline.extract(languages=['eng', 'fra'])
pipeline.load(languages=['eng', 'fra'])
```

### Extract Only

```python
from tatoeforge.extractors import TatoebaExtractor

extractor = TatoebaExtractor(data_dir='data')
sentences_df = extractor.extract_sentences(languages=['eng', 'jpn'])
```

### Transform Only

```python
from tatoeforge.transformers import ParquetTransformer

transformer = ParquetTransformer(output_dir='output', num_processes=4)
transformer.save_by_language(sentences_df, dataset_name='sentences')
```

### Load Only

```python
from tatoeforge.loaders import SQLiteLoader

loader = SQLiteLoader(database_path='tatoeba.db')
loader.load_sentences(sentences_df)
```

## Performance

### Multiprocessing

TatoeForge uses multiprocessing for parallel data transformation. By default, it uses all available CPU cores. You can control this with:

```bash
tatoeforge run --num-processes 8
```

Or in configuration:

```json
{
  "num_processes": 8
}
```

### Memory Considerations

- Large datasets can consume significant memory
- Consider processing languages in batches
- Parquet format provides good compression ratios

## Examples

### Example 1: Extract English and Japanese sentences

```bash
tatoeforge run --languages eng,jpn --output-dir output/en-jp
```

### Example 2: Load existing Parquet files to PostgreSQL

```bash
tatoeforge load --config config.postgres.json --languages eng,fra,deu
```

### Example 3: Extract with quality filter

```bash
tatoeforge extract --languages eng --quality-filter trusted_sentences.txt
```

## Troubleshooting

### Connection Issues

If you encounter database connection issues:

- **SQLite**: Ensure the directory exists and you have write permissions
- **PostgreSQL**: Verify credentials and ensure the database is running

### Memory Issues

If processing large datasets causes memory issues:

- Reduce `num_processes`
- Process languages individually
- Use quality filtering to reduce dataset size

### Tatoeba Data Issues

If extraction fails:

- Ensure you have internet connectivity
- The `tatoebatools` library downloads data from Tatoeba
- Check the `tatoebatools` documentation for updates

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Tatoeba](https://tatoeba.org) for providing the language data
- [tatoebatools](https://github.com/LBeaudoux/tatoebatools) for the data extraction library

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/Fenix-Okami/TatoeForge).
