"""
Box Integration for automatic document retrieval
"""
import os
from pathlib import Path
from boxsdk import Client, OAuth2
import requests
from datetime import datetime

class BoxDocumentRetriever:
    def __init__(self):
        self.client = None
        self.setup_box_client()
    
    def setup_box_client(self):
        """Setup Box client with OAuth2 authentication."""
        try:
            # You'll need to set these in your .env file
            client_id = os.getenv('BOX_CLIENT_ID')
            client_secret = os.getenv('BOX_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                print("❌ Box credentials not found in environment variables")
                print("💡 Please add BOX_CLIENT_ID and BOX_CLIENT_SECRET to your .env file")
                return
            
            # For development, you can use OAuth2 with manual token
            # For production, consider using JWT authentication
            oauth = OAuth2(
                client_id=client_id,
                client_secret=client_secret,
            )
            
            self.client = Client(oauth)
            print("✅ Box client configured")
            
        except Exception as e:
            print(f"❌ Error setting up Box client: {e}")
    
    def authenticate_with_developer_token(self, developer_token):
        """Alternative: Use developer token for testing (expires in 1 hour)."""
        try:
            from boxsdk import DeveloperTokenAuth
            
            auth = DeveloperTokenAuth(developer_token)
            self.client = Client(auth)
            
            # Test the connection
            user = self.client.user().get()
            print(f"✅ Connected to Box as: {user.name}")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def list_folders(self, folder_id='0'):
        """List all folders in a Box folder."""
        try:
            folder = self.client.folder(folder_id).get()
            print(f"📁 Contents of '{folder.name}':")
            
            items = folder.get_items()
            folders = []
            
            for item in items:
                if item.type == 'folder':
                    folders.append(item)
                    print(f"   📁 {item.name} (ID: {item.id})")
                elif item.type == 'file':
                    print(f"   📄 {item.name} (ID: {item.id})")
            
            return folders
            
        except Exception as e:
            print(f"❌ Error listing folders: {e}")
            return []
    
    def download_txt_files(self, folder_id, local_folder="./Agendas_COR"):
        """Download all .txt files from a Box folder."""
        try:
            local_path = Path(local_folder)
            local_path.mkdir(exist_ok=True)
            
            folder = self.client.folder(folder_id).get()
            items = folder.get_items()
            
            downloaded_files = []
            
            for item in items:
                if item.type == 'file' and item.name.lower().endswith('.txt'):
                    try:
                        print(f"📥 Downloading: {item.name}")
                        
                        # Download file content
                        file_content = self.client.file(item.id).content()
                        
                        # Save to local file
                        local_file_path = local_path / item.name
                        with open(local_file_path, 'wb') as f:
                            f.write(file_content)
                        
                        downloaded_files.append(local_file_path)
                        print(f"✅ Saved: {local_file_path}")
                        
                    except Exception as e:
                        print(f"❌ Error downloading {item.name}: {e}")
            
            print(f"\n📊 Downloaded {len(downloaded_files)} files")
            return downloaded_files
            
        except Exception as e:
            print(f"❌ Error downloading files: {e}")
            return []
    
    def sync_documents(self, folder_id, local_folder="./Agendas_COR"):
        """Sync documents from Box folder to local folder."""
        print(f"🔄 Syncing documents from Box folder {folder_id}...")
        
        downloaded_files = self.download_txt_files(folder_id, local_folder)
        
        if downloaded_files:
            print(f"✅ Sync complete! Downloaded {len(downloaded_files)} files")
            print("💡 Next steps:")
            print("   1. Run: python process_docs.py")
            print("   2. Run: python embed_docs.py")
            print("   3. Use your chatbot with updated documents!")
        else:
            print("❌ No files were downloaded")
        
        return downloaded_files


def main():
    """Main function to demonstrate Box integration."""
    print("📦 Box Document Retriever")
    print("=" * 50)
    
    retriever = BoxDocumentRetriever()
    
    # Option 1: Use developer token (quick setup for testing)
    print("\n🔑 Authentication Options:")
    print("1. Enter Box Developer Token (expires in 1 hour)")
    print("2. Set up OAuth2 credentials in .env file")
    
    choice = input("\nChoose option (1 or 2): ").strip()
    
    if choice == "1":
        token = input("Enter your Box Developer Token: ").strip()
        if not retriever.authenticate_with_developer_token(token):
            return
    elif choice == "2":
        if not retriever.client:
            print("❌ Please configure Box credentials in .env file first")
            return
    else:
        print("❌ Invalid option")
        return
    
    # List folders to find the right one
    print("\n📁 Exploring Box folders...")
    folders = retriever.list_folders()
    
    if folders:
        print(f"\nFound {len(folders)} folders. Enter folder ID to download from:")
        folder_id = input("Folder ID: ").strip()
        
        if folder_id:
            retriever.sync_documents(folder_id)
    else:
        print("No folders found or you may need to specify a folder ID")
        folder_id = input("Enter Box folder ID (or press Enter for root): ").strip()
        if not folder_id:
            folder_id = '0'  # Root folder
        retriever.sync_documents(folder_id)


if __name__ == "__main__":
    main()
