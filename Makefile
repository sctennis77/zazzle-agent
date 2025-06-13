VENV_NAME=zam
PYTHON=python3
PIP=pip3

.PHONY: help test venv install run run-full run-test-voting clean docker-build docker-run scrape run-generate-image test-pattern run-api stop-api

help:
	@echo "Available targets:"
	@echo "  make venv         - Create a Python virtual environment"
	@echo "  make install      - Install dependencies into venv"
	@echo "  make test         - Run the test suite with coverage"
	@echo "  make run-full     - Run the complete product generation pipeline"
	@echo "  make clean        - Remove venv and outputs"
	@echo "  make docker-build - Build Docker image (tests must pass first)"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make scrape       - Run only the scraping part of the program"
	@echo "  make run-generate-image IMAGE_PROMPT=\"<prompt>\" MODEL=<dall-e-2|dall-e-3> - Generate an image with DALL-E and upload to Imgur"
	@echo "  make run-api      - Run the API server"
	@echo "  make stop-api     - Stop the API server"

venv:
	$(PYTHON) -m venv $(VENV_NAME)

install: venv
	. $(VENV_NAME)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt

test:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m pytest tests/ --cov=app

test-pattern:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m pytest $(TEST_PATH) --cov=app

run-full:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main --mode full --model "$(MODEL)"

run-generate-image:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main --mode image --prompt "$(IMAGE_PROMPT)" --model "$(MODEL)"

clean:
	rm -rf $(VENV_NAME) outputs/ .coverage

# Docker targets

docker-build: test
	docker build -t zazzle-affiliate-agent .

docker-run:
	docker run -v $(PWD)/outputs:/app/outputs zazzle-affiliate-agent 

scrape:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.product_scraper 

run-api:
	@echo "Stopping any existing API instances..."
	@if lsof -ti :8000 > /dev/null; then \
	  echo "Killing process(es) using port 8000:"; \
	  lsof -i :8000; \
	  lsof -ti :8000 | xargs kill -9; \
	fi
	@echo "Waiting for port 8000 to be released..."
	@while lsof -i :8000 > /dev/null; do sleep 1; done
	@echo "Starting API server..."
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.api

stop-api:
	@echo "Stopping API server..."
	@if lsof -ti :8000 > /dev/null; then \
	  echo "Killing process(es) using port 8000:"; \
	  lsof -i :8000; \
	  lsof -ti :8000 | xargs kill -9; \
	fi
	@echo "Waiting for port 8000 to be released..."
	@while lsof -i :8000 > /dev/null; do sleep 1; done 