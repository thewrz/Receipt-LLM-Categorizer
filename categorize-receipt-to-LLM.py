import os
import time
import openai
import csv
import PyPDF2  # Simple PDF text extraction
import json
import io
import configparser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Read configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

OPENAI_API_KEY = config['DEFAULT']['OPENAI_API_KEY']
WATCH_FOLDER = config['DEFAULT']['WATCH_FOLDER']
OUTPUT_FOLDER = config['DEFAULT']['OUTPUT_FOLDER']

# Set OpenAI API key
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class ReceiptHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".pdf"):
            time.sleep(2)  # Wait for OneDrive to finish syncing
            process_receipt(event.src_path)

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file using PyPDF2 and cleans up spacing."""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text.strip() if text else None
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def process_receipt(receipt_path):
    print(f"Processing receipt: {receipt_path}")

    # Extract text from the receipt PDF
    extracted_text = extract_text_from_pdf(receipt_path)
    if not extracted_text:
        print("Error: Could not extract text from PDF. Ending script...")
        return
    print("Preparing to show extracted text...\n")
    time.sleep(2)
    print(f"Extracted Text (Preview):\n\n {extracted_text} \n\n")
    print("Sending to OpenAI in 5 seconds...\n")
    time.sleep(5)

    try:
        # Send extracted text to OpenAI for categorization
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},  # Return as JSON object
            messages=[
                {"role": "system", "content": "You are a highly accurate receipt parser. You will receive \n\
                receipt text where each line represents an item that was extracted using PyPDF2 before being \n\
                sent to you. Your goal is to analyze the receipt, categorize each item, calculate subtotals, \n\
                and verify the before-tax final total matches the before-tax final total found in the receipt data you received.\n\
                \n\
                **Instructions:**\n\
                1. **Extract Relevant Data:**\n\
                - Ignore blank lines, headers, and footers.\n\
                - Identify each **valid line item** and extract:\n\
                    - **Item Name**\n\
                    - **Price (after discounts, if applicable)**\n\
                - If a discount applies, **subtract it from the original item price.**\n\
                - If an item is \"voided,\" **exclude it** from calculations.\n\
                - Find receipt\"s total before taxes are calculated\n\
                \n\
                2. **Identify Relevant Categories:**\n\
                - Once each line item is extracted use your receipt knowledge to categorize each item:\n\
                    - **Category**:\n\
                        - \"Groceries\" for food items\n\
                        - \"Household\" for cleaning/supply items\n\
                        - \"Automotive\" for car-related purchases\n\
                        - \"Shopping\" for electronics, luxury items, or if the category is unclear/unidentified\n\
                \n\
                3. **Ensure JSON Format:**\n\
                - Return JSON formatted as it is in this example. This is just an example of the format, not the literal data:\n\
                \n\
                ```json\n\
                {\n\
                \"items\": [\n\
                    {\n\
                    \"name\": \"Item Name\",\n\
                    \"price\": #.##,\n\
                    \"category\": \"Groceries\"\n\
                    },\n\
                    {\n\
                    \"name\": \"Item Name\",\n\
                    \"price\": #.##,\n\
                    \"category\": \"Automotive\"\n\
                    },\n\
                    {\n\
                    \"name\": \"Item Name\",\n\
                    \"price\": #.##\n\
                    \"category\": \"Household\"\n\
                    },\n\
                    {\n\
                    \"name\": \"Item Name\",\n\
                    \"price\": #.##,\n\
                    \"category\": \"Shopping\"\n\
                    }\n\
                ],\n\
                \"subtotals\": {\n\
                    \"Groceries\": #.##,\n\
                    \"Automotive\": #.##,\n\
                    \"Household\": #.##,\n\
                    \"Shopping\": #.##\n\
                },\n\
                \"before_tax_subtotals_of_all_categories_calcuated_by_ChatGPT\": #.##,\n\
                \"before_tax_total_found_in_receipt_data_sent\": #.##,\n\
                \"sales_taxes_found_in_receipt_data_sent: #.##,\n\
                \"receipt_total_verified\": true\n\
                }"},
            ]
        )


        if response and response.choices:
            extracted_data = response.choices[0].message.content
            cleaned_data = clean_json(extracted_data)
            if cleaned_data:
                csv_data = convert_json_to_csv(cleaned_data)
                save_csv(csv_data, receipt_path)
            else:
                print("Failed to clean JSON data.")

    except Exception as e:
        print(f"OpenAI API Error: {e}")

def clean_json(extracted_data):
    """Cleans up JSON data by removing extra spaces and newlines if the LLM doesn't properly output the JSON."""
    try:
        # Locate the first '{' and the last '}' to extract valid JSON content
        start = extracted_data.find('{')
        end = extracted_data.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in the response.")
        json_str = extracted_data[start:end+1]
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"Error cleaning JSON: {e}")
        return None

def convert_json_to_csv(json_data):
    """Converts JSON data to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header for items
    writer.writerow(["Item Name", "Price", "Category"])
    for item in json_data.get("items", []):
        writer.writerow([item.get("name", ""), item.get("price", ""), item.get("category", "")])

    # Separator
    writer.writerow([])

    # Write header for subtotals
    writer.writerow(["Category", "Subtotal"])
    subtotals = json_data.get("subtotals", {})
    for category, subtotal in subtotals.items():
        writer.writerow([category, subtotal])

    # Additional summary information
    writer.writerow([])
    writer.writerow(["Before Tax Total (Calculated by ChatGPT)", json_data.get("before_tax_subtotals_of_all_categories_calcuated_by_ChatGPT", "")])
    writer.writerow(["Before Tax Total (Found in Receipt Data)", json_data.get("before_tax_total_found_in_receipt_data_sent", "")])
    writer.writerow(["Sales Taxes", json_data.get("sales_taxes_found_in_receipt_data_sent", "")])
    writer.writerow(["Receipt Total Verified", json_data.get("receipt_total_verified", "")])

    return output.getvalue()

def save_csv(csv_data, receipt_path):
    """Saves data to CSV."""
    csv_filename = os.path.basename(receipt_path).replace(".pdf", ".csv")
    output_path = os.path.join(OUTPUT_FOLDER, csv_filename)
    try:
        with open(output_path, "w", newline="") as f:
            f.write(csv_data)
        print(f"CSV saved to {output_path}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

# Start watching the folder
event_handler = ReceiptHandler()
observer = Observer()
observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
observer.start()

print(f"Watching {WATCH_FOLDER} for new receipts...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
