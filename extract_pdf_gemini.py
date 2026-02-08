import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_text_via_gemini(pdf_path):
    print(f"Uploading {pdf_path} to Gemini...")
    # Upload the file
    sample_file = genai.upload_file(path=pdf_path, display_name="Tennis Rules")
    
    print(f"File uploaded: {sample_file.name}")
    print(f"State: {sample_file.state.name}")
    
    # Wait for the file to be processed
    while sample_file.state.name == "PROCESSING":
        print("Processing file...")
        time.sleep(5)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        raise ValueError("File processing failed in Gemini.")
        
    print("File processed successfully. Requesting text extraction...")
    
    # Use standard Flash model
    model = genai.GenerativeModel('models/gemini-flash-latest')
    
    # Prompt to extract text
    response = model.generate_content([
        "Extract all text from this English PDF document exactly as it is, maintaining rule numbers, titles, and section formatting. Do not summarize. Output the full content.",
        sample_file
    ])
    
    return response.text

if __name__ == "__main__":
    pdf_path = "docs/2026-rules-of-tennis-english.pdf"
    try:
        text = extract_text_via_gemini(pdf_path)
        print("Extraction complete.")
        print(f"Length: {len(text)} characters")
        print("First 500 characters preview:")
        print(text[:500])
        
        # Save to text file
        output_path = "full_rules_text_en.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved text to {output_path}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
