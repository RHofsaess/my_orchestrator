import logging
import os


def setup_logger(log_file="run.log", log_level=logging.INFO):
    logger = logging.getLogger("HEPscoreLogger")

    # Prevent duplicate log handlers if the logger is reused
    if not logger.handlers:
        logger.setLevel(log_level)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Log format
        log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(log_format)
        console_handler.setFormatter(log_format)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Create preconfigured logger
log_file_path = os.path.join(os.getcwd(), "run.log")
logger = setup_logger(log_file=log_file_path, log_level=logging.DEBUG)

# Example
if __name__ == "__main__":
    # Log messages
    logger.debug("This is a debug message.")
    logger.info("Informational message here.")
    logger.warning("This is a warning!")
    logger.error("An error occurred!")
    logger.critical("Critical error occurred!")
