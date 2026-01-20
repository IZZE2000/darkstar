#!/usr/bin/env python3
"""
Simple API Test for Gap Detection
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import httpx


async def test_gaps_api():
    """Test the gaps API directly."""
    print("🔍 Testing /api/learning/gaps API...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/learning/gaps?days=10")
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Gaps found: {len(data)}")
                
                if data:
                    print("Gap details:")
                    for gap in data:
                        print(f"  {gap['start_time']} → {gap['end_time']} ({gap['missing_slots']} slots)")
                else:
                    print("❌ No gaps returned - this explains the 'up to date' message!")
            else:
                print(f"❌ API error: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the backend is running on localhost:8000")


if __name__ == "__main__":
    asyncio.run(test_gaps_api())
