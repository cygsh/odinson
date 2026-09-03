import serial
import time
import threading
import csv
from datetime import datetime
from flask import Flask, render_template, jsonify
import requests
import winsound
from collections import deque
import sqlite3
import os
import random

# Debug log for serial lines
debug_lines = []

# Global flag to control threads
running = True
use_mock = False

# ================= TELEGRAM CONFIG =================
TELEGRAM_API_TOKEN = '8176836564:AAHvJ4kzmchFaYoBhBXSsSSAK8YubHcighQ'
CHAT_ID = '5517493014'

# ================= SERIAL CONFIG ===================
SERIAL_PORT = 'COM3'  # Change this if needed
BAUD_RATE = 9600

# ================= DATA STORAGE ====================
# Buffers for waveform (last 200 points)
data_lock = threading.Lock()
time_buffer = deque(maxlen=200)
delta_buffer = deque(maxlen=200)
latest_data = {'time': '', 'delta': 0.0, 'alert': 0}

# ================= SENSITIVITY =====================
# DRastically reduced thresholds for maximum sensitivity
SOUND_THRESHOLD_LOW = 15   # Was 400 - now triggers on very light taps
LOG_THRESHOLD = 2          # Was 50 - now logs even tiny vibrations

alert_sent = False
sound_played = False
baseline = None

# ================= DATABASE SETUP ======================
DATABASE = 'vibration_data.db'

def init_db():
    """Initialize the database with vibration data table"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS vibration_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            delta REAL NOT NULL,
            alert INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def insert_vibration_data(timestamp, delta, alert):
    """Insert vibration data into database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('INSERT INTO vibration_data (timestamp, delta, alert) VALUES (?, ?, ?)',
              (timestamp, delta, alert))
    conn.commit()
    conn.close()

def get_recent_vibration_data(limit=100):
    """Get recent vibration data from database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT timestamp, delta, alert FROM vibration_data ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    # Return in chronological order (oldest first)
    return [{'time': row[0], 'delta': row[1], 'alert': row[2]} for row in reversed(rows)]

def get_vibration_data_by_time_range(start_time, end_time):
    """Get vibration data within a time range"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, delta, alert FROM vibration_data
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (start_time, end_time))
    rows = c.fetchall()
    conn.close()
    return [{'time': row[0], 'delta': row[1], 'alert': row[2]} for row in rows]

# ================= CSV LOGGER ======================
run_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
csv_filename = os.path.join(LOG_DIR, f"vibration_log_{run_time}.csv")

csv_file = open(csv_filename, 'w', newline='', buffering=1)  # Line-buffered
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["time_24h", "delta", "alert"])

# ================= ALERT FUNCTIONS =================
def send_telegram_message(message):
    def _send():
        try:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage"
                f"?chat_id={CHAT_ID}&text={message}"
            )
        except Exception as e:
            print(f"Telegram error: {e}")
    threading.Thread(target=_send, daemon=True).start()

def sound_alert():
    # Play sound in a blocking way but we'll call this from a thread
    winsound.Beep(1000, 500)

# ================= FLASK APP ======================
app = Flask(__name__)

# ================= SERIAL READING THREAD ==========
def serial_thread():
    global alert_sent, sound_played, baseline, running, use_mock
    # Keep trying to connect to serial port
    mock_attempts = 0
    while running and not use_mock:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            print("Serial thread started")
            break  # Exit retry loop on success
        except Exception as e:
            if not running:
                break
            print(f"Failed to open serial port {SERIAL_PORT}: {e}")
            mock_attempts += 1
            if mock_attempts >= 1:
                print("Switching to mock data mode after 1 failed attempt")
                use_mock = True
                break
            print("Retrying in 1 second...")
            time.sleep(1)  # Wait before retrying

    if use_mock:
        # Mock data generation
        import random
        baseline_mock = 1.0
        mock_counter = 0
        while running:
            # Simulate a reading with occasional spikes
            if random.random() < 0.5:  # 50% chance of a spike for testing
                current_mag = baseline_mock + random.uniform(10.0, 30.0)
            else:
                current_mag = baseline_mock + (random.random() - 0.5) * 0.5  # increased noise
            delta = abs(current_mag - baseline_mock)
            # update baseline_mock
            baseline_mock = 0.95 * baseline_mock + 0.05 * current_mag

            now = datetime.now()
            time_str = now.strftime('%H:%M:%S.%f')[:-3]

            alert_flag = 1 if delta > SOUND_THRESHOLD_LOW else 0

            # Update buffers for plotting and web (every reading)
            with data_lock:
                time_buffer.append(time_str)
                delta_buffer.append(delta)
                latest_data['time'] = time_str
                latest_data['delta'] = round(delta, 2)
                latest_data['alert'] = alert_flag

            # Log to CSV and database only if above LOG_THRESHOLD
            if delta > LOG_THRESHOLD:
                csv_writer.writerow([time_str, round(delta, 2), alert_flag])
                insert_vibration_data(time_str, round(delta, 2), alert_flag)

            mock_counter += 1
            if mock_counter % 10 == 0:  # Print every 10 iterations (0.5 seconds at 20 Hz)
                print(f"Mock data: delta={delta:.2f}, alert_flag={alert_flag}")

            time.sleep(0.05)  # 20 Hz
    else:
        # Actual serial reading
        while running:
            try:
                line = ser.readline().decode('utf-8').rstrip()
            except Exception as e:
                if not running:
                    break
                print(f"Serial read error: {e}")
                # Try to reconnect
                try:
                    ser.close()
                except:
                    pass
                time.sleep(0.1)  # Reduced sleep for faster error recovery
                # Reconnect loop
                while running:
                    try:
                        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                        time.sleep(1)
                        print("Serial reconnected")
                        break
                    except Exception as e:
                        if not running:
                            break
                        print(f"Reconnect failed: {e}")
                        time.sleep(2)
                if not running:
                    break
                continue
            if not line:
                continue
            # Debug: print first few lines
            if len(debug_lines) < 5:
                debug_lines.append(line)
                print(f"Serial line: {line}")
            data = line.split(',')
            if len(data) < 4:
                continue
            try:
                # Arduino sends: millis(), ax, ay, az (already calibrated)
                # We don't need millis from Arduino; we'll use our own timestamp
                ax = float(data[1])
                ay = float(data[2])
                az = float(data[3])

                current_mag = (ax**2 + ay**2 + az**2) ** 0.5

                if baseline is None:
                    baseline = current_mag
                    continue

                delta = abs(current_mag - baseline)
                # More responsive baseline adaptation for better sensitivity
                baseline = 0.95 * baseline + 0.05 * current_mag

                now = datetime.now()
                time_str = now.strftime('%H:%M:%S.%f')[:-3]

                alert_flag = 0
                if delta > SOUND_THRESHOLD_LOW:
                    alert_flag = 1
                    if not alert_sent:
                        send_telegram_message("plates might be shifting")
                        alert_sent = True
                    # Play sound in a separate thread to avoid blocking
                    if not sound_played:
                        sound_played = True
                        threading.Thread(target=sound_alert, daemon=True).start()
                else:
                    alert_sent = False
                    sound_played = False

                # Update buffers for plotting and web (every reading)
                with data_lock:
                    time_buffer.append(time_str)
                    delta_buffer.append(delta)
                    latest_data['time'] = time_str
                    latest_data['delta'] = round(delta, 2)
                    latest_data['alert'] = alert_flag

                # Log to CSV and database only if above LOG_THRESHOLD
                if delta > LOG_THRESHOLD:
                    csv_writer.writerow([time_str, round(delta, 2), alert_flag])
                    insert_vibration_data(time_str, round(delta, 2), alert_flag)

            except ValueError as e:
                if not running:
                    break
                print(f"ValueError: {e} on line: {line}")
                continue
            except Exception as e:
                if not running:
                    break
                print(f"Unexpected error: {e} on line: {line}")
                continue

# ================= ROUTES =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/latest')
def get_latest():
    with data_lock:
        return jsonify(latest_data)

@app.route('/buffer')
def get_buffer():
    with data_lock:
        return jsonify({
            'times': list(time_buffer),
            'deltas': list(delta_buffer)
        })

@app.route('/history')
def get_history():
    """Get historical data from database with optional limit"""
    limit = request.args.get('limit', default=500, type=int)
    data = get_recent_vibration_data(limit=limit)
    return jsonify({
        'times': [item['time'] for item in data],
        'deltas': [item['delta'] for item in data],
        'alerts': [item['alert'] for item in data]
    })

@app.route('/history/<start_time>/<end_time>')
def get_history_by_range(start_time, end_time):
    """Get historical data within time range"""
    data = get_vibration_data_by_time_range(start_time, end_time)
    return jsonify({
        'times': [item['time'] for item in data],
        'deltas': [item['delta'] for item in data],
        'alerts': [item['alert'] for item in data]
    })

@app.route('/history_view')
def history_view():
    """Render page to view past data with interactive graph"""
    return render_template('history.html')

# Shutdown endpoint for Flask server
@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

# ================= FLASK THREAD ==========
def run_flask():
    print("Starting Flask app on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ================= MAIN ===========================
if __name__ == '__main__':
    # Initialize database
    init_db()

    # Start serial reading thread (background)
    serial_thread_obj = threading.Thread(target=serial_thread, daemon=False)
    serial_thread_obj.start()

    # Start Flask thread (background)
    flask_thread = threading.Thread(target=run_flask, daemon=False)
    flask_thread.start()

    # ================= MATPLOTLIB SETUP (MAIN THREAD) =================
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('TkAgg')  # Use TkAgg backend for better threading compatibility

    # Initialize matplotlib plot with dark background to match website
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title('Real-time Vibration Delta')
    ax.set_xlabel('Time')
    ax.set_ylabel('Delta Magnitude')
    ax.grid(True, alpha=0.3)
    line, = ax.plot([], [], 'w-', linewidth=2)  # White line
    # Add threshold line as dotted white line
    threshold_line = ax.axhline(y=LOG_THRESHOLD, color='white', linestyle='--', linewidth=1, alpha=0.7)
    plt.tight_layout()

    # Show the plot non-blockingly
    plt.show(block=False)

    # Keep matplotlib plot updating in MAIN THREAD
    try:
        while True:
            # Update matplotlib plot with current data
            with data_lock:
                if len(delta_buffer) > 0:
                    line.set_data(range(len(delta_buffer)), list(delta_buffer))
                    ax.set_xlim(0, max(len(delta_buffer), 1))
                    # Set ylim with some padding
                    if delta_buffer:
                        ymax = max(list(delta_buffer)) * 1.5
                        ymin = min(list(delta_buffer)) * 1.5
                        # Ensure threshold line is visible with plenty of room
                        ymax = max(ymax, LOG_THRESHOLD * 3.0)
                        ymin = min(ymin, -LOG_THRESHOLD * 0.5)  # Allow negative going below zero
                        ax.set_ylim(ymin, ymax)
                    else:
                        ax.set_ylim(-10, 10)
                    fig.canvas.draw_idle()
            # Process GUI events
            plt.pause(0.001)
    except KeyboardInterrupt:
        print("Shutting down...")
        running = False
        # Wait for serial thread to finish
        serial_thread_obj.join(timeout=5.0)
        # Shutdown Flask server
        try:
            requests.post('http://localhost:5000/shutdown', timeout=2)
        except:
            pass
        # Wait for Flask thread to finish
        flask_thread.join(timeout=5.0)
    finally:
        csv_file.close()