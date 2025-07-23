"""
Database consolidator for agenda processing results.
Creates unified databases from individual JSON files for easier querying and analysis.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
import pandas as pd

from config import OUTPUT_DIR
from utils import setup_logging, load_json

logger = setup_logging()

class DatabaseConsolidator:
    """Consolidate individual JSON files into unified databases for easier querying."""
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.db_dir = self.output_dir / "databases"
        self.db_dir.mkdir(exist_ok=True)
        
    def create_unified_summaries_json(self) -> Dict[str, Any]:
        """Create a unified JSON file with all summaries."""
        summaries_dir = self.output_dir / "summaries"
        summary_files = list(summaries_dir.glob("summary_*.json"))
        
        unified_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_summaries": 0,
                "source": "individual summary files"
            },
            "summaries": []
        }
        
        successful = 0
        failed = 0
        
        for summary_file in sorted(summary_files):
            try:
                data = load_json(summary_file)
                if "error" not in data:
                    unified_data["summaries"].append(data)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Could not load {summary_file}: {e}")
                failed += 1
        
        unified_data["metadata"]["total_summaries"] = successful
        unified_data["metadata"]["failed_summaries"] = failed
        
        # Save unified JSON
        unified_file = self.db_dir / "all_summaries.json"
        with open(unified_file, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Unified summaries saved to {unified_file}")
        return unified_data
    
    def create_unified_json_data(self) -> Dict[str, Any]:
        """Create a unified JSON file with all structured data."""
        json_dir = self.output_dir / "json_data"
        json_files = list(json_dir.glob("data_*.json"))
        
        unified_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_agendas": 0,
                "source": "individual JSON data files"
            },
            "agendas": []
        }
        
        successful = 0
        failed = 0
        
        for json_file in sorted(json_files):
            try:
                data = load_json(json_file)
                if "error" not in data:
                    unified_data["agendas"].append(data)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Could not load {json_file}: {e}")
                failed += 1
        
        unified_data["metadata"]["total_agendas"] = successful
        unified_data["metadata"]["failed_agendas"] = failed
        
        # Save unified JSON
        unified_file = self.db_dir / "all_structured_data.json"
        with open(unified_file, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Unified structured data saved to {unified_file}")
        return unified_data
    
    def create_sqlite_database(self) -> str:
        """Create a SQLite database for easy querying."""
        db_file = self.db_dir / "agendas.db"
        conn = sqlite3.connect(db_file)
        
        try:
            # Create tables
            conn.executescript("""
                DROP TABLE IF EXISTS summaries;
                DROP TABLE IF EXISTS meetings;
                DROP TABLE IF EXISTS agenda_items;
                DROP TABLE IF EXISTS attendees;
                DROP TABLE IF EXISTS keywords;
                DROP TABLE IF EXISTS financial_items;
                
                CREATE TABLE summaries (
                    agenda_number INTEGER PRIMARY KEY,
                    source_file TEXT,
                    summary TEXT,
                    original_length INTEGER,
                    summary_length INTEGER,
                    processed_at TEXT
                );
                
                CREATE TABLE meetings (
                    agenda_number INTEGER PRIMARY KEY,
                    source_file TEXT,
                    meeting_date TEXT,
                    meeting_time TEXT,
                    meeting_type TEXT,
                    organization TEXT,
                    location TEXT,
                    chair TEXT
                );
                
                CREATE TABLE agenda_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agenda_number INTEGER,
                    item_number TEXT,
                    title TEXT,
                    description TEXT,
                    presenter TEXT,
                    action_required TEXT,
                    FOREIGN KEY (agenda_number) REFERENCES meetings (agenda_number)
                );
                
                CREATE TABLE attendees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agenda_number INTEGER,
                    name TEXT,
                    role TEXT,
                    FOREIGN KEY (agenda_number) REFERENCES meetings (agenda_number)
                );
                
                CREATE TABLE keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agenda_number INTEGER,
                    keyword TEXT,
                    FOREIGN KEY (agenda_number) REFERENCES meetings (agenda_number)
                );
                
                CREATE TABLE financial_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agenda_number INTEGER,
                    description TEXT,
                    amount TEXT,
                    type TEXT,
                    FOREIGN KEY (agenda_number) REFERENCES meetings (agenda_number)
                );
            """)
            
            # Insert summary data
            summaries_dir = self.output_dir / "summaries"
            summary_files = list(summaries_dir.glob("summary_*.json"))
            
            for summary_file in summary_files:
                try:
                    data = load_json(summary_file)
                    if "error" not in data:
                        conn.execute("""
                            INSERT OR REPLACE INTO summaries 
                            (agenda_number, source_file, summary, original_length, summary_length, processed_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            data.get("agenda_number"),
                            data.get("source_file"),
                            data.get("summary"),
                            data.get("original_length"),
                            data.get("summary_length"),
                            data.get("processed_at")
                        ))
                except Exception as e:
                    logger.warning(f"Could not insert summary from {summary_file}: {e}")
            
            # Insert structured data
            json_dir = self.output_dir / "json_data"
            json_files = list(json_dir.glob("data_*.json"))
            
            for json_file in json_files:
                try:
                    data = load_json(json_file)
                    if "error" not in data:
                        extracted = data.get("extracted_data", {})
                        meeting_info = extracted.get("meeting_info", {})
                        attendees_info = extracted.get("attendees", {})
                        
                        # Insert meeting info
                        conn.execute("""
                            INSERT OR REPLACE INTO meetings 
                            (agenda_number, source_file, meeting_date, meeting_time, meeting_type, organization, location, chair)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data.get("agenda_number"),
                            data.get("source_file"),
                            meeting_info.get("date"),
                            meeting_info.get("time"),
                            meeting_info.get("type"),
                            meeting_info.get("organization"),
                            meeting_info.get("location"),
                            attendees_info.get("chair")
                        ))
                        
                        agenda_number = data.get("agenda_number")
                        
                        # Insert agenda items
                        for item in extracted.get("agenda_items", []):
                            conn.execute("""
                                INSERT INTO agenda_items 
                                (agenda_number, item_number, title, description, presenter, action_required)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                agenda_number,
                                item.get("item_number"),
                                item.get("title"),
                                item.get("description"),
                                item.get("presenter"),
                                item.get("action_required")
                            ))
                        
                        # Insert attendees
                        for presenter in attendees_info.get("presenters", []):
                            conn.execute("""
                                INSERT INTO attendees (agenda_number, name, role)
                                VALUES (?, ?, ?)
                            """, (agenda_number, presenter, "presenter"))
                        
                        for participant in attendees_info.get("participants", []):
                            conn.execute("""
                                INSERT INTO attendees (agenda_number, name, role)
                                VALUES (?, ?, ?)
                            """, (agenda_number, participant, "participant"))
                        
                        # Insert keywords
                        for keyword in extracted.get("keywords", []):
                            conn.execute("""
                                INSERT INTO keywords (agenda_number, keyword)
                                VALUES (?, ?)
                            """, (agenda_number, keyword))
                        
                        # Insert financial items
                        for item in extracted.get("financial_items", []):
                            conn.execute("""
                                INSERT INTO financial_items (agenda_number, description, amount, type)
                                VALUES (?, ?, ?, ?)
                            """, (
                                agenda_number,
                                item.get("description"),
                                item.get("amount"),
                                item.get("type")
                            ))
                        
                except Exception as e:
                    logger.warning(f"Could not insert data from {json_file}: {e}")
            
            conn.commit()
            logger.info(f"SQLite database created at {db_file}")
            
            # Get row counts
            cursor = conn.cursor()
            counts = {}
            for table in ["summaries", "meetings", "agenda_items", "attendees", "keywords", "financial_items"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            
            return str(db_file), counts
            
        finally:
            conn.close()
    
    def create_all_databases(self) -> Dict[str, Any]:
        """Create all unified database formats."""
        logger.info("Creating unified databases...")
        
        results = {}
        
        # Create unified JSON files
        print("📄 Creating unified summaries JSON...")
        results["summaries_json"] = self.create_unified_summaries_json()
        
        print("📊 Creating unified structured data JSON...")
        results["structured_json"] = self.create_unified_json_data()
        
        # Create SQLite database
        print("🗃️ Creating SQLite database...")
        db_file, counts = self.create_sqlite_database()
        results["sqlite"] = {"file": db_file, "row_counts": counts}
        
        print(f"\n🎉 Database consolidation complete!")
        print(f"📁 Databases saved in: {self.db_dir}")
        print(f"📄 Unified summaries: {results['summaries_json']['metadata']['total_summaries']} summaries")
        print(f"📊 Unified structured: {results['structured_json']['metadata']['total_agendas']} agendas")
        print(f"🗃️ SQLite database: {db_file}")
        for table, count in counts.items():
            print(f"   - {table}: {count} rows")
        
        return results

def main():
    """Main function to create unified databases."""
    consolidator = DatabaseConsolidator()
    consolidator.create_all_databases()

if __name__ == "__main__":
    main()
