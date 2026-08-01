import logging

def setup_logger(name=None, log_file=None, level=logging.INFO, console=True):
    """
    Configures and returns a logger with the specified settings.

    :param name: (Optional) Name for the logger. If None, root logger is used.
    :param log_file: (Optional) File path to log file. If None, logs are not written to a file.
    :param level: Logging level (e.g., logging.INFO, logging.DEBUG).
    :param console: Boolean flag to determine if logs should also be output to console.
    :return: Configured logger object.
    """
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Create and configure handlers
    if log_file:
        # File handler for logging to a file
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console:
        # Console handler for logging to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.propagate = False  # Prevent logs from propagating to the root logger

    return logger

# Example usage:
# logger = setup_logger('CI2D3Helper', 'ci2d3_helper.log', level=logging.INFO, console=True)
