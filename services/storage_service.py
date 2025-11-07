"""
Supabase Storage service for uploading resume files
"""
from pathlib import Path
from typing import Optional, Tuple
import os
from config import supabase


class StorageService:
    """Service for managing file uploads to Supabase Storage"""

    def upload_file(
        self,
        bucket_name: str,
        storage_path: str,
        file_content: bytes,
        content_type: str
    ) -> str:
        """
        Upload a file to Supabase Storage

        Args:
            bucket_name: Name of the Supabase storage bucket
            storage_path: Full path where file should be stored in bucket
            file_content: File content as bytes
            content_type: MIME type of the file (e.g., "application/pdf")

        Returns:
            Public URL of the uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            # Upload to Supabase Storage
            supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            # Get the public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)

            return public_url

        except Exception as e:
            raise Exception(f"Failed to upload to Supabase Storage: {e}")

    def upload_file_from_path(
        self,
        bucket_name: str,
        file_path: str,
        storage_path: str
    ) -> Optional[str]:
        """
        Upload a file from local filesystem to Supabase Storage

        Args:
            bucket_name: Name of the Supabase storage bucket
            file_path: Local path to the file
            storage_path: Full path where file should be stored in bucket

        Returns:
            Public URL of the uploaded file, or None if upload failed
        """
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                print(f"File not found: {file_path}")
                return None

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Determine content type
            content_type = self._get_content_type(file_path_obj.suffix)

            # Upload using main upload method
            public_url = self.upload_file(bucket_name, storage_path, file_content, content_type)

            print(f"  ✓ Uploaded to Supabase Storage: {storage_path}")
            return public_url

        except Exception as e:
            print(f"  ✗ Error uploading to Supabase Storage: {e}")
            return None

    def download_file(
        self,
        bucket_name: str,
        storage_path: str,
        local_path: str
    ) -> bool:
        """
        Download a file from Supabase Storage

        Args:
            bucket_name: Name of the Supabase storage bucket
            storage_path: Path in the bucket (e.g., "scraped/resume.pdf")
            local_path: Local path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Download file content
            response = supabase.storage.from_(bucket_name).download(storage_path)

            # Write to local file
            with open(local_path, 'wb') as f:
                f.write(response)

            print(f"Downloaded: {storage_path} -> {local_path}")
            return True

        except Exception as e:
            print(f"Error downloading from Supabase Storage: {e}")
            return False

    def delete_file(self, bucket_name: str, storage_path: str) -> bool:
        """
        Delete a file from Supabase Storage

        Args:
            bucket_name: Name of the Supabase storage bucket
            storage_path: Path in the bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase.storage.from_(bucket_name).remove([storage_path])
            print(f"Deleted from storage: {storage_path}")
            return True

        except Exception as e:
            print(f"Error deleting from Supabase Storage: {e}")
            return False

    def list_files(self, bucket_name: str, folder: str = "") -> list:
        """
        List files in a folder

        Args:
            bucket_name: Name of the Supabase storage bucket
            folder: Folder path (empty string for root)

        Returns:
            List of file objects
        """
        try:
            files = supabase.storage.from_(bucket_name).list(folder)
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

    def get_signed_url(self, bucket_name: str, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a signed URL for private files

        Args:
            bucket_name: Name of the Supabase storage bucket
            storage_path: Path in the bucket
            expires_in: Seconds until URL expires (default 1 hour)

        Returns:
            Signed URL or None
        """
        try:
            signed_url = supabase.storage.from_(bucket_name).create_signed_url(
                storage_path,
                expires_in
            )
            return signed_url.get("signedURL")

        except Exception as e:
            print(f"Error creating signed URL: {e}")
            return None


# Global storage service instance
storage_service = StorageService()
