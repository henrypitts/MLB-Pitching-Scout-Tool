# MLB Pitcher Scouting Tool

An interactive MLB pitcher evaluation dashboard built with Python and Streamlit. The tool brings together traditional performance statistics, Statcast pitch-tracking data, pitch characteristics, and location-based analysis to support more complete pitcher scouting reports.

**[Launch the live dashboard](https://hpmlbpitchingscout.streamlit.app/)**

## Project Overview

Evaluating a pitcher requires more than a stat line. Results describe *what happened*; pitch characteristics, usage, and location data provide context for *how* those results were produced.

I developed this application to bring those perspectives into one interactive report. Users can select an MLB team and pitcher, examine season performance, study the pitch arsenal, and explore pitch execution and approach without moving among several separate data sources.

The dashboard is organized into two primary sections:

### Player Overview

- **Player profile and classifications:** Biographical information and descriptive scouting tags based on measurable pitching characteristics.
- **Traditional and advanced statistics:** Season results alongside strikeout, walk, expected-outcome, and contact-quality metrics.
- **Pitch movement and arsenal usage:** Visual comparisons of horizontal and induced vertical break, with pitch-type usage distributions.
- **Release characteristics:** Arm angle, extension, and pitch volume.
- **Arsenal breakdown:** Pitch-level characteristics and performance metrics, including velocity, movement, and vertical approach angle (VAA) where available.

### Pitch Strategy

- **Plate-location analysis:** Visualizations of where pitches are thrown by pitch type.
- **Strike-zone performance:** Location-based views designed to distinguish results within the zone from chase behavior outside it.
- **Pitch-level approach:** Tools for studying how an arsenal is deployed and how location relates to outcomes.

## Technical Approach

This project combines public baseball data with custom calculations, classification rules, and interactive visualizations.

- **Python / pandas / NumPy:** Data collection, cleaning, transformation, and metric calculations.
- **Streamlit:** Interactive interface, player selection, and deployment.
- **Plotly:** Pitch movement, arsenal usage, and other interactive baseball visualizations.
- **pybaseball / Statcast:** Pitch-by-pitch data access.
- **MLB Stats API and Baseball Savant:** Player, team, season, and advanced-statistics data.
- **Caching:** Reduces repeated requests and improves responsiveness when loading external data.

The classification system translates continuous measurements into readable scouting descriptors. These labels are intended to organize observations and identify traits worth investigating; they are not substitutes for a complete scouting evaluation.

## Skills Demonstrated

Building this tool involved:

1. **Baseball analytics:** Selecting and interpreting performance, pitch-shape, release, and plate-location metrics in a scouting context.
2. **Data engineering:** Combining information from multiple public sources and handling missing or inconsistent observations.
3. **Analytical programming:** Creating reusable Python functions and metric-driven player classifications.
4. **Data visualization:** Designing visuals that communicate pitch characteristics and strategic tendencies clearly.
5. **Application development:** Turning analytical workflows into a usable, publicly accessible dashboard.

My goal is to develop tools that make baseball data easier to explore, interpret, and use in player evaluation and decision-making.

## Run Locally

Clone the repository and install its dependencies:

```bash
git clone <your-repository-clone-url>
cd mlb-pitching-scout-tool
python -m pip install -r requirements.txt
streamlit run Baseball-dash.py
```

The application requires internet access to retrieve external baseball data. Availability of individual metrics depends on the selected pitcher's recorded data and the upstream sources.

## Data Sources and Limitations

- [MLB Stats API](https://statsapi.mlb.com/)
- [Baseball Savant](https://baseballsavant.mlb.com/)
- [pybaseball](https://github.com/jldbc/pybaseball)

This is an independent analytical project and is not affiliated with or endorsed by Major League Baseball. Public data availability, classification thresholds, sample sizes, and upstream API changes can affect displayed results. Small-sample conclusions should be interpreted cautiously.

## Author

**Henry Pitts**  
B.S. in Statistics, Virginia Tech  
Interested in baseball research and development, player evaluation, and data-informed decision-making.
