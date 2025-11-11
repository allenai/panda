    
import logging
import sys

# e.g., "run.log"
LOGGER_FILE = None

def setup_logger():
    logger = logging.getLogger("panda_logger")
#   logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logger.format="%(message)s",       # only show the message text    
    logger.handlers.clear()

    if LOGGER_FILE:
        handler = logging.FileHandler(LOGGER_FILE, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stderr)

    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

logger = setup_logger()

# silence any PARENT loggers (avoid duplicate lines)
logging.getLogger("panda_logger").propagate = False

# logger.info("Loading files...")

# utility to switch off logging for a function call:
# example: with_quiet_logging(do_research_task, task="What is 1 + 1?")
def with_quiet_logging(fn, *args, **kwargs):
    root = logging.getLogger()
    old_level = root.level
    try:
        root.setLevel(logging.ERROR)
        return fn(*args, **kwargs)
    finally:
        root.setLevel(old_level)
