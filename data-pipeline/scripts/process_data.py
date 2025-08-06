#!/usr/bin/env python3
"""
Data processing script for BrandBastion Analytics
Processes PDFs and comments, generates embeddings, and stores in FAISS
"""

import click
import os
import sys
from pathlib import Path
from typing import List
import json

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
    
    # Initialize components
    pdf_parser = PDFChartParser()
    comment_parser = CommentParser()
    embedding_generator = EmbeddingGenerator()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Process PDFs
    pdf_path = Path(pdf_dir)
    if pdf_path.exists():
        click.echo(f"Processing PDFs from {pdf_dir}...")
        pdf_texts = []
        pdf_metadatas = []
        
        for pdf_file in pdf_path.glob('*.pdf'):
            click.echo(f"  Processing {pdf_file.name}...")
            try:
                # Parse PDF
                pdf_data = pdf_parser.parse(str(pdf_file))
                
                # Save parsed data
                output_file = output_path / f"{pdf_file.stem}_parsed.json"
                with open(output_file, 'w') as f:
                    json.dump(pdf_data, f, indent=2)
                
                # Extract texts for embeddings
                if 'pdfplumber' in pdf_data:
                    for text_item in pdf_data['pdfplumber'].get('text', []):
                        pdf_texts.append(text_item['content'])
                        pdf_metadatas.append({
                            "source": "pdf",
                            "filename": pdf_file.name,
                            "page": text_item['page']
                        })
                
            except Exception as e:
                click.echo(f"    Error processing {pdf_file.name}: {e}", err=True)
        
        # Create embeddings for PDFs
        if pdf_texts:
            click.echo(f"Creating embeddings for {len(pdf_texts)} PDF text chunks...")
            embedding_generator.add_to_existing_index(
                f"{index_name}_pdfs",
                pdf_texts,
                pdf_metadatas
            )
    
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
                
                # Save parsed comments
                output_file = output_path / f"{comment_file.stem}_comments.json"
                with open(output_file, 'w') as f:
                    json.dump(comments, f, indent=2)
                
                # Extract texts for embeddings
                for comment in comments:
                    comment_texts.append(comment['text'])
                    comment_metadatas.append({
                        "source": "comment",
                        "filename": comment_file.name,
                        "comment_id": comment['id']
                    })
                
            except Exception as e:
                click.echo(f"    Error processing {comment_file.name}: {e}", err=True)
        
        # Create embeddings for comments
        if comment_texts:
            click.echo(f"Creating embeddings for {len(comment_texts)} comments...")
            embedding_generator.add_to_existing_index(
                f"{index_name}_comments",
                comment_texts,
                comment_metadatas
            )
    
    # Create combined index
    all_texts = pdf_texts + comment_texts
    all_metadatas = pdf_metadatas + comment_metadatas
    
    if all_texts:
        click.echo(f"\nCreating combined index with {len(all_texts)} documents...")
        embedding_generator.add_to_existing_index(
            index_name,
            all_texts,
            all_metadatas
        )
    
    click.echo("\nData processing complete!")

if __name__ == '__main__':
    process_data()