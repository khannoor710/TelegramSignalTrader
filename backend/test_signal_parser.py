"""Test the signal parser with sample messages"""
from app.services.signal_parser import SignalParser

parser = SignalParser()

# Test messages that might come from Telegram
test_messages = [
    "BUY RELIANCE @ 2450 Target 2500 SL 2420",
    "SELL TATASTEEL Target: 145 StopLoss: 155",
    "Buy INFY at Rs 1800, target 1850, sl 1780",
    "NIFTY 23500 CE BUY @ 150 TGT 200 SL 120",
    "HDFC BUY entry 1650 qty 10",
    "Just a random message with no signal",
    "Buy TCS for delivery, target 4200",
]

print("=" * 60)
print("SIGNAL PARSER TEST")
print("=" * 60)

for msg in test_messages:
    print(f"\nMessage: {msg}")
    result = parser.parse_message(msg)
    if result:
        print(f"  ✅ Parsed: {result}")
    else:
        print(f"  ❌ No signal detected")
