import logging
import os
from datetime import datetime
from pathlib import Path

# Base directories
LOG_DIR = Path(__file__).parent.parent / "logs"
SCREENSHOT_DIR = LOG_DIR / "screenshots"

def setup_logger(name: str = "wccc-agent") -> logging.Logger:
    """Set up logger with file and console handlers."""
    # Ensure directories exist
    LOG_DIR.mkdir(exist_ok=True)
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler - new file per run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOG_DIR / f"run_{timestamp}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"Log file: {log_file}")

    return logger

def get_screenshot_path(step_name: str = "step") -> Path:
    """Generate a screenshot path with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{step_name}_{timestamp}.png"
    return SCREENSHOT_DIR / filename

def log_screenshot(logger: logging.Logger, screenshot_path: Path, description: str = "Screenshot"):
    """Log a screenshot with a clickable file:// link."""
    file_url = f"file://{screenshot_path.absolute()}"
    logger.info(f"{description}: {file_url}")
