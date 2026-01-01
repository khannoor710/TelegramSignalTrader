"""Test lowercase signal parsing"""
import sys
sys.path.insert(0, 'backend')

from app.services.signal_parser import SignalParser

parser = SignalParser(prefer_ai=False)  # Use regex parser

# Test the exact signal from the user
test_signal = "banknifty 53200 pe buy above 350 tgt 400 sl 290"

print("=" * 70)
print("LOWERCASE SIGNAL TEST")
print("=" * 70)
print(f"\nTesting signal: {test_signal}\n")

result = parser.parse_message(test_signal)

if result:
    print("✅ Signal parsed successfully!")
    print(f"\nParsed details:")
    print(f"  Action:       {result.get('action')}")
    print(f"  Symbol:       {result.get('symbol')}")
    print(f"  Entry Price:  {result.get('entry_price')}")
    print(f"  Target Price: {result.get('target_price')}")
    print(f"  Stop Loss:    {result.get('stop_loss')}")
    print(f"  Exchange:     {result.get('exchange')}")
    print(f"  Product Type: {result.get('product_type')}")
else:
    print("❌ Signal parsing failed!")

print("\n" + "=" * 70)

# Test more lowercase variations
print("\nTesting additional lowercase signals:\n")

test_cases = [
    "banknifty 53200 pe buy above 350 tgt 400 sl 290",
    "nifty 24000 ce buy at 200 target 250 sl 180",
    "reliance buy above 2450 target 2500 sl 2420",
    "tatasteel sell below 150 tgt 145 sl 155",
    "HDFC BUY @ 1650 TGT 1700 SL 1620",  # uppercase (should still work)
]

for msg in test_cases:
    result = parser.parse_message(msg)
    status = "✅" if result else "❌"
    symbol = result.get('symbol') if result else "N/A"
    print(f"{status} {msg[:50]:<50} → Symbol: {symbol}")
