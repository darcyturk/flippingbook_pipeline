#!/bin/bash

# This script sets up the environment for the FlippingBook Data Pipeline.
# To run it, make it executable first: chmod +x setup.sh
# Then execute it: ./setup.sh

echo "--- Starting Environment Setup for Data Pipeline ---"

# --- Step 1: Install Python Dependencies ---
echo "[1/2] Installing Python packages from requirements.txt..."

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

# --- Step 2: Install Playwright Browser Binaries ---
echo "[2/2] Installing Playwright browser dependencies..."
playwright install --with-deps
echo "Playwright browsers installed."
echo ""

echo "--- Setup Complete! ---"
echo "You can now run the pipeline using:"
echo "source venv/bin/activate"
echo "python run_extractor.py"
