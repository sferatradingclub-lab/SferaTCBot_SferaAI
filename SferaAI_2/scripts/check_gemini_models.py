import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in environment variables.")
    exit(1)

genai.configure(api_key=api_key)

print("--- Available Gemini Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Name: {m.name}")
            print(f"Display Name: {m.display_name}")
            print(f"Description: {m.description}")
            print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")

print("\n--- Testing Generation ---")
models_to_test = ["gemini-1.5-flash", "gemini-1.5-flash-001", "gemini-1.5-flash-002", "gemini-2.0-flash-exp"]

for model_name in models_to_test:
    print(f"Testing {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, are you working?")
        print(f"SUCCESS: {model_name} responded: {response.text.strip()}")
    except Exception as e:
        print(f"FAILED: {model_name} error: {e}")
