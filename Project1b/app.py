import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaDrivenDocumentExtractor:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    # --- NEW --- Comprehensive cleaning function
    def _clean_text(self, text: str) -> str:
        """Replaces common PDF artifacts and unicode characters with standard ASCII."""
        replacements = {
            '\u2022': '',    # Bullet
            '\ufb00': 'ff',   # Ligature ff
            '\ufb01': 'fi',   # Ligature fi
            '\ufb02': 'fl',   # Ligature fl
            '\ufb03': 'ffi',  # Ligature ffi
            '\ufb04': 'ffl',  # Ligature ffl
            '\u2019': "'",    # Right single quotation mark
            '\u2018': "'",    # Left single quotation mark
            '\u201d': '"',    # Right double quotation mark
            '\u201c': '"',    # Left double quotation mark
            '\u2013': '-',    # En dash
            '\u2014': '-',    # Em dash
            '\u2026': '...',  # Horizontal ellipsis
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return re.sub(r'\s+', ' ', text).strip()

    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        sections = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_dict = page.get_text("dict")
                page_sections = self._split_into_sections_by_font(text_dict, page_num + 1)
                sections.extend(page_sections)
            doc.close()
            return sections
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return []

    def _split_into_sections_by_font(self, text_dict: Dict, page_num: int) -> List[Dict[str, Any]]:
        sections = []
        current_title = "Introduction"
        current_content = ""
        
        spans = [span for block in text_dict.get('blocks', []) if 'lines' in block for line in block['lines'] for span in line['spans']]
        if not spans:
            return []

        body_font_size = Counter(s['size'] for s in spans).most_common(1)[0][0]
        
        for block in text_dict.get('blocks', []):
            if 'lines' not in block:
                continue
            for line in block['lines']:
                line_spans = line.get('spans', [])
                if not line_spans:
                    continue

                line_text = self._clean_text("".join(s['text'] for s in line_spans))
                if not line_text:
                    continue
                
                # --- MODIFIED --- Use both font size and boldness to detect headers
                avg_size = np.mean([s['size'] for s in line_spans])
                is_bold = all((s['flags'] & 16) for s in line_spans) # 16 is the bold flag
                
                is_header = (avg_size > body_font_size + 0.5) or (is_bold and len(line_text.split()) < 15)

                if is_header:
                    if current_content.strip():
                        sections.append({'title': current_title, 'content': current_content.strip(), 'page_number': page_num})
                    current_title = line_text
                    current_content = ""
                else:
                    current_content += line_text + " "
        
        if current_content.strip():
            sections.append({'title': current_title, 'content': current_content.strip(), 'page_number': page_num})

        return sections

    def _extract_keywords_from_input(self, persona: str, job_description: str) -> List[str]:
        text = (persona + " " + job_description).lower()
        words = re.findall(r'\b[a-z]+\b', text)
        stop_words = {'a', 'an', 'the', 'for', 'and', 'to', 'is', 'of', 'in', 'with', 'from', 'or'}
        keywords = [word for word in words if word not in stop_words]
        
        if any(k in keywords for k in ["form", "forms"]):
            keywords.extend(["fillable", "sign", "signature", "e-signature", "fields", "interactive", "create"])
        if any(k in keywords for k in ["hr", "onboarding", "compliance"]):
            keywords.extend(["document", "manage", "track", "send", "employee", "professional", "compliance"])

        return list(set(keywords))
        
    def _calculate_score(self, text: str, dynamic_keywords: List[str], base_query_embedding: np.ndarray) -> float:
        content_embedding = self.model.encode([text], show_progress_bar=False, normalize_embeddings=True)
        similarity = np.dot(base_query_embedding, content_embedding.T)
        
        boost = sum(0.07 for keyword in dynamic_keywords if keyword in text.lower())
        return float(similarity[0][0] + min(boost, 0.7))

    # --- NEW METHOD --- For finding a 3-sentence cluster
    def _get_best_sentence_cluster(self, content: str, dynamic_keywords: List[str], base_query_embedding: np.ndarray) -> str:
        """Finds the most relevant sentence and returns it with its immediate neighbors."""
        sentences = re.split(r'(?<=[.?!])\s+', content)
        sentences = [s.strip() for s in sentences if len(s.strip().split()) > 4]
        if not sentences:
            return content[:500] # Return first 500 chars as a fallback

        scores = [self._calculate_score(s, dynamic_keywords, base_query_embedding) for s in sentences]
        
        if not scores:
            return content[:500]

        best_idx = np.argmax(scores)
        start_idx = max(0, best_idx - 1)
        end_idx = min(len(sentences), best_idx + 2)
        
        return " ".join(sentences[start_idx:end_idx])

    def process_documents(self, input_config: Dict[str, Any], pdf_directory: str) -> Dict[str, Any]:
        persona = input_config.get('persona', {}).get('role', '')
        job_description = input_config.get('job_to_be_done', {}).get('task', '')
        documents = input_config.get('documents', [])
        
        dynamic_keywords = self._extract_keywords_from_input(persona, job_description)
        base_query = f"{persona} who needs to {job_description}"
        base_query_embedding = self.model.encode([base_query], show_progress_bar=False, normalize_embeddings=True)

        best_sections_per_document = []
        
        for doc_info in documents:
            filename = doc_info['filename']
            pdf_path = os.path.join(pdf_directory, filename)
            if not os.path.exists(pdf_path):
                continue
            
            doc_title_text = self._clean_text(filename.replace('.pdf', '').replace('_', ' '))
            document_score = self._calculate_score(doc_title_text, dynamic_keywords, base_query_embedding)

            sections = self.extract_text_from_pdf(pdf_path)
            if not sections:
                continue

            doc_champion = max(
                sections,
                key=lambda s: self._calculate_score(s['title'] + " " + s['content'], dynamic_keywords, base_query_embedding) + (document_score * 0.3)
            )
            doc_champion['relevance_score'] = self._calculate_score(doc_champion['title'] + " " + doc_champion['content'], dynamic_keywords, base_query_embedding) + (document_score * 0.3)
            doc_champion['document'] = filename
            best_sections_per_document.append(doc_champion)
        
        best_sections_per_document.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_sections = best_sections_per_document[:5]
        
        extracted_sections = [{'document': s['document'], 'section_title': s['title'], 'importance_rank': i + 1, 'page_number': s['page_number']} for i, s in enumerate(top_sections)]
        
        subsection_analysis = [
            {
                'document': s['document'],
                'refined_text': self._get_best_sentence_cluster(s['content'], dynamic_keywords, base_query_embedding),
                'page_number': s['page_number']
            } for s in top_sections
        ]
        
        return {
            'metadata': { 'input_documents': [d['filename'] for d in documents], 'persona': persona, 'job_to_be_done': job_description, 'processing_timestamp': datetime.now().isoformat() },
            'extracted_sections': extracted_sections,
            'subsection_analysis': subsection_analysis
        }

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python your_script_name.py <collection_directory>")
        sys.exit(1)
    
    collection_dir = sys.argv[1]
    input_file = next((os.path.join(collection_dir, f) for f in os.listdir(collection_dir) if f.endswith('.json')), None)
    
    if not input_file:
        print(f"No JSON input file found in: {collection_dir}")
        sys.exit(1)

    output_file = os.path.join(collection_dir, 'challenge1b_output.json')
    pdf_dir = os.path.join(collection_dir, 'PDFs')
    if not os.path.exists(pdf_dir):
        pdf_dir = collection_dir

    try:
        with open(input_file, 'r') as f:
            input_config = json.load(f)
        
        extractor = PersonaDrivenDocumentExtractor()
        output = extractor.process_documents(input_config, pdf_dir)
        
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=4)
        
        print(f"Processing completed. Output saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()