#!/usr/bin/env python3
"""
Installation script for AWS S3 Backup Monitor
This script will install all required packages and set up the environment
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✓ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_packages():
    """Install required packages"""
    commands = [
        ("pip install --upgrade pip", "Upgrading pip"),
        ("pip install -r requirements.txt", "Installing required packages"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "backups",
        "temp"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✓ Created directory: {directory}")
        except Exception as e:
            print(f"✗ Failed to create directory {directory}: {e}")
            return False
    return True

def main():
    """Main installation process"""
    print("=" * 60)
    print("AWS S3 Backup Monitor - Installation Script")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install packages
    if not install_packages():
        print("\n✗ Package installation failed")
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        print("\n✗ Directory creation failed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ Installation completed successfully!")
    print("=" * 60)
    print("\nTo run the application:")
    print("1. Configure your AWS credentials in config.json")
    print("2. Run: streamlit run aws_ui.py")
    print("\nFor help, check the README.md file")

if __name__ == "__main__":
    main()