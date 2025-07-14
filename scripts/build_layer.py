#!/usr/bin/env python3
"""
Lambda Layer Builder

This script creates a Lambda Layer containing all the required dependencies.
The layer will be packaged in the 'python' directory structure required by AWS Lambda.
"""

import os
import sys
import zipfile
import shutil
import subprocess
from pathlib import Path

# Get the absolute path to the script's directory
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.absolute()

# Configuration
LAYER_NAME = "data-quality-deps"
BUILD_DIR = PROJECT_ROOT / "build" / "layer"
TEMP_DIR = BUILD_DIR / "temp"
PYTHON_DIR = TEMP_DIR / "python"
REQUIREMENTS = PROJECT_ROOT / "lambda_functions" / "data_quality_checker" / "requirements.txt"

# Files and directories to exclude from the layer
EXCLUDE_PATTERNS = [
    "__pycache__", "*.py[cod]", "*$py.class",
    "*.so", "*.so.*",  # Exclude compiled extensions as we'll build them
    "*.dist-info", "*.egg-info",
    "tests", "test", "doc", "docs", "examples",
    ".git", ".github", ".gitignore",
    "*.md", "*.txt", "LICENSE*", "NOTICE*", "VERSION*"
]

def run_command(command, cwd=None):
    """Run a shell command and return its output."""
    try:
        print(f"Running: {command}")
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout.strip():
            print(f"Output: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        sys.exit(1)

def install_dependencies(requirements_file, target_dir):
    """Install Python dependencies with optimization for Lambda."""
    print(f"\nInstalling dependencies from {requirements_file}")
    
    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the full path to pip3
    pip_path = "/usr/bin/pip3"
    
    # First install botocore and boto3 with all dependencies
    core_cmd = (
        f"{pip_path} install "
        f"--target {target_dir} "
        "--no-cache-dir "
        "--platform manylinux2014_x86_64 "
        "--implementation cp "
        "--python-version 3.9 "
        "--only-binary=:all: "
        "boto3>=1.28.0 "
        "botocore>=1.31.0"
    )
    
    # Then install other dependencies
    other_deps_cmd = (
        f"{pip_path} install -r {requirements_file} "
        f"--target {target_dir} "
        "--no-cache-dir "
        "--platform manylinux2014_x86_64 "
        "--implementation cp "
        "--python-version 3.9 "
        "--only-binary=:all: "
        "--upgrade "
        "--no-deps"
    )
    
    # Run both installation commands
    run_command(core_cmd)
    run_command(other_deps_cmd)
    
    # Clean up unnecessary files
    for pattern in ["__pycache__", "*.dist-info", "*.egg-info", "tests", "test"]:
        for item in target_dir.rglob(pattern):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink()
                except (FileNotFoundError, PermissionError):
                    pass

def create_layer_zip():
    """Create the Lambda Layer ZIP package."""
    try:
        # Clean and prepare build directory
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        PYTHON_DIR.mkdir(parents=True, exist_ok=True)
        
        # Install dependencies
        install_dependencies(REQUIREMENTS, PYTHON_DIR)
        
        # Create the ZIP file
        zip_path = BUILD_DIR / f"{LAYER_NAME}.zip"
        print(f"\nCreating Lambda Layer ZIP: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, _, files in os.walk(TEMP_DIR):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(TEMP_DIR)
                    zipf.write(file_path, arcname)
        
        # Verify the package size
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Successfully created Lambda Layer: {zip_path}")
        print(f"📦 Layer size: {size_mb:.2f} MB")
        
        # List the largest files in the layer
        print("\nLargest files in the layer:")
        file_sizes = []
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for file_info in zipf.infolist():
                if file_info.file_size > 100000:  # Files larger than 100KB
                    file_sizes.append((file_info.filename, file_info.file_size))
        
        # Sort by size (largest first) and print top 10
        for filename, size in sorted(file_sizes, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {filename}: {size/1024/1024:.2f} MB")
        
        return zip_path
        
    except Exception as e:
        print(f"\n❌ Error creating Lambda Layer: {e}")
        sys.exit(1)
    finally:
        # Clean up temporary directory
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    print("=== Lambda Layer Builder ===\n")
    create_layer_zip()
