"""
Main pipeline orchestrator for the agenda processing system.
Coordinates the entire workflow: summaries → JSON extraction → embeddings → chatbot.
"""
import argparse
import sys
from pathlib import Path

from config import AGENDAS_DIR, OUTPUT_DIR, VECTOR_DB_DIR
from utils import setup_logging, get_agenda_files
from summary_generator import SummaryGenerator
from json_extractor import JSONExtractor
from embedding_generator import EmbeddingGenerator
from combined_processor import CombinedProcessor
from database_consolidator import DatabaseConsolidator

logger = setup_logging()

class AgendaPipeline:
    """Main pipeline coordinator for processing agenda files."""
    
    def __init__(self):
        self.summary_generator = SummaryGenerator()
        self.json_extractor = JSONExtractor()
        self.embedding_generator = EmbeddingGenerator()
        self.combined_processor = CombinedProcessor()
        self.database_consolidator = DatabaseConsolidator()
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        logger.info("Checking prerequisites...")
        
        # Check if agenda directory exists
        if not AGENDAS_DIR.exists():
            logger.error(f"Agendas directory not found: {AGENDAS_DIR}")
            return False
        
        # Check if there are agenda files
        agenda_files = get_agenda_files(AGENDAS_DIR)
        if not agenda_files:
            logger.error(f"No agenda files found in {AGENDAS_DIR}")
            return False
        
        logger.info(f"Found {len(agenda_files)} agenda files")
        
        # Check OpenAI API key
        from config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not found. Please check your .env file.")
            return False
        
        logger.info("Prerequisites check passed")
        return True
    
    def run_summaries(self, limit: int = None) -> bool:
        """Step 1: Generate summaries for agenda files."""
        logger.info("Step 1: Generating summaries...")
        
        try:
            results = self.summary_generator.process_all_agendas(limit=limit)
            successful = len([r for r in results if "error" not in r])
            failed = len([r for r in results if "error" in r])
            
            logger.info(f"Summary generation complete: {successful} successful, {failed} failed")
            
            if successful == 0:
                logger.error("No summaries were generated successfully")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in summary generation: {e}")
            return False
    
    def run_json_extraction(self, limit: int = None) -> bool:
        """Step 2: Extract structured data from agenda files."""
        logger.info("Step 2: Extracting structured data...")
        
        try:
            results = self.json_extractor.process_all_agendas(limit=limit)
            successful = len([r for r in results if "error" not in r])
            failed = len([r for r in results if "error" in r])
            
            logger.info(f"JSON extraction complete: {successful} successful, {failed} failed")
            
            if successful == 0:
                logger.error("No JSON data was extracted successfully")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in JSON extraction: {e}")
            return False
    
    def run_database_consolidation(self) -> bool:
        """Step 3: Create unified databases from individual JSON files."""
        logger.info("Step 3: Creating unified databases...")
        
        try:
            results = self.database_consolidator.create_all_databases()
            
            summaries_count = results['summaries_json']['metadata']['total_summaries']
            structured_count = results['structured_json']['metadata']['total_agendas']
            
            logger.info(f"Database consolidation complete:")
            logger.info(f"  Unified summaries: {summaries_count}")
            logger.info(f"  Unified structured data: {structured_count}")
            logger.info(f"  SQLite database created with multiple tables")
            
            if summaries_count > 0 or structured_count > 0:
                return True
            else:
                logger.error("No data was consolidated")
                return False
            
        except Exception as e:
            logger.error(f"Error in database consolidation: {e}")
            return False

    def run_embeddings(self) -> bool:
        """Step 4: Generate embeddings for summaries and structured data."""
        logger.info("Step 4: Generating embeddings...")
        
        try:
            # Generate summary embeddings
            summary_results = self.embedding_generator.process_all_summaries()
            
            # Generate JSON embeddings
            json_results = self.embedding_generator.process_all_json_data()
            
            # Generate bond document embeddings
            bond_results = self.embedding_generator.process_bond_documents()
            
            # Get stats
            stats = self.embedding_generator.get_collection_stats()
            
            logger.info(f"Embeddings generation complete:")
            logger.info(f"  Summaries: {summary_results['successful']} successful, {summary_results['failed']} failed")
            logger.info(f"  JSON data: {json_results['successful']} successful, {json_results['failed']} failed")
            logger.info(f"  Bond docs: {bond_results['successful']} successful, {bond_results['failed']} failed")
            logger.info(f"  Total documents in vector DB: {stats['summaries_collection']['count'] + stats['json_collection']['count']}")
            
            if summary_results['successful'] == 0 and json_results['successful'] == 0:
                logger.error("No embeddings were generated successfully")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in embedding generation: {e}")
            return False
    
    def run_combined_processing(self, limit: int = None) -> bool:
        """Run combined summary + JSON extraction + embeddings processing."""
        logger.info("Running combined processing (summaries + JSON extraction + embeddings)...")
        
        try:
            # Step 1: Process summaries and JSON data together
            results = self.combined_processor.process_all_agendas(limit=limit)
            
            summary_successful = results['summary_stats']['successful']
            summary_failed = results['summary_stats']['failed']
            json_successful = results['json_stats']['successful']
            json_failed = results['json_stats']['failed']
            
            logger.info(f"Combined processing complete:")
            logger.info(f"  Summaries: {summary_successful} successful, {summary_failed} failed")
            logger.info(f"  JSON data: {json_successful} successful, {json_failed} failed")
            
            # Step 2: Update database consolidation if new files were processed
            if summary_successful > 0 or json_successful > 0:
                logger.info("Updating unified databases...")
                db_results = self.database_consolidator.create_all_databases()
                summaries_count = db_results['summaries_json']['metadata']['total_summaries']
                structured_count = db_results['structured_json']['metadata']['total_agendas']
                logger.info(f"Database consolidation updated: {summaries_count} summaries, {structured_count} structured data")
            
            # Step 3: Generate embeddings for any new files
            logger.info("Generating embeddings for processed files...")
            
            # Generate summary embeddings
            summary_emb_results = self.embedding_generator.process_all_summaries()
            
            # Generate JSON embeddings
            json_emb_results = self.embedding_generator.process_all_json_data()
            
            # Get final stats
            stats = self.embedding_generator.get_collection_stats()
            
            logger.info(f"Embeddings generation complete:")
            logger.info(f"  Summary embeddings: {summary_emb_results['successful']} successful, {summary_emb_results['failed']} failed")
            logger.info(f"  JSON embeddings: {json_emb_results['successful']} successful, {json_emb_results['failed']} failed")
            logger.info(f"  Total documents in vector DB: {stats['summaries_collection']['count'] + stats['json_collection']['count']}")
            
            # Consider successful if at least some files were processed successfully
            if summary_successful > 0 or json_successful > 0:
                return True
            elif summary_successful == 0 and json_successful == 0 and summary_failed == 0 and json_failed == 0:
                # All files already processed - still run embeddings in case any are missing
                return True
            else:
                logger.error("No files were processed successfully")
                return False
            
        except Exception as e:
            logger.error(f"Error in combined processing: {e}")
            return False

    def run_full_pipeline(self, limit: int = None) -> bool:
        """Run the complete pipeline."""
        logger.info("Starting full agenda processing pipeline...")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Combined processing (summaries + JSON extraction + databases + embeddings)
        if not self.run_combined_processing(limit=limit):
            logger.error("Pipeline failed at combined processing step")
            return False
        
        logger.info("Full pipeline completed successfully!")
        logger.info(f"Output directories:")
        logger.info(f"  Summaries: {OUTPUT_DIR / 'summaries'}")
        logger.info(f"  JSON data: {OUTPUT_DIR / 'json_data'}")
        logger.info(f"  Unified DBs: {OUTPUT_DIR / 'databases'}")
        logger.info(f"  Vector DB: {VECTOR_DB_DIR}")
        
        return True
    
    def show_status(self) -> None:
        """Show current status of processed data."""
        print("📊 Agenda Processing Pipeline Status")
        print("=" * 50)
        
        # Check agenda files
        agenda_files = get_agenda_files(AGENDAS_DIR)
        print(f"📁 Source files: {len(agenda_files)} agenda files")
        
        # Check summaries
        summaries_dir = OUTPUT_DIR / "summaries"
        if summaries_dir.exists():
            summary_files = list(summaries_dir.glob("summary_*.json"))
            print(f"📄 Summaries: {len(summary_files)} generated")
        else:
            print("📄 Summaries: 0 (not generated)")
        
        # Check JSON data
        json_dir = OUTPUT_DIR / "json_data"
        if json_dir.exists():
            json_files = list(json_dir.glob("data_*.json"))
            print(f"📊 JSON data: {len(json_files)} extracted")
        else:
            print("📊 JSON data: 0 (not extracted)")
        
        # Check vector database
        if VECTOR_DB_DIR.exists():
            try:
                from embedding_generator import EmbeddingGenerator
                generator = EmbeddingGenerator()
                stats = generator.get_collection_stats()
                print(f"🔍 Vector DB: {stats['summaries_collection']['count']} summaries, {stats['json_collection']['count']} structured docs, {stats['bond_collection']['count']} bond docs")
            except:
                print("🔍 Vector DB: Present but cannot read stats")
        else:
            print("🔍 Vector DB: Not created")
        
        print("\n💡 Next steps:")
        if not summaries_dir.exists():
            print("   Run: python main.py --step summaries")
        elif not json_dir.exists():
            print("   Run: python main.py --step json")
        elif not VECTOR_DB_DIR.exists():
            print("   Run: python main.py --step embeddings")
        else:
            print("   Run: streamlit run chatbot.py")

def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(description="Dallas City Agenda Processing Pipeline")
    parser.add_argument("--step", choices=["summaries", "json", "combined", "consolidate", "embeddings", "full"], 
                       help="Run specific step of the pipeline")
    parser.add_argument("--limit", type=int, help="Limit number of files to process (for testing)")
    parser.add_argument("--status", action="store_true", help="Show current status")
    
    args = parser.parse_args()
    
    pipeline = AgendaPipeline()
    
    if args.status:
        pipeline.show_status()
        return
    
    if not args.step:
        print("🏛️ Dallas City Agenda Processing Pipeline")
        print("=" * 50)
        print("This pipeline processes Dallas city meeting agendas to create a searchable knowledge base.")
        print()
        print("Usage:")
        print("  python main.py --step full          # Run complete pipeline")
        print("  python main.py --step combined      # Generate summaries + JSON data + databases + embeddings") 
        print("  python main.py --step summaries     # Generate summaries only") 
        print("  python main.py --step json          # Extract structured data only")
        print("  python main.py --step consolidate   # Create unified databases from JSON files")
        print("  python main.py --step embeddings    # Generate embeddings only")
        print("  python main.py --status             # Show current status")
        print("  python main.py --limit 5        `    # Process only first 5 files (testing)")
        print()
        print("After processing, run the chatbot:")
        print("  streamlit run chatbot.py")
        return
    
    success = False
    
    if args.step == "summaries":
        success = pipeline.run_summaries(limit=args.limit)
    elif args.step == "json":
        success = pipeline.run_json_extraction(limit=args.limit)
    elif args.step == "combined":
        success = pipeline.run_combined_processing(limit=args.limit)
    elif args.step == "consolidate":
        success = pipeline.run_database_consolidation()
    elif args.step == "embeddings":
        success = pipeline.run_embeddings()
    elif args.step == "full":
        success = pipeline.run_full_pipeline(limit=args.limit)
    
    if success:
        print("\n✅ Step completed successfully!")
        if args.step == "full":
            print("\n🚀 Ready to use the chatbot!")
            print("Run: streamlit run chatbot.py")
    else:
        print("\n❌ Step failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
