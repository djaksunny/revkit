import sys
import serial
import time
import threading
import tkinter as tk
from tkinter import PhotoImage, ttk
import tkinter.messagebox as msgbox
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
import json
import os
from simple_pid import PID

# --- PyInstaller resource path helper ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Config Handling ---
def get_config_path():
    config_dir = os.path.join(os.path.expanduser("~"), ".revkit")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "revkit_config.json")

CONFIG_FILE = get_config_path()
default_config = {
    "Kp": 1.0,
    "Ki": 1.8,
    "Kd": 0.05,
    "Amplitude": 50,
    "Offset": 150,
    "Period": 10,
    "Wave": "sine"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return default_config.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f)
    except Exception as e:
        print(f"Failed to save config: {e}")

config = load_config()

# --- Serial scanner and setup ---
def auto_connect_serial(baudrate=115200):
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        try:
            s = serial.Serial(p.device, baudrate, timeout=0.1, write_timeout=0.1)
            time.sleep(2)
            return s
        except:
            continue
    raise Exception("No serial device found.")

try:
    ser = auto_connect_serial()
except Exception as e:
    msgbox.showerror("RevKit Desktop Interface", "RevKit couldn't launch: No serial device found.")
    sys.exit()

Kp = config["Kp"]
Ki = config["Ki"]
Kd = config["Kd"]
square_amp = config["Amplitude"]
square_offset = config["Offset"]
square_period = config["Period"]

setpoint = 100
rpm = 0
pwm = 0

rpm_history = []
square_history = []
pwm_history = []

pid = PID(Kp, Ki, Kd, setpoint=setpoint)
pid.sample_time = 0.01
pid.output_limits = (-255, 255)

# --- PID loop ---
def pid_loop():
    global rpm, pwm, Kp, Ki, Kd, setpoint
    while True:
        ser.reset_input_buffer()
        line = ser.readline().decode().strip()
        if line.startswith("I:"):
            try:
                rpm = float(line[2:])
            except ValueError:
                continue

        pid.Kp = Kp
        pid.Ki = Ki
        pid.Kd = Kd
        pid.setpoint = setpoint

        pwm = int(pid(rpm))

        try:
            ser.write(f"{pwm}\n".encode())
        except serial.SerialTimeoutException:
            print("serial timeout")

# --- Setpoint update loop ---
def update_setpoint():
    global setpoint
    t0 = time.time()
    while True:
        t = time.time() - t0
        wave = waveform_type.get()
        if wave == "square":
            if (t % square_period) < (square_period / 2):
                setpoint = square_offset + square_amp
            else:
                setpoint = square_offset - square_amp
        elif wave == "sine":
            omega = 2 * math.pi / square_period
            setpoint = square_offset + square_amp * math.sin(omega * t)
        elif wave == "triangle":
            phase = (t % square_period) / square_period
            if phase < 0.5:
                val = 2 * phase
            else:
                val = 2 * (1 - phase)
            setpoint = square_offset + square_amp * (2 * val - 1)
        time.sleep(0.05)

# --- GUI update ---
def update_gui():
    current_rpm.set(f"{rpm:.1f}")
    pwm_value.set(pwm)
    current_setpoint.set(f"{setpoint:.1f}")

# --- Plot animation ---
def animate(i):
    rpm_history.append(rpm)
    square_history.append(setpoint)
    pwm_history.append(pwm)

    if len(rpm_history) > 100:
        rpm_history.pop(0)
        square_history.pop(0)
        pwm_history.pop(0)

    x_vals = list(range(len(rpm_history)))
    line.set_data(x_vals, rpm_history)
    square_line.set_data(x_vals, square_history)
    pwm_line.set_data(x_vals, pwm_history)

    ax1.set_xlim(max(0, len(rpm_history) - 100), len(rpm_history))
    ax2.set_xlim(max(0, len(rpm_history) - 100), len(rpm_history))

    update_gui()
    return line, square_line, pwm_line

# --- GUI Setup ---
root = tk.Tk()
root.title("RevKit Desktop Interface")
photo = PhotoImage(file=resource_path("revkit_small.png"))
root.iconphoto(False, photo)

current_setpoint = tk.StringVar()
current_rpm = tk.StringVar()
pwm_value = tk.IntVar()

main_frame = ttk.Frame(root, padding=10)
main_frame.pack(fill='both', expand=True)
left_frame = ttk.Frame(main_frame)
right_frame = ttk.Frame(main_frame)
left_frame.pack(side='left', fill='y', padx=(0, 10))
right_frame.pack(side='left', fill='both', expand=True)

bottom_logo_frame = ttk.Frame(left_frame)
bottom_logo_frame.pack(side='bottom', anchor='w', pady=(15, 0))

logo_img = PhotoImage(file=resource_path("revkit_logo.png")).subsample(8, 8)
logo_label = ttk.Label(bottom_logo_frame, image=logo_img)
logo_label.pack(side='left', pady=(15, 0))
version_label = ttk.Label(bottom_logo_frame, text="RevKit Desktop Interface v1.0", font=("Segoe UI", 10))
version_label.pack(side='left', padx=(10, 0))

# Labels
for label, var in [("Target RPM:", current_setpoint), ("Current RPM:", current_rpm), ("PWM Output:", pwm_value)]:
    ttk.Label(left_frame, text=label).pack(anchor='w')
    ttk.Label(left_frame, textvariable=var).pack(anchor='w', pady=(0,10))

# PID sliders
pid_frame = ttk.LabelFrame(left_frame, text="PID Controls", padding=(10,10))
pid_frame.pack(fill='x', pady=(0,15))

def update_kp(val): global Kp; Kp = float(val); config["Kp"] = Kp; save_config(config)
def update_ki(val): global Ki; Ki = float(val); config["Ki"] = Ki; save_config(config)
def update_kd(val): global Kd; Kd = float(val); config["Kd"] = Kd; save_config(config)

def create_slider_entry(parent, label_text, from_, to, initial, resolution, command):
    frame = ttk.Frame(parent)
    ttk.Label(frame, text=label_text, width=14).pack(side='left', padx=(0,5))
    var = tk.DoubleVar(value=initial)

    def on_slider_change(val):
        val = float(val)
        entry_var.set(f"{val:.2f}")
        command(val)

    slider = ttk.Scale(frame, from_=from_, to=to, orient='horizontal', variable=var, command=on_slider_change)
    slider.pack(side='left', fill='x', expand=True)

    entry_var = tk.StringVar(value=f"{initial:.2f}")
    entry = ttk.Entry(frame, width=6, textvariable=entry_var)
    entry.pack(side='left', padx=(5,0))

    def on_entry_change(event=None):
        try:
            val = float(entry_var.get())
            val = max(from_, min(to, val))
            var.set(val)
            command(val)
        except ValueError:
            entry_var.set(f"{var.get():.2f}")

    entry.bind('<Return>', on_entry_change)
    entry.bind('<FocusOut>', on_entry_change)
    return frame

create_slider_entry(pid_frame, "Kp", 0, 10, Kp, 0.01, update_kp).pack(fill='x', pady=3)
create_slider_entry(pid_frame, "Ki", 0, 10, Ki, 0.01, update_ki).pack(fill='x', pady=3)
create_slider_entry(pid_frame, "Kd", 0, 0.5, Kd, 0.01, update_kd).pack(fill='x', pady=3)

# Waveform settings
square_frame = ttk.LabelFrame(left_frame, text="Waveform Settings", padding=(10,10))
square_frame.pack(fill='x')

def update_amp(val): global square_amp; square_amp = float(val); config["Amplitude"] = square_amp; save_config(config)
def update_offset(val): global square_offset; square_offset = float(val); config["Offset"] = square_offset; save_config(config)
def update_period(val): global square_period; square_period = float(val); config["Period"] = square_period; save_config(config)

def update_waveform_type(): config["Wave"] = waveform_type.get(); save_config(config)

create_slider_entry(square_frame, "Amplitude", 0, 300, square_amp, 0.01, update_amp).pack(fill='x', pady=3)
create_slider_entry(square_frame, "Offset", -300, 300, square_offset, 0.01, update_offset).pack(fill='x', pady=3)
create_slider_entry(square_frame, "Period", 0.1, 20, square_period, 0.01, update_period).pack(fill='x', pady=3)

# Waveform type selector
waveform_frame = ttk.LabelFrame(left_frame, text="Waveform Type", padding=(10,10))
waveform_frame.pack(fill='x', pady=(10, 0))
waveform_type = tk.StringVar(value=config.get("Wave", "square"))
ttk.Radiobutton(waveform_frame, text="Square", variable=waveform_type, value="square", command=update_waveform_type).pack(anchor='w')
ttk.Radiobutton(waveform_frame, text="Sine", variable=waveform_type, value="sine", command=update_waveform_type).pack(anchor='w')
ttk.Radiobutton(waveform_frame, text="Triangle", variable=waveform_type, value="triangle", command=update_waveform_type).pack(anchor='w')

# Plot setup
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 6), sharex=True)
line, = ax1.plot([], [], label="RPM", lw=2)
square_line, = ax1.plot([], [], label="Setpoint", linestyle="--", lw=2)
ax1.set_ylim(-310, 310)
ax1.set_ylabel("RPM")
ax1.set_title("RPM vs Setpoint")
ax1.grid()
ax1.legend()

pwm_line, = ax2.plot([], [], label="PWM", color='orange')
ax2.set_ylim(-255, 255)
ax2.set_xlabel("Samples")
ax2.set_ylabel("PWM")
ax2.set_title("PWM Output")
ax2.grid()
ax2.legend()

canvas_tk = FigureCanvasTkAgg(fig, master=right_frame)
canvas_tk.draw()
canvas_tk.get_tk_widget().pack(fill='both', expand=True)

ani = FuncAnimation(fig, animate, interval=100)
threading.Thread(target=pid_loop, daemon=True).start()
threading.Thread(target=update_setpoint, daemon=True).start()

# --- On close ---
def on_closing():
    try:
        ser.write(f"{0}\n".encode())
        ser.close()
    except: pass
    root.quit()
    root.destroy()
    sys.exit()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Menu bar
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
def export_data():
    filename = time.strftime("motor_data_%Y%m%d_%H%M%S.csv")
    try:
        with open(filename, 'w') as f:
            f.write("RPM,Setpoint,PWM\n")
            for r, s, p in zip(rpm_history, square_history, pwm_history):
                f.write(f"{r:.2f},{s:.2f},{p}\n")
        print(f"Data exported to {filename}")
    except Exception as e:
        print(f"Export failed: {e}")
file_menu.add_command(label="Export Data", command=export_data)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_closing)
menubar.add_cascade(label="File", menu=file_menu)
root.config(menu=menubar)

root.mainloop()

