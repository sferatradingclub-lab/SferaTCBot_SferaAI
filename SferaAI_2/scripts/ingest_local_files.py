import asyncio
import os
import sys
import shutil
import logging
import re
import yaml # Requires PyYAML, but we can use simple parsing if needed. Let's try simple parsing first to avoid deps.

# Add project root to path to import etl_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from etl_pipeline import run_pipeline_from_text
except ImportError:
    # Fallback if running from root
    from etl_pipeline import run_pipeline_from_text

# Config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# CHANGED: Now looking at the UNIFIED directory
DATA_DIR = os.path.join(BASE_DIR, "data", "knowledge_base_unified")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_frontmatter(text):
    """
    Parses YAML frontmatter from text.
    Returns (metadata_dict, content_text)
    """
    metadata = {}
    content = text
    
    # Check for frontmatter block
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        content = match.group(2)
        
        # Simple YAML parsing (key: value)
        for line in yaml_block.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                # Handle lists like [a, b]
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(',')]
                
                metadata[key] = value
                
    return metadata, content

async def process_files():
    """
    Scans DATA_DIR for .txt and .md files, runs them through the ETL pipeline,
    and moves them to PROCESSED_DIR upon success.
    """
    # Ensure directories exist
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logging.info(f"Created directory: {DATA_DIR}")
    
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)
        logging.info(f"Created directory: {PROCESSED_DIR}")

    # List files
    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(('.txt', '.md')) and os.path.isfile(os.path.join(DATA_DIR, f))]
    
    if not files:
        logging.info(f"No .txt or .md files found in {DATA_DIR}")
        logging.info("Please place your text files in this directory to ingest them.")
        return

    logging.info(f"Found {len(files)} files to process.")

    for filename in files:
        file_path = os.path.join(DATA_DIR, filename)
        logging.info(f"Processing file: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not text.strip():
                logging.warning(f"File {filename} is empty. Skipping.")
                continue

            # Parse Metadata
            metadata, content = parse_frontmatter(text)
            
            # Determine doc_id and title
            # Priority: Metadata > Filename
            name_without_ext = os.path.splitext(filename)[0]
            
            doc_id = metadata.get('doc_id') or name_without_ext.lower().replace(' ', '_').replace('-', '_')
            doc_title = metadata.get('title') or name_without_ext.replace('_', ' ').replace('-', ' ').title()
            
            # Prepare extra metadata for Qdrant payload
            extra_metadata = {
                "source_filename": filename,
                "is_unified": True,
                **metadata # Include all frontmatter fields (difficulty, tags, etc.)
            }

            # Run pipeline
            logging.info(f"Starting ETL for '{doc_title}' (ID: {doc_id})...")
            # Pass extra_metadata to the pipeline
            success = await run_pipeline_from_text(content, doc_id, doc_title, extra_metadata=extra_metadata)
            
            if success:
                # Copy to processed (keep original for safety)
                destination = os.path.join(PROCESSED_DIR, filename)
                shutil.copy2(file_path, destination)
                logging.info(f"SUCCESS: Processed and copied to {destination}")
            else:
                logging.error(f"FAILED: Pipeline returned failure for {filename}. File remains in {DATA_DIR}")

        except Exception as e:
            logging.error(f"FAILED to process {filename}: {e}")

if __name__ == "__main__":
    print("--- Sfera AI Unified Knowledge Base Ingestion ---")
    print(f"Target Directory: {DATA_DIR}")
    asyncio.run(process_files())
