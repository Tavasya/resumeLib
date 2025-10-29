"""
Cleanup script to remove duplicate resumes from database and storage bucket
"""
import re
from config.supabase import supabase


def extract_storage_path(file_url: str) -> str:
    """
    Extract the storage path from a Supabase file URL

    Example:
    https://rvyjvklfvwkzgbnxsrzy.supabase.co/storage/v1/object/public/resumes/scraped/30742c62_AndrewKaminerResume2025.pdf
    -> scraped/30742c62_AndrewKaminerResume2025.pdf
    """
    if not file_url:
        return None

    # Pattern: /storage/v1/object/public/resumes/{path}
    match = re.search(r'/storage/v1/object/public/resumes/(.+)$', file_url)
    if match:
        return match.group(1)
    return None


def get_duplicates_to_delete():
    """
    Get all duplicate resumes that should be deleted (keeps the newest one)
    Returns list of dicts with id, name, email, file_url, created_at
    """
    # Get all resumes
    response = supabase.table('resumes').select('id,name,email,file_url,created_at').not_.is_('name', 'null').order('name', desc=False).order('created_at', desc=True).execute()

    if not response.data:
        return []

    # Group by name+email and identify duplicates
    seen = {}  # key: (name, email), value: first (newest) resume
    duplicates = []

    for resume in response.data:
        key = (resume['name'], resume.get('email') or 'NO_EMAIL_PROVIDED')

        if key in seen:
            # This is a duplicate (older entry)
            duplicates.append(resume)
        else:
            # This is the first (newest) entry for this person
            seen[key] = resume

    return duplicates


def delete_files_from_storage(file_urls):
    """
    Delete files from Supabase storage bucket
    """
    storage_paths = []
    for url in file_urls:
        if url:
            path = extract_storage_path(url)
            if path:
                storage_paths.append(path)

    if not storage_paths:
        print("No files to delete from storage")
        return

    # Remove duplicates from the list
    storage_paths = list(set(storage_paths))

    print(f"Deleting {len(storage_paths)} files from storage bucket...")

    deleted_count = 0
    failed_count = 0

    for path in storage_paths:
        try:
            # Delete from 'resumes' bucket
            supabase.storage.from_('resumes').remove([path])
            deleted_count += 1
            if deleted_count % 10 == 0:
                print(f"  Deleted {deleted_count}/{len(storage_paths)} files...")
        except Exception as e:
            failed_count += 1
            print(f"  Failed to delete {path}: {e}")

    print(f"✓ Storage cleanup complete: {deleted_count} deleted, {failed_count} failed")


def delete_duplicate_rows(resume_ids):
    """
    Delete duplicate resume rows from database
    """
    if not resume_ids:
        print("No database rows to delete")
        return

    print(f"Deleting {len(resume_ids)} duplicate rows from database...")

    # Delete in batches of 50
    batch_size = 50
    deleted_count = 0

    for i in range(0, len(resume_ids), batch_size):
        batch = resume_ids[i:i + batch_size]
        try:
            supabase.table('resumes').delete().in_('id', batch).execute()
            deleted_count += len(batch)
            print(f"  Deleted {deleted_count}/{len(resume_ids)} rows...")
        except Exception as e:
            print(f"  Failed to delete batch: {e}")

    print(f"✓ Database cleanup complete: {deleted_count} rows deleted")


def main():
    """
    Main cleanup process
    """
    print("=" * 60)
    print("DUPLICATE RESUME CLEANUP")
    print("=" * 60)

    # Step 1: Get duplicates
    print("\n[Step 1] Fetching duplicate resumes...")
    duplicates = get_duplicates_to_delete()

    if not duplicates:
        print("No duplicates found!")
        return

    print(f"Found {len(duplicates)} duplicate resumes to delete")

    # Extract IDs and file URLs
    resume_ids = [dup['id'] for dup in duplicates]
    file_urls = [dup.get('file_url') for dup in duplicates if dup.get('file_url')]

    # Show preview
    print("\nSample duplicates to delete:")
    for dup in duplicates[:5]:
        print(f"  - {dup['name']} (ID: {dup['id'][:8]}..., Created: {dup['created_at'][:10]})")
    print(f"  ... and {len(duplicates) - 5} more\n")

    # Step 2: Delete files from storage
    print("[Step 2] Deleting files from storage bucket...")
    delete_files_from_storage(file_urls)

    # Step 3: Delete rows from database
    print("\n[Step 3] Deleting duplicate rows from database...")
    delete_duplicate_rows(resume_ids)

    print("\n" + "=" * 60)
    print("CLEANUP COMPLETE!")
    print("=" * 60)
    print(f"✓ Removed {len(duplicates)} duplicate resumes")
    print("✓ Database and storage are now clean")


if __name__ == "__main__":
    main()
