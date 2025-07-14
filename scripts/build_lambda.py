#!/usr/bin/env python3
"""
Lambda Deployment Package Builder

This script creates a deployment package for AWS Lambda functions.
It packages the Lambda function code and its dependencies into a ZIP file.
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
LAMBDA_DIR = PROJECT_ROOT / "lambda_functions" / "data_quality_checker"
BUILD_DIR = PROJECT_ROOT / "build" / "lambda"
PACKAGE_NAME = "data_quality_checker.zip"

print(f"Script directory: {SCRIPT_DIR}")
print(f"Project root: {PROJECT_ROOT}")
print(f"Lambda directory: {LAMBDA_DIR}")
print(f"Build directory: {BUILD_DIR}")


def run_command(command, cwd=None):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def create_zip_package():
    """Create a ZIP package for the Lambda function."""
    # Create build directory
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    output_zip = BUILD_DIR / PACKAGE_NAME
    
    # Create a temporary directory
    temp_dir = PROJECT_ROOT / "temp_lambda_build"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    try:
        print(f"\n=== Copying Lambda function from {LAMBDA_DIR} ===")
        # Check if source directory exists
        if not LAMBDA_DIR.exists():
            print(f"Error: Lambda directory not found at {LAMBDA_DIR}")
            sys.exit(1)
            
        # List all Python files in the Lambda directory
        py_files = list(LAMBDA_DIR.glob("*.py"))
        if not py_files:
            print(f"Warning: No Python files found in {LAMBDA_DIR}")
        else:
            print(f"Found {len(py_files)} Python files:")
            for py_file in py_files:
                print(f"  - {py_file.name}")
                
        # Copy Python files
        for py_file in py_files:
            dest_path = temp_dir / py_file.name
            print(f"Copying {py_file} to {dest_path}")
            shutil.copy2(py_file, temp_dir)
        
        # Install dependencies
        requirements_file = LAMBDA_DIR / "requirements.txt"
        if requirements_file.exists():
            print(f"\n=== Installing dependencies from {requirements_file} ===")
            print(f"Installing to: {temp_dir}")
            cmd = [
                sys.executable,  # Use the same Python interpreter
                "-m", "pip", 
                "install", 
                "-r", str(requirements_file), 
                "-t", str(temp_dir),
                "--no-cache-dir"
            ]
            print(f"Running command: {' '.join(cmd)}")
            run_command(" ".join(cmd), cwd=PROJECT_ROOT)
        else:
            print(f"Warning: No requirements.txt found at {requirements_file}")
        
        # List all files to be included in the ZIP
        print(f"\n=== Creating ZIP package at {output_zip} ===")
        print(f"Contents to be zipped from: {temp_dir}")
        
        # First, verify files exist in temp directory
        temp_files = list(temp_dir.glob("*"))
        if not temp_files:
            print("Error: No files found in temporary directory. Nothing to zip.")
            sys.exit(1)
            
        print("Files to be included in the ZIP:")
        for f in temp_files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
        
        # Create ZIP file
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = os.path.relpath(file_path, temp_dir)
                    print(f"  Adding to ZIP: {file_path} as {arcname}")
                    zipf.write(file_path, arcname)
        
        # Verify the ZIP was created and has content
        if not output_zip.exists():
            print(f"Error: Failed to create ZIP file at {output_zip}")
            sys.exit(1)
            
        zip_size = os.path.getsize(output_zip)
        print(f"\n✅ Successfully created Lambda package: {output_zip}")
        print(f"Package size: {zip_size / (1024 * 1024):.2f} MB")
        
        # List contents of the ZIP file
        print("\nZIP file contents:")
        with zipfile.ZipFile(output_zip, 'r') as zipf:
            for file_info in zipf.infolist():
                print(f"  - {file_info.filename} ({file_info.file_size} bytes)")
        
    finally:
        # Clean up
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("=== Lambda Deployment Package Builder ===\n")
    create_zip_package()
