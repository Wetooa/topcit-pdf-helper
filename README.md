# TOPCIT PDF Learning Guide Generator

A Python CLI tool that processes large PDFs, extracts text using OCR, and generates simplified learning guides using Google's Gemini API. Creates concise, easy-to-read study materials that you can use instead of reading the lengthy original text.

## Features

- **OCR Text Extraction**: Automatically extracts text from PDFs using Tesseract OCR
- **Smart Text Detection**: Attempts text extraction first, falls back to OCR only when needed
- **Simplified Learning Guides**: Creates concise learning guides from verbose PDFs - removes filler and focuses on essential information
- **Sliding Window Processing**: Processes pages in overlapping groups of 5 (1-5, 4-9, 8-13, etc.)
- **Multiple Output Formats**: Generates both Markdown files and a compiled PDF
- **Batch Processing**: Handles multiple PDFs efficiently with progress tracking

## Prerequisites

- Python 3.8 or higher
- Tesseract OCR installed on your system:
  - **Linux**: `sudo apt-get install tesseract-ocr`
  - **macOS**: `brew install tesseract`
  - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key:
```bash
cp env.template .env
# Edit .env and add your GEMINI_API_KEY
```

Or export it as an environment variable:
```bash
export GEMINI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

Process a single PDF:
```bash
python main.py path/to/your/document.pdf
```

Process multiple PDFs:
```bash
python main.py pdf1.pdf pdf2.pdf pdf3.pdf
```

Process all PDFs in a directory:
```bash
python main.py /path/to/pdfs/
```

### Options

- `--output-dir` or `-o`: Specify output directory (default: `./output`)
- `--dpi`: OCR DPI setting (default: 300, higher = more accurate but slower)
- `--overlap`: Pages of overlap between groups (default: 2)

Example:
```bash
python main.py documents.pdf -o ./summaries --dpi 400
```

## Output Structure

The tool generates:
- `output/summaries/`: Individual Markdown files per PDF containing learning guides
- `output/compiled.pdf`: Combined PDF with all learning guides
- `output/ocr_text/`: Individual text files for each page's extracted text (for verification)
  - Files named: `{pdf_name}_page_{page_num}_{source}.txt`
  - Source can be: `direct_extraction` or `ocr`
- `output/raw_summaries/`: Individual API response files (saved immediately as learning guides are generated)
  - Files named: `{pdf_name}_pages_{start}-{end}_{timestamp}.txt`
  - Contains both the learning guide and preview of original text

## How It Works

1. **PDF Processing**: Extracts pages and checks for text content
2. **OCR Extraction**: If no text found, converts pages to images and runs OCR
3. **Page Grouping**: Groups pages in sliding windows (e.g., pages 1-5, 4-9, 8-13)
4. **Learning Guide Creation**: Sends each group to Gemini API to create simplified, concise learning guides
   - Removes unnecessary verbosity and filler words
   - Focuses on essential concepts and key information
   - Organizes content for easy studying
5. **Output Generation**: Creates Markdown files and compiles final PDF

## Notes

- Processing 300-page PDFs can take significant time due to OCR and API calls
- Ensure you have sufficient API quota for Gemini
- Output quality depends on PDF image quality for OCR accuracy

## Troubleshooting

**Tesseract not found**: Make sure Tesseract is installed and in your PATH
**API errors**: Check your Gemini API key and quota limits
**Memory issues**: Reduce DPI setting or process PDFs individually

## License

MIT
