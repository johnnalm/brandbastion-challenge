import fitz  # PyMuPDF
import pdfplumber
from typing import List, Dict, Any
import re
from pathlib import Path

class PDFChartParser:
    """Parse PDF files to extract chart data and text"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.PDF']
    
    def parse_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using PyMuPDF for text extraction"""
        doc = fitz.open(pdf_path)
        extracted_data = {
            "text": [],
            "tables": [],
            "metadata": {
                "page_count": len(doc),
                "title": doc.metadata.get('title', 'Unknown'),
                "author": doc.metadata.get('author', 'Unknown')
            }
        }
        
        for page_num, page in enumerate(doc):
            # Extract text
            text = page.get_text()
            if text.strip():
                extracted_data["text"].append({
                    "page": page_num + 1,
                    "content": text
                })
            
            # Extract tables (basic implementation)
            tables = page.find_tables()
            if tables:
                for table in tables:
                    extracted_data["tables"].append({
                        "page": page_num + 1,
                        "data": table.extract()
                    })
        
        doc.close()
        return extracted_data
    
    def parse_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using pdfplumber for better table extraction"""
        extracted_data = {
            "text": [],
            "tables": [],
            "charts_data": []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text()
                if text:
                    extracted_data["text"].append({
                        "page": page_num + 1,
                        "content": text
                    })
                
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        extracted_data["tables"].append({
                            "page": page_num + 1,
                            "data": table
                        })
                
                # Try to extract numerical data that might be from charts
                numbers = re.findall(r'\b\d+\.?\d*%?\b', text or '')
                if numbers:
                    extracted_data["charts_data"].append({
                        "page": page_num + 1,
                        "values": numbers
                    })
        
        return extracted_data
    
    def extract_chart_descriptions(self, text: str) -> List[str]:
        """Extract chart titles and descriptions from text"""
        patterns = [
            r'(?i)figure\s*\d+[:\s]*(.*?)(?=\n|$)',
            r'(?i)chart\s*\d+[:\s]*(.*?)(?=\n|$)',
            r'(?i)graph\s*\d+[:\s]*(.*?)(?=\n|$)',
            r'(?i)table\s*\d+[:\s]*(.*?)(?=\n|$)'
        ]
        
        descriptions = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            descriptions.extend(matches)
        
        return descriptions
    
    def parse(self, pdf_path: str, method: str = 'both') -> Dict[str, Any]:
        """Main parsing method"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if pdf_path.suffix not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {pdf_path.suffix}")
        
        results = {}
        
        if method in ['pymupdf', 'both']:
            try:
                results['pymupdf'] = self.parse_with_pymupdf(str(pdf_path))
            except Exception as e:
                results['pymupdf_error'] = str(e)
        
        if method in ['pdfplumber', 'both']:
            try:
                results['pdfplumber'] = self.parse_with_pdfplumber(str(pdf_path))
            except Exception as e:
                results['pdfplumber_error'] = str(e)
        
        # Extract chart descriptions from all text
        all_text = ""
        if 'pymupdf' in results:
            all_text += " ".join([t['content'] for t in results['pymupdf'].get('text', [])])
        if 'pdfplumber' in results:
            all_text += " ".join([t['content'] for t in results['pdfplumber'].get('text', [])])
        
        results['chart_descriptions'] = self.extract_chart_descriptions(all_text)
        
        return results


class CommentParser:
    """Parse user comments from text files"""
    
    def parse_comments(self, text: str) -> List[Dict[str, Any]]:
        """Parse comments from plain text"""
        # Handle both line-by-line and comma-separated quoted comments
        comments = []
        
        # Check if it's a single line with comma-separated quoted comments
        if text.count('\n') <= 1 and text.count('"') > 2:
            # Split by comma and clean up quotes
            import re
            # Find all quoted strings
            quoted_comments = re.findall(r'"([^"]*)"', text)
            
            for idx, comment in enumerate(quoted_comments):
                if comment.strip():
                    comments.append({
                        "id": idx + 1,
                        "text": comment.strip(),
                        "length": len(comment.strip())
                    })
        else:
            # Original line-by-line parsing
            lines = text.strip().split('\n')
            
            for idx, line in enumerate(lines):
                if line.strip():
                    comments.append({
                        "id": idx + 1,
                        "text": line.strip(),
                        "length": len(line.strip())
                    })
        
        return comments
    
    def extract_sentiment_keywords(self, comment: str) -> List[str]:
        """Extract potential sentiment keywords from a comment"""
        positive_keywords = ['good', 'great', 'excellent', 'love', 'amazing', 'best']
        negative_keywords = ['bad', 'terrible', 'hate', 'worst', 'awful', 'poor']
        
        words = comment.lower().split()
        found_keywords = []
        
        for word in words:
            if word in positive_keywords:
                found_keywords.append(('positive', word))
            elif word in negative_keywords:
                found_keywords.append(('negative', word))
        
        return found_keywords