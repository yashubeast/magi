import logging
import colorlog
import os

LOG_LEVEL_ENV = os.environ.get("LOG_LEVEL", "DEBUG").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_ENV, logging.DEBUG)

log = logging.getLogger('app')
log.setLevel(LOG_LEVEL)

handler = logging.StreamHandler()
formatter = colorlog.ColoredFormatter(
	"%(log_color)s%(asctime)s - %(levelname)s - %(name)s - %(message)s",
	datefmt = "%d-%m-%Y %H:%M:%S",
	log_colors = {
		'DEBUG': 'purple',
		'INFO': 'green',
		'WARNING': 'yellow',
		'ERROR': 'red',
		'CRITICAL': 'bold_red',
	}
)

handler.setFormatter(formatter)
log.addHandler(handler)

# log.debug("debug message")
# log.info("info message")
# log.warning("warning message")
# log.error("error message")
# log.critical("critical message")