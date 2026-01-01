#!/usr/bin/env bash
set -e

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation complete."
echo "Run: source venv/bin/activate"
