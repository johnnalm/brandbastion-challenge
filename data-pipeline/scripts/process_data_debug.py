#!/usr/bin/env python3
"""
Debug version of data processing script with enhanced error handling
"""

import click
import os
import sys
from pathlib import Path
from typing import List
import json
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.pdf_parser import PDFChartParser, CommentParser
from embeddings.generator import EmbeddingGenerator

@click.command()
@click.option('--pdf-dir', default='/app/data/raw/pdfs', help='Directory containing PDF files')
@click.option('--comments-dir', default='/app/data/raw/comments', help='Directory containing comment files')
@click.option('--output-dir', default='/app/data/processed', help='Output directory for processed data')
@click.option('--index-name', default='brandbastion', help='Name for the FAISS index')
def process_data(pdf_dir: str, comments_dir: str, output_dir: str, index_name: str):
    """Process PDFs and comments to create embeddings"""
    
    try:
        # Initialize components
        click.echo("Initializing components...")
        pdf_parser = PDFChartParser()
        comment_parser = CommentParser()
        embedding_generator = EmbeddingGenerator()
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Process PDFs
        pdf_texts = []
        pdf_metadatas = []
        
        pdf_path = Path(pdf_dir)
        if pdf_path.exists():
            click.echo(f"Processing PDFs from {pdf_dir}...")
            for pdf_file in pdf_path.glob('*.pdf'):
                click.echo(f"  Processing {pdf_file.name}...")
                try:
                    # Extract text from PDF
                    pdf_data = pdf_parser.parse(str(pdf_file))
                    
                    # Save extracted data
                    output_file = output_path / f"{pdf_file.stem}_extracted.json"
                    with open(output_file, 'w') as f:
                        json.dump(pdf_data, f, indent=2)
                    
                    # Extract texts for embeddings
                    # Handle both pymupdf and pdfplumber results
                    for parser_name in ['pymupdf', 'pdfplumber']:
                        if parser_name in pdf_data:
                            parser_results = pdf_data[parser_name]
                            for text_item in parser_results.get('text', []):
                                if text_item.get('content', '').strip():
                                    pdf_texts.append(text_item['content'])
                                    pdf_metadatas.append({
                                        "source": "pdf",
                                        "filename": pdf_file.name,
                                        "page": text_item.get('page', 1),
                                        "parser": parser_name
                                    })
                            break  # Use first successful parser only
                    
                except Exception as e:
                    click.echo(f"    Error processing {pdf_file.name}: {e}", err=True)
                    traceback.print_exc()
            
            # Create embeddings for PDFs
            if pdf_texts:
                click.echo(f"Creating embeddings for {len(pdf_texts)} PDF text chunks...")
                try:
                    embedding_generator.add_to_existing_index(
                        f"{index_name}_pdfs",
                        pdf_texts,
                        pdf_metadatas
                    )
                except Exception as e:
                    click.echo(f"Error creating PDF embeddings: {e}", err=True)
                    traceback.print_exc()
        
        # Process comments
        comments_path = Path(comments_dir)
        if comments_path.exists():
            click.echo(f"\nProcessing comments from {comments_dir}...")
            comment_texts = []
            comment_metadatas = []
            
            for comment_file in comments_path.glob('*.txt'):
                click.echo(f"  Processing {comment_file.name}...")
                try:
                    # Read and parse comments
                    with open(comment_file, 'r') as f:
                        text = f.read()
                    
                    comments = comment_parser.parse_comments(text)
                    click.echo(f"    Parsed {len(comments)} comments")
                    
                    # Save parsed comments
                    output_file = output_path / f"{comment_file.stem}_comments.json"
                    with open(output_file, 'w') as f:
                        json.dump(comments, f, indent=2)
                    
                    # Extract texts for embeddings
                    for i, comment in enumerate(comments):
                        comment_text = comment.get('text', '').strip()
                        if comment_text:
                            comment_texts.append(comment_text)
                            comment_metadatas.append({
                                "source": "comment",
                                "filename": comment_file.name,
                                "comment_id": comment.get('id', i)
                            })
                    
                except Exception as e:
                    click.echo(f"    Error processing {comment_file.name}: {e}", err=True)
                    traceback.print_exc()
            
            # Create embeddings for comments
            if comment_texts:
                click.echo(f"Creating embeddings for {len(comment_texts)} comments...")
                click.echo("  Processing in batches to avoid rate limits...")
                
                try:
                    # Process in smaller batches
                    batch_size = 50
                    for i in range(0, len(comment_texts), batch_size):
                        batch_end = min(i + batch_size, len(comment_texts))
                        click.echo(f"  Processing batch {i//batch_size + 1}: comments {i+1} to {batch_end}")
                        
                        batch_texts = comment_texts[i:batch_end]
                        batch_metadatas = comment_metadatas[i:batch_end]
                        
                        embedding_generator.add_to_existing_index(
                            f"{index_name}_comments",
                            batch_texts,
                            batch_metadatas
                        )
                    
                    click.echo("  Comment embeddings created successfully!")
                    
                except Exception as e:
                    click.echo(f"Error creating comment embeddings: {e}", err=True)
                    click.echo(f"Error type: {type(e)}")
                    traceback.print_exc()
                    raise
        
        # Create combined index
        all_texts = pdf_texts + comment_texts
        all_metadatas = pdf_metadatas + comment_metadatas
        
        if all_texts:
            click.echo(f"\nCreating combined index with {len(all_texts)} documents...")
            try:
                embedding_generator.add_to_existing_index(
                    index_name,
                    all_texts,
                    all_metadatas
                )
            except Exception as e:
                click.echo(f"Error creating combined index: {e}", err=True)
                traceback.print_exc()
        
        click.echo("\nData processing complete!")
        
    except Exception as e:
        click.echo(f"\nFatal error: {e}", err=True)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    process_data()