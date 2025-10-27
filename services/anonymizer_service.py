"""
Service for detecting PII in resumes with coordinate information
"""
import re
import fitz  # PyMuPDF
from typing import List, Dict, Any
import json
import io
import uuid
from services.llm_service import llm_service


class AnonymizerService:
    """Service for detecting PII in resumes with coordinate information"""

    def detect_pii_with_coordinates(self, pdf_path: str) -> Dict[str, Any]:
        """
        Detect PII in PDF and return coordinates for each detection

        Uses PyMuPDF (fitz) to get text positions

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with success status, detections list, and total pages
        """
        try:
            doc = fitz.open(pdf_path)
            detections = []

            for page_num, page in enumerate(doc):
                # Get full page text for AI analysis
                page_text = page.get_text()

                # 1. Regex-based detection (fast, reliable)
                regex_detections = self._detect_pii_regex(page, page_num)
                detections.extend(regex_detections)

                # 2. AI-based detection (names, companies, schools)
                ai_detections = self._detect_pii_ai(page, page_text, page_num)
                detections.extend(ai_detections)

            total_pages = len(doc)
            doc.close()

            return {
                "success": True,
                "detections": detections,
                "total_pages": total_pages
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "detections": [],
                "total_pages": 0
            }

    def _detect_pii_regex(self, page, page_num: int) -> List[Dict[str, Any]]:
        """
        Detect emails, phones, URLs using regex

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            List of detection dictionaries
        """
        detections = []

        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        detections.extend(
            self._find_pattern_coords(page, email_pattern, "email", page_num)
        )

        # Phone patterns (various formats)
        phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
            r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b',    # (123) 456-7890
            r'\+\d{1,3}\s?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1 123-456-7890
        ]
        for pattern in phone_patterns:
            detections.extend(
                self._find_pattern_coords(page, pattern, "phone", page_num)
            )

        # LinkedIn URL
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        detections.extend(
            self._find_pattern_coords(page, linkedin_pattern, "linkedin", page_num)
        )

        # GitHub URL
        github_pattern = r'github\.com/[\w-]+'
        detections.extend(
            self._find_pattern_coords(page, github_pattern, "github", page_num)
        )

        # Website/Portfolio (exclude linkedin and github)
        website_pattern = r'https?://(?!.*(?:linkedin|github))[\w.-]+\.\w+[^\s]*'
        detections.extend(
            self._find_pattern_coords(page, website_pattern, "website", page_num)
        )

        return detections

    def _find_pattern_coords(
        self,
        page,
        pattern: str,
        pii_type: str,
        page_num: int
    ) -> List[Dict[str, Any]]:
        """
        Find regex pattern and get coordinates using PyMuPDF

        Args:
            page: PyMuPDF page object
            pattern: Regular expression pattern
            pii_type: Type of PII being detected
            page_num: Page number (0-indexed)

        Returns:
            List of detection dictionaries with coordinates
        """
        detections = []
        text = page.get_text()

        for match in re.finditer(pattern, text, re.IGNORECASE):
            matched_text = match.group()

            # Search for text location in PDF
            text_instances = page.search_for(matched_text)

            for rect in text_instances:
                bbox = {
                    "x": float(rect.x0),
                    "y": float(rect.y0),
                    "width": float(rect.x1 - rect.x0),
                    "height": float(rect.y1 - rect.y0)
                }

                # Extract style information
                style = self._extract_text_with_style(page, bbox)

                detections.append({
                    "id": str(uuid.uuid4()),
                    "type": pii_type,
                    "text": matched_text,
                    "page": page_num,
                    "bbox": bbox,
                    "confidence": 1.0,  # Regex is 100% confident
                    "style": style
                })

        return detections

    def _detect_pii_ai(
        self,
        page,
        page_text: str,
        page_num: int
    ) -> List[Dict[str, Any]]:
        """
        Use OpenAI to detect names, companies, schools

        Args:
            page: PyMuPDF page object
            page_text: Text content of the page
            page_num: Page number (0-indexed)

        Returns:
            List of detection dictionaries with coordinates
        """
        prompt = f"""Analyze this resume text and extract personal identifiable information.

Return as JSON:
{{
  "names": ["Full Name"],
  "companies": ["Company Name 1", "Company Name 2"],
  "schools": ["University Name 1", "University Name 2"],
  "addresses": ["123 Main St, City, State ZIP"]
}}

Rules:
- Extract the person's full name (usually at the top of the resume)
- Extract all company names from work experience section
- Extract all school/university names from education section
- Extract full addresses if present (street, city, state)
- Return empty arrays if category not found
- Be precise with exact text as it appears in the resume
- Do NOT include job titles, degrees, or dates

Text:
{page_text}
"""

        try:
            # Call LLM service
            response = llm_service.client.chat.completions.create(
                model=llm_service.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a PII detection system. Extract personal information from resume text and return it as valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            data = json.loads(result)

            detections = []

            # Find coordinates for each detected entity
            for name in data.get("names", []):
                detections.extend(
                    self._find_text_coords(page, name, "name", page_num, confidence=0.9)
                )

            for company in data.get("companies", []):
                detections.extend(
                    self._find_text_coords(page, company, "company", page_num, confidence=0.85)
                )

            for school in data.get("schools", []):
                detections.extend(
                    self._find_text_coords(page, school, "school", page_num, confidence=0.85)
                )

            for address in data.get("addresses", []):
                detections.extend(
                    self._find_text_coords(page, address, "address", page_num, confidence=0.8)
                )

            return detections

        except Exception:
            return []

    def _find_text_coords(
        self,
        page,
        text: str,
        pii_type: str,
        page_num: int,
        confidence: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Find text coordinates in PDF

        Args:
            page: PyMuPDF page object
            text: Text to search for
            pii_type: Type of PII
            page_num: Page number (0-indexed)
            confidence: Confidence score for this detection

        Returns:
            List of detection dictionaries with coordinates
        """
        detections = []

        # Try exact match first
        text_instances = page.search_for(text)

        # If no exact match, try case-insensitive
        if not text_instances:
            text_instances = page.search_for(text, flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for rect in text_instances:
            bbox = {
                "x": float(rect.x0),
                "y": float(rect.y0),
                "width": float(rect.x1 - rect.x0),
                "height": float(rect.y1 - rect.y0)
            }

            # Extract style information
            style = self._extract_text_with_style(page, bbox)

            detections.append({
                "id": str(uuid.uuid4()),
                "type": pii_type,
                "text": text,
                "page": page_num,
                "bbox": bbox,
                "confidence": confidence,
                "style": style
            })

        return detections

    def _extract_text_with_style(self, page, bbox: Dict[str, float]) -> Dict[str, Any]:
        """
        Extract font information from text at given location

        Args:
            page: PyMuPDF page object
            bbox: Bounding box dictionary with x, y, width, height

        Returns:
            Dictionary with font_name, font_size, color, flags
        """
        try:
            # Get all text blocks on the page with detailed info
            blocks = page.get_text("dict", flags=11)  # flags=11 gets font info

            rect = fitz.Rect(
                bbox['x'],
                bbox['y'],
                bbox['x'] + bbox['width'],
                bbox['y'] + bbox['height']
            )

            # Find text that overlaps with our bbox
            for block in blocks.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        line_rect = fitz.Rect(line["bbox"])
                        if rect.intersects(line_rect):
                            for span in line.get("spans", []):
                                span_rect = fitz.Rect(span["bbox"])
                                if rect.intersects(span_rect):
                                    return {
                                        "font_name": span.get("font", "helv"),
                                        "font_size": float(span.get("size", 12)),
                                        "color": int(span.get("color", 0)),
                                        "flags": int(span.get("flags", 0))
                                    }

        except Exception:
            pass

        # Default fallback
        return {
            "font_name": "helv",
            "font_size": float(bbox.get('height', 12) * 0.75),
            "color": 0,  # Black
            "flags": 0
        }

    def generate_anonymized_pdf(
        self,
        pdf_bytes: bytes,
        replacements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a new PDF with text replacements

        Args:
            pdf_bytes: Original PDF file content as bytes
            replacements: List of replacement dictionaries with:
                - page: int (0-indexed page number)
                - bbox: dict with x, y, width, height
                - original_text: str (text to replace)
                - replacement_text: str (new text)
                - type: str (PII type)
                - style: dict with font_name, font_size, color, flags

        Returns:
            Dictionary with success status and PDF bytes, or error
        """
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Apply replacements
            for replacement in replacements:
                page_num = replacement["page"]
                page = doc[page_num]

                # Create rectangle from bounding box
                bbox = replacement["bbox"]
                rect = fitz.Rect(
                    bbox["x"],
                    bbox["y"],
                    bbox["x"] + bbox["width"],
                    bbox["y"] + bbox["height"]
                )

                # Check if there's replacement text
                replacement_text = replacement.get("replacement_text", "").strip()

                if replacement_text:
                    # User provided replacement text - draw white rectangle to cover original text
                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

                    # Get original style or use defaults
                    style = replacement.get("style", {})

                    # Convert color integer to RGB tuple (0.0 to 1.0 range)
                    color_int = style.get("color", 0)
                    color_rgb = (
                        ((color_int >> 16) & 0xFF) / 255.0,
                        ((color_int >> 8) & 0xFF) / 255.0,
                        (color_int & 0xFF) / 255.0
                    )

                    # Use original font size or estimate from bbox
                    font_size = style.get("font_size", self._estimate_font_size(rect))

                    # Map extracted font to PyMuPDF built-in font
                    original_font = style.get("font_name", "helv").lower()
                    font_name = self._map_to_builtin_font(original_font)

                    # Insert new text with original styling
                    # insert_textbox returns number of successfully written characters (or negative if failed)
                    result = page.insert_textbox(
                        rect,
                        replacement_text,
                        fontsize=font_size,
                        fontname=font_name,
                        color=color_rgb,
                        align=0  # Left align
                    )

                    # If insert_textbox failed, try insert_text as fallback
                    if result <= 0:
                        try:
                            # Use insert_text with a point instead of a box
                            # Position at left edge, vertically centered
                            text_point = fitz.Point(rect.x0, rect.y0 + rect.height * 0.75)
                            page.insert_text(
                                text_point,
                                replacement_text,
                                fontsize=font_size,
                                fontname=font_name,
                                color=color_rgb
                            )
                        except Exception:
                            pass
                else:
                    # No replacement text - just black out (redact) the area
                    page.add_redact_annot(rect, fill=(0, 0, 0))  # Black fill
                    page.apply_redactions()

            # Save to buffer
            pdf_buffer = io.BytesIO()
            doc.save(pdf_buffer)
            doc.close()

            return {
                "success": True,
                "pdf_bytes": pdf_buffer.getvalue()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _estimate_font_size(self, rect: fitz.Rect) -> float:
        """
        Estimate appropriate font size based on bounding box height

        Args:
            rect: PyMuPDF rectangle

        Returns:
            Estimated font size in points
        """
        # Use 75% of box height as font size (leaves some padding)
        height = rect.height
        font_size = height * 0.75

        # Clamp between reasonable values
        min_size = 6.0
        max_size = 18.0

        return max(min_size, min(font_size, max_size))

    def _map_to_builtin_font(self, font_name: str) -> str:
        """
        Map extracted font name to PyMuPDF built-in font

        PyMuPDF only supports these built-in fonts:
        - helv: Helvetica (sans-serif)
        - tiro: Times Roman (serif)
        - cour: Courier (monospace)

        Args:
            font_name: Font name extracted from PDF (e.g., "Calibri-Bold")

        Returns:
            PyMuPDF built-in font name
        """
        font_lower = font_name.lower()

        # Sans-serif fonts → Helvetica
        sans_serif = ['arial', 'helvetica', 'calibri', 'verdana', 'tahoma',
                      'segoe', 'sans', 'gill']
        if any(s in font_lower for s in sans_serif):
            return "helv"

        # Serif fonts → Times Roman
        serif = ['times', 'georgia', 'garamond', 'palatino', 'baskerville',
                 'cambria', 'serif']
        if any(s in font_lower for s in serif):
            return "tiro"

        # Monospace fonts → Courier
        monospace = ['courier', 'consolas', 'monaco', 'monospace', 'mono']
        if any(s in font_lower for s in monospace):
            return "cour"

        # Default to Helvetica
        return "helv"


# Global instance
anonymizer_service = AnonymizerService()
