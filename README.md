🌴 WhereverWeGo: Multi-Criteria Decision Support System
An advanced vacation planning tool that uses mathematical optimization to rank destinations based on user-specific preferences and real-time data.

📊 Project Preview
Below are the interactive interfaces where users can define their criteria and view the results:

1. Main Criteria & Scoring Interface Interactive sliders for 11 different criteria and budget settings.

2. Real-time Analysis & Weather Integration Live weather data synchronization for the top 5 recommended locations.

3. Geospatial Mapping & Final Results Interactive map showing the exact locations of recommended hotels.

🧠 Core Methodology
Instead of basic filtering, this system implements the TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution) algorithm.

Ideal Matching: The algorithm creates a hypothetical "Perfect Hotel" based on user weights.

Mathematical Ranking: Calculates the geometric distance of every hotel in the SQLite database to this ideal point.

🚀 Key Features
Data Engineering: Migrated unstructured data from Excel to a structured SQLite environment.

External API Integration: Real-time sync with OpenWeatherMap for current vacation conditions.

Automated Geocoding: Used Nominatim API to retrieve geographic coordinates for map visualization.

🛠 Tech Stack
Language: Python

Libraries: Pandas, NumPy, Streamlit.

Database: SQLite.
