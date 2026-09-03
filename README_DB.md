# Odinson Vibration Monitor with Database and Data Viewing

This version enhances the original Odinson Vibration Monitor with database storage and a historical data viewing interface while preserving the original structure and matplotlib display.

## Features
- All original functionality preserved:
  - Real-time serial communication with MPU6050
  - Matplotlib real-time waveform display (runs in main thread with black background)
  - Flask web server for monitoring
  - Telegram alerts for significant events
  - Sound alerts
  - CSV logging
- Added database storage (SQLite):
  - All vibration data stored in `vibration_data.db`
  - Historical data persists between program runs
- Enhanced frontend with:
  - Clean, professional design using color #28282B
  - Live monitor view (real-time data)
  - Historical data viewing page with:
    - Interactive, movable graph
    - paginated data table
    - CSV export functionality
    - Date range filtering
- Runnable directly in VS Code (just run the Python file)

## Files
- `maincode_withdb.py` - Main application with database integration
- `templates/index.html` - Live monitoring interface (clean frontend)
- `templates/history.html` - Historical data viewing interface
- `vibration_data.db` - SQLite database (created automatically)
- `logs/vibration_log_*.csv` - CSV log files (created automatically in logs directory)

## How to Use
1. **Connect your Arduino** to the serial port (default COM3 - change in code if needed)
2. **Install required packages**:
   ```
   pip install flask pyserial requests
   ```
   (matplotlib, winsound, sqlite3, collections, datetime, time, threading should be available in standard Python)
3. **Run the application**:
   - In VS Code: Open `maincode_with_db.py` and press F5, or
   - From command line: `python maincode_with_db.py`
4. **Open your browser** to `http://localhost:5000` to see the monitoring interface
5. **Navigate to "View Past Data"** in the top menu to see historical data
6. **The matplotlib window** will also appear showing real-time vibration data with black background

## Navigation
- **Live Monitor** (`/`): Real-time vibration monitoring with matplotlib graph
- **View Past Data** (`/history_view`): Historical data viewing with interactive graph and table

## API Endpoints
- `GET /` - Main monitoring interface
- `GET /latest` - Current vibration data (JSON)
- `GET /buffer` - Buffered time/delta arrays for waveform (JSON)
- `GET /history` - Historical data from database (supports limit, start, end parameters)
- `GET /history/<start_time>/<end_time>` - Data within specific time range (JSON)
- `GET /history_view` - Historical data viewing interface

## Database Schema
The SQLite database `vibration_data.db` contains one table:
```
vibration_data
- id: INTEGER PRIMARY KEY
- timestamp: TEXT (format: HH:MM:SS.sss)
- delta: REAL (vibration magnitude)
- alert: INTEGER (0 or 1)
```

## Notes
- The matplotlib display runs in the main thread for optimal performance with black background
- The Flask server runs in a background thread
- Serial reading runs in a background thread
- Data is stored simultaneously in: CSV file (in logs directory), memory buffers (for real-time display), and SQLite database (for persistence)
- Historical data can be viewed while the program is running via the `/history_view` page
- No emojis or distracting symbols in the frontend - clean, professional appearance
- Uses color #28282B as the primary background color throughout the interface

## Regarding Vercel Deployment
Due to the requirements of this application (direct serial port access to Arduino, long-running background threads for serial reading and data processing, and the use of matplotlib for real-time plotting), it is **not suitable for deployment on Vercel**. Vercel is designed for serverless functions and static sites, and does not provide:
- Access to local hardware ports (like COM3)
- Long-running process capabilities (background threads would be terminated)
- GUI capabilities for matplotlib display

If you wish to deploy a version to Vercel that shows historical data or simulates the monitoring interface, we would need to:
1. Create a separate version that uses mock data or connects to a remote API for data
2. Host the serial/data processing component elsewhere (e.g., on a cloud VM or your local machine with a public API)
3. Deploy only the frontend and API endpoints to Vercel

Please let me know if you would like me to create such a Vercel-compatible version, and I can provide instructions for setting it up.