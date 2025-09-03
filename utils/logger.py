import logging

log = logging.getLogger('app')

handler = logging.StreamHandler()
formatter = logging.Formatter(
	"%(asctime)s - %(levelname)s - %(name)s - %(message)s",
	datefmt = "%Y-%m-%d %H:%M:%S"
)

log.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
log.addHandler(handler)