def log(message, level="INFO"):
    print(f"[{level}] {message}") Additionally, incorporate comments in the docstring to explain the logic.# Importing necessary library
import logging# Setting up loggerlogging.basicConfig(filename='/home/shangkat5/Desktop/Major_Project/PySage/Server/logs/server.log', level=logging.INFO)logging.getLogger().addHandler(logging.StreamHandler())
# Function to log messages with different levelsdef log(message, level="INFO"):    Logs a message with a specified level. Parameters:
    message (str): The message to log.
    level (str): The level of the log, default is 'INFO'.Returns:
    None    if level == "INFO":logging.info(message)elif level == "WARNING":        logging.warning(message)    elif level == logging.error(message)
    elif level == "CRITICAL":logging.critical(message)
    else:logging.error(f"Unknown log level: {level}")
# Example usage