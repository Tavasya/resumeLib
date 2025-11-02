"""
Centralized PDF service for all PDF manipulation operations
"""
import fitz  # PyMuPDF
import io
from typing import List, Dict, Any


class PDFService:
    """Service for PDF manipulation operations"""

    def generate_annotated_pdf(
        self,
        pdf_bytes: bytes,
        annotations: List[Dict[str, Any]],
        watermark_text: str = "Reviewed by cookedcareer.com"
    ) -> Dict[str, Any]:
        """
        Generate a PDF with annotations (highlights and comments) burned in

        Args:
            pdf_bytes: Original PDF file content as bytes
            annotations: List of annotation dictionaries with:
                - page_number: int (0-indexed page number)
                - position: dict with x, y, width, height
                - content: dict with selectedText (optional) and comment (optional)
                - annotation_type: str ('highlight', 'area', or 'drawing')
            watermark_text: Text to use for watermark

        Returns:
            Dictionary with success status and PDF bytes with annotations, or error
        """
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Apply annotations
            for annot in annotations:
                page_num = annot.get("page_number", 0)

                # Validate page number
                if page_num < 0 or page_num >= len(doc):
                    continue

                page = doc[page_num]
                pos = annot.get("position", {})
                content = annot.get("content", {})
                annot_type = annot.get("annotation_type", "highlight")

                # Create rectangle from position
                rect = fitz.Rect(
                    pos.get("x", 0),
                    pos.get("y", 0),
                    pos.get("x", 0) + pos.get("width", 0),
                    pos.get("y", 0) + pos.get("height", 0)
                )

                # Skip invalid rectangles
                if rect.is_empty or not rect.is_valid:
                    continue

                # Draw based on annotation type
                if annot_type == "highlight":
                    # Add yellow highlight
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=[1, 1, 0])  # Yellow
                    highlight.update()

                elif annot_type == "area":
                    # Draw red border rectangle
                    page.draw_rect(rect, color=(1, 0, 0), width=2)  # Red border

                elif annot_type == "drawing":
                    # Draw red rectangle (could be extended for other shapes)
                    page.draw_rect(rect, color=(1, 0, 0), width=2)

                # Add comment text if present
                comment = content.get("comment", "").strip()
                if comment:
                    # Position comment above the annotation
                    comment_rect = fitz.Rect(
                        rect.x0,
                        rect.y0 - 30,  # 30 points above
                        rect.x0 + 400,  # Max width for comment
                        rect.y0 - 5     # 5 points above annotation
                    )

                    # Draw semi-transparent yellow background for comment
                    page.draw_rect(
                        comment_rect,
                        color=(1, 1, 0.8),  # Light yellow
                        fill=(1, 1, 0.8),   # Fill with light yellow
                        width=0.5
                    )

                    # Insert comment text
                    page.insert_textbox(
                        comment_rect,
                        f"💬 {comment}",
                        fontsize=9,
                        fontname="helv",
                        color=(0, 0, 0),  # Black text
                        align=0  # Left align
                    )

            # Add watermark to all pages
            self._add_watermark(doc, watermark_text)

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

    def _add_watermark(self, doc, watermark_text: str = "Processed by cookedcareer.com") -> None:
        """
        Add watermark to all pages of the PDF

        Args:
            doc: PyMuPDF document object (modified in place)
            watermark_text: Text to use for watermark
        """
        for page in doc:
            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            # Use light gray color for watermark
            text_color = (0.7, 0.7, 0.7)  # Medium-light gray

            # Font size - small but visible
            font_size = 10

            # Position at bottom center of page
            # Leave some margin from the bottom
            margin_bottom = 20
            y_position = page_height - margin_bottom

            # Calculate text width to center it
            text_width = fitz.get_text_length(watermark_text, fontname="hebo", fontsize=font_size)
            x_position = (page_width - text_width) / 2

            # Insert text at bottom center
            insert_point = fitz.Point(x_position, y_position)

            page.insert_text(
                insert_point,
                watermark_text,
                fontname="hebo",  # Helvetica Bold
                fontsize=font_size,
                color=text_color
            )

    def add_watermark_to_pdf(
        self,
        pdf_bytes: bytes,
        watermark_text: str = "Processed by cookedcareer.com"
    ) -> Dict[str, Any]:
        """
        Add watermark to a PDF

        Args:
            pdf_bytes: PDF file content as bytes
            watermark_text: Text to use for watermark

        Returns:
            Dictionary with success status and PDF bytes with watermark, or error
        """
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Add watermark
            self._add_watermark(doc, watermark_text)

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


# Global instance
pdf_service = PDFService()
