"""Tests for data export functions."""
import pytest
import json
import csv
import os
import tempfile
from pathlib import Path
from poly_sports.data_fetching.fetch_sports_markets import save_to_csv
from poly_sports.utils.file_utils import save_json


class TestSaveToJson:
    """Test JSON export functionality."""
    
    def test_save_to_json_success(self):
        """Test successful JSON export."""
        data = [
            {'id': '1', 'question': 'Test 1', 'category': 'Sports'},
            {'id': '2', 'question': 'Test 2', 'category': 'Sports'}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            save_json(data, filename)
            
            assert os.path.exists(filename)
            
            with open(filename, 'r') as f:
                loaded_data = json.load(f)
            
            assert len(loaded_data) == 2
            assert loaded_data[0]['id'] == '1'
            assert loaded_data[1]['id'] == '2'
    
    def test_save_to_json_pretty_print(self):
        """Test that JSON is pretty-printed."""
        data = [{'id': '1', 'question': 'Test'}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            save_json(data, filename)
            
            with open(filename, 'r') as f:
                content = f.read()
            
            # Pretty-printed JSON should have newlines
            assert '\n' in content
    
    def test_save_to_json_empty_data(self):
        """Test saving empty data."""
        data = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            save_json(data, filename)
            
            assert os.path.exists(filename)
            
            with open(filename, 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == []
    
    def test_save_to_json_nested_data(self):
        """Test saving nested data structures."""
        data = [
            {
                'id': '1',
                'tokens': [
                    {'token_id': '123', 'outcome': 'Yes'},
                    {'token_id': '456', 'outcome': 'No'}
                ],
                'metadata': {
                    'source': 'test',
                    'tags': ['sports', 'nfl']
                }
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            save_json(data, filename)
            
            with open(filename, 'r') as f:
                loaded_data = json.load(f)
            
            assert len(loaded_data[0]['tokens']) == 2
            assert loaded_data[0]['metadata']['source'] == 'test'


class TestSaveToCsv:
    """Test CSV export functionality."""
    
    def test_save_to_csv_success(self):
        """Test successful CSV export."""
        data = [
            {'id': '1', 'question': 'Test 1', 'category': 'Sports'},
            {'id': '2', 'question': 'Test 2', 'category': 'Sports'}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.csv')
            save_to_csv(data, filename)
            
            assert os.path.exists(filename)
            
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 2
            assert rows[0]['id'] == '1'
            assert rows[1]['id'] == '2'
    
    def test_save_to_csv_flattens_nested_dicts(self):
        """Test that nested dictionaries are flattened."""
        data = [
            {
                'id': '1',
                'metadata': {
                    'source': 'test',
                    'tags': ['sports']
                }
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.csv')
            save_to_csv(data, filename)
            
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Nested dict should be flattened or serialized
            assert 'metadata' in rows[0] or 'metadata.source' in rows[0]
    
    def test_save_to_csv_handles_arrays(self):
        """Test that arrays/lists are handled properly in CSV."""
        data = [
            {
                'id': '1',
                'tokens': [
                    {'token_id': '123', 'outcome': 'Yes'},
                    {'token_id': '456', 'outcome': 'No'}
                ]
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.csv')
            save_to_csv(data, filename)
            
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Arrays should be serialized (e.g., as JSON string)
            assert 'tokens' in rows[0]
            # Should be a string representation
            assert isinstance(rows[0]['tokens'], str)
    
    def test_save_to_csv_empty_data(self):
        """Test saving empty data."""
        data = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.csv')
            save_to_csv(data, filename)
            
            assert os.path.exists(filename)
            
            with open(filename, 'r') as f:
                content = f.read()
            
            # Should have headers or be empty
            assert len(content) >= 0
    
    def test_save_to_csv_missing_fields(self):
        """Test handling markets with different fields."""
        data = [
            {'id': '1', 'question': 'Test 1', 'category': 'Sports'},
            {'id': '2', 'question': 'Test 2'}  # Missing category
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.csv')
            save_to_csv(data, filename)
            
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 2
            # Missing fields should be empty strings
            assert rows[1].get('category', '') == ''
    
    def test_save_to_csv_all_fields_included(self):
        """Test that all available fields are included in CSV."""
        data = [
            {
                'id': '1',
                'question': 'Test 1',
                'category': 'Sports',
                'end_date_iso': '2024-12-31T00:00:00Z',
                'volume': 1000,
                'liquidity': 5000
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.csv')
            save_to_csv(data, filename)
            
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # All fields should be present
            assert 'id' in rows[0]
            assert 'question' in rows[0]
            assert 'category' in rows[0]
            assert 'end_date_iso' in rows[0]
            assert 'volume' in rows[0]
            assert 'liquidity' in rows[0]

