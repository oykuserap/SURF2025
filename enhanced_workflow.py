"""
Enhanced workflow with JSON-based processing
"""
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        if isinstance(command, str):
            command = command.split()
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def get_python_command():
    """Get the correct Python command for this system."""
    return sys.executable

def check_documents():
    """Check if documents exist in Agendas_COR folder."""
    agendas_path = Path("./Agendas_COR")
    if not agendas_path.exists():
        return 0
    
    txt_files = list(agendas_path.glob("*.txt"))
    return len(txt_files)

def check_json_exists():
    """Check if JSON file exists."""
    json_path = Path("./processed_meetings.json")
    return json_path.exists()

def enhanced_workflow():
    """Run the enhanced document processing workflow with JSON structure."""
    print("🚀 Enhanced Document Processing Workflow")
    print("📊 Text → JSON → Embeddings → Enhanced Chatbot")
    print("=" * 60)
    
    # Get Python command
    python_cmd = get_python_command()
    print(f"🐍 Using Python command: {python_cmd}")
    
    # Step 1: Check current documents
    current_docs = check_documents()
    print(f"📊 Current documents: {current_docs} files")
    
    if current_docs == 0:
        print("❌ No documents found in Agendas_COR folder!")
        print("💡 Please add .txt files to the Agendas_COR folder first")
        return False
    
    # Step 2: Convert to JSON structure
    print("\n🔄 Converting documents to structured JSON format...")
    if not run_command([python_cmd, "convert_to_json.py"], "JSON conversion"):
        print("❌ Cannot continue without JSON structure")
        return False
    
    # Step 3: Process JSON into enhanced embeddings
    print("\n🔄 Creating enhanced embeddings from JSON structure...")
    if not run_command([python_cmd, "embed_json.py"], "Enhanced embedding"):
        print("❌ Cannot continue without enhanced embeddings")
        return False
    
    # Step 4: Ready for enhanced chatbot
    print("\n🎉 Enhanced workflow complete!")
    print("✅ Your enhanced chatbot is ready with structured data")
    print("\n🚀 Enhanced features available:")
    print("   - Search by date, attendee, or financial impact")
    print("   - Analyze trends across meetings")
    print("   - Track specific agenda items")
    print("   - Financial analysis capabilities")
    
    print("\n💡 Starting enhanced chatbot...")
    
    # Step 5: Start enhanced chatbot
    print("\n🚀 Starting enhanced chatbot...")
    subprocess.run([python_cmd, "enhanced_chatbot.py"])
    
    return True

if __name__ == "__main__":
    enhanced_workflow()
