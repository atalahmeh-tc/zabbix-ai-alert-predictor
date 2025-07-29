import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_logger(module_name):
    """
    Returns the configured logger instance.
    """
    return logging.getLogger(module_name)
