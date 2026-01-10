"""
Symbol Resolver Service
Resolves generic signal names to correct broker-compatible instrument names
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from app.core.logging_config import get_logger

logger = get_logger("symbol_resolver")


class SymbolResolver:
    """
    Resolves generic stock/option names from signals to correct trading symbols
    
    Examples:
    - "RELIANCE" → "RELIANCE-EQ" (NSE equity)
    - "NIFTY 25000 CE" → "NIFTY25DEC24500CE" (current month option)
    - "BANKNIFTY 52000 PE" → "BANKNIFTY25JAN52000PE" (current month option)
    - "TCS FUT" → "TCS25JANFUT" (current month future)
    """
    
    # Common stock name variations and corrections
    STOCK_ALIASES = {
        "RELIANCE": ["RIL", "RELIANCE INDUSTRIES", "RELIANCE IND"],
        "TATASTEEL": ["TATA STEEL", "TATA STEEL LTD"],
        "TATAMOTORS": ["TATA MOTORS", "TATAMOT"],
        "HDFCBANK": ["HDFC BANK", "HDFC"],
        "ICICIBANK": ["ICICI BANK", "ICICI"],
        "SBIN": ["SBI", "STATE BANK", "STATE BANK OF INDIA"],
        "INFY": ["INFOSYS", "INFOSYS LTD"],
        "TCS": ["TATA CONSULTANCY", "TATA CONSULTANCY SERVICES"],
        "WIPRO": ["WIPRO LTD"],
        "BHARTIARTL": ["AIRTEL", "BHARTI AIRTEL", "BHARTI"],
        "AXISBANK": ["AXIS BANK", "AXIS"],
        "KOTAKBANK": ["KOTAK", "KOTAK MAHINDRA", "KOTAK BANK"],
        "HINDUNILVR": ["HUL", "HINDUSTAN UNILEVER"],
        "MARUTI": ["MARUTI SUZUKI", "MSIL"],
        "BAJFINANCE": ["BAJAJ FINANCE", "BAJ FINANCE"],
        "BAJAJFINSV": ["BAJAJ FINSERV"],
        "ASIANPAINT": ["ASIAN PAINTS"],
        "ULTRACEMCO": ["ULTRATECH", "ULTRATECH CEMENT"],
        "SUNPHARMA": ["SUN PHARMA"],
        "DRREDDY": ["DR REDDY", "DR REDDYS"],
        "CIPLA": ["CIPLA LTD"],
        "ONGC": ["OIL AND NATURAL GAS", "OIL INDIA"],
        "NTPC": ["NTPC LTD"],
        "POWERGRID": ["POWER GRID"],
        "COALINDIA": ["COAL INDIA"],
        "JSWSTEEL": ["JSW STEEL"],
        "HINDALCO": ["HINDALCO INDUSTRIES"],
        "ADANIENT": ["ADANI ENT", "ADANI ENTERPRISES"],
        "ADANIPORTS": ["ADANI PORTS"],
        "LT": ["L&T", "LARSEN", "LARSEN & TOUBRO", "LARSEN AND TOUBRO"],
        "TECHM": ["TECH MAHINDRA"],
        "HCLTECH": ["HCL TECH", "HCL TECHNOLOGIES"],
        "M&M": ["MAHINDRA", "M AND M", "MAHINDRA AND MAHINDRA"],
        "EICHERMOT": ["EICHER", "EICHER MOTORS"],
        "HEROMOTOCO": ["HERO", "HERO MOTOCORP"],
        "BAJAJ-AUTO": ["BAJAJ AUTO", "BAJAJAUTO"],
        "DIVISLAB": ["DIVIS LAB", "DIVIS LABORATORIES"],
        "GRASIM": ["GRASIM INDUSTRIES"],
        "BRITANNIA": ["BRITANNIA INDUSTRIES"],
        "NESTLEIND": ["NESTLE", "NESTLE INDIA"],
        "TITAN": ["TITAN COMPANY"],
        "ITC": ["ITC LTD"],
    }
    
    # Index options with their exchanges
    # NSE indices trade on NFO, BSE indices trade on BFO
    INDEX_OPTIONS = {
        "NIFTY": {"symbol": "NIFTY", "exchange": "NFO"},
        "BANKNIFTY": {"symbol": "BANKNIFTY", "exchange": "NFO"},
        "FINNIFTY": {"symbol": "FINNIFTY", "exchange": "NFO"},
        "MIDCPNIFTY": {"symbol": "MIDCPNIFTY", "exchange": "NFO"},
        "SENSEX": {"symbol": "SENSEX", "exchange": "BFO"},
        "BANKEX": {"symbol": "BANKEX", "exchange": "BFO"},
    }
    
    # Month codes for F&O
    MONTH_CODES = {
        1: "JAN", 2: "FEB", 3: "MAR", 4: "APR",
        5: "MAY", 6: "JUN", 7: "JUL", 8: "AUG",
        9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"
    }
    
    def __init__(self, symbol_master=None):
        self.symbol_master = symbol_master
        self._reverse_aliases = self._build_reverse_aliases()
    
    def _build_reverse_aliases(self) -> Dict[str, str]:
        """Build reverse lookup for aliases"""
        reverse = {}
        for canonical, aliases in self.STOCK_ALIASES.items():
            for alias in aliases:
                reverse[alias.upper()] = canonical
        return reverse
    
    def resolve_symbol(
        self, 
        raw_symbol: str, 
        exchange: str = "NSE",
        instrument_type: str = None
    ) -> Dict[str, Any]:
        """
        Resolve a generic symbol to the correct trading symbol
        
        Args:
            raw_symbol: The symbol from the signal (e.g., "RELIANCE", "NIFTY 25000 CE")
            exchange: Target exchange (NSE, BSE, NFO, MCX)
            instrument_type: Optional hint (EQUITY, OPTION, FUTURE)
        
        Returns:
            Dict with resolved symbol info:
            {
                "success": True/False,
                "original": "RELIANCE",
                "resolved_symbol": "RELIANCE-EQ",
                "token": "2885",
                "exchange": "NSE",
                "instrument_type": "EQUITY",
                "name": "RELIANCE INDUSTRIES LTD",
                "message": "Successfully resolved"
            }
        """
        raw_symbol = raw_symbol.strip().upper()
        logger.info(f"🔍 Resolving symbol: '{raw_symbol}' for exchange: {exchange}")
        
        # Check if it's an F&O symbol
        fno_result = self._parse_fno_symbol(raw_symbol)
        if fno_result:
            return self._resolve_fno_symbol(fno_result, raw_symbol)
        
        # It's an equity symbol
        return self._resolve_equity_symbol(raw_symbol, exchange)
    
    def _parse_fno_symbol(self, raw_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Parse F&O symbol components from raw input
        
        Examples:
        - "NIFTY 25000 CE" → {index: "NIFTY", strike: 25000, option_type: "CE"}
        - "BANKNIFTY 52000 PE JAN" → {index: "BANKNIFTY", strike: 52000, option_type: "PE", expiry: "JAN"}
        - "RELIANCE 1400 CE" → {symbol: "RELIANCE", strike: 1400, option_type: "CE"}
        - "NIFTY FUT" → {index: "NIFTY", is_future: True}
        """
        # Pattern for options: SYMBOL STRIKE CE/PE [EXPIRY]
        # Supports: "NIFTY 25000 CE", "SENSEX 85500CE", "BANKNIFTY52000PE"
        option_pattern = r'^(\w+)\s*(\d+(?:\.\d+)?)\s*(CE|PE|CALL|PUT)(?:\s+(\w+))?$'
        # Pattern for futures: SYMBOL FUT [EXPIRY]
        future_pattern = r'^(\w+)\s+FUT(?:URE)?(?:\s+(\w+))?$'
        
        # Try option pattern
        match = re.match(option_pattern, raw_symbol, re.IGNORECASE)
        if match:
            symbol = match.group(1).upper()
            strike = float(match.group(2))
            option_type = match.group(3).upper()
            expiry = match.group(4).upper() if match.group(4) else None
            
            # Normalize option type
            if option_type == "CALL":
                option_type = "CE"
            elif option_type == "PUT":
                option_type = "PE"
            
            return {
                "symbol": symbol,
                "strike": strike,
                "option_type": option_type,
                "expiry_hint": expiry,
                "is_option": True,
                "is_index": symbol in self.INDEX_OPTIONS,
                "exchange": self.INDEX_OPTIONS.get(symbol, {}).get("exchange", "NFO") if symbol in self.INDEX_OPTIONS else "NFO"
            }
        
        # Try future pattern
        match = re.match(future_pattern, raw_symbol, re.IGNORECASE)
        if match:
            symbol = match.group(1).upper()
            expiry = match.group(2).upper() if match.group(2) else None
            
            return {
                "symbol": symbol,
                "expiry_hint": expiry,
                "is_future": True,
                "is_index": symbol in self.INDEX_OPTIONS
            }
        
        return None
    
    def _resolve_fno_symbol(self, fno_info: Dict, original: str) -> Dict[str, Any]:
        """Resolve F&O symbol to correct format"""
        symbol = fno_info["symbol"]
        # Get exchange from fno_info (BFO for SENSEX/BANKEX, NFO for others)
        target_exchange = fno_info.get("exchange", "NFO")
        
        if fno_info.get("is_option"):
            strike = fno_info["strike"]
            option_type = fno_info["option_type"]
            
            # Format strike (remove decimal if whole number)
            strike_str = str(int(strike)) if strike == int(strike) else str(strike)
            
            # Try to find matching option from symbol master
            if self.symbol_master:
                # Search for options matching symbol, strike, and option type
                search_results = self._search_fno_options(symbol, strike_str, option_type, fno_info.get("expiry_hint"), target_exchange)
                if search_results:
                    best = search_results[0]
                    logger.info(f"✅ Found F&O match: {original} → {best['symbol']} (token: {best['token']}, exchange: {best['exchange']})")
                    return {
                        "success": True,
                        "original": original,
                        "resolved_symbol": best["symbol"],
                        "token": best["token"],
                        "exchange": best["exchange"],
                        "instrument_type": "OPTION",
                        "message": f"Found match: {best['symbol']}"
                    }
            
            # Fallback: construct symbol with weekly expiry format (DDMON2Y)
            expiry = self._get_weekly_expiry_string(fno_info.get("expiry_hint"))
            resolved = f"{symbol}{expiry}{strike_str}{option_type}"
            exchange = target_exchange  # Use BFO for SENSEX/BANKEX
            
        else:  # Future
            expiry = self._get_monthly_expiry_string(fno_info.get("expiry_hint"))
            resolved = f"{symbol}{expiry}FUT"
            exchange = target_exchange  # Use BFO for SENSEX/BANKEX
            
            if self.symbol_master:
                token = self.symbol_master.get_token(resolved, exchange)
                if token:
                    logger.info(f"✅ Resolved future: {original} → {resolved} (token: {token})")
                    return {
                        "success": True,
                        "original": original,
                        "resolved_symbol": resolved,
                        "token": token,
                        "exchange": exchange,
                        "instrument_type": "FUTURE",
                        "message": f"Resolved to {resolved}"
                    }
        
        # Return constructed symbol without validation
        logger.warning(f"⚠️ Could not validate F&O symbol: {resolved}")
        return {
            "success": True,
            "original": original,
            "resolved_symbol": resolved,
            "token": None,
            "exchange": exchange,
            "instrument_type": "OPTION" if fno_info.get("is_option") else "FUTURE",
            "message": f"Constructed symbol (unvalidated): {resolved}"
        }
    
    def _search_fno_options(
        self, 
        symbol: str, 
        strike: str, 
        option_type: str, 
        expiry_hint: str = None,
        exchange: str = "NFO"
    ) -> List[Dict]:
        """Search for F&O options matching criteria on specified exchange"""
        if not self.symbol_master:
            return []
        
        # Search pattern: symbol + strike + option_type
        search_query = f"{symbol}{strike}{option_type}"
        logger.info(f"🔍 Searching F&O: {search_query} on {exchange}")
        
        results = self.symbol_master.search_symbol(search_query, exchange, limit=20)
        
        if not results:
            # Try searching just with symbol
            logger.info(f"🔍 Fallback search: {symbol} on {exchange}")
            results = self.symbol_master.search_symbol(symbol, exchange, limit=50)
        
        # Filter and sort results
        matching = []
        now = datetime.now()
        
        for r in results:
            sym = r.get("symbol", "")
            # Check if it matches our criteria
            if strike in sym and option_type in sym and symbol in sym:
                # Parse expiry from symbol to sort by nearest expiry
                matching.append(r)
        
        # Sort by symbol (nearest expiry first - they're usually sorted alphabetically by date)
        matching.sort(key=lambda x: x.get("symbol", ""))
        
        logger.info(f"🔍 Found {len(matching)} matching options for {symbol}{strike}{option_type} on {exchange}")
        
        # Filter by expiry hint if provided
        if expiry_hint and matching:
            hint_upper = expiry_hint.upper()
            filtered = [m for m in matching if hint_upper in m.get("symbol", "").upper()]
            if filtered:
                return filtered
        
        return matching
    
    def _resolve_equity_symbol(self, raw_symbol: str, exchange: str) -> Dict[str, Any]:
        """Resolve equity symbol to correct format"""
        # First, check for aliases
        canonical = self._reverse_aliases.get(raw_symbol, raw_symbol)
        
        # For NSE, try with -EQ suffix first
        if exchange == "NSE":
            candidates = [
                f"{canonical}-EQ",
                canonical,
                f"{raw_symbol}-EQ",
                raw_symbol
            ]
        else:
            candidates = [canonical, raw_symbol]
        
        if self.symbol_master:
            for symbol_candidate in candidates:
                token = self.symbol_master.get_token(symbol_candidate, exchange)
                if token:
                    logger.info(f"✅ Resolved equity: {raw_symbol} → {symbol_candidate} (token: {token})")
                    return {
                        "success": True,
                        "original": raw_symbol,
                        "resolved_symbol": symbol_candidate,
                        "token": token,
                        "exchange": exchange,
                        "instrument_type": "EQUITY",
                        "message": f"Resolved to {symbol_candidate}"
                    }
            
            # Try searching
            results = self.symbol_master.search_symbol(canonical, exchange, limit=10)
            if results:
                # Prefer exact name matches or -EQ suffix
                for result in results:
                    if result.get("name", "").upper() == canonical or \
                       result.get("symbol", "").upper() == f"{canonical}-EQ":
                        logger.info(f"✅ Found equity match: {raw_symbol} → {result['symbol']} (token: {result['token']})")
                        return {
                            "success": True,
                            "original": raw_symbol,
                            "resolved_symbol": result["symbol"],
                            "token": result["token"],
                            "exchange": result["exchange"],
                            "instrument_type": "EQUITY",
                            "name": result.get("name"),
                            "message": f"Found match: {result['symbol']}"
                        }
                
                # Return first result as fallback
                best = results[0]
                logger.info(f"✅ Using best equity match: {raw_symbol} → {best['symbol']}")
                return {
                    "success": True,
                    "original": raw_symbol,
                    "resolved_symbol": best["symbol"],
                    "token": best["token"],
                    "exchange": best["exchange"],
                    "instrument_type": "EQUITY",
                    "name": best.get("name"),
                    "message": f"Best match: {best['symbol']}"
                }
        
        # Fallback: return with -EQ suffix for NSE
        if exchange == "NSE":
            resolved = f"{canonical}-EQ"
        else:
            resolved = canonical
        
        logger.warning(f"⚠️ Could not validate equity symbol: {resolved}")
        return {
            "success": False,
            "original": raw_symbol,
            "resolved_symbol": resolved,
            "token": None,
            "exchange": exchange,
            "instrument_type": "EQUITY",
            "message": f"Could not validate symbol: {resolved}"
        }
    
    def _get_expiry_string(self, hint: str = None) -> str:
        """Get expiry string (e.g., '25DEC' for December 2025)"""
        now = datetime.now()
        
        if hint:
            # Check if hint is a month name
            for month_num, month_code in self.MONTH_CODES.items():
                if hint.upper() == month_code:
                    year = now.year
                    # If the month has passed, use next year
                    if month_num < now.month:
                        year += 1
                    return f"{str(year)[2:]}{month_code}"
        
        # Default to current month
        year_short = str(now.year)[2:]
        month_code = self.MONTH_CODES[now.month]
        return f"{year_short}{month_code}"
    
    def _get_weekly_expiry_string(self, hint: str = None) -> str:
        """
        Get weekly expiry string (e.g., '02JAN25' for 2nd January 2025)
        Weekly expiry format: DDMONYY
        """
        now = datetime.now()
        
        if hint:
            # Check if hint is a month name - use next expiry in that month
            for month_num, month_code in self.MONTH_CODES.items():
                if hint.upper() == month_code:
                    year = now.year
                    if month_num < now.month:
                        year += 1
                    # Default to first week of the month
                    return f"02{month_code}{str(year)[2:]}"
        
        # Find next Thursday (NIFTY/BANKNIFTY weekly expiry is on Thursday)
        days_until_thursday = (3 - now.weekday()) % 7
        if days_until_thursday == 0 and now.hour >= 15:  # Past 3 PM on Thursday
            days_until_thursday = 7
        
        next_expiry = now + timedelta(days=days_until_thursday)
        day = str(next_expiry.day).zfill(2)
        month_code = self.MONTH_CODES[next_expiry.month]
        year_short = str(next_expiry.year)[2:]
        
        return f"{day}{month_code}{year_short}"
    
    def _get_monthly_expiry_string(self, hint: str = None) -> str:
        """
        Get monthly expiry string for futures (e.g., '25JAN' for January 2025)
        Monthly format: YYMON
        """
        now = datetime.now()
        
        if hint:
            for month_num, month_code in self.MONTH_CODES.items():
                if hint.upper() == month_code:
                    year = now.year
                    if month_num < now.month:
                        year += 1
                    return f"{str(year)[2:]}{month_code}"
        
        # Default to current month
        year_short = str(now.year)[2:]
        month_code = self.MONTH_CODES[now.month]
        return f"{year_short}{month_code}"
    
    def _find_best_fno_match(self, results: List[Dict], fno_info: Dict) -> Optional[Dict]:
        """Find best matching F&O symbol from search results"""
        strike = fno_info.get("strike")
        option_type = fno_info.get("option_type")
        
        for result in results:
            symbol = result.get("symbol", "")
            
            # Check if strike and option type match
            if strike and option_type:
                strike_str = str(int(strike)) if strike == int(strike) else str(strike)
                if strike_str in symbol and option_type in symbol:
                    return result
            elif fno_info.get("is_future") and "FUT" in symbol:
                return result
        
        return results[0] if results else None
    
    def resolve_and_get_order_params(
        self, 
        raw_symbol: str, 
        exchange: str = "NSE"
    ) -> Tuple[str, str, str]:
        """
        Convenience method to get order parameters
        
        Returns:
            Tuple of (resolved_symbol, token, exchange)
        """
        result = self.resolve_symbol(raw_symbol, exchange)
        
        return (
            result.get("resolved_symbol", raw_symbol),
            result.get("token", "0"),
            result.get("exchange", exchange)
        )


# Global instance (will be initialized with symbol_master)
symbol_resolver: Optional[SymbolResolver] = None


def get_symbol_resolver(symbol_master=None) -> SymbolResolver:
    """Get or create the symbol resolver instance"""
    global symbol_resolver
    if symbol_resolver is None or symbol_master is not None:
        symbol_resolver = SymbolResolver(symbol_master)
    return symbol_resolver
