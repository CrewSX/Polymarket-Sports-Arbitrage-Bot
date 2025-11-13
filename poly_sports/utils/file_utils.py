"""File I/O utilities for JSON operations."""
import json
from pathlib import Path
from typing import Any


def load_json(filepath: str) -> Any:
    """
    Load data from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Parsed JSON data (dict, list, etc.)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(
    data: Any,
    filepath: str,
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Save data to JSON file with pretty printing.
    
    Args:
        data: Data to save (dict, list, etc.)
        filepath: Output file path
        indent: JSON indentation level (default: 2)
        ensure_ascii: Whether to ensure ASCII-only output (default: False)
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

