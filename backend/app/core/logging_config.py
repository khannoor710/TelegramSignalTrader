"""
Logging configuration for the application
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure application logging"""
    
    # Create logger
    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # File handler - rotating daily
    log_file = LOGS_DIR / f"trading_bot_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Create default logger instance
logger = setup_logging()


def get_logger(name: str = None) -> logging.Logger:
    """Get a child logger"""
    if name:
        return logging.getLogger(f"trading_bot.{name}")
    return logger
