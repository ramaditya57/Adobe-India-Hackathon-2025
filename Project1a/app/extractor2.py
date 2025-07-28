import os
import json
import fitz
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
import re
import unicodedata


class MultilingualHeadingExtractor:
    def __init__(self):
        self.script_ranges = {
            'latin': [(0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x017F), (0x0100, 0x024F)],
            'japanese': [(0x3040, 0x309F), (0x30A0, 0x30FF), (0x4E00, 0x9FAF), (0x31F0, 0x31FF)],
            'chinese': [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x20000, 0x2A6DF)],
            'korean': [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)],
            'arabic': [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)],
            'cyrillic': [(0x0400, 0x04FF), (0x0500, 0x052F)],
            'devanagari': [(0x0900, 0x097F)],
            'thai': [(0x0E00, 0x0E7F)]
        }
        
        self.sentence_endings = {
            'latin': ['.', '!', '?', ';', ':'],
            'japanese': ['。', '？', '！', 'です', 'ます', 'である', 'だ'],
            'chinese': ['。', '？', '！', '：', '；'],
            'korean': ['다', '요', '니다', '습니다', '.', '?', '!'],
            'arabic': ['.', '؟', '!', '؛', '：'],
            'cyrillic': ['.', '!', '?', ';', ':'],
            'devanagari': ['।', '॥', '.', '?', '!'],
            'thai': ['.', '?', '!', '๚', '๛']
        }
        
        self.common_words = {
            'latin': ['the', 'and', 'or', 'but', 'if', 'when', 'where', 'how', 'what', 'is', 'a', 'in', 'for', 'to', 'of', 'with'],
            'japanese': ['は', 'が', 'を', 'に', 'へ', 'と', 'の', 'で', 'から', 'まで', 'より', 'について', 'において', 'という'],
            'chinese': ['的', '了', '是', '在', '有', '和', '或', '但', '如果', '当', '哪里', '怎么', '什么'],
            'korean': ['은', '는', '이', '가', '을', '를', '에', '에서', '로', '와', '과', '하다', '이다', '있다'],
            'arabic': ['في', 'من', 'إلى', 'على', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي'],
            'cyrillic': ['и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'что', 'как', 'где', 'когда'],
            'devanagari': ['और', 'में', 'से', 'को', 'का', 'की', 'के', 'है', 'हैं', 'था', 'थे', 'होगा'],
            'thai': ['และ', 'ใน', 'ของ', 'ที่', 'จาก', 'ไป', 'มา', 'ได้', 'เป็น', 'อยู่', 'แล้ว']
        }

    def detect_script(self, text: str) -> str:
        if not text:
            return 'latin'
        
        script_counts = defaultdict(int)
        
        for char in text:
            code_point = ord(char)
            for script, ranges in self.script_ranges.items():
                for start, end in ranges:
                    if start <= code_point <= end:
                        script_counts[script] += 1
                        break
        
        if not script_counts:
            return 'latin'
        
        return max(script_counts.items(), key=lambda x: x[1])[0]

    def is_likely_heading_by_script(self, text: str, script: str) -> bool:
        text = text.strip()
        
        if len(text) < 2:
            return False
        
        max_length = 50 if script == 'japanese' else 100
        if len(text) > max_length:
            return False
        
        sentence_endings = self.sentence_endings.get(script, [])
        if any(text.endswith(ending) for ending in sentence_endings):
            return False
        
        if script == 'japanese':
            return self._is_heading_japanese(text)
        elif script == 'chinese':
            return self._is_heading_chinese(text)
        elif script == 'korean':
            return self._is_heading_korean(text)
        elif script == 'arabic':
            return self._is_heading_arabic(text)
        elif script in ['cyrillic', 'devanagari', 'thai']:
            return self._is_heading_generic(text, script)
        else:
            return self._is_heading_latin(text)

    def _is_heading_japanese(self, text: str) -> bool:
        if '、' in text:
            return False
        
        particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'の', 'で']
        particle_count = sum(1 for char in text if char in particles)
        if len(text) > 10 and particle_count > 2:
            return False
        
        sentence_patterns = ['という', 'である', 'ことが', 'ために', 'として']
        if any(text.endswith(pattern) for pattern in sentence_patterns):
            return False
            
        return True

    def _is_heading_chinese(self, text: str) -> bool:
        common_words = self.common_words['chinese']
        word_count = sum(1 for char in text if char in common_words)
        if len(text) > 5 and word_count > len(text) * 0.3:
            return False
        
        if '，' in text or '；' in text:
            return False
            
        return True

    def _is_heading_korean(self, text: str) -> bool:
        particles = self.common_words['korean']
        particle_count = sum(1 for word in text.split() if word in particles)
        total_words = len(text.split())
        if total_words > 2 and particle_count > total_words * 0.4:
            return False
            
        return True

    def _is_heading_arabic(self, text: str) -> bool:
        common_words = self.common_words['arabic']
        words = text.split()
        common_count = sum(1 for word in words if word in common_words)
        if len(words) > 2 and common_count > len(words) * 0.4:
            return False
            
        return True

    def _is_heading_generic(self, text: str, script: str) -> bool:
        common_words = self.common_words.get(script, [])
        if common_words:
            words = text.split()
            common_count = sum(1 for word in words if word in common_words)
            if len(words) > 2 and common_count > len(words) * 0.4:
                return False
        return True

    def _is_heading_latin(self, text: str) -> bool:
        if not (text[0].isupper() or text[0].isdigit()):
            return False
        
        common_words = self.common_words['latin']
        words = text.lower().split()
        common_count = sum(1 for word in words if word in common_words)
        if len(words) > 3 and common_count > len(words) * 0.4:
            return False
        
        punct_count = sum(1 for char in text if char in ',.;:()""\'')
        if punct_count > len(text) * 0.15:
            return False
            
        return True

    def is_likely_heading(self, text: str) -> bool:
        text = text.strip()
        if len(text) < 2:
            return False
        
        script = self.detect_script(text)
        return self.is_likely_heading_by_script(text, script)

    def cluster_font_sizes(self, sizes: List[float], cluster_eps: float = 1.0) -> List[float]:
        if not sizes:
            return []
        
        unique_sizes = sorted(set(sizes), reverse=True)
        
        if len(unique_sizes) <= 1:
            return unique_sizes
        
        clusters = []
        current_cluster = [unique_sizes[0]]
        
        for size in unique_sizes[1:]:
            if abs(current_cluster[0] - size) <= cluster_eps:
                current_cluster.append(size)
            else:
                center = sum(current_cluster) / len(current_cluster)
                clusters.append(center)
                current_cluster = [size]
        
        center = sum(current_cluster) / len(current_cluster)
        clusters.append(center)
        
        return sorted(clusters, reverse=True)

    def get_font_size_outliers(self, all_sizes: List[float], threshold_percentile: float = 80) -> List[float]:
        if not all_sizes:
            return []
        
        sorted_sizes = sorted(all_sizes)
        threshold_idx = int(len(sorted_sizes) * threshold_percentile / 100)
        threshold_size = sorted_sizes[threshold_idx] if threshold_idx < len(sorted_sizes) else sorted_sizes[-1]
        
        outliers = [size for size in set(all_sizes) if size > threshold_size]
        return sorted(outliers, reverse=True)

    def get_heading_level(self, fontsize: float, clustered_sizes: List[float], is_bold: bool, tol: float = 2.0) -> Optional[str]:
        if not clustered_sizes:
            return None
        
        closest_idx = None
        min_diff = float('inf')
        
        for idx, cluster_size in enumerate(clustered_sizes):
            diff = abs(fontsize - cluster_size)
            if diff < min_diff:
                min_diff = diff
                closest_idx = idx
        
        if min_diff <= tol:
            if closest_idx == 0: return "H1"
            elif closest_idx == 1: return "H2"
            elif closest_idx <= 4: return "H3"
        
        if is_bold and len(clustered_sizes) > 0:
            avg_size = sum(clustered_sizes) / len(clustered_sizes)
            if fontsize >= avg_size - 1:
                return "H3"
        
        return None

    def extract_outline_from_pdf(self, pdf_path: str) -> Dict:
        doc = fitz.open(pdf_path)
        
        title = doc.metadata.get("title", "").strip()
        if not title:
            title = os.path.splitext(os.path.basename(pdf_path))[0]
        
        all_text_blocks = []
        all_font_sizes = []
        potential_heading_sizes = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    if not line["spans"]:
                        continue
                    
                    line_text = "".join(span["text"] for span in line["spans"]).strip()
                    
                    if not line_text:
                        continue
                    
                    max_fontsize = max(span["size"] for span in line["spans"])
                    is_bold = any(span.get("flags", 0) & 2 for span in line["spans"])
                    
                    all_font_sizes.append(max_fontsize)
                    
                    all_text_blocks.append({
                        "text": line_text,
                        "fontsize": max_fontsize,
                        "is_bold": is_bold,
                        "page": page_num + 1
                    })
                    
                    if self.is_likely_heading(line_text):
                        potential_heading_sizes.append(max_fontsize)
        
        clustered_sizes = self.cluster_font_sizes(potential_heading_sizes, cluster_eps=1.5)
        
        if len(clustered_sizes) < 2:
            font_outliers = self.get_font_size_outliers(all_font_sizes, threshold_percentile=75)
            if font_outliers:
                clustered_sizes = font_outliers[:3]
        
        if len(clustered_sizes) < 3 and all_font_sizes:
            sorted_sizes = sorted(set(all_font_sizes), reverse=True)
            if len(sorted_sizes) >= 3:
                clustered_sizes = sorted_sizes[:3]
            elif len(sorted_sizes) == 2:
                clustered_sizes = [sorted_sizes[0], sorted_sizes[1], sorted_sizes[1] - 1]
            elif len(sorted_sizes) == 1:
                clustered_sizes = [sorted_sizes[0], sorted_sizes[0] - 1, sorted_sizes[0] - 2]
        
        headings = []
        seen_headings = set()
        
        for block in all_text_blocks:
            text = block["text"]
            fontsize = block["fontsize"]
            is_bold = block["is_bold"]
            page = block["page"]
            
            is_content_heading = self.is_likely_heading(text)
            is_size_outlier = fontsize in self.get_font_size_outliers(all_font_sizes, threshold_percentile=70)
            
            if not (is_content_heading or is_size_outlier):
                continue
            
            text_normalized = text.lower().strip()
            if text_normalized in seen_headings:
                continue
            
            level = self.get_heading_level(fontsize, clustered_sizes, is_bold)
            
            if level:
                headings.append({
                    "level": level,
                    "text": text.strip(),
                    "page": page
                })
                seen_headings.add(text_normalized)
        
        headings.sort(key=lambda x: (x["page"], 0 if x["level"] == "H1" else 1 if x["level"] == "H2" else 2))
        
        if len(headings) > 30:
            h1_headings = [h for h in headings if h["level"] == "H1"][:5]
            h2_headings = [h for h in headings if h["level"] == "H2"][:10]  
            h3_headings = [h for h in headings if h["level"] == "H3"][:15]
            headings = h1_headings + h2_headings + h3_headings
            headings.sort(key=lambda x: x["page"])
        
        doc.close()
        
        return {
            "title": title,
            "outline": headings
        }


def process_all_pdfs(input_dir: str, output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"No PDF files found in input directory: {input_dir}")
        return
    
    extractor = MultilingualHeadingExtractor()
    
    for filename in pdf_files:
        input_path = os.path.join(input_dir, filename)
        output_filename = os.path.splitext(filename)[0] + ".json"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            print(f"Processing '{filename}'...")
            outline = extractor.extract_outline_from_pdf(input_path)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(outline, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Processed '{filename}' -> '{output_filename}' ({len(outline['outline'])} headings)")
            
        except Exception as e:
            print(f"✗ Error processing '{filename}': {e}")


if __name__ == "__main__":
    INPUT_DIR = "/app/input"
    OUTPUT_DIR = "/app/output"
    
    if not os.path.exists(INPUT_DIR):
        print("Running in local mode. Using './input' and './output' directories.")
        INPUT_DIR = "input"
        OUTPUT_DIR = "output"
        if not os.path.exists(INPUT_DIR):
            os.makedirs(INPUT_DIR)
    
    process_all_pdfs(INPUT_DIR, OUTPUT_DIR)