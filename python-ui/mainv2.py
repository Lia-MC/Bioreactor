# py -m pip install pyserial

# imports

import time
import serial
import json
import threading
import tkinter as tk
from tkinter import ttk

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

    # initial od setup

    initial_setup_frame = ttk.LabelFrame(
        root,
        text="Initial Setup",
        padding=15
    )

    initial_setup_frame.pack(
        fill="x",
        padx=30,
        pady=(25, 10)
    )

    # collect blank OD

    def collect_blank_od():
        print("Collecting OD of blank vial holder")
        # more code goes here


    blank_od_button = ttk.Button(
        initial_setup_frame,
        text="Collect OD of blank vial with no vial (nothing in the vial holder)",
        command=collect_blank_od
    )

    blank_od_button.pack(
        fill="x",
        pady=5
    )

    # collect OD with vial

    def collect_vial_od():
        print("Collecting OD with empty vial")
        # more code goes here


    vial_od_button = ttk.Button(
        initial_setup_frame,
        text="Collect OD with vial inside bioreactor with nothing in the vial",
        command=collect_vial_od
    )

    vial_od_button.pack(
        fill="x",
        pady=5
    )


    # reference collection

    def reference_collection():
        print("Starting reference collection")
        # more code goes here


    reference_button = ttk.Button(
        initial_setup_frame,
        text="Reference Collection",
        command=reference_collection
    )

    reference_button.pack(
        fill="x",
        pady=5
    )



    # pump control

    pump_power = tk.IntVar(value=50)


    def pump_power_changed(value):

        power = int(float(value))

        pump_power_label.config(
            text=f"Pump Power: {power}%"
        )


    def stop_pumps():

        print("STOP PUMPS")

        pump_status.config(
            text="Pumps: STOPPED"
        )

    # pump controls

    pump_frame = ttk.LabelFrame(
        root,
        text="Pump Controls",
        padding=15
    )

    pump_frame.pack(
        fill="x",
        padx=30,
        pady=10
    )


    # stop button

    stop_button = ttk.Button(
        pump_frame,
        text="STOP PUMPS",
        command=stop_pumps
    )

    stop_button.pack(
        pady=(0, 15)
    )


    # pump power label

    pump_power_label = ttk.Label(
        pump_frame,
        text="Pump Power: 50%"
    )

    pump_power_label.pack()


    # pump power slider

    pump_slider = tk.Scale(
        pump_frame,
        from_=50,
        to=100,
        orient="horizontal",
        resolution=1,
        variable=pump_power,
        command=pump_power_changed
    )

    pump_slider.pack(
        fill="x",
        padx=20,
        pady=10
    )


    # pump range labels

    pump_range_frame = ttk.Frame(pump_frame)

    pump_range_frame.pack(
        fill="x",
        padx=20
    )

    ttk.Label(
        pump_range_frame,
        text="50%"
    ).pack(side="left")

    ttk.Label(
        pump_range_frame,
        text="100%"
    ).pack(side="right")


    # pump status

    pump_status = ttk.Label(
        pump_frame,
        text="Pumps: READY"
    )

    pump_status.pack(
        pady=(10, 0)
    )


    # temperature graph placeholder

    temperature_frame = ttk.LabelFrame(
        root,
        text="Temperature",
        padding=10
    )

    temperature_frame.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=10
    )


    temperature_placeholder = ttk.Label(
        temperature_frame,
        text=(
            "temp graph will be added here"
        ),
        justify="center"
    )

    temperature_placeholder.pack(
        expand=True
    )


# main

if __name__ == "__main__":

    root = tk.Tk()

    root.title("Bioreactor Dashboard")
    root.geometry("900x700")

    create_dashboard(root)

    root.mainloop()
