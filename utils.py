"""
Utility functions for the agenda processing pipeline.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import re
from datetime import datetime

def setup_logging(log_file: str = "pipeline.log") -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page separators
    text = re.sub(r'-+ Page \d+ -+', '', text)
    # Remove header/footer noise
    text = re.sub(r'RECEIVED.*?SECRETARY', '', text, flags=re.DOTALL)
    # Clean up spacing
    text = text.strip()
    return text

def extract_meeting_date(text: str) -> str:
    """Extract meeting date from agenda text."""
    # Look for date patterns like "March 28, 2025" or "April 7, 2025"
    date_patterns = [
        r'([A-Z][a-z]+ \d{1,2}, \d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "Date not found"

def extract_meeting_type(text: str) -> str:
    """Extract meeting type from agenda text."""
    # Look for common meeting types
    if "SPECIAL CALLED" in text.upper():
        return "Special Called Meeting"
    elif "REGULAR MEETING" in text.upper():
        return "Regular Meeting"
    elif "BRIEFING" in text.upper():
        return "Briefing"
    else:
        return "Meeting"

def save_json(data: Dict[str, Any], file_path: Path) -> None:
    """Save data to JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_agenda_files(agendas_dir: Path) -> List[Path]:
    """Get all agenda text files."""
    return sorted(list(agendas_dir.glob("Agenda_*.txt")))

def extract_agenda_number(file_path: Path) -> int:
    """Extract agenda number from filename."""
    match = re.search(r'Agenda_(\d+)\.txt', file_path.name)
    return int(match.group(1)) if match else 0
