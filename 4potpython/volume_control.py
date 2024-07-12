import serial.tools.list_ports
import pycaw
import tkinter as tk
from tkinter import ttk, messagebox
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioEndpointVolume, AudioDeviceState
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import json
import os
import pystray
from PIL import Image
import win32gui
import win32con
import warnings

CONFIG_FILE = "volume_control_config.json"

class VolumeControlApp:
    def __init__(self, master):
        self.master = master
        master.title("Volume Control")
        
        # Hide maximize button
        master.resizable(0, 0)
        master.overrideredirect(False)
        master.after(10, self.remove_maximize_button)

        self.arduino = None
        self.com_port = 'COM3'
        self.baud_rate = 9600
        self.reconnect_attempts = 0

        self.sessions = AudioUtilities.GetAllSessions()
        self.devices = AudioUtilities.GetSpeakers()

        self.create_widgets()
        self.load_config()

        if self.initialize_serial():
            self.update_volume()

        # Create system tray icon
        self.icon = self.create_tray_icon()

        # Bind close button to minimize to tray
        master.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def remove_maximize_button(self):
        hwnd = self.master.winfo_id()
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style = style & ~win32con.WS_MAXIMIZEBOX
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    def create_tray_icon(self):
        image = Image.open("volume_control.ico")
        menu = pystray.Menu(pystray.MenuItem('Show', self.show_window),
                            pystray.MenuItem('Exit', self.quit_window))
        icon = pystray.Icon("name", image, "Volume Control", menu)
        icon.run_detached()
        return icon

    def minimize_to_tray(self):
        self.master.withdraw()
        self.icon.visible = True

    def show_window(self):
        self.icon.visible = False
        self.master.deiconify()

    def quit_window(self):
        self.icon.stop()
        self.master.quit()

    def create_widgets(self):
        self.pot_controls = []
        self.refresh_audio_apps()

        for i in range(4):
            frame = ttk.Frame(self.master)
            frame.grid(row=i, column=0, padx=10, pady=10, sticky="w")

            label = ttk.Label(frame, text=f"Channel {i+1}:")
            label.grid(row=0, column=0, padx=5, pady=5)

            combobox = ttk.Combobox(frame, values=self.app_device_list)
            combobox.grid(row=0, column=1, padx=5, pady=5)
            combobox.set("Select an app or device")

            progress = ttk.Progressbar(frame, length=200, mode='determinate')
            progress.grid(row=0, column=2, padx=5, pady=5)

            volume_label = ttk.Label(frame, text="0%")
            volume_label.grid(row=0, column=3, padx=5, pady=5)

            self.pot_controls.append({
                'combobox': combobox,
                'progress': progress,
                'volume_label': volume_label
            })

        # Add refresh button
        self.refresh_button = ttk.Button(self.master, text="Refresh Audio Apps", command=self.refresh_audio_apps)
        self.refresh_button.grid(row=4, column=0, padx=10, pady=10)

        # Add save button
        self.save_button = ttk.Button(self.master, text="Save Configuration", command=self.save_config)
        self.save_button.grid(row=5, column=0, padx=10, pady=10)

        # Add COM port and baud rate entry fields
        com_frame = ttk.Frame(self.master)
        com_frame.grid(row=6, column=0, padx=10, pady=10, sticky="w")

        ttk.Label(com_frame, text="COM Port:").grid(row=0, column=0, padx=5, pady=5)
        self.com_entry = ttk.Entry(com_frame, width=10)
        self.com_entry.grid(row=0, column=1, padx=5, pady=5)
        self.com_entry.insert(0, self.com_port)

        ttk.Label(com_frame, text="Baud Rate:").grid(row=0, column=2, padx=5, pady=5)
        self.baud_entry = ttk.Entry(com_frame, width=10)
        self.baud_entry.grid(row=0, column=3, padx=5, pady=5)
        self.baud_entry.insert(0, str(self.baud_rate))

        ttk.Button(com_frame, text="Apply", command=self.apply_serial_settings).grid(row=0, column=4, padx=5, pady=5)

        # Add reconnect button
        self.reconnect_button = ttk.Button(self.master, text="Reconnect Serial", command=self.reconnect_serial)
        self.reconnect_button.grid(row=7, column=0, padx=10, pady=10)

    def apply_serial_settings(self):
        self.com_port = self.com_entry.get()
        self.baud_rate = int(self.baud_entry.get())
        if self.initialize_serial():
            messagebox.showinfo("Success", "Serial settings applied successfully.")
        else:
            messagebox.showerror("Error", "Failed to initialize serial connection. Please check your settings.")

    def initialize_serial(self):
        try:
            if self.arduino:
                self.arduino.close()
            self.arduino = serial.Serial(self.com_port, self.baud_rate)
            self.reconnect_attempts = 0
            return True
        except serial.SerialException as e:
            messagebox.showerror("Serial Connection Error", f"Failed to connect to {self.com_port}. Error: {str(e)}")
            return False

    def reconnect_serial(self):
        self.reconnect_attempts += 1
        print(f"Attempting to reconnect... (Attempt {self.reconnect_attempts})")

        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        if self.com_port not in available_ports:
            print(f"COM port {self.com_port} not found. Available ports: {available_ports}")
            self.master.after(5000, self.reconnect_serial)  # Retry after 5 seconds
            return
        
        if self.arduino:
            self.arduino.close()

        try:
            self.arduino = serial.Serial(self.com_port, self.baud_rate)
            messagebox.showinfo("Success", "Reconnected to the serial device successfully.")
            self.update_volume()  # Restart the volume update loop
        except serial.SerialException as e:
            print(f"Reconnection attempt {self.reconnect_attempts} failed: {str(e)}")
            self.master.after(5000, self.reconnect_serial)  # Retry after 5 seconds

    def refresh_audio_apps(self):
        self.sessions = AudioUtilities.GetAllSessions()
        app_names = ["Select an app"] + [s.Process.name() if s.Process else "System Sounds" for s in self.sessions]
        
        # Get all audio devices
        devices = AudioUtilities.GetAllDevices()
        device_names = ["Select a device"]

        # Filter only active (not disabled) playback devices
        active_devices = []
        for d in devices:
            try:
                if d.state == AudioDeviceState.Active:
                    active_devices.append(d.FriendlyName)
            except Exception as e:
                warnings.warn(f"Error accessing device: {e}")
                print(f"Problematic device: {d}")

        device_names.extend(active_devices)

        self.app_device_list = app_names + device_names

        # Update combobox values
        for control in self.pot_controls:
            current_value = control['combobox'].get()
            control['combobox']['values'] = self.app_device_list
            if current_value not in self.app_device_list:
                control['combobox'].set("Select an app or device")
            else:
                control['combobox'].set(current_value)

        print("Available playback devices in dropdown:", active_devices)

    def update_volume(self):
        if not self.arduino or not self.arduino.is_open:
            self.master.after(1000, self.update_volume)  # Check again after 1 second
            return

        try:
            if self.arduino.in_waiting:
                serial_data = self.arduino.readline().decode('utf-8').strip()
                print(f"Raw serial data: {serial_data}")  # Debug print

                if '|' not in serial_data:
                    print(f"Invalid data format: {serial_data}")
                    self.master.after(10, self.update_volume)
                    return

                pot_values = []
                for val in serial_data.split('|'):
                    try:
                        pot_values.append(int(val))
                    except ValueError:
                        print(f"Invalid value: {val}")

                if len(pot_values) == 4:
                    self.process_pot_values(pot_values)
                else:
                    print(f"Unexpected number of values: {len(pot_values)}")

        except serial.SerialException:
            print("Serial connection lost.")
            if self.arduino:
                self.arduino.close()
            self.arduino = None
            self.reconnect_serial()  # Trigger reconnect attempts

    def process_pot_values(self, pot_values):
        # Assuming pot_values contains the volume values for each channel
        for i, value in enumerate(pot_values):
            # Process volume control for each channel
            pass

    def save_config(self):
        # Save configuration to JSON file
        pass

    def load_config(self):
        # Load configuration from JSON file
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = VolumeControlApp(root)
    root.mainloop()
