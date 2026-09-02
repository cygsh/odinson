import serial
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import requests
import winsound
import csv
from datetime import datetime

# ================= TELEGRAM CONFIG =================
TELEGRAM_API_TOKEN = 'token'
CHAT_ID = 'id'

# ================= SERIAL CONFIG ===================
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

# ================= DATA STORAGE ====================
time_labels = []
delta_data = []

# ================= SENSITIVITY =====================
SOUND_THRESHOLD_LOW = 400
LOG_THRESHOLD = 50

alert_sent = False
sound_played = False
baseline = None

# ================= CSV LOGGER ======================
run_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
csv_filename = f"vibration_log_{run_time}.csv"

csv_file = open(csv_filename, 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["time_24h", "delta", "alert"])

# ================= ALERT FUNCTIONS =================
def send_telegram_message(message):
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage"
        f"?chat_id={CHAT_ID}&text={message}"
    )

def sound_alert():
    winsound.Beep(1000, 500)

# ================= MAIN UPDATE LOOP =================
def update(frame):
    global alert_sent, sound_played, baseline

    line = ser.readline().decode('utf-8').rstrip()
    if not line:
        return

    data = line.split(',')
    if len(data) < 4:
        return

    try:
        ax = float(data[1])
        ay = float(data[2])
        az = float(data[3])

        current_mag = (ax**2 + ay**2 + az**2) ** 0.5

        if baseline is None:
            baseline = current_mag
            return

        delta = abs(current_mag - baseline)
        baseline = 0.98 * baseline + 0.02 * current_mag

        now = datetime.now()
        time_str = now.strftime('%H:%M:%S.%f')[:-3]

        alert_flag = 0

        if delta > SOUND_THRESHOLD_LOW:
            alert_flag = 1

            if not alert_sent:
                send_telegram_message("plates might be shifting")
                alert_sent = True

            if not sound_played:
                sound_alert()
                sound_played = True
        else:
            alert_sent = False
            sound_played = False

        if delta > LOG_THRESHOLD:
            csv_writer.writerow([time_str, round(delta, 2), alert_flag])
            csv_file.flush()

            time_labels.append(time_str)
            delta_data.append(delta)

        if len(delta_data) > 150:
            delta_data.pop(0)
            time_labels.pop(0)

        delta_line.set_data(range(len(delta_data)), delta_data)
        ax_plot.set_ylim(0, max(600, max(delta_data) + 50))
        ax_plot.set_xlim(0, len(delta_data))

    except ValueError:
        pass

# ================= PLOTTING ========================
fig, ax_plot = plt.subplots(figsize=(10, 6))

delta_line, = ax_plot.plot([], [], linewidth=2, label="Delta (Vibration)")
ax_plot.axhline(y=SOUND_THRESHOLD_LOW, linestyle='--', label="Alert Threshold")

ax_plot.set_title("Vibration Delta vs Time")
ax_plot.set_xlabel("Samples (time progressing)")
ax_plot.set_ylabel("Delta Magnitude")
ax_plot.legend()

ani = FuncAnimation(fig, update, interval=20)

plt.tight_layout()
plt.show()

# ================= SAVE FINAL GRAPH =================
plot_filename = f"vibration_plot_{run_time}.png"
fig.savefig(plot_filename)
csv_file.close()
