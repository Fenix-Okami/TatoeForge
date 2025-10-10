# TatoeForge Quick Reference

Quick reference guide for common operations.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Basic Commands

### Run Full Pipeline
```bash
# All languages (default)
tatoeforge run

# Specific languages
tatoeforge run --languages eng,fra,deu

# With config file
tatoeforge run --config my_config.json

# With custom output directory
tatoeforge run --languages eng --output-dir my_output
```

### Extract Only
```bash
# Extract to Parquet (no database)
tatoeforge extract --languages eng,spa

# With quality filter
tatoeforge extract --languages eng --quality-filter quality.txt
```

### Load Only
```bash
# Load from existing Parquet files
tatoeforge load --languages eng,fra

# Load to PostgreSQL
tatoeforge load --config postgres_config.json
```

## Configuration File Examples

### Minimal SQLite Config
```json
{
  "languages": ["eng"],
  "database": {
    "type": "sqlite",
    "path": "tatoeba.db"
  }
}
```

### Full-Featured Config
```json
{
  "languages": ["eng", "fra", "deu", "spa"],
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

### PostgreSQL Config
```json
{
  "languages": ["eng", "fra"],
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

## Python API Examples

### Basic Pipeline
```python
from tatoeforge import ETLPipeline
from tatoeforge.utils.config import Config

config = Config({'languages': ['eng', 'fra']})
pipeline = ETLPipeline(config)
pipeline.run()
```

### Extract Only
```python
from tatoeforge.extractors import TatoebaExtractor

extractor = TatoebaExtractor()
sentences = extractor.extract_sentences(languages=['eng', 'jpn'])
print(sentences.head())
```

### Transform to Parquet
```python
from tatoeforge.transformers import ParquetTransformer
import pandas as pd

transformer = ParquetTransformer(output_dir='output')
df = pd.DataFrame({
    'sentence_id': [1, 2, 3],
    'language': ['eng', 'eng', 'fra'],
    'text': ['Hello', 'World', 'Bonjour']
})
transformer.save_by_language(df, 'sentences')
```

### Load from Parquet
```python
from tatoeforge.transformers import ParquetTransformer

transformer = ParquetTransformer(output_dir='output')

# Load specific language
eng_df = transformer.load_parquet('sentences', language='eng')

# Load all languages
all_df = transformer.load_parquet('sentences')
```

### Quality Filtering
```python
from tatoeforge.utils.quality_filter import QualityFilter
import pandas as pd

# Load from file
qf = QualityFilter.from_file('quality_ids.txt')

# Filter DataFrame
df = pd.DataFrame({
    'sentence_id': [1, 2, 3, 4, 5],
    'text': ['a', 'b', 'c', 'd', 'e']
})
filtered = qf.filter_dataframe(df)
```

### SQLite Operations
```python
from tatoeforge.loaders import SQLiteLoader
import pandas as pd

loader = SQLiteLoader('tatoeba.db')

# Load data
df = pd.DataFrame({
    'sentence_id': [1, 2],
    'language': ['eng', 'fra'],
    'text': ['Hello', 'Bonjour']
})
loader.load_sentences(df)

# Query data
results = loader.query("SELECT * FROM sentences WHERE language = ?", ('eng',))
eng_sentences = loader.get_sentences_by_language('eng')
```

### PostgreSQL Operations
```python
from tatoeforge.loaders import PostgresLoader

loader = PostgresLoader(
    host='localhost',
    database='tatoeba',
    user='postgres',
    password='password'
)

# Same interface as SQLiteLoader
loader.load_sentences(df)
results = loader.get_sentences_by_language('eng')
```

## SQL Query Examples

### Basic Queries
```sql
-- Get all English sentences
SELECT * FROM sentences WHERE language = 'eng';

-- Count sentences by language
SELECT language, COUNT(*) as count 
FROM sentences 
GROUP BY language 
ORDER BY count DESC;

-- Get sentence with ID
SELECT * FROM sentences WHERE sentence_id = 123456;
```

### Translation Queries
```sql
-- Get all translations of a sentence
SELECT s2.* 
FROM sentences s1
JOIN links l ON s1.sentence_id = l.sentence_id
JOIN sentences s2 ON l.translation_id = s2.sentence_id
WHERE s1.sentence_id = 123456;

-- Get English-French translation pairs
SELECT s1.text as english, s2.text as french
FROM sentences s1
JOIN links l ON s1.sentence_id = l.sentence_id
JOIN sentences s2 ON l.translation_id = s2.sentence_id
WHERE s1.language = 'eng' AND s2.language = 'fra';
```

### Tag Queries
```sql
-- Get all sentences with a tag
SELECT s.* 
FROM sentences s
JOIN tags t ON s.sentence_id = t.sentence_id
WHERE t.tag_name = 'OK';

-- Count tags by sentence
SELECT sentence_id, COUNT(*) as tag_count
FROM tags
GROUP BY sentence_id
ORDER BY tag_count DESC;
```

## Pandas Examples

### Reading Parquet
```python
import pandas as pd

# Read single language
df = pd.read_parquet('output/sentences/eng.parquet')

# Filter long sentences
long = df[df['text'].str.len() > 50]

# Group by language
by_lang = df.groupby('language').size()
```

### Data Analysis
```python
import pandas as pd

df = pd.read_parquet('output/sentences/eng.parquet')

# Statistics
print(df['text'].str.len().describe())

# Word count
df['word_count'] = df['text'].str.split().str.len()

# Most common words
from collections import Counter
words = ' '.join(df['text']).lower().split()
Counter(words).most_common(10)
```

## Common Issues

### Command Not Found
```bash
# If "tatoeforge" command not found, use:
python -m tatoeforge.cli run --languages eng
```

### Memory Issues
```bash
# Reduce processes
tatoeforge run --num-processes 2

# Process one language at a time
tatoeforge run --languages eng
```

### Permission Errors
```bash
# Check write permissions
ls -la output/
ls -la data/

# Change ownership if needed
chmod 755 output/
```

### PostgreSQL Connection
```python
# Test connection
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    database='tatoeba',
    user='postgres',
    password='password'
)
print("Connected!")
conn.close()
```

## File Locations

### Default Directories
- Data: `data/`
- Output: `output/`
- Database: `tatoeba.db` (current directory)
- Logs: `tatoeforge.log` (current directory)

### Parquet Files
```
output/
├── sentences/
│   ├── eng.parquet
│   ├── fra.parquet
│   └── deu.parquet
└── links/
    └── ...
```

## Language Codes

| Code | Language |
|------|----------|
| eng | English |
| fra | French |
| deu | German |
| spa | Spanish |
| jpn | Japanese |
| cmn | Mandarin |
| rus | Russian |
| ita | Italian |
| por | Portuguese |
| ara | Arabic |
| nld | Dutch |
| pol | Polish |
| tur | Turkish |
| vie | Vietnamese |
| kor | Korean |

See [ISO 639-3](https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes) for complete list.

## Performance Tips

### Faster Extraction
- Extract specific languages only
- Use quality filter to reduce data
- Run during off-peak hours

### Faster Transform
- Increase `num_processes` (up to CPU count)
- Use SSD for output directory
- Process languages in batches

### Faster Loading
- Use batch loading (default)
- Create indexes after loading
- Use VACUUM after loading

### Disk Space
- Each language varies (eng ~2GB, fra ~500MB)
- Parquet uses ~70% of CSV size
- Plan for 3x raw data size total

## Logging

### Enable Verbose Logging
```bash
tatoeforge run --verbose
```

### Log File
Check `tatoeforge.log` for detailed logs.

### Python Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Testing

### Run Tests
```bash
python -m pytest tests/
```

### Test Specific Module
```bash
python -m pytest tests/test_config.py
```

### Test Coverage
```bash
pip install pytest-cov
python -m pytest --cov=tatoeforge tests/
```

## Getting Help

- Check `README.md` for full documentation
- Check `GETTING_STARTED.md` for tutorials
- Check `ARCHITECTURE.md` for design details
- Open an issue on GitHub
