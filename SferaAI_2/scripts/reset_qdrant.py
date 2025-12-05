import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_base import recreate_collection

if __name__ == "__main__":
    print("WARNING: This will DELETE all existing data in the Qdrant collection.")
    confirmation = input("Type 'yes' to confirm: ")
    if confirmation.lower() == 'yes':
        recreate_collection()
        print("Collection recreated successfully.")
    else:
        print("Operation cancelled.")
