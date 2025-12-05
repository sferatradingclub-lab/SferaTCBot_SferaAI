import os
import sys
import shutil

# Add parent directory to path to import knowledge_base
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_base import recreate_collection

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'knowledge_base')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

def clear_knowledge_base():
    print("--- Sfera AI Knowledge Base Cleanup ---")
    
    # 1. Recreate Qdrant Collection
    print("\n1. Clearing Qdrant Database...")
    try:
        recreate_collection()
    except Exception as e:
        print(f"ERROR clearing Qdrant: {e}")
        return

    # 2. Clear Processed Directory
    print(f"\n2. Clearing processed files in {PROCESSED_DIR}...")
    if os.path.exists(PROCESSED_DIR):
        files = os.listdir(PROCESSED_DIR)
        count = 0
        for file in files:
            file_path = os.path.join(PROCESSED_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    count += 1
            except Exception as e:
                print(f"Error deleting {file}: {e}")
        print(f"Deleted {count} files from processed directory.")
    else:
        print("Processed directory does not exist.")

    print("\n--- Cleanup Complete! ---")
    print("You can now upload clean data.")

if __name__ == "__main__":
    confirm = input("Are you sure you want to DELETE ALL KNOWLEDGE BASE DATA? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_knowledge_base()
    else:
        print("Cleanup cancelled.")
