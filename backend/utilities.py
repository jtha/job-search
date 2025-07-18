import logging 
import logging.config 
import os 

def setup_logging(): 
    """ 
    Loads the logging configuration from a file. 
    """ 
    config_file = os.path.join(os.path.dirname(__file__), 'logging.conf') 
    logging.config.fileConfig(config_file, disable_existing_loggers=False) 

def get_logger(name): 
    """ 
    Returns a logger with the specified name. 
    """ 
    return logging.getLogger(name)