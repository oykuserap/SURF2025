"""
Automated Document Processing Workflow
Processes → Embeds → Chatbot
"""
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        # Split command into list for better subprocess handling
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
    # Use the same Python interpreter that's running this script
    # This ensures we use the virtual environment if it's active
    return sys.executable

def check_documents():
    """Check if documents exist in Agendas_COR folder."""
    agendas_path = Path("./Agendas_COR")
    if not agendas_path.exists():
        return 0
    
    txt_files = list(agendas_path.glob("*.txt"))
    return len(txt_files)

def full_workflow():
    """Run the complete document processing workflow."""
    print("🚀 Automated Document Processing Workflow")
    print("=" * 50)
    
    # Get the correct Python command
    python_cmd = get_python_command()
    print(f"🐍 Using Python command: {python_cmd}")
    
    # Step 1: Check current documents
    current_docs = check_documents()
    print(f"📊 Current documents: {current_docs} files")
    
    if current_docs == 0:
        print("❌ No documents found in Agendas_COR folder!")
        print("� Please add .txt files to the Agendas_COR folder first")
        return False
    
    # Step 2: Process documents into chunks
    if not run_command([python_cmd, "process_docs.py"], "Document processing"):
        print("❌ Cannot continue without processed documents")
        return False
    
    # Step 3: Create embeddings
    if not run_command([python_cmd, "embed_docs.py"], "Document embedding"):
        print("❌ Cannot continue without embeddings")
        return False
    
    # Step 4: Ready for chatbot
    print("\n🎉 Workflow complete!")
    print("✅ Your chatbot is ready with updated documents")
    print("\n💡 Starting chatbot automatically...")
    
    # Step 5: Start chatbot directly
    print("\n🚀 Starting chatbot...")
    subprocess.run([python_cmd, "chatbot.py"])
    
    return True

if __name__ == "__main__":
    full_workflow()
