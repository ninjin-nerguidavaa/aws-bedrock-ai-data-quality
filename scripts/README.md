# Lambda Deployment Scripts

This directory contains scripts to build and package Lambda functions for deployment.

## Available Scripts

### 1. `build_lambda.py` (Recommended)
A Python-based build script that creates a deployment package for AWS Lambda.

**Features:**
- Cross-platform compatibility (Windows, macOS, Linux)
- Clean dependency installation
- Detailed logging
- Automatic cleanup of temporary files

**Usage:**
```bash
# Make the script executable (Unix-like systems)
chmod +x build_lambda.py

# Run the script
./build_lambda.py
```

### 2. `build_lambda.sh`
A shell script alternative for Unix-like systems.

**Usage:**
```bash
# Make the script executable
chmod +x build_lambda.sh

# Run the script
./build_lambda.sh
```

## Output

The built Lambda package will be saved to:
```
/build/lambda/data_quality_checker.zip
```

## Prerequisites

- Python 3.6+
- pip
- AWS CLI (for deployment)
- Required Python packages (will be installed automatically)

## Adding to Version Control

The `build/` directory is typically excluded from version control. You can add the built packages to your `.gitignore` file.
