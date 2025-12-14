import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

class CustomLogger:
    def __init__(self, name=None, log_level=logging.INFO, log_dir="logs"):
        """
        Initialize the custom logger
        
        Args:
            name (str): Logger name (usually __name__)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir (str): Directory to store log files
        """
        self.name = name or "app"
        self.log_level = log_level
        self.log_dir = Path(log_dir)
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup console and file handlers"""
        # Formatter with timestamp
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        
        # File Handler - Daily rotating logs
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30  # Keep 30 days of logs
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        
        # Error File Handler - Only errors and above
        error_log_file = self.log_dir / f"{self.name}_error.log"
        error_handler = logging.handlers.TimedRotatingFileHandler(
            error_log_file,
            when='midnight',
            interval=1,
            backupCount=30
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def get_logger(self):
        """Return the configured logger instance"""
        return self.logger

# Global logger instance
_app_logger = None

def setup_logger(name=None, log_level=logging.INFO, log_dir="logs"):
    """Setup and return a global logger instance"""
    global _app_logger
    if _app_logger is None:
        _app_logger = CustomLogger(name, log_level, log_dir).get_logger()
    return _app_logger

def get_logger(name=None):
    """Get the global logger instance or create a new one"""
    if _app_logger is not None:
        return _app_logger
    return setup_logger(name)

# Convenience functions
def debug(msg, *args, **kwargs):
    get_logger().debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    get_logger().error(msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    get_logger().critical(msg, *args, **kwargs)

def exception(msg, *args, **kwargs):
    get_logger().exception(msg, *args, **kwargs)