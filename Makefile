VENV_NAME=zam
PYTHON=python3
PIP=pip3

.PHONY: help test venv install run run-full run-test-voting clean docker-build docker-run scrape run-generate-image

help:
	@echo "Available targets:"
	@echo "  make venv         - Create a Python virtual environment"
	@echo "  make install      - Install dependencies into venv"
	@echo "  make test         - Run the test suite with coverage"
	@echo "  make run-full     - Run the complete product generation pipeline"
	@echo "  make run-test-voting - Test Reddit agent voting behavior"
	@echo "  make clean        - Remove venv and outputs"
	@echo "  make docker-build - Build Docker image (tests must pass first)"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make scrape       - Run only the scraping part of the program"
	@echo "  make run-generate-image <image prompt> - Generate an image with DALL-E and upload to Imgur"

venv:
	$(PYTHON) -m venv $(VENV_NAME)

install: venv
	. $(VENV_NAME)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt

test:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m pytest tests/ --cov=app

run-full:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main full

run-test-voting:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main test-voting

# Default run target (alias for run-full)
run: run-full

run-generate-image:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main run-generate-image --image-prompt "$(IMAGE_PROMPT)"

clean:
	rm -rf $(VENV_NAME) outputs/ .coverage

# Docker targets

docker-build: test
	docker build -t zazzle-affiliate-agent .

docker-run:
	docker run -v $(PWD)/outputs:/app/outputs zazzle-affiliate-agent 

scrape:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.product_scraper 