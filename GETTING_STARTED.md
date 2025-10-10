# Getting Started with TatoeForge

This guide will help you get started with TatoeForge quickly.

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install TatoeForge

```bash
pip install -e .
```

## Basic Usage

### Example 1: Extract English Sentences Only

This is the simplest way to get started - extract English sentences only:

```bash
tatoeforge run --languages eng --database-path my_tatoeba.db
```

This will:
1. Download English sentences from Tatoeba
2. Save them to Parquet files in the `output/` directory
3. Load them into `my_tatoeba.db` SQLite database

### Example 2: Multiple Languages

Extract multiple languages:

```bash
tatoeforge run --languages eng,fra,deu,spa,jpn
```

### Example 3: Using a Configuration File

Create a file `my_config.json`:

```json
{
  "languages": ["eng", "fra"],
  "data_dir": "data",
  "output_dir": "output",
  "num_processes": 4,
  "database": {
    "type": "sqlite",
    "path": "tatoeba.db"
  }
}
```

Then run:

```bash
tatoeforge run --config my_config.json
```

### Example 4: Extract Only (No Database)

If you only want the Parquet files and don't need a database:

```bash
tatoeforge extract --languages eng,jpn
```

Your data will be in `output/sentences/` as `eng.parquet` and `jpn.parquet`.

### Example 5: Load Existing Parquet Files

If you already have Parquet files and want to load them into a database:

```bash
tatoeforge load --languages eng,fra --database-path my_db.db
```

## Working with the Data

### Querying with Python

```python
import pandas as pd

# Read from Parquet
df = pd.read_parquet('output/sentences/eng.parquet')
print(df.head())

# Filter sentences
long_sentences = df[df['text'].str.len() > 50]
```

### Querying SQLite

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('tatoeba.db')

# Get all English sentences
df = pd.read_sql_query("SELECT * FROM sentences WHERE language = 'eng'", conn)

# Get sentence with translations
query = """
    SELECT s1.text as original, s2.text as translation, s2.language
    FROM sentences s1
    JOIN links l ON s1.sentence_id = l.sentence_id
    JOIN sentences s2 ON l.translation_id = s2.sentence_id
    WHERE s1.sentence_id = ?
"""
translations = pd.read_sql_query(query, conn, params=(123456,))

conn.close()
```

## Advanced Usage

### Quality Filtering

If you have a list of trusted sentence IDs, create a file `quality_ids.txt`:

```
123456
234567
345678
```

Then run:

```bash
tatoeforge run --languages eng --quality-filter quality_ids.txt
```

### With PostgreSQL

First, set up your PostgreSQL database:

```sql
CREATE DATABASE tatoeba;
```

Create `postgres_config.json`:

```json
{
  "languages": ["eng", "fra"],
  "database": {
    "type": "postgres",
    "host": "localhost",
    "port": 5432,
    "database": "tatoeba",
    "user": "your_username",
    "password": "your_password"
  }
}
```

Run:

```bash
tatoeforge run --config postgres_config.json
```

### Multiprocessing

By default, TatoeForge uses all CPU cores. To control this:

```bash
tatoeforge run --languages eng,fra --num-processes 4
```

### Extract Links and Tags

To also extract translation links and tags:

```bash
tatoeforge run --languages eng --extract-links --extract-tags
```

## Troubleshooting

### "tatoeforge: command not found"

Make sure you installed the package:

```bash
pip install -e .
```

Or run directly with Python:

```bash
python -m tatoeforge.cli run --languages eng
```

### Memory Issues

If you run out of memory:

1. Process fewer languages at once
2. Reduce the number of processes: `--num-processes 2`
3. Process languages one at a time

### Slow Downloads

The first run will download data from Tatoeba, which can take time depending on:
- Number of languages
- Your internet connection
- Tatoeba server load

Subsequent runs will be faster as data is cached.

## Next Steps

- Read the full [README.md](README.md) for more details
- Check out the example configurations in `config.example.json`
- Explore the Python API for programmatic access
- Join the community and contribute!

## Language Codes

Common language codes:
- `eng` - English
- `fra` - French (Français)
- `deu` - German (Deutsch)
- `spa` - Spanish (Español)
- `jpn` - Japanese (日本語)
- `cmn` - Mandarin Chinese (中文)
- `rus` - Russian (Русский)
- `ita` - Italian (Italiano)
- `por` - Portuguese (Português)
- `ara` - Arabic (العربية)

For a full list, see the [ISO 639-3 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes).
