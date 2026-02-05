#!/usr/bin/env python3
"""Main CLI interface for TOPCIT PDF Summarizer."""
import argparse
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from config import Config
from pdf_processor import PDFProcessor
from summarizer import Summarizer
from output_generator import OutputGenerator
from utils import (
    setup_logging,
    get_pdf_files,
    create_sliding_windows
)

logger = logging.getLogger(__name__)


def process_single_pdf(
    pdf_path: str,
    pdf_processor: PDFProcessor,
    summarizer: Summarizer,
    output_gen: OutputGenerator,
    window_size: int,
    overlap: int
) -> Dict[Tuple[int, int], str]:
    """
    Process a single PDF and generate summaries.
    
    Args:
        pdf_path: Path to the PDF file
        pdf_processor: Initialized PDF processor
        summarizer: Initialized summarizer
        output_gen: Initialized output generator
        window_size: Number of pages per group
        overlap: Number of pages to overlap
    
    Returns:
        Dictionary mapping page ranges to summaries
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {Path(pdf_path).name}")
    logger.info(f"{'='*60}\n")
    
    try:
        # Extract text from all pages
        logger.info("Step 1: Extracting text from PDF pages...")
        page_texts = pdf_processor.process_pdf(pdf_path)
        
        if not page_texts:
            logger.error(f"No text extracted from {pdf_path}")
            return {}
        
        total_pages = max(page_texts.keys())
        logger.info(f"Successfully extracted text from {len(page_texts)} pages")
        
        # Create sliding windows
        logger.info(f"Step 2: Creating sliding windows (size={window_size}, overlap={overlap})...")
        windows = create_sliding_windows(total_pages, window_size, overlap)
        logger.info(f"Created {len(windows)} page groups")
        
        # Group text by windows
        logger.info("Step 3: Grouping page text...")
        page_groups = {}
        for start_page, end_page in windows:
            texts = []
            for page_num in range(start_page, end_page + 1):
                if page_num in page_texts:
                    texts.append(f"--- Page {page_num} ---\n{page_texts[page_num]}\n")
            
            if texts:
                combined_text = "\n".join(texts)
                page_groups[(start_page, end_page)] = combined_text
        
        logger.info(f"Prepared {len(page_groups)} groups for summarization")
        
        # Create learning guides for page groups
        logger.info("Step 4: Creating simplified learning guides with Gemini API...")
        pdf_name = Path(pdf_path).stem
        summaries = summarizer.summarize_multiple_groups(
            page_groups,
            pdf_name=pdf_name,
            delay_between_requests=1.0
        )
        
        logger.info(f"Generated {len(summaries)} learning guides")
        return summaries
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {e}", exc_info=True)
        return {}


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="TOPCIT PDF Summarizer - Extract text from PDFs and generate summaries using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'pdfs',
        nargs='+',
        help='PDF file(s) or directory containing PDFs to process'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default=Config.DEFAULT_OUTPUT_DIR,
        help=f'Output directory for summaries (default: {Config.DEFAULT_OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=Config.OCR_DPI,
        help=f'DPI for OCR image conversion (default: {Config.OCR_DPI})'
    )
    
    parser.add_argument(
        '--window-size',
        type=int,
        default=Config.PAGES_PER_GROUP,
        help=f'Number of pages per group (default: {Config.PAGES_PER_GROUP})'
    )
    
    parser.add_argument(
        '--overlap',
        type=int,
        default=Config.DEFAULT_OVERLAP,
        help=f'Pages of overlap between groups (default: {Config.DEFAULT_OVERLAP})'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--skip-compiled',
        action='store_true',
        help='Skip generating the compiled PDF (only generate Markdown files)'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(verbose=args.verbose)
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Collect all PDF files
    all_pdf_files = []
    for pdf_input in args.pdfs:
        try:
            pdf_files = get_pdf_files(pdf_input)
            all_pdf_files.extend(pdf_files)
        except ValueError as e:
            logger.warning(f"Skipping {pdf_input}: {e}")
    
    if not all_pdf_files:
        logger.error("No PDF files found to process")
        sys.exit(1)
    
    logger.info(f"Found {len(all_pdf_files)} PDF file(s) to process")
    
    # Set up output directories
    output_dir = Path(args.output_dir)
    ocr_output_dir = output_dir / Config.OCR_TEXT_SUBDIR
    raw_summaries_dir = output_dir / Config.RAW_SUMMARIES_SUBDIR
    
    # Ensure output directories exist
    from utils import ensure_directory
    ensure_directory(str(output_dir))
    ensure_directory(str(ocr_output_dir))
    ensure_directory(str(raw_summaries_dir))
    
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"OCR text will be saved to: {ocr_output_dir}")
    logger.info(f"Raw summaries will be saved to: {raw_summaries_dir}\n")
    
    # Initialize components
    try:
        pdf_processor = PDFProcessor(dpi=args.dpi, ocr_output_dir=str(ocr_output_dir))
        summarizer = Summarizer(raw_summaries_dir=str(raw_summaries_dir))
        output_gen = OutputGenerator(args.output_dir)
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        sys.exit(1)
    
    # Process each PDF
    all_summaries = {}
    successful_pdfs = []
    failed_pdfs = []
    
    for pdf_path in all_pdf_files:
        try:
            pdf_name = Path(pdf_path).name
            
            # Check if final markdown already exists
            existing_md = output_gen.markdown_exists(pdf_path)
            if existing_md:
                logger.info(f"\n{'='*60}")
                logger.info(f"Found existing markdown for: {pdf_name}")
                logger.info(f"File: {existing_md.name}")
                logger.info(f"Skipping processing - markdown already exists")
                logger.info(f"{'='*60}\n")
                
                # Load existing summaries from raw files if available, or skip entirely
                # For now, we'll skip the entire PDF if markdown exists
                # User can delete markdown to reprocess if needed
                successful_pdfs.append(pdf_path)
                continue
            
            summaries = process_single_pdf(
                pdf_path,
                pdf_processor,
                summarizer,
                output_gen,
                args.window_size,
                args.overlap
            )
            
            if summaries:
                all_summaries[pdf_path] = summaries
                
                # Generate individual Markdown file
                logger.info("Step 5: Generating Markdown output...")
                output_gen.generate_markdown(pdf_path, summaries)
                successful_pdfs.append(pdf_path)
                logger.info(f"✓ Successfully processed {pdf_name}\n")
            else:
                failed_pdfs.append(pdf_path)
                logger.warning(f"✗ No summaries generated for {pdf_name}\n")
        
        except KeyboardInterrupt:
            logger.warning("\n\nProcess interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to process {pdf_path}: {e}", exc_info=True)
            failed_pdfs.append(pdf_path)
    
    # Generate compiled PDF if requested
    if all_summaries and not args.skip_compiled:
        logger.info(f"\n{'='*60}")
        logger.info("Generating compiled PDF with all summaries...")
        logger.info(f"{'='*60}\n")
        
        try:
            compiled_pdf = output_gen.compile_all_to_single_pdf(all_summaries)
            logger.info(f"✓ Compiled PDF created: {compiled_pdf}\n")
        except Exception as e:
            logger.error(f"Failed to compile PDF: {e}", exc_info=True)
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("Processing Summary")
    logger.info(f"{'='*60}")
    logger.info(f"Total PDFs: {len(all_pdf_files)}")
    logger.info(f"Successful: {len(successful_pdfs)}")
    logger.info(f"Failed: {len(failed_pdfs)}")
    
    if successful_pdfs:
        logger.info("\nSuccessfully processed:")
        for pdf in successful_pdfs:
            logger.info(f"  - {Path(pdf).name}")
    
    if failed_pdfs:
        logger.warning("\nFailed to process:")
        for pdf in failed_pdfs:
            logger.warning(f"  - {Path(pdf).name}")
        sys.exit(1)


if __name__ == "__main__":
    main()

