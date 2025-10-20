"""
Resume file downloader
Downloads PDF and DOCX files from URLs
"""
import os
import requests
from typing import Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse


class ResumeDownloader:
    """Downloads resume files from URLs"""

    def __init__(self, download_dir: str = "./downloads"):
        """
        Initialize downloader

        Args:
            download_dir: Directory to save downloaded files
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, filename: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """
        Download a file from URL

        Args:
            url: URL to download from
            filename: Optional custom filename (will be auto-generated if not provided)

        Returns:
            Tuple of (file_path, file_type) if successful, None otherwise
        """
        try:
            # Set headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            # Download the file
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()

            # Determine file type from content-type or URL
            content_type = response.headers.get('content-type', '').lower()
            file_type = self._determine_file_type(url, content_type)

            if not file_type:
                print(f"Could not determine file type for {url}")
                return None

            # Generate filename if not provided
            if not filename:
                filename = self._generate_filename(url, file_type)

            # Full file path
            file_path = self.download_dir / filename

            # Write file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Downloaded: {filename}")
            return (str(file_path), file_type)

        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error downloading {url}: {e}")
            return None

    def _determine_file_type(self, url: str, content_type: str) -> Optional[str]:
        """
        Determine file type from URL or content-type

        Args:
            url: File URL
            content_type: HTTP content-type header

        Returns:
            'pdf' or 'docx' if valid, None otherwise
        """
        # Check content-type
        if 'pdf' in content_type:
            return 'pdf'
        elif 'word' in content_type or 'document' in content_type:
            return 'docx'

        # Check URL extension
        url_lower = url.lower()
        if url_lower.endswith('.pdf'):
            return 'pdf'
        elif url_lower.endswith('.docx') or url_lower.endswith('.doc'):
            return 'docx'

        return None

    def _generate_filename(self, url: str, file_type: str) -> str:
        """
        Generate a unique filename from URL to prevent collisions

        Args:
            url: File URL
            file_type: File extension (pdf or docx)

        Returns:
            Generated unique filename
        """
        import hashlib

        # Generate unique hash prefix from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Parse URL to get path
        parsed = urlparse(url)
        path = parsed.path

        # Try to extract filename from path
        if path:
            filename = Path(path).name
            if filename and not filename.startswith('.'):
                # Clean filename
                filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.'))
                # Remove existing extension
                filename_base = filename.rsplit('.', 1)[0] if '.' in filename else filename
                # Prepend hash to make it unique
                return f"{url_hash}_{filename_base}.{file_type}"

        # Fallback: just use hash
        return f"resume_{url_hash}.{file_type}"

    def download_batch(self, urls: list) -> list:
        """
        Download multiple files

        Args:
            urls: List of URLs to download

        Returns:
            List of tuples (file_path, file_type) for successful downloads
        """
        results = []
        for url in urls:
            result = self.download(url)
            if result:
                results.append(result)
        return results


# Global downloader instance
resume_downloader = ResumeDownloader()
