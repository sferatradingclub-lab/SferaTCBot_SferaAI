import os
import sys
import glob
import time
import json
import logging
import random
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm
from collections import defaultdict
from google.api_core import exceptions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kb_unification.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logging.critical("GOOGLE_API_KEY not found in environment variables.")
    sys.exit(1)

genai.configure(api_key=GOOGLE_API_KEY)

# Model Configuration
MODEL_NAME = "gemini-2.5-flash" 
GENERATION_CONFIG = {
    "temperature": 0.3, 
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Directories
INPUT_DIR = Path("data/knowledge_base")
INTERMEDIATE_DIR = Path("data/knowledge_base_unified/intermediate") # Temp storage for Phase 1
OUTPUT_DIR = Path("data/knowledge_base_unified") # Final Master Guides
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- PROMPTS ---

PHASE_1_CLEAN_PROMPT = """
You are an expert Knowledge Engineer. Transform this raw transcript into a structured, anonymous knowledge block.

**CRITICAL RULE: OUTPUT MUST BE IN RUSSIAN LANGUAGE ONLY.**

**RULES:**
1. **DEPERSONALIZE:** Remove ALL speaker names, dates, and video context.
2. **EXTRACT FACTS:** Keep only strategies, definitions, and rules.
3. **TAGGING:** At the end, suggest a 'Topic Cluster' (e.g., Psychology, Risk Management, Technical Analysis).
4. **LANGUAGE:** TRANSLATE/WRITE EVERYTHING IN RUSSIAN.

**Input:**
{text}

**Output Format (Markdown):**
```markdown
---
doc_id: "{{slug}}"
topic_cluster: "{{Cluster Name}}"
tags: ["{{tag1}}", "{{tag2}}"]
---
# {{Descriptive Title in Russian}}

{{Content in Russian...}}
```
"""

PHASE_2_MERGE_PROMPT = """
You are the Chief Editor of the "Unified Trading Knowledge Base".
You are given multiple articles on the SAME topic. Your task is to MERGE them into ONE definitive "Master Guide".

**CRITICAL RULE: OUTPUT MUST BE IN RUSSIAN LANGUAGE ONLY.**

**INPUTS:**
{inputs}

**RULES:**
1. **SYNTHESIZE:** Combine all unique insights. Do not lose information.
2. **RESOLVE CONFLICTS:** If Source A says "Stop 1%" and Source B says "Stop 2%", write: "There are varying approaches: Conservative (1%) and Aggressive (2%)."
3. **STRUCTURE:** Create a cohesive document with a logical flow (Definition -> Principles -> Strategies).
4. **NO DUPLICATES:** Remove repetitive information.
5. **LANGUAGE:** The final document MUST be in RUSSIAN.
**OUTPUT FORMAT:**
Return a single, perfect Markdown file starting with YAML frontmatter.
"""

def generate_with_retry(model, prompt, max_retries=15, base_delay=10):
    """
    Helper function to generate content with exponential backoff for rate limits.
    """
    retries = 0
    while retries < max_retries:
        try:
            response = model.generate_content(prompt)
            return response
        except exceptions.ResourceExhausted as e:
            wait_time = base_delay * (1.5 ** retries) + random.uniform(0, 5)
            logging.warning(f"Rate limit hit (429). Retrying in {wait_time:.2f}s... (Attempt {retries + 1}/{max_retries})")
            time.sleep(wait_time)
            retries += 1
        except Exception as e:
            if "429" in str(e):
                wait_time = base_delay * (1.5 ** retries) + random.uniform(0, 5)
                logging.warning(f"Rate limit hit (429 in msg). Retrying in {wait_time:.2f}s... (Attempt {retries + 1}/{max_retries})")
                time.sleep(wait_time)
                retries += 1
            else:
                logging.error(f"Generation failed with non-retryable error: {e}")
                raise e
    
    raise Exception("Max retries exceeded for Gemini API.")

def phase_1_process_file(file_path: Path):
    """Phase 1: Clean and Depersonalize individual files."""
    try:
        logging.info(f"[Phase 1] Processing: {file_path.name}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        if not raw_text.strip():
            return None, False

        # Check if already processed
        output_filename = file_path.stem + "_clean.md"
        output_path = INTERMEDIATE_DIR / output_filename
        
        if output_path.exists():
            logging.info(f"Skipping {file_path.name} (Already processed)")
            return output_path, False # False = No API call made

        # Configure safety settings to allow all content (trading metaphors can trigger filters)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=GENERATION_CONFIG,
            safety_settings=safety_settings,
            system_instruction="You are a strict editor removing personalities from text. You MUST write in Russian."
        )

        # Using retry wrapper
        response = generate_with_retry(model, PHASE_1_CLEAN_PROMPT.format(text=raw_text[:30000]))
        processed_content = response.text
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(processed_content)
            
        return output_path, True # True = API call made

    except Exception as e:
        logging.error(f"Phase 1 failed for {file_path.name}: {e}")
        return None, False

def parse_topic_cluster(file_path: Path):
    """Extracts topic_cluster from frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.startswith('topic_cluster:'):
                    # Normalize to Title Case to avoid "Trading" vs "trading" collisions
                    raw_cluster = line.split(':')[1].strip().strip('"').strip("'")
                    return raw_cluster.strip().title() 
    except:
        pass
    return "Uncategorized"

def phase_2_merge_files(cluster_name: str, file_paths: list):
    """Phase 2: Merge multiple files of the same cluster into one Master Guide."""
    logging.info(f"[Phase 2] Merging cluster: {cluster_name} ({len(file_paths)} files)")
    
    combined_input = ""
    for fp in file_paths:
        with open(fp, 'r', encoding='utf-8') as f:
            combined_input += f"\n\n--- SOURCE: {fp.name} ---\n" + f.read()

    try:
        # Configure safety settings for Phase 2 as well
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=GENERATION_CONFIG,
            safety_settings=safety_settings,
            system_instruction="You are a Master Synthesizer creating definitive guides. You MUST write in Russian."
        )

        # Using retry wrapper
        # Increased input limit to 2M chars (Gemini has huge context)
        response = generate_with_retry(model, PHASE_2_MERGE_PROMPT.format(inputs=combined_input[:2000000]))
        master_content = response.text
        
        output_filename = f"MASTER_{cluster_name.replace(' ', '_')}.md"
        output_path = OUTPUT_DIR / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(master_content)
            
        logging.info(f"SUCCESS: Created Master Guide: {output_path}")
        
    except Exception as e:
        logging.error(f"Phase 2 failed for cluster {cluster_name}: {e}")

def main():
    # --- PHASE 1: MAP (Clean) ---
    logging.info("--- STARTING PHASE 1: CLEAN & DEPERSONALIZE ---")
    raw_files = list(INPUT_DIR.glob("*.txt")) + list(INPUT_DIR.glob("*.md"))
    intermediate_files = []
    
    for file_path in tqdm(raw_files, desc="Phase 1"):
        result, was_processed = phase_1_process_file(file_path)
        if result:
            intermediate_files.append(result)
        
        # Only sleep if we actually hit the API
        if was_processed:
            time.sleep(10) 

    # --- PHASE 2: REDUCE (Merge) ---
    logging.info("--- STARTING PHASE 2: CLUSTER & MERGE ---")
    
    # Group by cluster
    clusters = defaultdict(list)
    for fp in intermediate_files:
        cluster = parse_topic_cluster(fp)
        clusters[cluster].append(fp)
        
    for cluster_name, files in tqdm(clusters.items(), desc="Phase 2"):
        phase_2_merge_files(cluster_name, files)
        time.sleep(5)

    logging.info("=== UNIFICATION COMPLETE ===")

if __name__ == "__main__":
    main()
