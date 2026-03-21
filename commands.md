## Install Requirements

python -m pip install geopy timezonefinder pytz pyswisseph PyQt6 astral


## Build

pyinstaller --noconfirm --name "Astro Basics" --windowed --icon "icon.ico" --add-data "icon.ico;." --add-data "ephe;ephe" --add-data "dynamic_settings_modules;dynamic_settings_modules" --collect-data timezonefinder main.py

*(Note for Mac/Linux users: change the separator in `--add-data` from a semicolon `;` to a colon `:`)*

### 3. Crucial Rule for Swisseph (`ephe` folder)

Because `swisseph` relies on the massive ephemeris files (which you mapped to `swe.set_ephe_path('ephe')`), you must ensure that your `ephe` folder is placed exactly in the same directory as the final generated `Astro Basics.exe`. 

**Troubleshooting Tip:** If it *still* fails to open after this, build it once **without** the `--windowed` flag. This will force a black command prompt window to appear alongside your app and it will instantly print out the exact Python error preventing the launch!