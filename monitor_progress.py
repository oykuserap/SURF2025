#!/usr/bin/env python3
"""
Monitor the progress of the agenda processing pipeline.
"""

from pathlib import Path
import time
import json

def monitor_progress():
    summaries_dir = Path("/Users/serap/SURF2025/processed_data/summaries")
    json_data_dir = Path("/Users/serap/SURF2025/processed_data/json_data")
    agendas_dir = Path("/Users/serap/SURF2025/Agendas_COR")
    
    # Count total agenda files
    total_agendas = len(list(agendas_dir.glob("agenda_*.txt")))
    
    while True:
        # Count processed files
        summary_files = len(list(summaries_dir.glob("summary_agenda_*.json")))
        json_files = len(list(json_data_dir.glob("data_agenda_*.json")))
        
        # Calculate progress
        summary_progress = (summary_files / total_agendas) * 100
        json_progress = (json_files / total_agendas) * 100
        
        print(f"\n📊 PIPELINE PROGRESS MONITOR")
        print(f"=" * 50)
        print(f"📁 Total agenda files: {total_agendas}")
        print(f"📄 Summaries generated: {summary_files} ({summary_progress:.1f}%)")
        print(f"📊 JSON data extracted: {json_files} ({json_progress:.1f}%)")
        
        if summary_files == total_agendas and json_files == total_agendas:
            print(f"\n🎉 PROCESSING COMPLETE!")
            print(f"✅ All {total_agendas} files processed")
            print(f"🔗 Ready for embeddings generation")
            break
        
        # Show progress bars
        summary_bar = "█" * int(summary_progress // 2) + "░" * (50 - int(summary_progress // 2))
        json_bar = "█" * int(json_progress // 2) + "░" * (50 - int(json_progress // 2))
        
        print(f"📄 Summaries: [{summary_bar}] {summary_progress:.1f}%")
        print(f"📊 JSON Data: [{json_bar}] {json_progress:.1f}%")
        
        # Check for recent activity
        try:
            recent_summary = max(summaries_dir.glob("summary_agenda_*.json"), key=lambda p: p.stat().st_mtime, default=None)
            if recent_summary:
                recent_time = recent_summary.stat().st_mtime
                time_diff = time.time() - recent_time
                if time_diff < 60:
                    print(f"🔄 Last processed: {recent_summary.name} ({time_diff:.0f}s ago)")
                else:
                    print(f"⏳ Last processed: {recent_summary.name} ({time_diff/60:.1f}m ago)")
        except:
            pass
        
        print(f"⏱️  Next update in 30 seconds...")
        time.sleep(30)

if __name__ == "__main__":
    try:
        monitor_progress()
    except KeyboardInterrupt:
        print(f"\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")