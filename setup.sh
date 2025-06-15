#!/bin/bash

# ==============================================================================
#                 Setup Script for FlippingBook Data Pipeline
# ==============================================================================
#
# This script automates the entire setup process. Before running it for the
# first time, you must make it executable.
#
# Instructions:
# 1. Make the script executable (give it permissions to run):
#    chmod +x setup.sh
#
# 2. Execute the script from the project's root directory:
#    ./setup.sh
#
# ==============================================================================


echo "--- Starting Environment Setup for Data Pipeline ---"

# --- Step 1: Install System Dependencies (Tesseract-OCR) ---
# We need to check which OS we are on to use the correct package manager.

echo "[1/3] Installing Tesseract-OCR system package..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # For Debian/Ubuntu based systems
    echo "Detected Linux. Using apt-get..."
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # For macOS
    echo "Detected macOS. Using Homebrew..."
    if ! command -v brew &> /dev/null
    then
        echo "Homebrew not found. Please install it first from https://brew.sh"
        exit 1
    fi
    brew install tesseract
else
    echo "Unsupported OS for automatic Tesseract installation."
    echo "Please install Tesseract manually from the official website."
    exit 1
fi

echo "Tesseract installation complete."
echo ""


# --- Step 2: Install Python Dependencies ---
echo "[2/3] Installing Python packages from requirements.txt..."

# It's a good practice to use a virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install the packages
pip install -r requirements.txt

echo "Python packages installed."
echo ""


# --- Step 3: Install Playwright Browser Binaries ---
echo "[3/3] Installing Playwright browser dependencies..."

playwright install --with-deps

echo "Playwright browsers installed."
echo ""

echo "--- Setup Complete! ---"
echo "You can now run the pipeline using:"
echo "python run_extractor.py"

