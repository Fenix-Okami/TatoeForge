"""Tests for configuration management."""

import unittest
import json
import tempfile
from pathlib import Path

from tatoeforge.utils.config import Config


class TestConfig(unittest.TestCase):
    """Test Config class."""

    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        self.assertIsNotNone(config)
        self.assertEqual(config.database_type, 'sqlite')
        self.assertEqual(config.output_dir, 'output')
        self.assertEqual(config.data_dir, 'data')

    def test_config_from_dict(self):
        """Test configuration from dictionary."""
        config_dict = {
            'languages': ['eng', 'fra'],
            'num_processes': 8,
            'output_dir': 'my_output'
        }
        config = Config(config_dict)
        self.assertEqual(config.languages, ['eng', 'fra'])
        self.assertEqual(config.num_processes, 8)
        self.assertEqual(config.output_dir, 'my_output')

    def test_config_get_set(self):
        """Test get and set methods."""
        config = Config()
        config.set('test_key', 'test_value')
        self.assertEqual(config.get('test_key'), 'test_value')
        
        # Test nested keys
        config.set('nested.key', 'nested_value')
        self.assertEqual(config.get('nested.key'), 'nested_value')

    def test_config_from_file(self):
        """Test loading configuration from file."""
        config_dict = {
            'languages': ['eng'],
            'database': {
                'type': 'sqlite',
                'path': 'test.db'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_dict, f)
            temp_path = f.name
        
        try:
            config = Config.from_file(temp_path)
            self.assertEqual(config.languages, ['eng'])
            self.assertEqual(config.database_type, 'sqlite')
            self.assertEqual(config.get('database.path'), 'test.db')
        finally:
            Path(temp_path).unlink()

    def test_config_properties(self):
        """Test configuration properties."""
        config_dict = {
            'languages': ['eng', 'fra'],
            'output_dir': 'output',
            'data_dir': 'data',
            'num_processes': 4,
            'database': {
                'type': 'postgres',
                'host': 'localhost'
            },
            'quality_filter': {
                'enabled': True
            }
        }
        config = Config(config_dict)
        
        self.assertEqual(config.languages, ['eng', 'fra'])
        self.assertEqual(config.output_dir, 'output')
        self.assertEqual(config.data_dir, 'data')
        self.assertEqual(config.num_processes, 4)
        self.assertEqual(config.database_type, 'postgres')
        self.assertTrue(config.use_quality_filter)

    def test_config_defaults(self):
        """Test default values."""
        config = Config()
        
        self.assertIsNone(config.languages)
        self.assertEqual(config.output_dir, 'output')
        self.assertEqual(config.data_dir, 'data')
        self.assertEqual(config.database_type, 'sqlite')
        self.assertFalse(config.use_quality_filter)
        self.assertEqual(config.num_processes, 4)


if __name__ == '__main__':
    unittest.main()
