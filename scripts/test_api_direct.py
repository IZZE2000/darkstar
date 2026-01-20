#!/usr/bin/env python3
"""
Test the gaps API directly using curl-like approach
"""

import json
import urllib.error
import urllib.request


def test_api():
    """Test the gaps API directly."""
    print("🔍 Testing /api/learning/gaps API directly...")

    try:
        # Test the API endpoint
        url = "http://localhost:8000/api/learning/gaps?days=10"

        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        print("✅ API Response:")
        print("Status: 200")
        print(f"Gaps found: {len(data)}")

        if data:
            print("\n📋 Gap Details:")
            for i, gap in enumerate(data):
                print(f"  Gap {i + 1}:")
                print(f"    Start: {gap['start_time']}")
                print(f"    End: {gap['end_time']}")
                print(f"    Missing slots: {gap['missing_slots']}")
        else:
            print("\n❌ NO GAPS RETURNED!")
            print("This explains why the UI shows 'System data up to date'")

        return data

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the backend is running on localhost:8000")
        return None


if __name__ == "__main__":
    result = test_api()

    if result is not None:
        print("\n🎯 CONCLUSION:")
        if len(result) == 0:
            print("The API is working but returns no gaps.")
            print("Either:")
            print("1. The fix didn't work correctly")
            print("2. There actually are no gaps (unlikely)")
            print("3. The database has more data than expected")
        else:
            print(f"The API correctly found {len(result)} gaps.")
            print("The issue might be:")
            print("1. Frontend caching")
            print("2. Frontend not calling the API")
            print("3. Frontend parsing the response incorrectly")
