# py -m pip install pyserial

# imports

import time
import serial
import json
import threading
import tkinter as tk
from tkinter import ttk, simpledialog
import tkinter.messagebox

# constants

PORTS = [
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "COM10"
]

BAUDRATE = 115200

connections = []
reactors = []

# bioreactor class

class Bioreactor:

    def __init__(self, reactor_id):

        self.id = reactor_id
        self.time = 0

        self.temp = 0
        self.temp_target = 0
        self.od = 0

        self.pump_active = False
        self.pump_speed = 0

        self.fan_pwm = 0
        self.fan_rpm = 0

        self.history = []

        self.error_count = 0
        self.last_error = None
        self.last_valid_data_time = None
        self.connected = True

        self.targets = {
            "Temperature": 37.0,
            "Input Pump 1": 50,
            "Input Pump 2": 50,
            "Output Pump 1": 50
        }

# connecting to COM ports

def connect_serial():

    for i, port in enumerate(PORTS):

        try:
            ser = serial.Serial(
                port,
                BAUDRATE,
                timeout=1
            )

            connections.append(ser)
            reactors.append(Bioreactor(i + 1))

            print(f"Connected to {port}")

        except serial.SerialException:

            print(f"Could not connect to {port}")

# check for messages from Arduino

def serial_thread():

    while True:

        for i, ser in enumerate(connections):

            if ser.in_waiting > 0:

                try:

                    raw_line = ser.readline()
                    line = raw_line.decode("utf-8").strip()

                    parse_data(i, line)

                except UnicodeDecodeError:

                    reactors[i].error_count += 1
                    reactors[i].last_error = "Invalid UTF-8 data"

                except serial.SerialException as e:

                    reactors[i].connected = False
                    reactors[i].error_count += 1
                    reactors[i].last_error = str(e)

                except Exception as e:

                    reactors[i].error_count += 1
                    reactors[i].last_error = str(e)

        time.sleep(0.05)

# parse data from Arduino

def parse_data(reactor_number, line):

    if reactor_number < 0 or reactor_number >= len(reactors):

        print(f"Invalid reactor number: {reactor_number}")

        return

    reactor = reactors[reactor_number]

    try:

        if not line:
            raise ValueError("Empty serial message")

        data = json.loads(line)

        if not isinstance(data, dict):
            raise ValueError("JSON data is not a dictionary")

        if "Fan PWM" in data:
            reactor.fan_pwm = data["Fan PWM"]

        if "Fan RPM" in data:
            reactor.fan_rpm = data["Fan RPM"]

        if "Pump Active" in data:
            reactor.pump_active = data["Pump Active"]

        if "Pump Speed" in data:
            reactor.pump_speed = data["Pump Speed"]

        if "Temperature" in data:
            reactor.temp = float(data["Temperature"])

        if "Temperature Target" in data:
            reactor.temp_target = float(data["Temperature Target"])

        if "OD" in data:
            reactor.od = float(data["OD"])

        reactor.time = time.time()
        reactor.last_valid_data_time = reactor.time
        reactor.connected = True
        reactor.last_error = None

        reactor.history.append({
            "time": reactor.time,
            "temp": reactor.temp,
            "od": reactor.od
        })

    except json.JSONDecodeError:

        reactor.error_count += 1
        reactor.last_error = "Invalid JSON"

        print(
            f"[ERROR] Reactor {reactor.id}: "
            f"Invalid JSON: {line}"
        )

    except (ValueError, TypeError) as e:

        reactor.error_count += 1
        reactor.last_error = str(e)

        print(
            f"[ERROR] Reactor {reactor.id}: "
            f"Invalid data: {e}"
        )

# send commands to Arduino

def send_command(
    reactor_number,
    temperature=None,
    input_pump1=None,
    input_pump2=None,
    output_pump1=None,
    stirring_fan=None
):

    if reactor_number >= len(connections):

        print("Invalid reactor number.")

        return

    command = {}

    if temperature is not None:
        command["Temperature"] = temperature

    if input_pump1 is not None:
        command["Input Pump 1"] = input_pump1

    if input_pump2 is not None:
        command["Input Pump 2"] = input_pump2

    if output_pump1 is not None:
        command["Output Pump 1"] = output_pump1

    if stirring_fan is not None:
        command["Stirring Fan"] = stirring_fan

    try:

        msg = json.dumps(command) + "\n"

        connections[reactor_number].write(
            msg.encode("utf-8")
        )

    except Exception as e:

        print(f"Failed to send command: {e}")

# create dashboard

def create_dashboard(root):

    dashboard_frame = tk.Frame(
        root
    )

    dashboard_frame.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=20
    )

    dashboard_frame.grid_columnconfigure(0, weight=1)
    dashboard_frame.grid_columnconfigure(1, weight=1)
    dashboard_frame.grid_columnconfigure(2, weight=2)

    dashboard_frame.grid_rowconfigure(0, weight=1)
    dashboard_frame.grid_rowconfigure(1, weight=1)

    colors = {
        "background": "#F4F6F8",
        "card": "#FFFFFF",
        "navy": "#17324D",
        "blue": "#2F80ED",
        "green": "#27AE60",
        "orange": "#F2994A",
        "red": "#EB5757",
        "grey": "#D9DEE5",
        "dark_grey": "#5B6573"
    }

    root.configure(bg=colors["background"])

    style = ttk.Style()
    style.configure("TFrame", background=colors["background"])
    style.configure("Card.TFrame", background=colors["card"])
    style.configure(
        "TLabel",
        background=colors["background"],
        foreground=colors["navy"],
        font=("Arial", 10)
    )
    style.configure(
        "Card.TLabel",
        background=colors["card"],
        foreground=colors["navy"],
        font=("Arial", 10)
    )
    style.configure(
        "Title.TLabel",
        background=colors["navy"],
        foreground="white",
        font=("Arial", 22, "bold")
    )
    style.configure(
        "Subtitle.TLabel",
        background=colors["navy"],
        foreground="#DCE6F0",
        font=("Arial", 10)
    )
    style.configure(
        "Header.TLabel",
        background=colors["card"],
        foreground=colors["navy"],
        font=("Arial", 14, "bold")
    )
    style.configure(
        "Value.TLabel",
        background=colors["card"],
        foreground=colors["navy"],
        font=("Arial", 24, "bold")
    )
    style.configure(
        "Status.TLabel",
        background=colors["card"],
        foreground=colors["green"],
        font=("Arial", 10, "bold")
    )
    style.configure(
        "TNotebook",
        background=colors["background"],
        borderwidth=0
    )
    style.configure(
        "TNotebook.Tab",
        padding=(20, 10),
        font=("Arial", 10, "bold")
    )
    style.configure(
        "Accent.TButton",
        background=colors["blue"],
        foreground="white",
        font=("Arial", 10, "bold"),
        padding=8
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#2469BE")]
    )
    style.configure(
        "Danger.TButton",
        background=colors["red"],
        foreground="white",
        font=("Arial", 10, "bold"),
        padding=8
    )
    style.configure(
        "TButton",
        padding=7
    )

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=15, pady=15)

    dashboard_tab = ttk.Frame(notebook, padding=15)
    setup_tab = ttk.Frame(notebook, padding=15)
    spectrophotometer_tab = ttk.Frame(notebook, padding=15)

    notebook.add(dashboard_tab, text="Dashboard")
    notebook.add(setup_tab, text="OD Calibration")
    notebook.add(spectrophotometer_tab, text="Spectrophotometer")

    calibration_steps = {
        "blank": False,
        "vial": False,
        "reference": False
    }

    temperature_commands = {}

    def calibration_complete():
        return all(calibration_steps.values())

    def update_calibration_status():
        completed = sum(calibration_steps.values())

        if completed == 3:
            calibration_status.config(
                text="✓ OD CALIBRATION COMPLETE",
                foreground=colors["green"]
            )
        else:
            calibration_status.config(
                text=f"OD Calibration: {completed}/3 complete",
                foreground=colors["orange"]
            )

    def require_calibration():
        if calibration_complete():
            return True

        result = calibration_warning(root)

        if result == "calibrate":
            notebook.select(setup_tab)

        return False

    def collect_blank_od():
        print("Collecting OD of blank vial holder")
        calibration_steps["blank"] = True
        blank_od_button.config(
            state="disabled",
            text="✓ Blank OD collected"
        )
        update_calibration_status()

    def collect_vial_od():
        print("Collecting OD with empty vial")
        calibration_steps["vial"] = True
        vial_od_button.config(
            state="disabled",
            text="✓ Vial OD collected"
        )
        update_calibration_status()

    def reference_collection():
        print("Starting reference collection")
        calibration_steps["reference"] = True
        reference_button.config(
            state="disabled",
            text="✓ Reference collected"
        )
        update_calibration_status()

    header = tk.Frame(
        dashboard_tab,
        bg=colors["navy"],
        height=95
    )
    header.pack(fill="x", pady=(0, 15))
    header.pack_propagate(False)

    header_text = tk.Frame(header, bg=colors["navy"])
    header_text.pack(side="left", padx=25, pady=15)

    ttk.Label(
        header_text,
        text="BIOREACTOR DASHBOARD",
        style="Title.TLabel"
    ).pack(anchor="w")

    ttk.Label(
        header_text,
        # text="Monitor and control your connected bioreactors",
        style="Subtitle.TLabel"
    ).pack(anchor="w", pady=(3, 0))

    spectro_button = ttk.Button(
        header,
        text="SPECTROPHOTOMETER",
        style="TButton",
        command=lambda: notebook.select(spectrophotometer_tab)
    )
    spectro_button.pack(side="right", padx=25, pady=25)

    reactor_bar = tk.Frame(
        dashboard_tab,
        bg=colors["card"],
        padx=15,
        pady=10
    )
    reactor_bar.pack(fill="x", pady=(0, 15))

    tk.Label(
        reactor_bar,
        text="Current Reactor",
        bg=colors["card"],
        fg=colors["navy"],
        font=("Arial", 10, "bold")
    ).pack(side="left")

    reactor_choice = tk.StringVar(value="Reactor 1")

    reactor_menu = ttk.Combobox(
        reactor_bar,
        textvariable=reactor_choice,
        values=[f"Reactor {i + 1}" for i in range(len(PORTS))],
        state="readonly",
        width=15
    )
    reactor_menu.pack(side="left", padx=10)

    connection_status = tk.Label(
        reactor_bar,
        text="● NOT CONNECTED",
        bg=colors["card"],
        fg=colors["orange"],
        font=("Arial", 10, "bold")
    )
    connection_status.pack(side="left", padx=10)

    main_cards = tk.Frame(
        dashboard_tab,
        bg=colors["background"]
    )
    main_cards.pack(fill="x")

    readings_frame = tk.Frame(
        main_cards,
        bg=colors["card"],
        padx=20,
        pady=15
    )
    readings_frame.pack(
        side="left",
        fill="both",
        expand=True,
        padx=(0, 8)
    )

    ttk.Label(
        readings_frame,
        text="LIVE READINGS",
        style="Header.TLabel"
    ).pack(anchor="w")

    current_temp_label = ttk.Label(
        readings_frame,
        text="--.- °C",
        style="Value.TLabel"
    )
    current_temp_label.pack(anchor="w", pady=(15, 0))

    ttk.Label(
        readings_frame,
        text="Current Temperature",
        style="Card.TLabel"
    ).pack(anchor="w")

    current_od_label = ttk.Label(
        readings_frame,
        text="--",
        style="Value.TLabel"
    )
    current_od_label.pack(anchor="w", pady=(15, 0))

    ttk.Label(
        readings_frame,
        text="Optical Density",
        style="Card.TLabel"
    ).pack(anchor="w")

    pump_live_status = ttk.Label(
        readings_frame,
        text="Pumps: STOPPED",
        style="Status.TLabel"
    )
    pump_live_status.pack(anchor="w", pady=(15, 0))

    controls_frame = tk.Frame(
        main_cards,
        bg=colors["card"],
        padx=20,
        pady=15
    )
    controls_frame.pack(
        side="right",
        fill="both",
        expand=True,
        padx=(8, 0)
    )

    ttk.Label(
        controls_frame,
        text="CONTROLS",
        style="Header.TLabel"
    ).pack(anchor="w")

    # OD normalization setting
    od_normalized = tk.BooleanVar(value=False)

    od_checkbox = ttk.Checkbutton(
        controls_frame,
        text="OD is normalized",
        variable=od_normalized
    )
    od_checkbox.pack(anchor="w", pady=(10, 5))

    target_temperature = tk.DoubleVar(value=37.0)

    slider_warning = {"shown": False}

    def show_slider_warning():
        if slider_warning["shown"]:
            return False

        slider_warning["shown"] = True
        result = calibration_warning(root)

        if result == "calibrate":
            notebook.select(setup_tab)

        root.after(300, lambda: slider_warning.update({"shown": False}))
        return True

    def pump_power_changed(value):
        power = int(float(value))

        pump_power_label.config(
            text=f"Pump Power: {power}%"
        )

    def temperature_changed(value):
        temperature = float(value)

        temperature_label.config(
            text=f"Target Temperature: {temperature:.1f} °C"
        )

    def stop_pumps():
        print("STOP PUMPS")

        for reactor_index in range(len(connections)):
            send_command(
                reactor_index,
                input_pump1=0,
                input_pump2=0,
                output_pump1=0
            )

        pump_live_status.config(
            text="Pumps: STOPPED",
            foreground=colors["red"]
        )

    def start_pumps():
        power = pump_power.get()
  
        reactor_index = reactor_choice.get().split()[-1]

        if not reactor_index.isdigit():
            return

        reactor_index = int(reactor_index) - 1

        send_command(
            reactor_index,
            input_pump1=power,
            input_pump2=power,
            output_pump1=power
        )

        pump_live_status.config(
            text="Pumps: RUNNING",
            foreground=colors["green"]
        )

    def set_temperature():
        temperature = simpledialog.askfloat(
            "Set Temperature",
            "Enter target temperature (°C):",
            parent=root,
            minvalue=20,
            maxvalue=45
        )

        if temperature is None:
            return

        reactor_index = get_selected_reactor_index()

        if reactor_index is None:
            tkinter.messagebox.showwarning(
                "No Reactor Selected",
                "Please select a reactor first."
            )
            return

        target_temperature.set(temperature)

        temperature_label.config(
            text=f"Target Temperature: {temperature:.1f} °C"
        )

        reactors[reactor_index].targets["Temperature"] = temperature

        send_command(
            reactor_index,
            temperature=temperature
        )

        temperature_commands.setdefault(
            reactor_index,
            []
        ).append({
            "time": time.time(),
            "temperature": temperature
        })

        update_temperature_graph()

    pump_power = tk.IntVar(value=50)

    pump_power_label = ttk.Label(
        controls_frame,
        text="Pump Power: 50%",
        style="Card.TLabel"
    )
    pump_power_label.pack(anchor="w", pady=(15, 0))

    pump_slider = tk.Scale(
        controls_frame,
        from_=50,
        to=100,
        orient="horizontal",
        resolution=1,
        variable=pump_power,
        command=pump_power_changed,
        bg=colors["card"],
        fg=colors["navy"],
        highlightthickness=0
    )
    pump_slider.pack(
        fill="x",
        padx=5,
        pady=5
    )

    temperature_label = ttk.Label(
        controls_frame,
        text="Target Temperature",
        style="Card.TLabel"
    )
    temperature_label.pack(anchor="w", pady=(8, 0))

    temperature_slider = tk.Scale(
        controls_frame,
        from_=20,
        to=45,
        orient="horizontal",
        resolution=0.5,
        variable=target_temperature,
        command=temperature_changed,
        bg=colors["card"],
        fg=colors["navy"],
        highlightthickness=0
    )
    temperature_slider.pack(
        fill="x",
        padx=5,
        pady=5
    )

    temperature_button = ttk.Button(
        controls_frame,
        text="SET TEMPERATURE",
        style="TButton",
        command=set_temperature
    )
    temperature_button.pack(fill="x", pady=(5, 8))

    pump_button_frame = ttk.Frame(controls_frame)
    pump_button_frame.pack(fill="x")

    start_button = ttk.Button(
        pump_button_frame,
        text="START PUMPS",
        command=start_pumps, 
        style="TButton"
    )
    start_button.pack(side="left", fill="x", expand=True, padx=(0, 5))

    stop_button = ttk.Button(
        pump_button_frame,
        text="STOP PUMPS",
        style="TButton",
        command=stop_pumps
    )
    stop_button.pack(side="right", fill="x", expand=True, padx=(5, 0))

    graph_frame = tk.Frame(
        dashboard_tab,
        bg=colors["card"],
        padx=15,
        pady=10
    )
    graph_frame.pack(
        fill="both",
        expand=True,
        pady=(15, 0)
    )

    ttk.Label(
        graph_frame,
        text="TEMPERATURE",
        style="Header.TLabel"
    ).pack(anchor="w")

    try:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        temperature_figure = Figure(
            figsize=(8, 3.2),
            dpi=100
        )
        temperature_axis = temperature_figure.add_subplot(111)
        temperature_axis.set_xlabel("Time (s)")
        temperature_axis.set_ylabel("Temperature (°C)")
        temperature_axis.grid(True, alpha=0.25)

        temperature_canvas = FigureCanvasTkAgg(
            temperature_figure,
            master=graph_frame
        )
        temperature_canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )
    except ImportError:
        temperature_figure = None
        temperature_axis = None
        temperature_canvas = None

        ttk.Label(
            graph_frame,
            text="Install matplotlib with: py -m pip install matplotlib",
            style="Card.TLabel"
        ).pack(expand=True)

    def get_selected_reactor_index():
        value = reactor_choice.get().split()[-1]

        if value.isdigit():
            index = int(value) - 1

            if 0 <= index < len(reactors):
                return index

        return None

    def update_temperature_graph():
        if temperature_axis is None:
            return

        temperature_axis.clear()
        temperature_axis.set_xlabel("Time (s)")
        temperature_axis.set_ylabel("Temperature (°C)")
        temperature_axis.grid(True, alpha=0.25)

        reactor_index = get_selected_reactor_index()

        if reactor_index is None:
            temperature_canvas.draw_idle()
            return

        reactor = reactors[reactor_index]

        if reactor.history:
            start_time = reactor.history[0]["time"]

            x_values = [
                item["time"] - start_time
                for item in reactor.history
            ]

            y_values = [
                item["temp"]
                for item in reactor.history
            ]

            temperature_axis.plot(
                x_values,
                y_values,
                linewidth=2,
                label=f"Reactor {reactor_index + 1}"
            )

            temperature_axis.legend(loc="upper left")

            for command in temperature_commands.get(reactor_index, []):
                command_x = command["time"] - start_time

                if x_values and command_x >= x_values[0]:
                    temperature_axis.axvline(
                        command_x,
                        linestyle="--",
                        alpha=0.7
                    )

                    temperature_axis.text(
                        command_x,
                        temperature_axis.get_ylim()[1],
                        f" {command['temperature']:.1f}°C",
                        rotation=90,
                        verticalalignment="top"
                    )

        temperature_figure.tight_layout()
        temperature_canvas.draw_idle()

    def update_dashboard():
        reactor_index = get_selected_reactor_index()

        if reactor_index is not None:
            reactor = reactors[reactor_index]

            current_temp_label.config(
                text=f"{reactor.temp:.1f} °C"
            )

            current_od_label.config(
                text=f"{reactor.od:.3f}"
            )

            if reactor.connected:
                connection_status.config(
                    text="● CONNECTED",
                    fg=colors["green"]
                )
            else:
                connection_status.config(
                    text="● DISCONNECTED",
                    fg=colors["red"]
                )

            if reactor.pump_active:
                pump_live_status.config(
                    text="Pumps: RUNNING",
                    foreground=colors["green"]
                )
            else:
                pump_live_status.config(
                    text="Pumps: STOPPED",
                    foreground=colors["red"]
                )

        update_temperature_graph()
        root.after(500, update_dashboard)

    def reactor_changed(event=None):
        reactor_index = get_selected_reactor_index()

        if reactor_index is not None and reactor_index < len(reactors):
            target_temperature.set(
                reactors[reactor_index].targets["Temperature"]
            )

    reactor_menu.bind("<<ComboboxSelected>>", reactor_changed)

    # initial od setup

    calibration_header = tk.Frame(
        setup_tab,
        bg=colors["navy"],
        padx=20,
        pady=15
    )
    calibration_header.pack(fill="x", pady=(0, 15))

    tk.Label(
        calibration_header,
        text="OD CALIBRATION",
        bg=colors["navy"],
        fg="white",
        font=("Arial", 18, "bold")
    ).pack(anchor="w")

    tk.Label(
        calibration_header,
        # text="Complete all three steps before using the reactor controls.",
        bg=colors["navy"],
        fg="#DCE6F0",
        font=("Arial", 10)
    ).pack(anchor="w", pady=(3, 0))

    initial_setup_frame = tk.Frame(
        setup_tab,
        bg=colors["card"],
        padx=20,
        pady=20
    )
    initial_setup_frame.pack(fill="both", expand=True)

    # collect blank OD

    def collect_blank_od_setup():
        collect_blank_od()

    blank_od_button = ttk.Button(
        initial_setup_frame,
        text="Collect OD of blank vial with no vial (nothing in the vial holder)",
        command=collect_blank_od_setup
    )
    blank_od_button.pack(
        fill="x",
        pady=8
    )

    # collect OD with vial

    def collect_vial_od_setup():
        collect_vial_od()

    vial_od_button = ttk.Button(
        initial_setup_frame,
        text="Collect OD with vial inside bioreactor with nothing in the vial",
        command=collect_vial_od_setup
    )
    vial_od_button.pack(
        fill="x",
        pady=8
    )

    # reference collection

    def reference_collection_setup():
        reference_collection()

    reference_button = ttk.Button(
        initial_setup_frame,
        text="Reference Collection",
        command=reference_collection_setup
    )
    reference_button.pack(
        fill="x",
        pady=8
    )

    calibration_status = tk.Label(
        initial_setup_frame,
        text="OD Calibration: 0/3 complete",
        bg=colors["card"],
        fg=colors["orange"],
        font=("Arial", 12, "bold")
    )
    calibration_status.pack(
        pady=20
    )

    ttk.Button(
        initial_setup_frame,
        text="BACK TO DASHBOARD",
        command=lambda: notebook.select(dashboard_tab)
    ).pack(pady=10)

    spectro_header = tk.Frame(
        spectrophotometer_tab,
        bg=colors["navy"],
        padx=20,
        pady=20
    )
    spectro_header.pack(fill="x", pady=(0, 15))

    tk.Label(
        spectro_header,
        text="SPECTROPHOTOMETER",
        bg=colors["navy"],
        fg="white",
        font=("Arial", 20, "bold")
    ).pack(anchor="w")

    tk.Label(
        spectro_header,
        # text="Collect and view spectrophotometer measurements",
        bg=colors["navy"],
        fg="#DCE6F0",
        font=("Arial", 10)
    ).pack(anchor="w", pady=(3, 0))

    spectro_content = tk.Frame(
        spectrophotometer_tab,
        bg=colors["card"],
        padx=30,
        pady=30
    )
    spectro_content.pack(fill="both", expand=True)

    spectro_reading_label = tk.Label(
        spectro_content,
        text="--",
        bg=colors["card"],
        fg=colors["navy"],
        font=("Arial", 32, "bold")
    )
    spectro_reading_label.pack(pady=(20, 5))

    tk.Label(
        spectro_content,
        text="Spectrophotometer Reading",
        bg=colors["card"],
        fg=colors["dark_grey"],
        font=("Arial", 11)
    ).pack()

    def collect_spectrophotometer_od():
        print("Collecting spectrophotometer OD")
        spectro_reading_label.config(text="Waiting... (insert spectrophotometer od collection code here)")

    ttk.Button(
        spectro_content,
        text="COLLECT OD",
        style="TButton",
        command=collect_spectrophotometer_od
    ).pack(fill="x", pady=25)

    ttk.Button(
        spectro_content,
        text="BACK TO DASHBOARD",
        command=lambda: notebook.select(dashboard_tab)
    ).pack()

    update_calibration_status()
    update_dashboard()


# main

if __name__ == "__main__":

    root = tk.Tk()

    root.title("Bioreactor Dashboard")
    root.geometry("1100x800")
    root.minsize(900, 700)

    connect_serial()

    if connections:
        threading.Thread(
            target=serial_thread,
            daemon=True
        ).start()

    create_dashboard(root)

    root.mainloop()
