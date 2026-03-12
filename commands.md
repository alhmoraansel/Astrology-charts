## Install Requirements

python -m pip install geopy timezonefinder pytz pyswisseph PyQt6


## Build

pyinstaller --name "Astro Basics" --windowed --icon "icon.ico" --add-data "icon.ico;." main.py --noconfirm