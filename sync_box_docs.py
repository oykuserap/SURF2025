"""
Simple Box Document Sync Script
Usage: python sync_box_docs.py
"""
import os
from pathlib import Path

def download_with_developer_token():
    """Download documents using Box Developer Token (easiest method)."""
    try:
        from boxsdk import DeveloperTokenAuth, Client
        
        print("🔑 Box Developer Token Authentication")
        print("=" * 50)
        print("1. Go to https://developer.box.com/")
        print("2. Create a new app (or use existing)")
        print("3. Go to Configuration → Developer Token")
        print("4. Generate a new token (valid for 1 hour)")
        print("5. Copy the token and paste it below")
        print()
        
        token = input("Enter your Box Developer Token: ").strip()
        
        if not token:
            print("❌ No token provided")
            return False
        
        # Authenticate
        auth = DeveloperTokenAuth(token)
        client = Client(auth)
        
        # Test connection
        user = client.user().get()
        print(f"✅ Connected as: {user.name}")
        
        # List folders in root
        print("\n📁 Exploring your Box account...")
        root_folder = client.folder('0').get()
        items = root_folder.get_items()
        
        folders = []
        for item in items:
            if item.type == 'folder':
                folders.append(item)
                print(f"📁 {item.name} (ID: {item.id})")
        
        if not folders:
            print("No folders found. You may need to specify a folder ID directly.")
            folder_id = input("Enter Box folder ID: ").strip()
        else:
            folder_id = input(f"\nEnter folder ID to download from: ").strip()
        
        if not folder_id:
            print("❌ No folder ID provided")
            return False
        
        # Download files
        return download_txt_files(client, folder_id)
        
    except ImportError:
        print("❌ boxsdk not installed. Run: pip install boxsdk")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def download_txt_files(client, folder_id, local_folder="./Agendas_COR"):
    """Download all .txt files from Box folder."""
    try:
        local_path = Path(local_folder)
        local_path.mkdir(exist_ok=True)
        
        folder = client.folder(folder_id).get()
        print(f"\n📂 Downloading from: {folder.name}")
        
        items = folder.get_items()
        downloaded_files = []
        
        for item in items:
            if item.type == 'file' and item.name.lower().endswith('.txt'):
                try:
                    print(f"📥 Downloading: {item.name}")
                    
                    # Download file content
                    file_content = client.file(item.id).content()
                    
                    # Save to local file
                    local_file_path = local_path / item.name
                    with open(local_file_path, 'wb') as f:
                        f.write(file_content)
                    
                    downloaded_files.append(local_file_path)
                    print(f"✅ Saved: {local_file_path}")
                    
                except Exception as e:
                    print(f"❌ Error downloading {item.name}: {e}")
        
        print(f"\n📊 Successfully downloaded {len(downloaded_files)} files")
        
        if downloaded_files:
            print("\n💡 Next steps:")
            print("   1. Run: python process_docs.py")
            print("   2. Run: python embed_docs.py")
            print("   3. Use your chatbot with updated documents!")
        
        return len(downloaded_files) > 0
        
    except Exception as e:
        print(f"❌ Error downloading files: {e}")
        return False

def main():
    """Main function."""
    print("📦 Box Document Sync")
    print("=" * 30)
    
    success = download_with_developer_token()
    
    if success:
        print("\n✅ Document sync complete!")
    else:
        print("\n❌ Document sync failed")
        print("\n🔧 Alternative methods:")
        print("1. Manually download files from Box web interface")
        print("2. Use Box Drive to sync folder locally")
        print("3. Set up Box OAuth2 app for automated sync")

if __name__ == "__main__":
    main()
