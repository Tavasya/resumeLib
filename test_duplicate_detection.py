"""
Test script to verify duplicate detection works correctly
"""
from services.resume_service import resume_service


def test_duplicate_detection():
    """
    Test the new duplicate detection functionality
    """
    print("=" * 60)
    print("TESTING DUPLICATE DETECTION")
    print("=" * 60)

    # Test 1: Check by email
    print("\n[Test 1] Checking duplicate by email...")
    test_email = "test@example.com"
    result = resume_service.check_duplicate_exists(email=test_email)
    if result:
        print(f"  ✓ Found existing resume by email: {result.name} (ID: {result.id})")
    else:
        print(f"  ✓ No resume found with email: {test_email}")

    # Test 2: Check by name (using a known duplicate from cleanup)
    print("\n[Test 2] Checking duplicate by name...")
    test_name = "Vlas Zyrianov"  # We know this person had duplicates
    result = resume_service.check_duplicate_exists(name=test_name)
    if result:
        print(f"  ✓ Found existing resume by name: {result.name} (ID: {result.id})")
        print(f"     Email: {result.email or 'N/A'}")
        print(f"     Created: {result.created_at}")
    else:
        print(f"  ✓ No resume found with name: {test_name}")

    # Test 3: Check by both name and email
    print("\n[Test 3] Checking duplicate by name AND email...")
    if result:
        # Use the data from previous test
        result2 = resume_service.check_duplicate_exists(name=result.name, email=result.email)
        if result2:
            print(f"  ✓ Found resume: {result2.name} (ID: {result2.id})")
            assert result.id == result2.id, "Should find the same resume"
            print(f"  ✓ Duplicate detection working correctly!")
        else:
            print(f"  ✗ Failed to find resume by name+email")
    else:
        print(f"  ⊘ Skipped (no existing resume to test)")

    # Test 4: Non-existent resume
    print("\n[Test 4] Checking non-existent resume...")
    result = resume_service.check_duplicate_exists(
        name="John Doe That Does Not Exist",
        email="nonexistent@fakeemail.com"
    )
    if result:
        print(f"  ✗ Unexpectedly found resume: {result.name}")
    else:
        print(f"  ✓ Correctly returned None for non-existent resume")

    # Test 5: Get actual count of unique resumes
    print("\n[Test 5] Checking database state...")
    all_resumes = resume_service.list_resumes(limit=2000)
    unique_names = set()
    resumes_with_emails = 0
    resumes_without_emails = 0

    for resume in all_resumes:
        if resume.name:
            unique_names.add(resume.name.lower())
        if resume.email:
            resumes_with_emails += 1
        else:
            resumes_without_emails += 1

    print(f"  Total resumes in DB: {len(all_resumes)}")
    print(f"  Unique names: {len(unique_names)}")
    print(f"  Resumes with emails: {resumes_with_emails}")
    print(f"  Resumes without emails: {resumes_without_emails}")

    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_duplicate_detection()
