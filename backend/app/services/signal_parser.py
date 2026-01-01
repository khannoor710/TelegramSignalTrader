"""
Signal parser for extracting trading information from messages
Supports both regex-based and AI-powered parsing (Google Gemini)
"""
import re
import os
import json
import httpx
from typing import Optional, Dict, Any
from app.core.logging_config import get_logger

logger = get_logger("signal_parser")


class AISignalParser:
    """AI-powered signal parser using Google Gemini for intelligent extraction"""
    
    SYSTEM_PROMPT = """You are a trading signal parser. Extract trading information from messages.

IMPORTANT RULES:
1. Only extract if there's a clear BUY or SELL signal
2. Symbol must be a valid Indian stock symbol (e.g., RELIANCE, TCS, INFY, TATASTEEL, HDFCBANK)
3. For F&O, extract the full symbol including expiry and strike (e.g., NIFTY24DEC23500CE)
4. Prices should be numeric values only
5. If information is not present, use null
6. Be smart about understanding context - "above 2450" means entry is 2450

Respond ONLY with valid JSON in this exact format:
{
    "is_signal": true/false,
    "action": "BUY" or "SELL" or null,
    "symbol": "SYMBOL" or null,
    "entry_price": number or null,
    "target_price": number or null,
    "stop_loss": number or null,
    "quantity": number or null,
    "exchange": "NSE" or "BSE" or "NFO" or "MCX",
    "product_type": "INTRADAY" or "DELIVERY",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}

Examples:
- "BUY RELIANCE @ 2450 TGT 2500 SL 2420" → {"is_signal": true, "action": "BUY", "symbol": "RELIANCE", "entry_price": 2450, "target_price": 2500, "stop_loss": 2420, ...}
- "Good morning everyone!" → {"is_signal": false, ...}
- "NIFTY 23500 CE looking bullish, buy above 150" → {"is_signal": true, "action": "BUY", "symbol": "NIFTY24DEC23500CE", "entry_price": 150, "exchange": "NFO", ...}"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.api_base = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}"
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("AI Signal Parser disabled - GEMINI_API_KEY not set")
        else:
            logger.info(f"AI Signal Parser enabled with Google Gemini ({self.model})")
    
    def _build_request_body(self, message: str) -> dict:
        """Build the Gemini API request body"""
        return {
            "contents": [
                {
                    "parts": [
                        {"text": f"{self.SYSTEM_PROMPT}\n\nParse this trading message:\n\n{message}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 500,
                "topP": 0.8,
                "topK": 10
            }
        }
    
    def _extract_result(self, data: dict) -> Optional[Dict[str, Any]]:
        """Extract and parse the result from Gemini response"""
        try:
            # Gemini response structure
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            parsed = json.loads(content.strip())
            
            if not parsed.get("is_signal"):
                return None
            
            # Convert to standard format
            return {
                "action": parsed.get("action"),
                "symbol": parsed.get("symbol"),
                "entry_price": parsed.get("entry_price"),
                "target_price": parsed.get("target_price"),
                "stop_loss": parsed.get("stop_loss"),
                "quantity": parsed.get("quantity"),
                "exchange": parsed.get("exchange", "NSE"),
                "product_type": parsed.get("product_type", "INTRADAY"),
                "confidence": parsed.get("confidence", 0.8),
                "reasoning": parsed.get("reasoning", ""),
                "ai_parsed": True
            }
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to extract Gemini response: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
    
    async def parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse message using Google Gemini AI"""
        if not self.enabled or not message:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=self._build_request_body(message)
                )
                
                if response.status_code != 200:
                    logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                    return None
                
                return self._extract_result(response.json())
                
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            return None
    
    def parse_sync(self, message: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of parse for non-async contexts"""
        if not self.enabled or not message:
            return None
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.api_base}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=self._build_request_body(message)
                )
                
                if response.status_code != 200:
                    logger.error(f"Gemini API error: {response.status_code}")
                    return None
                
                return self._extract_result(response.json())
                
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            return None


class RegexSignalParser:
    """Fallback regex-based signal parser"""
    
    EXCLUDED_WORDS = {'BUY', 'SELL', 'TARGET', 'TGT', 'SL', 'QTY', 'QUANTITY', 'PRICE', 
                      'ENTRY', 'EXIT', 'STOP', 'LOSS', 'AT', 'RS', 'INR', 'NSE', 'BSE',
                      'NFO', 'MCX', 'CDS', 'MARKET', 'LIMIT', 'INTRADAY', 'DELIVERY',
                      'TP', 'CE', 'PE', 'CALL', 'PUT', 'ABOVE', 'BELOW', 'AROUND', 'NEAR',
                      'ABV', 'BLW'}
    
    def __init__(self):
        self.patterns = {
            'symbol': r'\b([A-Za-z][A-Za-z0-9]{1,15})\b',  # Case-insensitive symbol matching
            'buy': r'\b(?:BUY|buy|Buy|ABV|abv|Abv)\b',  # ABV (above) implies BUY
            'sell': r'\b(?:SELL|sell|Sell|BLW|blw|Blw)\b',  # BLW (below) implies SELL
            'price': r'(?:@|at|price|entry|above|below|abv|blw)\s*:?\s*(?:Rs\.?\s*)?(\d+(?:\.\d{1,2})?)',
            'target': r'(?:target|tgt|tp|t1|t2)\s*:?\s*(?:Rs\.?\s*)?(\d+(?:\.\d{1,2})?)',
            'stop_loss': r'(?:sl|stop\s*loss|stoploss)\s*:?\s*(?:Rs\.?\s*)?(\d+(?:\.\d{1,2})?)',
            'quantity': r'(?:qty|quantity|lot)\s*:?\s*(\d+)',
        }
    
    def parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse trading signal using regex patterns"""
        if not message:
            return None
        
        is_buy = re.search(self.patterns['buy'], message)
        is_sell = re.search(self.patterns['sell'], message)
        
        if not (is_buy or is_sell):
            return None
        
        signal = {
            'action': 'BUY' if is_buy else 'SELL',
            'symbol': None,
            'entry_price': None,
            'target_price': None,
            'stop_loss': None,
            'quantity': None,
            'exchange': 'NSE',
            'product_type': 'INTRADAY',
            'ai_parsed': False
        }
        
        # Extract symbol
        potential_symbols = re.findall(self.patterns['symbol'], message)
        for sym in potential_symbols:
            if sym.upper() not in self.EXCLUDED_WORDS and len(sym) >= 2:
                signal['symbol'] = sym.upper()
                break
        
        # Extract prices
        price_match = re.search(self.patterns['price'], message, re.IGNORECASE)
        if price_match:
            signal['entry_price'] = float(price_match.group(1))
        
        target_match = re.search(self.patterns['target'], message, re.IGNORECASE)
        if target_match:
            signal['target_price'] = float(target_match.group(1))
        
        sl_match = re.search(self.patterns['stop_loss'], message, re.IGNORECASE)
        if sl_match:
            signal['stop_loss'] = float(sl_match.group(1))
        
        qty_match = re.search(self.patterns['quantity'], message, re.IGNORECASE)
        if qty_match:
            signal['quantity'] = int(qty_match.group(1))
        
        if signal['symbol']:
            return signal
        
        return None


class SignalParser:
    """
    Hybrid signal parser that uses AI when available, falls back to regex.
    AI provides smarter parsing with context understanding.
    """
    
    def __init__(self, prefer_ai: bool = True):
        self.ai_parser = AISignalParser()
        self.regex_parser = RegexSignalParser()
        self.prefer_ai = prefer_ai and self.ai_parser.enabled
        
        if self.prefer_ai:
            logger.info("Signal Parser initialized with AI mode")
        else:
            logger.info("Signal Parser initialized with regex mode (AI not available)")
    
    async def parse_message_async(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse message, preferring AI if available"""
        if self.prefer_ai:
            result = await self.ai_parser.parse(message)
            if result:
                return result
        
        # Fallback to regex
        return self.regex_parser.parse(message)
    
    def parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Synchronous parse method for compatibility"""
        if self.prefer_ai:
            result = self.ai_parser.parse_sync(message)
            if result:
                return result
        
        return self.regex_parser.parse(message)
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate if signal has minimum required information"""
        return bool(signal.get('symbol') and signal.get('action'))
    
    @property
    def is_ai_enabled(self) -> bool:
        """Check if AI parsing is available"""
        return self.ai_parser.enabled
