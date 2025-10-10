"""Tests for quality filtering."""

import unittest
import tempfile
from pathlib import Path
import pandas as pd

from tatoeforge.utils.quality_filter import QualityFilter


class TestQualityFilter(unittest.TestCase):
    """Test QualityFilter class."""

    def test_empty_filter(self):
        """Test empty quality filter."""
        qf = QualityFilter()
        self.assertEqual(len(qf), 0)
        self.assertFalse(qf.is_quality(123))

    def test_quality_filter_with_ids(self):
        """Test quality filter with IDs."""
        quality_ids = {1, 2, 3, 4, 5}
        qf = QualityFilter(quality_ids)
        
        self.assertEqual(len(qf), 5)
        self.assertTrue(qf.is_quality(1))
        self.assertTrue(qf.is_quality(5))
        self.assertFalse(qf.is_quality(10))

    def test_quality_filter_from_file(self):
        """Test loading quality IDs from file."""
        quality_ids = [1, 2, 3, 4, 5]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            for qid in quality_ids:
                f.write(f"{qid}\n")
            temp_path = f.name
        
        try:
            qf = QualityFilter.from_file(temp_path)
            self.assertEqual(len(qf), 5)
            self.assertTrue(qf.is_quality(3))
            self.assertFalse(qf.is_quality(10))
        finally:
            Path(temp_path).unlink()

    def test_filter_dataframe(self):
        """Test filtering DataFrame."""
        quality_ids = {1, 2, 3}
        qf = QualityFilter(quality_ids)
        
        df = pd.DataFrame({
            'sentence_id': [1, 2, 3, 4, 5],
            'text': ['a', 'b', 'c', 'd', 'e']
        })
        
        filtered_df = qf.filter_dataframe(df)
        self.assertEqual(len(filtered_df), 3)
        self.assertListEqual(filtered_df['sentence_id'].tolist(), [1, 2, 3])

    def test_add_quality_ids(self):
        """Test adding quality IDs."""
        qf = QualityFilter({1, 2, 3})
        self.assertEqual(len(qf), 3)
        
        qf.add_quality_ids({4, 5, 6})
        self.assertEqual(len(qf), 6)
        self.assertTrue(qf.is_quality(5))

    def test_filter_empty_dataframe(self):
        """Test filtering with no quality IDs warns."""
        qf = QualityFilter()
        
        df = pd.DataFrame({
            'sentence_id': [1, 2, 3],
            'text': ['a', 'b', 'c']
        })
        
        # Should return unfiltered when no quality IDs
        filtered_df = qf.filter_dataframe(df)
        self.assertEqual(len(filtered_df), len(df))


if __name__ == '__main__':
    unittest.main()
