VENV_NAME=zam
PYTHON=python3
PIP=pip3

.PHONY: help test venv install run clean docker-build docker-run scrape

help:
	@echo "Available targets:"
	@echo "  make venv         - Create a Python virtual environment"
	@echo "  make install      - Install dependencies into venv"
	@echo "  make test         - Run the test suite with coverage"
	@echo "  make run          - Run the app locally in venv"
	@echo "  make clean        - Remove venv and outputs"
	@echo "  make docker-build - Build Docker image (tests must pass first)"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make scrape       - Run only the scraping part of the program"

venv:
	$(PYTHON) -m venv $(VENV_NAME)

install: venv
	. $(VENV_NAME)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt

test:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m pytest tests/ --cov=app

run:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main

clean:
	rm -rf $(VENV_NAME) outputs/ .coverage

# Docker targets

docker-build: test
	docker build -t zazzle-affiliate-agent .

docker-run:
	docker run -v $(PWD)/outputs:/app/outputs zazzle-affiliate-agent 

scrape:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.product_scraper 