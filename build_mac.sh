#!/bin/bash
# Auf einem Mac ausfuehren (Python 3.10+ von python.org installiert, nicht Homebrew)
set -e
python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller --noconfirm --windowed --name WG-Abrechnung wg_abrechnung.py
rm -f WG-Abrechnung-mac.zip
ditto -c -k --keepParent dist/WG-Abrechnung.app WG-Abrechnung-mac.zip
echo
echo "Fertig: WG-Abrechnung-mac.zip (enthaelt WG-Abrechnung.app)"
