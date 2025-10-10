# Contributing to TatoeForge

Thank you for your interest in contributing to TatoeForge! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Features

For feature requests, open an issue with:
- Clear description of the feature
- Use cases and benefits
- Possible implementation approach
- Any related existing features

### Submitting Changes

1. **Fork the Repository**
   ```bash
   git clone https://github.com/Fenix-Okami/TatoeForge.git
   cd TatoeForge
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make Your Changes**
   - Write clean, readable code
   - Follow existing code style
   - Add tests for new features
   - Update documentation as needed

4. **Test Your Changes**
   ```bash
   # Run tests
   python -m pytest tests/
   
   # Check syntax
   python -m py_compile tatoeforge/**/*.py
   ```

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

6. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Explain testing performed

## Development Setup

### Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### Install Development Dependencies

```bash
pip install pytest pytest-cov black flake8 mypy
```

### Run Tests

```bash
# All tests
python -m pytest tests/

# With coverage
python -m pytest --cov=tatoeforge tests/

# Specific test file
python -m pytest tests/test_config.py
```

### Code Formatting

```bash
# Format code with black
black tatoeforge/ tests/

# Check with flake8
flake8 tatoeforge/ tests/
```

### Type Checking

```bash
mypy tatoeforge/
```

## Code Style

### Python Style
- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for all public functions/classes
- Keep functions focused and small
- Use meaningful variable names

### Example
```python
def extract_sentences(self, languages: Optional[List[str]] = None) -> pd.DataFrame:
    """Extract sentences from Tatoeba.
    
    Args:
        languages: List of language codes to extract (e.g., ['eng', 'fra'])
                  If None, extracts all languages
        
    Returns:
        DataFrame with columns: sentence_id, language, text
    """
    # Implementation
    pass
```

### Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line: brief summary (50 chars or less)
- Blank line, then detailed description if needed

Example:
```
Add quality filtering for sentences

- Implement QualityFilter class
- Add file-based ID loading
- Integrate with extraction pipeline
- Add tests for filtering logic
```

## Project Structure

```
TatoeForge/
├── tatoeforge/          # Main package
│   ├── extractors/      # Data extraction modules
│   ├── transformers/    # Data transformation modules
│   ├── loaders/         # Database loading modules
│   ├── utils/           # Utility modules
│   ├── etl.py          # Main ETL orchestrator
│   └── cli.py          # Command-line interface
├── tests/              # Test suite
├── examples/           # Example scripts
├── docs/               # Documentation
└── README.md          # Main documentation
```

## Adding New Features

### New Extractor
1. Create class in `tatoeforge/extractors/`
2. Implement extraction methods
3. Add to `__init__.py`
4. Write tests
5. Update documentation

### New Loader
1. Create class in `tatoeforge/loaders/`
2. Implement loading methods
3. Add to `__init__.py`
4. Write tests
5. Update documentation

### New Transformer
1. Create class in `tatoeforge/transformers/`
2. Implement transformation logic
3. Add to `__init__.py`
4. Write tests
5. Update documentation

## Testing Guidelines

### Writing Tests
- Use pytest framework
- Test both success and failure cases
- Use descriptive test names
- Mock external dependencies
- Clean up test data

### Example
```python
import unittest
from tatoeforge.utils.config import Config

class TestConfig(unittest.TestCase):
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        self.assertEqual(config.database_type, 'sqlite')
    
    def test_config_override(self):
        """Test configuration override with custom values."""
        config = Config({'database': {'type': 'postgres'}})
        self.assertEqual(config.database_type, 'postgres')
```

## Documentation

### Docstrings
- Use Google style docstrings
- Document all parameters and return values
- Include usage examples for complex functions
- Document exceptions that may be raised

### README Updates
- Update README.md for user-facing changes
- Add examples for new features
- Update installation instructions if needed

### Architecture Documentation
- Update ARCHITECTURE.md for design changes
- Document new components
- Explain integration points

## Pull Request Process

1. **Before Submitting**
   - Run all tests
   - Update documentation
   - Add changelog entry
   - Rebase on latest main

2. **PR Description**
   - What: What changes are included
   - Why: Why these changes are needed
   - How: How the changes work
   - Testing: What testing was done

3. **Review Process**
   - Address review comments
   - Update PR as needed
   - Be responsive to feedback

4. **After Merge**
   - Delete your branch
   - Pull latest main
   - Celebrate! 🎉

## Getting Help

- Open an issue for questions
- Check existing issues and PRs
- Read the documentation
- Ask in discussions

## Recognition

Contributors will be recognized in:
- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing to TatoeForge!
