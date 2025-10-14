PYTHON_CMD = uv run main.py

dev:
	clear
	@echo "---Running in Development Mode (logging at DEBUG, uvicorn RELOAD is true)---"
	@export LOG_LEVEL=DEBUG UVICORN_RELOAD=True; $(PYTHON_CMD)

test:
	clear
	@echo "---Running in Testing Mode (logging at INFO, uvicorn RELOAD is false)---"
	@export LOG_LEVEL=INFO UVICORN_RELOAD=False; $(PYTHON_CMD)

prod:
	@echo "---Running in Production Mode (logging at INFO, uvicorn RELOAD is false)---"
	@export LOG_LEVEL=INFO UVICORN_RELOAD=False; $(PYTHON_CMD)

sim:
	clear
	uv run simulate.py

all: dev