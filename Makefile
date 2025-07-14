.PHONY: help init init-python init-terraform test lint format clean tf-init tf-plan tf-apply tf-destroy tf-output package-lambda deploy-lambda invoke-lambda check pre-commit-install pre-commit-run

# Colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

# Variables
PYTHON = python3
PIP = pip3
TERRAFORM = terraform
PYTEST = python -m pytest
PROJECT_NAME = $(shell grep -E '^project_name\s*=' terraform.tfvars | awk -F'"' '{print $$2}' | head -1)
ENVIRONMENT = $(shell grep -E '^environment\s*=' terraform.tfvars | awk -F'"' '{print $$2}' | head -1)
AWS_REGION = $(shell grep -E '^aws_region\s*=' terraform.tfvars | awk -F'"' '{print $$2}' | head -1)
LAMBDA_NAME = $(PROJECT_NAME)-$(ENVIRONMENT)-checker
S3_BUCKET = $(PROJECT_NAME)-$(ENVIRONMENT)-$(shell aws sts get-caller-identity --query Account --output text)-$(AWS_REGION)

# Help
help:
	@echo "${YELLOW}Available targets:${RESET}"
	@echo "  ${GREEN}init${RESET} - Initialize development environment"
	@echo "  ${GREEN}test${RESET} - Run tests"
	@echo "  ${GREEN}lint${RESET} - Run linters"
	@echo "  ${GREEN}format${RESET} - Format code"
	@echo "  ${GREEN}clean${RESET} - Clean up temporary files"
	@echo "  ${GREEN}tf-init${RESET} - Initialize Terraform"
	@echo "  ${GREEN}tf-plan${RESET} - Show Terraform execution plan"
	@echo "  ${GREEN}tf-apply${RESET} - Apply Terraform configuration"
	@echo "  ${GREEN}tf-destroy${RESET} - Destroy Terraform-managed infrastructure"
	@echo "  ${GREEN}tf-output${RESET} - Show Terraform outputs"
	@echo "  ${GREEN}package-lambda${RESET} - Package Lambda function code"
	@echo "  ${GREEN}deploy-lambda${RESET} - Deploy Lambda function"
	@echo "  ${GREEN}invoke-lambda${RESET} - Invoke Lambda function"
	@echo "  ${GREEN}check${RESET} - Run all checks and tests"
	@echo "  ${GREEN}pre-commit-install${RESET} - Install pre-commit hooks"
	@echo "  ${GREEN}pre-commit-run${RESET} - Run pre-commit on all files"

# Initialize development environment
init: init-python init-terraform pre-commit-install

init-python:
	@echo "${YELLOW}Installing Python dependencies...${RESET}"
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -r lambda_functions/data_quality_checker/requirements.txt

init-terraform:
	@echo "${YELLOW}Initializing Terraform...${RESET}"
	$(TERRAFORM) init

# Run tests
test:
	@echo "${YELLOW}Running tests...${RESET}"
	cd lambda_functions/data_quality_checker && \
	$(PYTEST) tests/ -v --cov=. --cov-report=term-missing

# Lint code
lint:
	@echo "${YELLOW}Running linters...${RESET}"
	black --check .
	isort --check-only .
	flake8 .
	mypy .

# Format code
format:
	@echo "${YELLOW}Formatting code...${RESET}"
	black .
	isort .

# Clean up
clean:
	@echo "${YELLOW}Cleaning up...${RESET}"
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type f -name "*.py[co]" -delete
	find . -type f -name "*.so" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "dist" -exec rm -r {} +
	find . -type d -name "build" -exec rm -r {} +
	rm -f *.zip
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*
	rm -f *.tfvars

# Terraform commands
tf-init:
	@echo "${YELLOW}Initializing Terraform...${RESET}"
	$(TERRAFORM) init

tf-plan:
	@echo "${YELLOW}Creating Terraform execution plan...${RESET}"
	$(TERRAFORM) plan

tf-apply:
	@echo "${YELLOW}Applying Terraform configuration...${RESET}"
	$(TERRAFORM) apply -auto-approve

tf-destroy:
	@echo "${YELLOW}${YELLOW}WARNING: This will destroy all managed infrastructure!${RESET}"
	@read -p "Are you sure? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(TERRAFORM) destroy -auto-approve; \
	fi

tf-output:
	@echo "${YELLOW}Terraform outputs:${RESET}"
	$(TERRAFORM) output

# Package Lambda function
package-lambda:
	@echo "${YELLOW}Packaging Lambda function...${RESET}"
	cd lambda_functions/data_quality_checker && \
	zip -r ../../$(LAMBDA_NAME).zip . && \
	cd ../..

# Deploy Lambda function
deploy-lambda: package-lambda
	@echo "${YELLOW}Deploying Lambda function...${RESET}"
	aws lambda update-function-code \
		--function-name $(LAMBDA_NAME) \
		--zip-file fileb://$(LAMBDA_NAME).zip \
		--region $(AWS_REGION)

# Invoke Lambda function
invoke-lambda:
	@echo "${YELLOW}Invoking Lambda function...${RESET}"
	aws lambda invoke \
		--function-name $(LAMBDA_NAME) \
		--payload '{"database": "$(or $(DATABASE),$(shell grep -E '^default_database\s*=' terraform.tfvars | awk -F'"' '{print $$2}'))", "table": "$(or $(TABLE),$(shell grep -E '^default_table\s*=' terraform.tfvars | awk -F'"' '{print $$2}'))"}' \
		--region $(AWS_REGION) \
		--log-type Tail \
		--query 'LogResult' \
		--output text \
		invoke-output.json | base64 --decode
	@echo "${YELLOW}Lambda output:${RESET}"
	@cat invoke-output.json
	@echo ""

# View Lambda logs
logs-lambda:
	@echo "${YELLOW}Tailing Lambda logs...${RESET}"
	aws logs tail /aws/lambda/$(LAMBDA_NAME) --follow --region $(AWS_REGION)

# Run all checks and tests
check: lint test

# Pre-commit hooks
pre-commit-install:
	@echo "${YELLOW}Installing pre-commit hooks...${RESET}"
	pre-commit install

pre-commit-run:
	@echo "${YELLOW}Running pre-commit on all files...${RESET}"
	pre-commit run --all-files

# Default target
.DEFAULT_GOAL := help
