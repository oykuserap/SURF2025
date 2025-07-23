"""
LLM Summary Generator for agenda text files.
Generates concise summaries of meeting agendas using OpenAI's GPT models.
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
import json

from config import OPENAI_API_KEY, OPENAI_MODEL, AGENDAS_DIR, OUTPUT_DIR
from utils import setup_logging, clean_text, save_json, get_agenda_files, extract_agenda_number

logger = setup_logging()

class SummaryGenerator:
    """Generate summaries for agenda text files using OpenAI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.output_dir = OUTPUT_DIR / "summaries"
        
    def create_summary_prompt(self, text: str) -> str:
        """Create a prompt for summarizing agenda content."""
        return f"""
Please provide a comprehensive but concise summary of this meeting agenda. Include:

1. **Meeting Overview**: Type of meeting, organization/committee, and general purpose
2. **Key Agenda Items**: Main topics and decisions to be made
3. **Important Details**: Significant proposals, budget items, policy changes, or projects
4. **Action Items**: What decisions or approvals are being sought

Keep the summary between 150-300 words and focus on the most important content.

AGENDA TEXT:
{text}

SUMMARY:
"""

    def generate_summary(self, text: str) -> str:
        """Generate summary using OpenAI API."""
        try:
            cleaned_text = clean_text(text)
            prompt = self.create_summary_prompt(cleaned_text)
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing government meeting agendas. Provide clear, concise summaries that capture the essential information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"

    def process_agenda_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single agenda file and generate summary."""
        logger.info(f"Processing {file_path.name}")
        
        try:
            # Read the agenda file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate summary
            summary = self.generate_summary(content)
            
            # Prepare output data
            agenda_number = extract_agenda_number(file_path)
            output_data = {
                "agenda_number": agenda_number,
                "source_file": file_path.name,
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary),
                "processed_at": str(asyncio.get_event_loop().time())
            }
            
            # Save summary
            output_file = self.output_dir / f"summary_{agenda_number}.json"
            save_json(output_data, output_file)
            
            logger.info(f"Summary saved for {file_path.name}")
            return output_data
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return {"error": str(e), "file": file_path.name}

    def get_already_processed_files(self) -> set:
        """Get set of agenda numbers that have already been processed."""
        processed = set()
        
        # Check existing summary files
        for summary_file in self.output_dir.glob("summary_*.json"):
            try:
                with open(summary_file, 'r') as f:
                    data = json.load(f)
                    if "error" not in data and data.get("agenda_number"):
                        processed.add(data["agenda_number"])
            except:
                continue
                
        return processed

    def process_all_agendas(self, limit: int = None) -> List[Dict[str, Any]]:
        """Process all agenda files and generate summaries with resume capability."""
        all_agenda_files = get_agenda_files(AGENDAS_DIR)
        
        # Filter out already processed files
        already_processed = self.get_already_processed_files()
        agenda_files = []
        
        for file_path in all_agenda_files:
            agenda_number = extract_agenda_number(file_path)
            if agenda_number not in already_processed:
                agenda_files.append(file_path)
        
        if limit:
            agenda_files = agenda_files[:limit]
        
        print(f"\n🔍 Found {len(all_agenda_files)} total agenda files")
        print(f"📋 {len(already_processed)} already processed")
        print(f"🆕 {len(agenda_files)} new files to process")
        
        if len(agenda_files) == 0:
            print("✅ All files already processed!")
            return []
            
        logger.info(f"Processing {len(agenda_files)} new agenda files")
        
        results = []
        successful = 0
        failed = 0
        batch_size = 10
        
        # Process in batches of 10 with progress saving
        for i in range(0, len(agenda_files), batch_size):
            batch = agenda_files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(agenda_files) + batch_size - 1) // batch_size
            
            print(f"\n📦 Processing Batch {batch_num}/{total_batches} ({len(batch)} files)")
            print("=" * 60)
            
            batch_successful = 0
            batch_failed = 0
            
            for j, file_path in enumerate(batch, 1):
                print(f"📄 [{j}/{len(batch)}] Processing {file_path.name}...")
                
                result = self.process_agenda_file(file_path)
                results.append(result)
                
                if "error" not in result:
                    successful += 1
                    batch_successful += 1
                    print(f"   ✅ Summary generated and saved")
                else:
                    failed += 1
                    batch_failed += 1
                    print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            
            print(f"\n📦 Batch {batch_num} complete: ✅ {batch_successful} successful, ❌ {batch_failed} failed")
            print(f"📊 Overall progress: {successful + failed}/{len(agenda_files)} new files processed")
        
        # Save overall results
        results_file = self.output_dir / "summary_results.json"
        save_json({
            "total_files_found": len(all_agenda_files),
            "already_processed": len(already_processed),
            "new_files_processed": len(agenda_files),
            "successful": successful,
            "failed": failed,
            "results": results
        }, results_file)
        
        print(f"\n🎉 Summary generation complete!")
        print(f"   ✅ Total successful: {successful}")
        print(f"   ❌ Total failed: {failed}")
        print(f"   📋 Total in database: {len(already_processed) + successful}")
        
        logger.info(f"Summary generation complete. Results saved to {results_file}")
        return results

def main():
    """Main function to run summary generation."""
    generator = SummaryGenerator()
    
    # Process first 5 files as a test
    print("Generating summaries for agenda files...")
    results = generator.process_all_agendas(limit=5)
    
    successful = len([r for r in results if "error" not in r])
    failed = len([r for r in results if "error" in r])
    
    print(f"\nSummary Generation Complete!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful > 0:
        print(f"\nSummaries saved in: {OUTPUT_DIR / 'summaries'}")

if __name__ == "__main__":
    main()
