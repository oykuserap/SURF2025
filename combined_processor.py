"""
Combined processor for generating summaries and extracting JSON data in one pass.
This module processes agenda files to create both summaries and structured data efficiently.
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any

from config import OUTPUT_DIR, AGENDAS_DIR
from utils import setup_logging, get_agenda_files, load_json, save_json
from summary_generator import SummaryGenerator
from json_extractor import JSONExtractor

logger = setup_logging()

class CombinedProcessor:
    """
    Processes agenda files to generate both summaries and JSON data in one pass.
    Includes batch saving and resume functionality.
    """
    
    def __init__(self):
        self.summary_generator = SummaryGenerator()
        self.json_extractor = JSONExtractor()
        self.summaries_dir = OUTPUT_DIR / "summaries"
        self.json_dir = OUTPUT_DIR / "json_data"
        self.combined_output_file = self.json_dir / "combined_results.json"
        
        # Create output directories
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)
        
        self.batch_size = 10  # Save every 10 files
        
    def get_processed_files(self) -> Dict[str, set]:
        """Get sets of already processed files."""
        processed = {
            'summaries': set(),
            'json': set(),
            'combined': set()
        }
        
        # Check individual summary files
        if self.summaries_dir.exists():
            for file in self.summaries_dir.glob("summary_*.json"):
                try:
                    # Extract agenda number from filename like "summary_102.json"
                    agenda_num = int(file.stem.split('_')[1])
                    processed['summaries'].add(agenda_num)
                except (ValueError, IndexError):
                    continue
        
        # Check individual JSON files
        if self.json_dir.exists():
            for file in self.json_dir.glob("data_*.json"):
                try:
                    # Extract agenda number from filename like "data_102.json"
                    agenda_num = int(file.stem.split('_')[1])
                    processed['json'].add(agenda_num)
                except (ValueError, IndexError):
                    continue
        
        # Check combined results file
        if self.combined_output_file.exists():
            try:
                combined_data = load_json(self.combined_output_file)
                if combined_data and 'results' in combined_data:
                    for result in combined_data['results']:
                        if 'agenda_number' in result:
                            processed['combined'].add(result['agenda_number'])
            except Exception as e:
                logger.warning(f"Could not read combined results file: {e}")
        
        return processed
    
    def process_single_agenda(self, agenda_file: Path) -> Dict[str, Any]:
        """Process a single agenda file for both summary and JSON extraction."""
        try:
            # Extract agenda number from filename
            agenda_number = int(agenda_file.stem.split('_')[1])
        except (ValueError, IndexError):
            return {
                'agenda_number': None,
                'source_file': agenda_file.name,
                'summary_result': {'error': f"Could not parse agenda number from filename: {agenda_file.name}"},
                'json_result': {'error': f"Could not parse agenda number from filename: {agenda_file.name}"},
                'error': f"Could not parse agenda number from filename: {agenda_file.name}"
            }
        
        result = {
            'agenda_number': agenda_number,
            'source_file': agenda_file.name,
            'summary_result': None,
            'json_result': None
        }
        
        # Process summary and save individual file
        try:
            summary_result = self.summary_generator.process_agenda_file(agenda_file)
            result['summary_result'] = summary_result
            
            # Also save individual summary file
            if summary_result and 'error' not in summary_result:
                summary_output_file = self.summaries_dir / f"summary_{agenda_number}.json"
                save_json(summary_result, summary_output_file)
                
        except Exception as e:
            logger.error(f"Error processing summary for {agenda_file.name}: {e}")
            result['summary_result'] = {'error': str(e)}
        
        # Process JSON extraction and save individual file
        try:
            json_result = self.json_extractor.process_agenda_file(agenda_file)
            result['json_result'] = json_result
            
            # Also save individual JSON file
            if json_result and 'error' not in json_result:
                json_output_file = self.json_dir / f"data_{agenda_number}.json"
                save_json(json_result, json_output_file)
                
        except Exception as e:
            logger.error(f"Error processing JSON for {agenda_file.name}: {e}")
            result['json_result'] = {'error': str(e)}
        
        return result
    
    def save_combined_results(self, results: List[Dict[str, Any]]) -> None:
        """Save combined results to a single JSON file."""
        try:
            # Load existing data if file exists
            existing_data = {'results': []}
            if self.combined_output_file.exists():
                existing_data = load_json(self.combined_output_file) if self.combined_output_file.exists() else {'results': []}
            
            # Create a lookup for existing results by agenda number
            existing_lookup = {}
            for result in existing_data.get('results', []):
                if 'agenda_number' in result:
                    existing_lookup[result['agenda_number']] = result
            
            # Update with new results
            for new_result in results:
                if 'agenda_number' in new_result and new_result['agenda_number'] is not None:
                    existing_lookup[new_result['agenda_number']] = new_result
            
            # Convert back to list and sort by agenda number
            all_results = list(existing_lookup.values())
            all_results.sort(key=lambda x: x.get('agenda_number', 0))
            
            # Save updated data
            combined_data = {
                'metadata': {
                    'total_agendas': len(all_results),
                    'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'description': 'Combined processing results with both summaries and JSON extraction'
                },
                'results': all_results
            }
            
            save_json(combined_data, self.combined_output_file)
            logger.info(f"Saved combined results to {self.combined_output_file}")
            
        except Exception as e:
            logger.error(f"Error saving combined results: {e}")
    
    def process_all_agendas(self, limit: int = None) -> Dict[str, Any]:
        """
        Process all agenda files with combined summary and JSON extraction.
        Includes batch saving and resume functionality.
        """
        logger.info("Starting combined processing (summaries + JSON extraction)...")
        
        # Get all agenda files
        agenda_files = get_agenda_files(AGENDAS_DIR)
        if limit:
            agenda_files = agenda_files[:limit]
        
        # Get already processed files
        processed = self.get_processed_files()
        
        # Filter out files that have been processed AND have individual files
        files_to_process = []
        for agenda_file in agenda_files:
            try:
                agenda_number = int(agenda_file.stem.split('_')[1])
                
                # Check if both individual summary and JSON files exist
                summary_file = self.summaries_dir / f"summary_{agenda_number}.json"
                json_file = self.json_dir / f"data_{agenda_number}.json"
                
                # Only skip if both individual files exist AND it's in combined results
                if (summary_file.exists() and json_file.exists() and 
                    agenda_number in processed['combined']):
                    continue  # Skip this file
                else:
                    files_to_process.append(agenda_file)
                    
            except (ValueError, IndexError):
                # Include files we can't parse the number from
                files_to_process.append(agenda_file)
        
        if not files_to_process:
            logger.info("All files have already been processed in combined mode")
            return {
                'summary_stats': {'successful': 0, 'failed': 0, 'skipped': len(agenda_files)},
                'json_stats': {'successful': 0, 'failed': 0, 'skipped': len(agenda_files)}
            }
        
        logger.info(f"Processing {len(files_to_process)} files (skipping {len(agenda_files) - len(files_to_process)} already processed)")
        
        # Process files in batches
        all_results = []
        summary_successful = 0
        summary_failed = 0
        json_successful = 0
        json_failed = 0
        
        for i, agenda_file in enumerate(files_to_process, 1):
            logger.info(f"Processing {agenda_file.name} ({i}/{len(files_to_process)})")
            
            # Process the file
            result = self.process_single_agenda(agenda_file)
            all_results.append(result)
            
            # Update stats
            if result['summary_result'] and 'error' not in result['summary_result']:
                summary_successful += 1
            else:
                summary_failed += 1
            
            if result['json_result'] and 'error' not in result['json_result']:
                json_successful += 1
            else:
                json_failed += 1
            
            # Save batch if needed
            if i % self.batch_size == 0 or i == len(files_to_process):
                logger.info(f"Saving batch of {len(all_results)} results...")
                self.save_combined_results(all_results)
                all_results = []  # Clear for next batch
        
        logger.info("Combined processing complete")
        
        return {
            'summary_stats': {
                'successful': summary_successful,
                'failed': summary_failed,
                'skipped': len(agenda_files) - len(files_to_process)
            },
            'json_stats': {
                'successful': json_successful,
                'failed': json_failed,
                'skipped': len(agenda_files) - len(files_to_process)
            }
        }
