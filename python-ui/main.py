# imports
import time
import serial
from pathlib import Path
import csv
import json

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

# variables
connections = []
reactors = []

# bioreactor class
class Bioreactor:

    def __init__(self, reactor_id):

        self.id = reactor_id
        self.time = 0
        self.fan_pwm = 0
        self.fan_rpm = 0
        self.pump_active = False
        self.pump_speed = 0
        self.pump_duration = 0
        self.temp = 0
        self.temp_target = 0
        self.od = 0
        #self.ph = 0
        #self.volume = 0
        self.history = []
        self.error_count = 0
        self.last_error = None
        self.last_valid_data_time = None

# connect to serial ports
def connect_serial():
    for i, port in enumerate(PORTS):
        try:
            ser = serial.Serial(port, BAUDRATE, timeout=1)
            connections.append(ser)
            reactors.append(Bioreactor(i + 1))
            print(f"Connected to {port}")
        except serial.SerialException:
            print(f"Could not connect to {port}")

# read data from serial ports
def serial_thread():
    while True:
        for ser, reactor in zip(connections, reactors):

            if ser.in_waiting == 0:
                continue

            try:
                line = ser.readline().decode("utf-8").strip() # one json msg
                data = json.loads(line) # json to python

                reactor.fan_pwm = data.get("Fan PWM", reactor.fan_pwm)
                reactor.fan_rpm = data.get("Fan RPM", reactor.fan_rpm)
                reactor.pump_active = data.get("Pump Active", reactor.pump_active)
                reactor.pump_speed = data.get("Pump Speed", reactor.pump_speed)
                reactor.pump_duration = data.get("Pump Duration", reactor.pump_duration)
                reactor.temp = data.get("Temperature", reactor.temp)
                reactor.temp_target = data.get("Temperature Target", reactor.temp_target)
                reactor.od = data.get("OD", reactor.od)
                #reactor.ph = data.get("pH", reactor.ph)
                #reactor.volume = data.get("Volume of Liquid", reactor.volume)

                reactor.time = time.time()

                reactor.history.append({
                    "time": reactor.time,
                    "temp": reactor.temp,
                    "od": reactor.od,
                    #"ph": reactor.ph, # no pH sensor yet 
                    #"volume": reactor.volume # need to write code for volume measurements + addition in arduino before we can add it to the history 
                })

                save_csv(reactor)

            except json.JSONDecodeError:
                print(f"Invalid JSON received: {line}")

            except Exception as e:
                print(f"Error reading reactor {reactor.id}: {e}")

        time.sleep(0.05)
        
# parse data from serial port
def parse_data(reactor_number, line):
    reactor = reactors[reactor_number]

    try:
        data = json.loads(line)

        reactor.fan_pwm = data.get("Fan PWM", reactor.fan_pwm)
        reactor.fan_rpm = data.get("Fan RPM", reactor.fan_rpm)
        reactor.pump_active = data.get("Pump Active", reactor.pump_active)
        reactor.pump_speed = data.get("Pump Speed", reactor.pump_speed)
        reactor.pump_duration = data.get("Pump Duration", reactor.pump_duration)
        reactor.temp = data.get("Temperature", reactor.temp)
        reactor.temp_target = data.get("Temperature Target", reactor.temp_target)
        reactor.od = data.get("OD", reactor.od)
        #reactor.ph = data.get("pH", reactor.ph)
        #reactor.volume = data.get("Volume of Liquid", reactor.volume)
        reactor.time = time()

        reactor.history.append({
            "time": reactor.time,
            "temp": reactor.temp,
            "od": reactor.od,
            #"ph": reactor.ph,
            #"volume": reactor.volume
        })

        save_csv(reactor)

    except json.JSONDecodeError:
        print(f"Invalid JSON from Reactor {reactor.id}: {line}")

# send command to bioreactor via serial port
def send_command(reactor_number,
                 temperature=None,
                 input_pump1=None,
                 input_pump2=None,
                 output_pump1=None,
                 stirring_fan=None):

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
        connections[reactor_number].write(msg.encode("utf-8"))

    except Exception as e:
        print(f"Failed to send command: {e}")

# update graphs with new data w every refresh
def update_graphs():

    for reactor in reactors:
        if reactor.history:
            latest = reactor.history[-1]

            print(
                f"R{reactor.id}: "
                f"T={latest['temp']}°C "
                f"OD={latest['od']} "
                #f"pH={latest['ph']} "
                #f"V={latest['volume']} mL"
            )

# update tkinter / other gui w every refresh
def update_gui():
    for reactor in reactors:
        print(
            f"Reactor {reactor.id}: "
            f"{reactor.temp:.2f}°C | "
            f"OD={reactor.od:.3f} | "
            #f"pH={reactor.ph:.2f}"
        )

# save data to CSV file
def save_csv(reactor):
    csv_path = Path(f"python-ui/reactor_{reactor.id}.csv")
    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "time",
                "temperature",
                "OD",
                #"pH",
                #"volume"
            ])

        writer.writerow([
            reactor.time,
            reactor.temp,
            reactor.od,
            #reactor.ph,
            #reactor.volume
        ])


if __name__ == "__main__":

    PORTS = ["COM8", "COM11"] # port numbers for the arduino serial connections

    print("Connecting to Arduinos...")
    connect_serial()

    if not connections:
        print("No Arduinos connected.")
        exit()

    print(f"Connected to {len(connections)} Arduino(s).")

    time.sleep(2)

    for i in range(len(connections)):
        send_command(
            reactor_number=i,
            temperature=37,
            stirring_fan=50
        )

    print("Listening for data... (Ctrl+C to stop)")

    try:
        while True:

            for i, ser in enumerate(connections): # check arduino for new data

                if ser.in_waiting > 0:

                    line = ser.readline().decode("utf-8").strip()

                    print(f"Reactor {i+1}: {line}")

                    parse_data(i, line)

            update_gui() # latest reactor values printed

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        for ser in connections:
            ser.close()

        print("Serial ports closed.")

