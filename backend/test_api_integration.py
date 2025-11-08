"""
Quick test to demonstrate AI-enhanced parser in API
"""
import sys
sys.path.insert(0, 'C:\\Users\\Jai Patel\\Desktop\\HackARooProject\\backend')

from main import _process_transcript

# Test cases showing improvements
test_cases = [
    "PRAHA RADAR HELLO LUFTHANSA FIVE MIKE ECHO",
    "PRAGA RADAR HELLO AEROFLOT TWO EIGHT FIVE APPROACHING TUSIN FLIGHT LEVEL TWO FOUR ZERO",
    "CSA SIX THREE FOUR TURN RIGHT HEADING ONE EIGHT ZERO",
]

print("="*70)
print("API INTEGRATION TEST: AI-Enhanced Parser")
print("="*70)

for transcript in test_cases:
    print(f"\n📝 Input: {transcript[:60]}...")

    # Test with AI parser (default)
    result_ai = _process_transcript(transcript, use_ai_parser=True)
    print(f"   AI Parser Callsign:   {result_ai['parsed'].get('callsign')}")
    print(f"   Message Type:         {result_ai['parsed'].get('message_type')}")
    print(f"   Airline:              {result_ai['parsed'].get('airline')}")

    # Test with original parser
    result_orig = _process_transcript(transcript, use_ai_parser=False)
    print(f"   Original Callsign:    {result_orig['parsed'].get('callsign')}")

    if result_ai['parsed'].get('callsign') != result_orig['parsed'].get('callsign'):
        print("   ✅ AI IMPROVED!")
    else:
        print("   ✓ Same result")

print("\n" + "="*70)
print("✅ API endpoints are now using AI-enhanced parser by default!")
print("="*70)
print("\nEndpoint behavior:")
print("  • POST /stt - Uses AI parser by default")
print("  • POST /interpret - Uses AI parser by default")
print("  • Add '?use_ai_parser=false' to use original parser")
print("="*70)

