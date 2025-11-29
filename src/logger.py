import logging
import os
from datetime import datetime
from pathlib import Path

# Base directories
LOG_DIR = Path(__file__).parent.parent / "logs"
SCREENSHOT_DIR = LOG_DIR / "screenshots"

def setup_logger(name: str = "wccc-agent") -> logging.Logger:
    """Set up logger with file and console handlers."""
    global _current_log_session, _current_screenshot_dir

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
    _current_log_session = f"run_{timestamp}"
    log_file = LOG_DIR / f"{_current_log_session}.log"

    # Create screenshot directory for this run (directly in logs directory)
    _current_screenshot_dir = LOG_DIR / _current_log_session
    _current_screenshot_dir.mkdir(exist_ok=True)

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
    """Generate a screenshot path in the current run's screenshot directory."""
    filename = f"{step_name}.png"
    return _current_screenshot_dir / filename

def log_screenshot(logger: logging.Logger, screenshot_path: Path, description: str = "Screenshot"):
    """Log a screenshot with a clickable file:// link."""
    file_url = f"file://{screenshot_path.absolute()}"
    logger.info(f"{description}: {file_url}")

# Store current log session and screenshot directory for screenshot naming
_current_log_session = ""
_current_screenshot_dir = SCREENSHOT_DIR

def get_current_log_session() -> str:
    """Get the current log session identifier for screenshot naming."""
    return _current_log_session

def get_current_screenshot_dir() -> Path:
    """Get the current screenshot directory path."""
    return _current_screenshot_dir
