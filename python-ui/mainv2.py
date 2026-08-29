import tkinter as tk
from tkinter import ttk

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
