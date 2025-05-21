"""
Centralized logging configuration for the Bedrock application
"""
import logging
import os
import sys
from datetime import datetime
import traceback

# Define log levels for different components
LOG_LEVELS = {
    "root": logging.INFO,       # Default level for root logger
    "app": logging.INFO,        # Main application
    "services": logging.INFO,   # Services
    "ui": logging.WARNING,      # UI components (reduce verbosity)
    "sensors": logging.INFO,    # Sensor data
    "weather": logging.INFO,    # Weather service
    "alarm": logging.INFO,      # Alarm functionality
}

# Log file paths
LOG_DIR = "logs"
MAIN_LOG = os.path.join(LOG_DIR, "bedrock.log")
ERROR_LOG = os.path.join(LOG_DIR, "errors.log")

def configure_logging():
    """Configure logging for the entire application"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVELS["root"])
        
        # Create formatters
        console_format = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        
        # Console handler - shows info and above
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(LOG_LEVELS["root"])
        console.setFormatter(console_format)
        root_logger.addHandler(console)
        
        # File handler - main log
        file_handler = logging.FileHandler(MAIN_LOG, encoding='utf-8')
        file_handler.setLevel(LOG_LEVELS["root"])
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
        
        # Error log - errors only
        error_handler = logging.FileHandler(ERROR_LOG, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        root_logger.addHandler(error_handler)
        
        # Configure specific loggers
        _configure_component_loggers()
        
        # Log startup
        root_logger.info(f"Logging configured at {datetime.now().isoformat()}")
        root_logger.info(f"Python version: {sys.version}")
        root_logger.info(f"Running on platform: {sys.platform}")
        
        return True
    except Exception as e:
        # If logging setup fails, print to stderr
        print(f"ERROR: Failed to configure logging: {e}", file=sys.stderr)
        traceback.print_exc()
        return False

def _configure_component_loggers():
    """Configure individual component loggers"""
    # App logger
    app_logger = logging.getLogger("BedrockApp")
    app_logger.setLevel(LOG_LEVELS["app"])
    
    # Services loggers
    services = ["AlarmService", "WeatherService", "ScheduleService", 
               "PigsService", "NotificationService", "SensorService"]
    
    for service in services:
        logger = logging.getLogger(service)
        logger.setLevel(LOG_LEVELS["services"])
    
    # UI loggers
    ui_components = ["HomeScreen", "AlarmScreen", "WeatherScreen", 
                    "ScheduleScreen", "PigsScreen", "SettingsScreen"]
    
    for component in ui_components:
        logger = logging.getLogger(component)
        logger.setLevel(LOG_LEVELS["ui"])
        
    # Special configurations
    logging.getLogger("SensorService").setLevel(LOG_LEVELS["sensors"])
    logging.getLogger("WeatherService").setLevel(LOG_LEVELS["weather"])
    logging.getLogger("AlarmClock").setLevel(LOG_LEVELS["alarm"])
    logging.getLogger("AlarmPopup").setLevel(LOG_LEVELS["alarm"])

def log_exception(logger, message, exception):
    """Helper to consistently log exceptions"""
    logger.error(f"{message}: {exception}", exc_info=True)

# Create a test logger when this module is run directly
if __name__ == "__main__":
    configure_logging()
    logger = logging.getLogger("LoggingTest")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    try:
        1/0
    except Exception as e:
        log_exception(logger, "Testing exception logging", e)
        
    print(f"Log files created in {LOG_DIR} directory")