#!/usr/bin/env python3
"""
Lambda Deployment Package Builder

This script creates an optimized deployment package for AWS Lambda functions.
It excludes unnecessary files and is designed to stay under the 50MB limit.
"""

import os
import sys
import zipfile
import shutil
import subprocess
import re
from pathlib import Path

# Get the absolute path to the script's directory
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.absolute()

# Configuration
LAMBDA_DIR = PROJECT_ROOT / "lambda_functions" / "data_quality_checker"
BUILD_DIR = PROJECT_ROOT / "build" / "lambda"
PACKAGE_NAME = "data_quality_checker.zip"
TEMP_DIR = BUILD_DIR / "temp"

# Files and directories to exclude from the package
EXCLUDE_PATTERNS = [
    # Python cache and compiled files
    "__pycache__", "*.py[cod]", "*$py.class",
    # Distribution / packaging
    ".Python", "build/", "develop-eggs/", "dist/", "downloads/", "eggs/", 
    ".eggs/", "lib/", "lib64/", "parts/", "sdist/", "var/", "wheels/",
    "*.egg-info/", ".installed.cfg", "*.egg",
    # Unit test / coverage reports
    "htmlcov/", ".tox/", ".nox/", ".coverage", ".coverage.*", ".cache",
    "nosetests.xml", "coverage.xml", "*.cover", "*.py,cover", 
    ".hypothesis/", ".pytest_cache/",
    # Jupyter Notebook
    ".ipynb_checkpoints",
    # Environments
    ".venv", "env/", "venv/", "ENV/", ".env", ".python-version",
    # IDEs and editors
    ".idea/", ".vscode/", "*.swp", "*.swo", "*~",
    # Specific large packages (will use Lambda Layers)
    "numpy*", "pandas*", "pyarrow*", "boto3*", "botocore*"
]

print(f"=== Lambda Deployment Package Builder ===")
print(f"Project root: {PROJECT_ROOT}")
print(f"Lambda source: {LAMBDA_DIR}")
print(f"Build directory: {BUILD_DIR}")
print(f"Excluding patterns: {', '.join(EXCLUDE_PATTERNS)}\n")


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


def should_exclude(file_path, patterns):
    """Check if a file should be excluded based on patterns."""
    file_str = str(file_path)
    return any(re.search(pattern.replace('*', '.*').replace('/', '[/\\\\]') + '$', file_str) 
               for pattern in patterns)


def copy_files(src, dst, exclude_patterns=None):
    """Copy files from src to dst, excluding files that match patterns."""
    if exclude_patterns is None:
        exclude_patterns = []
    
    src_path = Path(src)
    dst_path = Path(dst)
    
    if src_path.is_file():
        if not should_exclude(src_path, exclude_patterns):
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"Copied: {src_path.relative_to(PROJECT_ROOT)}")
        return
    
    for item in src_path.iterdir():
        if should_exclude(item, exclude_patterns):
            print(f"Excluded: {item.relative_to(PROJECT_ROOT)}")
            continue
            
        if item.is_dir():
            copy_files(item, dst_path / item.name, exclude_patterns)
        else:
            dst_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst_path / item.name)
            print(f"Copied: {item.relative_to(PROJECT_ROOT)}")


def install_dependencies(requirements_file, target_dir):
    """Install Python dependencies with optimization for Lambda."""
    print("\nInstalling dependencies...")
    
    # Create a temporary virtual environment using the full path to python3
    venv_dir = TEMP_DIR / "venv"
    run_command(f"/usr/bin/python3 -m venv {venv_dir}")
    
    try:
        # Use the virtual environment's pip
        pip_path = venv_dir / "bin" / "pip"
        if sys.platform == "win32":
            pip_path = venv_dir / "Scripts" / "pip.exe"
        
        # Upgrade pip
        run_command(f"{pip_path} install --upgrade pip")
        
        # Install only the required packages
        run_command(
            f"{pip_path} install -r {requirements_file} "
            f"--target {target_dir} "
            "--no-cache-dir "
            "--only-binary=:none: "
            "--platform manylinux2014_x86_64 "
            "--implementation cp "
            "--python-version 3.9 "
            "--no-deps"
        )
        
        # Clean up Python cache files
        for pycache in target_dir.rglob("__pycache__"):
            shutil.rmtree(pycache, ignore_errors=True)
        
        # Remove test directories and other unnecessary files
        for pattern in ["*.dist-info", "*.egg-info", "tests", "test", "doc", "docs"]:
            for item in target_dir.glob(f"**/{pattern}"):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink()
                    except (FileNotFoundError, PermissionError):
                        pass
        
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        raise
    finally:
        # Clean up virtual environment
        shutil.rmtree(venv_dir, ignore_errors=True)


def create_zip_package():
    """Create an optimized ZIP package for Lambda deployment."""
    try:
        # Clean and prepare build directory
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create package directory structure
        package_dir = TEMP_DIR / "package"
        package_dir.mkdir()
        
        print("Copying Lambda function files...")
        copy_files(LAMBDA_DIR, package_dir, EXCLUDE_PATTERNS)
        
        # Install dependencies if requirements.txt exists
        requirements_file = LAMBDA_DIR / "requirements.txt"
        if requirements_file.exists():
            install_dependencies(requirements_file, package_dir)
        
        # Create the ZIP file
        zip_path = BUILD_DIR / PACKAGE_NAME
        print(f"\nCreating optimized ZIP file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, _, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        # Verify the package size
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Successfully created Lambda package: {zip_path}")
        print(f"📦 Package size: {size_mb:.2f} MB")
        
        if size_mb > 45:  # Leave some buffer under 50MB
            print("\n⚠️  WARNING: Package is approaching the 50MB limit!")
            print("   Consider using Lambda Layers for large dependencies.")
        
        # List the largest files in the package
        print("\nLargest files in the package:")
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
        print(f"\n❌ Error creating Lambda package: {e}")
        sys.exit(1)
    finally:
        # Clean up temporary directory
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    print("=== Lambda Deployment Package Builder ===\n")
    create_zip_package()
