#!/bin/bash

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting background remover server..."
python3 main.py

echo "Server process initiated. To stop it, you might need to use Ctrl+C in this terminal, or find and kill the process if it's detached."
read -p "Press Enter to exit this script..."
