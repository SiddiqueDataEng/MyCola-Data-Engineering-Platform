#!/usr/bin/env python3
"""
MyCola Data Generator — Launcher Script
Launches the Tkinter GUI application.
"""
import sys
import os

# Add data_generator to path
sys.path.insert(0, os.path.dirname(__file__))

from data_generator.ui.app import main

if __name__ == "__main__":
    main()
