"""
Supabase Storage service for uploading resume files
"""
from pathlib import Path
from typing import Optional, Tuple
import os
from config import supabase


class StorageService:
    """Service for managing file uploads to Supabase Storage"""

    def __init__(self, bucket_name: str = "resumes"):
        """
        Initialize storage service

        Args:
            bucket_name: Name of the Supabase storage bucket
        """
        self.bucket_name = bucket_name

    def upload_file(
        self,
        file_path: str,
        folder: str = "scraped"
    ) -> Optional[str]:
        """
        Upload a file to Supabase Storage

        Args:
            file_path: Local path to the file
            folder: Folder within the bucket (organizes files)

        Returns:
            Public URL of the uploaded file, or None if upload failed
        """
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                print(f"File not found: {file_path}")
                return None

            # Generate storage path: folder/filename
            storage_path = f"{folder}/{file_path_obj.name}"

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Determine content type
            content_type = self._get_content_type(file_path_obj.suffix)

            # Upload to Supabase Storage
            response = supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            # Get the public URL (even for private buckets, we can get signed URLs)
            # For private buckets, you'll need to use get_public_url with signed=True
            public_url = supabase.storage.from_(self.bucket_name).get_public_url(storage_path)

            print(f"  ✓ Uploaded to Supabase Storage: {storage_path}")
            return public_url

        except Exception as e:
            print(f"  ✗ Error uploading to Supabase Storage: {e}")
            return None

    def download_file(
        self,
        storage_path: str,
        local_path: str
    ) -> bool:
        """
        Download a file from Supabase Storage

        Args:
            storage_path: Path in the bucket (e.g., "scraped/resume.pdf")
            local_path: Local path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Download file content
            response = supabase.storage.from_(self.bucket_name).download(storage_path)

            # Write to local file
            with open(local_path, 'wb') as f:
                f.write(response)

            print(f"Downloaded: {storage_path} -> {local_path}")
            return True

        except Exception as e:
            print(f"Error downloading from Supabase Storage: {e}")
            return False

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from Supabase Storage

        Args:
            storage_path: Path in the bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase.storage.from_(self.bucket_name).remove([storage_path])
            print(f"Deleted from storage: {storage_path}")
            return True

        except Exception as e:
            print(f"Error deleting from Supabase Storage: {e}")
            return False

    def list_files(self, folder: str = "") -> list:
        """
        List files in a folder

        Args:
            folder: Folder path (empty string for root)

        Returns:
            List of file objects
        """
        try:
            files = supabase.storage.from_(self.bucket_name).list(folder)
            return files

        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def _get_content_type(self, extension: str) -> str:
        """
        Get content type from file extension

        Args:
            extension: File extension (e.g., ".pdf")

        Returns:
            MIME type string
        """
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
        }

        return content_types.get(extension.lower(), "application/octet-stream")

    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a signed URL for private files

        Args:
            storage_path: Path in the bucket
            expires_in: Seconds until URL expires (default 1 hour)

        Returns:
            Signed URL or None
        """
        try:
            signed_url = supabase.storage.from_(self.bucket_name).create_signed_url(
                storage_path,
                expires_in
            )
            return signed_url.get("signedURL")

        except Exception as e:
            print(f"Error creating signed URL: {e}")
            return None


# Global storage service instance
storage_service = StorageService(bucket_name="resumes")
