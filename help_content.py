# help_content.py

tab1_basics_html = """
<div style="line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Core Basics & Setup</h2>
    <p>Welcome to AstroBasics Diamond Chart Pro! This application is designed to calculate and visualize Vedic astrological charts in real-time. Here is how to set up your base information:</p>

    <h3 style="color: #2980b9;">Location Settings</h3>
    <ul>
        <li><b>Search Box:</b> Type a city name (e.g., "New Delhi") and click <b>Search</b>. The app will automatically fetch the exact Latitude, Longitude, and Timezone.</li>
        <li><b>Custom Coordinates (...):</b> Click the small yellow <b>"..."</b> button to manually input precise Latitude and Longitude if your city is not found.</li>
    </ul>

    <h3 style="color: #2980b9;">Date, Time & Panchang</h3>
    <ul>
        <li><b>Date & Time Spinners:</b> Adjust the Day (D), Month (M), Year (Y), and exact Time (T). The charts update instantly as you change these values.</li>
        <li><b>Panchang (...):</b> Click the yellow <b>"..."</b> button next to the date to view the traditional Panchang for the current time, including Nakshatra, Tithi, Sunrise, and Sunset.</li>
        <li><b>Current Dasha:</b> A quick reference below the time shows the currently active Vimshottari Dasha sequence.</li>
    </ul>

    <h3 style="color: #2980b9;">Divisional Charts (Vargas)</h3>
    <ul>
        <li>Select which charts you want to display simultaneously by checking the boxes (D1, D9, D10, etc.).</li>
        <li><b>Custom Vargas:</b> If enabled, you can click "Manage Custom Vargas" to define your own mathematical chart divisions.</li>
    </ul>

    <h3 style="color: #2980b9;">User Interface & Layout</h3>
    <ul>
        <li><b>Drag-and-Drop Sidebar:</b> You can click and drag the headers of the left-side control panels (Location, Animation, Settings, etc.) to reorder them to your liking.</li>
        <li><b>Layout Mode:</b> In the Settings group, you can change how charts are arranged on the screen (3 Columns, 2 Columns, or 1 Left/2 Right Stacked).</li>
    </ul>

    <h3 style="color: #2980b9;">Saving, Loading & Exporting</h3>
    <ul>
        <li><b>Save/Load:</b> Save your current chart data as a JSON file to easily reload it later.</li>
        <li><b>PNG Export:</b> Takes a high-quality screenshot of your current chart layout.</li>
        <li><b>Export Detailed:</b> Generates a comprehensive JSON text file containing planetary degrees, dignities, dashas, and auspiciousness analysis for external use.</li>
    </ul>
    <p style="text-align: right; font-size: 11px; color: #7f8c8d;"><i>-</i></p>
</div>
"""


tab2_visuals_html = """
<div style="line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Chart Interaction & Visuals</h2>
    <p>The charts in this app are highly interactive, designed to surface complex astrological data intuitively. Here is how to read and manipulate them:</p>

    <h3 style="color: #2980b9;">Interactive Features</h3>
    <ul>
        <li><b>Hover for Tooltips:</b> Move your mouse over any Planet or House. A detailed tooltip will appear showing degrees, dynamic functional nature (Yoga Karaka, Functional Benefic/Malefic, Neutral), dignities (Exalted, Debilitated, Retrograde, Combust), Nakshatra info, and what houses that planet rules.</li>
        <li><b>Double-Click to Rotate:</b> Double-click on any house in a chart to instantly rotate the chart and make that house the Ascendant (Lagna). This is highly useful for derivative house analysis (e.g., viewing the chart from the Moon or the 7th house). Double-click the current 1st house to reset it to the true Ascendant.</li>
        <li><b>Right-Click to Swap:</b> Right-click any chart to quickly swap it out for a different divisional chart without changing your layout.</li>
    </ul>

    <h3 style="color: #2980b9;">Visual Settings</h3>
    <ul>
        <li><b>Circ UI:</b> Check this box in settings to switch from the traditional North Indian Diamond chart to a Western-style Circular wheel chart.</li>
        <li><b>Symb:</b> Switches planetary names (Sun, Moon) to astronomical unicode symbols (☉, ☽) to save space.</li>
        <li><b>Ra/Ke:</b> Toggles the visibility of Rahu and Ketu on or off.</li>
    </ul>

    <h3 style="color: #2980b9;">Aspects & Arrows</h3>
    <ul>
        <li><b>Aspects Checkbox:</b> Turns on the visual display of planetary aspects (drishti).</li>
        <li><b>Aspects From:</b> A new panel will appear allowing you to select exactly <i>which</i> planets' aspects you want to see, preventing the chart from getting cluttered.</li>
        <li><b>Arrows & Tints:</b> Toggles whether aspects are shown as pointing lines (Arrows) hitting the targeted houses, or as soft background colors inside the targeted houses (Tints).</li>
    </ul>

    <h3 style="color: #2980b9; margin-top: 25px;">The Outlining Logic (Advanced House Context)</h3>
    <p>The <b>Outlines</b> dropdown in the Settings panel is one of the most powerful features in the app. It transforms the static borders of the chart's houses into dynamic, color-coded heatmaps that instantly convey deep astrological principles calculated directly by the engine.</p>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #27ae60; padding: 10px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #2c3e50;">1. Vitality (Lords)</h4>
        <p><i>Evaluates the structural integrity of the house based entirely on its ruling planet.</i> It ignores the occupants and asks: "Is the foundation of this house strong?"</p>
        <ul>
            <li><b style="color: #27ae60;">Thick Green (Life Engine):</b> The lord of this house is exceptionally strong (Exalted or in its Own Sign), is NOT situated in a negative Dusthana house (6, 8, or 12), and is NOT combust. This house has a highly vital, powerful foundation.</li>
            <li><b style="color: #e67e22;">Thick Orange (Plot Twist):</b> A complex paradox. Either the lord is very strong but trapped in a bad house (Dusthana 6, 8, 12), OR the lord is Debilitated but sitting in a highly auspicious Kendra or Trikona house (1, 4, 5, 7, 9, 10).</li>
            <li><b style="color: #c0392b;">Thick Red (Friction Zone):</b> The foundation is severely compromised. The lord is either Debilitated and not placed in a supportive house, OR the lord is Combust (burned by the Sun).</li>
            <li><b>Thin Gray (Background Scenery):</b> The lord is in a neutral state, neither exceptionally strong nor severely afflicted.</li>
        </ul>
    </div>

    <div style="background-color: #f8f9fa; border-left: 4px solid #f1c40f; padding: 10px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #2c3e50;">Pressure (Aspects)</h4>
        <p><i>Evaluates the external stress or focus placed upon the house.</i> This mode ignores the house lord and instead calculates how many <i>other</i> planets are actively looking at (aspecting) this specific house.</p>
        <ul>
            <li><b style="color: #c0392b;">Thick Red (Overloaded):</b> Extreme focus. <b>4 or more</b> planetary aspects are hitting this single house, indicating massive pressure or a highly complex area of life.</li>
            <li><b style="color: #f39c12;">Medium Gold (Strong):</b> Heavy focus. Exactly <b>3</b> planetary aspects are targeting this house.</li>
            <li><b style="color: #2980b9;">Thin Blue (Moderately Active):</b> Standard focus. Exactly <b>2</b> aspects are targeting this house.</li>
            <li><b>Thin Gray (Quiet):</b> 1 or 0 aspects. The house is relatively undisturbed by external forces.</li>
        </ul>
    </div>

    <div style="background-color: #f8f9fa; border-left: 4px solid #8e44ad; padding: 10px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #2c3e50;">Regime (Forces)</h4>
        <p><i>Displays a multi-layered view of active occupants and dominant forces.</i> Some houses act as massive energy hubs. If a house meets multiple criteria, it will draw <b>multiple concentric colored rings</b> inside the border.</p>
        <ul>
            <li><b style="color: #DC143C;">Crimson Ring (Dispositor Terminal):</b> This house is the ultimate "boss." Other planets sit in signs ruled by planets that sit in signs ruled by the planet in <i>this</i> house. It is the end of an astrological chain of command.</li>
            <li><b style="color: #005FFF;">Blue Ring (Aspect Projection Hub):</b> This house is acting as a massive spotlight. The planets sitting inside this house are casting <b>3 or more</b> aspects outward across the chart.</li>
            <li><b style="color: #f39c12;">Gold Ring (Theme Convergence):</b> This house is incredibly crowded. Combining the planets physically sitting inside it PLUS the aspects hitting it, there are <b>4 or more</b> total influences converging here.</li>
        </ul>
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #bdc3c7; padding: 10px;">
        <h4 style="margin-top: 0; color: #2c3e50;">None</h4>
        <p><i>The minimalist view.</i> Forces all house outlines to remain as static, thin gray lines regardless of astrological conditions. Perfect for clean screenshots or traditional, unassisted analysis.</p>
    </div>

    <p style="text-align: right; font-size: 11px; color: #7f8c8d; margin-top: 20px;"><i>-</i></p>
</div>
"""





tab3_animation_html = """
<div style="line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Animation & Transit Search</h2>
    <p>This application features a powerful real-time temporal engine allowing you to animate the sky or search for specific planetary events.</p>

    <h3 style="color: #2980b9;">Time Animation</h3>
    <ul>
        <li><b>Play/Pause:</b> Click <b>▶ Play</b> to start moving time forward automatically. All charts, tooltips, and plugins will update in real-time.</li>
        <li><b>Speed Control:</b> Change the dropdown next to the Play button to speed up time (from 1x real-time up to 604,800x, which equals weeks passing per second).</li>
        <li><b>Manual Stepping:</b> Use the <b>&lt;&lt;d</b>, <b>&lt;h</b>, <b>m&gt;</b> buttons to precisely jump backward or forward by days, hours, or minutes.</li>
    </ul>

    <h3 style="color: #2980b9;">Transit Constraints (Finding Events)</h3>
    <p>Use the Transit group to automatically calculate exactly when a planet will change signs.</p>
    <ul>
        <li><b>Target Planet & Varga:</b> Select a planet (e.g., Jupiter) and a chart division (e.g., D9).</li>
        <li><b>Calculate Next/Prev:</b> The buttons under "Lagna" and "Jump" will automatically calculate how much time is left until the Ascendant or your chosen planet moves into the next Zodiac sign.</li>
        <li><b>Jump Buttons (&lt; and &gt;):</b> Clicking the arrow buttons under "Jump" will instantly fast-forward or rewind the app's time to the exact moment that planet changes signs.</li>
    </ul>

    <h3 style="color: #2980b9;">Freezing Planets (Advanced Searching)</h3>
    <p>You can lock specific planets in place to search for rare planetary alignments.</p>
    <ol>
        <li>Check the <b>Table (Details)</b> box in settings to open the planetary data table at the bottom right.</li>
        <li>Find a planet and check the <b>"Freeze"</b> box. This tells the app: <i>"I want to find a time when this planet is in this exact sign in this exact divisional chart."</i></li>
        <li>If you press Play, the animation will automatically <b>Pause</b> if a frozen planet tries to leave its designated sign.</li>
        <li>If you use the Transit Jump buttons with frozen planets, the engine will search deep into the future/past to find the next time your target planet changes signs <b>WHILE</b> all your frozen conditions are also met!</li>
    </ol>
    <p style="text-align: right; font-size: 11px; color: #7f8c8d;"><i>-</i></p>
</div>
"""

tab4_plugins_html = """
<div style="line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Plugins & Extensions</h2>
    <p>The app includes dynamic plugins that load automatically in the left panel to provide advanced calculations.</p>

    <h3 style="color: #2980b9;">Vimshottari Dasha Timeline</h3>
    <ul>
        <li>Click <b>"Open Dasha Tree"</b> to view a complete, hierarchical breakdown of the native's planetary periods.</li>
        <li>It calculates down to 5 levels deep (Maha Dasha → Antar → Pratyantar → Sookshma → Prana).</li>
        <li>The tree automatically highlights the currently active timeline in green based on the app's current date, and automatically scrolls to it.</li>
    </ul>

    <h3 style="color: #2980b9;">Shadbala (6-Fold Strength)</h3>
    <ul>
        <li>Provides a real-time leaderboard of planetary strengths (Sthana, Dig, Kala, Cheshta, Naisargika, Drik).</li>
        <li>Because it calculates live, you can press Play on the animation and watch the Shadbala scores change dynamically as planets move.</li>
        <li>Click <b>"Detail Charts (Live)"</b> to open a comprehensive breakdown window with visual progress bars indicating if a planet meets its required classical strength thresholds.</li>
    </ul>

    <h3 style="color: #2980b9;">Chart Rectification</h3>
    <p>A tool for finding an unknown birth time based on known life events or desired planetary placements.</p>
    <ul>
        <li><b>Build Target Chart:</b> Opens a visual builder. Tell the app exactly where you want the planets or Ascendant to be in a specific chart (like the D9 or D60), and specify if they should be Retrograde.</li>
        <li><b>Search Birth Time:</b> The engine will scan through thousands of years using a lock-pick algorithm to find exact dates and times that perfectly match the planetary layout you built.</li>
    </ul>

    <h3 style="color: #2980b9;">Updater</h3>
    <ul>
        <li><b>Check for Updates:</b> Scans the remote server for bug fixes or new features and applies them safely without deleting your saves or any other exports.</li>
        <li><b>UPDATE FULL:</b> A diagnostic tool that forces a complete wipe and redownload of the app's core files in case your installation becomes corrupted. (Saves, exports and app settings are protected).</li>
        <li>Special care has been taking regarding data persistance. Updates will in no case remove any of the saved or charts data. </li>
    </ul>
    <p style="text-align: right; font-size: 11px; color: #7f8c8d;"><i>- </i></p>
</div>
"""

credits_html = """
        <div>
            <p>This application is an independent effort built with the intent 
            to explore and implement classical Vedic astrological computations and 
            visualizations in a modern software environment.</p>
            <h3 style="color: #2980b9; margin-top: 20px;">Core Technologies Used</h3>
            <ul>
                <li><b>PyQt6</b> — for the graphical user interface and application framework</li>
                <li><b>Swiss Ephemeris (swisseph)</b> — for astronomical and planetary calculations</li>
                <li><b>Custom rendering logic</b> (using QPainter) for diamond-style chart visualization</li>
            </ul>

            <h3 style="color: #2980b9; margin-top: 20px;">Credits and References</h3>
            <p>The design philosophy, workflow clarity, and certain interpretative structures 
            were inspired by Jagannatha Hora software without which this work would not have been be possible.</p>
            <p>Classical Vedic astrology principles, including Shadbala, Vargas, and planetary strengths, 
            are based on traditional texts and standard computational doctrines.</p>

            <h3 style="color: #c0392b; margin-top: 25px;">Important Clarification on Accuracy and Responsibility</h3>
            <p>This application is a personal implementation of complex astrological systems.<br>
            While significant effort has been made to align calculations with traditional methods 
            and known software references, this is <b>NOT</b> an authoritative or certified 
            implementation.</p>
            
            <p>Any discrepancies, inaccuracies, computational deviations, or interpretational 
            inconsistencies within this application are:</p>
            <ul style="list-style-type: square;">
                <li><b>SOLELY</b> the responsibility of The developer  of this application</li>
                <li><b>Not</b> attributable to Swiss Ephemeris, Jagannatha Hora, or 
                <b>any</b> classical sources referenced.</li>
                <li>Should be brought into attention (so corrections could be made) to The developer .</li>
            </ul>

            <div style="background-color: #fdf2f2; border-left: 5px solid #e74c3c; padding: 12px; 
            margin-top: 20px; border-radius: 3px;">
                <p style="margin-top: 0;"><b>In other words:</b></p>
                <p>If something is wrong, unclear, inconsistent, or behaves unexpectedly — 
                the fault lies in <b>IMPLEMENTATION</b> of complex vedic mathematics and 
                computations and <b>NOT</b> the sources themselves.</p>
                <p style="margin-bottom: 0;">This software is provided as-is, without guarantees of 
                accuracy, completeness, or fitness for any specific purpose. 
                It is intended for educational, exploratory, and personal use <b>ONLY</b>.</p>
            </div>

            <h3 style="color: #2c3e50; margin-top: 25px;">Final Note</h3>
            <p><i>Astrology itself is a deeply interpretative discipline. 
            This application represents one attempt at structuring, computing and visualizing its 
            principles - <b>NO CLAIMS ARE MADE REGARDING CORRECTNESS OF RESULTS 
            DERIVED FORM THIS APP.</b></i></p>

            <p style="text-align: right; font-weight: bold; margin-top: 30px;">——— Developer</p>
        </div>
        """

privacy_html = """
        <h2 style="color: #c0392b; margin-top: 25px;">Privacy Policy</h2>
        <p><b>This app does not collect ANY of user information for ANY purpose. All your charts
        and exported data are locally stored on your disk, and are never accessed during updates.
        </b></p>

        <hr style="margin: 15px 0; border: 0; border-top: 1px solid #e2e8f0;">

        <h3 style="color: #2b6cb0;">1. 100% Local Data Storage</h3>
        <p>Everything you create within AstroBasics Diamond Chart Pro stays strictly on your machine. 
        This software does not have servers, or a cloud database of its own. Your data is yours alone.</p>
        <ul>
            <li><b>Saved Charts:</b> All `.json` chart files containing sensitive birth times and details are saved
            directly to your chosen local directory (defaulting to the <code>saves/</code> folder).</li>
            <li><b>Autosaves:</b> Temporary backups are stored locally in the <code>autosave/</code> 
            folder purely to protect your work from unexpected application closures.</li>
            <li><b>Preferences & Settings:</b> Your UI preferences, selected Ayanamsa, default locations, 
            and custom layouts are stored in a local <code>astro_settings.json</code> file on your hard drive.
            (and are NOT and will NEVER be used for ANY purpose.)</li>
        </ul>

        <h3 style="color: #2b6cb0;">2. Absolute Transparency on Network Usage</h3>
        <p>AstroBasics is designed to be fully functional completely offline, with <b>one specific exception</b> to make your life easier:</p>
        <ul>
            <li><b>Location Search (Geocoding):</b> When you type a city name (e.g., "New Delhi") and 
            click "Search," the app sends <i><b>ONLY that search string</b></i> to the open-source 
            OpenStreetMap (Nominatim) API to fetch the exact Latitude, Longitude, and Timezone.</li>
            <li><b>What is NOT sent:</b> Absolutely no astrological data, birth dates, times, or other 
            details are ever attached to this search request. Once the coordinates are fetched, the 
            calculation engine runs 100% locally using the Swiss Ephemeris.</li>
        </ul>

        <h3 style="color: #2b6cb0;">3. Zero Telemetry, Tracking, or Analytics</h3>
        <p>The developer believes your software should just work, without silently watching you. Therefore:</p>
        <ul>
            <li><b>No Analytics:</b> There are no hidden tracking scripts, Google Analytics, or usage metrics 
            embedded in this application.</li>
            <li><b>No Crash Reporting:</b> If the app crashes, it crashes quietly on your machine.
            It does not automatically send crash logs, memory dumps, or system information back to 
            The developer. (that is why logs and errors can be viewed in the app itself only)</li>
            <li><b>No Ads or Subscriptions:</b> There is no background network activity fetching advertisements or verifying license keys.</li>
        </ul>

        <h3 style="color: #2b6cb0;">4. Data Export and Ownership</h3>
        <p>You have full ownership of any analysis generated by the software. 
        When you use the <b>"Export PNG"</b> or <b>"Export Detailed"</b> (JSON) features, 
        the resulting files are compiled locally and written straight to your personal disk. 
        The developer cannot view, access, or monetize your generated reports.</p>

        <h3 style="color: #2b6cb0;">5. Safe Application Updates</h3>
        <p>If you download a newer version of AstroBasics Diamond Chart Pro in the future (or update current version), 
        the new executable will never overwrite, scan, or upload your existing 
        <code>saves/</code>, <code>autosave/</code>, <code>custom_vargas.json</code> or <code> astro_settings.json</code> 
        files/directories. Your historical work remains untouched and entirely yours.</p>

        <br>
        <p><i>If you have any questions or require further technical clarification about how your data is handled locally, please review the open-source codebase or contact The developer directly.</i></p>
"""
