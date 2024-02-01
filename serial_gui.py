import serial
import csv
import simplekml
import shutil
import os
from datetime import datetime
import tkinter as tk
import threading

# Serial port configuration
port = "COM4"  # Change this to your Arduino's serial port
baud_rate = 9600

# Create the KML File with certain settings
def create_kml():
    kml = simplekml.Kml()
    linestring = kml.newlinestring(name="Vila2Sat_Track")
    linestring.style.linestyle.color = simplekml.Color.red
    linestring.style.linestyle.width = 4
    linestring.altitudemode = simplekml.AltitudeMode.absolute
    return kml, linestring

# Function that updates the kml
def update_kml(kml, linestring, coordinates, last_coordinate):
    linestring.coords = coordinates
    linestring.altitudemode = simplekml.AltitudeMode.absolute
    linestring.extrude = 0
    linestring.tessellate = 0

    lookat = simplekml.LookAt(longitude=last_coordinate[0],
                              latitude=last_coordinate[1],
                              altitude=last_coordinate[2] + 10,
                              heading=0,
                              tilt=45,
                              range=20,
                              altitudemode=simplekml.AltitudeMode.absolute)
    
    kml.document.lookat = lookat
    kml.save("live_track.kml")

def is_csv_empty(file_path):
    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header
        return not any(reader)  # Check if there's any data after the header

def load_existing_data(csv_file):
    coordinates = []
    if os.path.exists(csv_file) and not is_csv_empty(csv_file):
        with open(csv_file, 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                try:
                    lat, lon, alt = float(row[4]), float(row[5]), float(row[3])
                    coordinates.append((lon, lat, alt))
                except ValueError:
                    continue
    return coordinates

def create_backup_files(csv_file, kml_file):
    backup_folder = 'backup'
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_csv_file = os.path.join(backup_folder, f'{timestamp}_{csv_file}')
    backup_kml_file = os.path.join(backup_folder, f'{timestamp}_live_track.kml')

    if os.path.exists(csv_file):
        shutil.copy(csv_file, backup_csv_file)
    if os.path.exists("live_track.kml"):
        shutil.copy("live_track.kml", backup_kml_file)

    return backup_csv_file, backup_kml_file

def update_backup_files(backup_csv_file, backup_kml_file):
    shutil.copy("output.csv", backup_csv_file)
    shutil.copy("live_track.kml", backup_kml_file)

def parse_data(data_line):
    if "Time=" in data_line:
        return "Time", data_line.split("Time=")[-1].strip()
    elif "Temperature=" in data_line:
        return "Temperature", data_line.split("Temperature=")[-1].strip()
    elif "Pressure=" in data_line:
        return "Pressure", data_line.split("Pressure=")[-1].strip()
    elif "Altitude=" in data_line:
        return "Altitude", data_line.split("Altitude=")[-1].strip()
    elif "Latitude=" in data_line:
        return "Latitude", data_line.split("Latitude=")[-1].strip()
    elif "Longitude=" in data_line:
        return "Longitude", data_line.split("Longitude=")[-1].strip()
    return None, None

def add_data_to_text_widget(text_widget, data):
    text_widget.config(state=tk.NORMAL)  # Temporarily enable the widget to modify it
    text_widget.insert(tk.END, data + '\n')  # Add data
    text_widget.see(tk.END)  # Scroll to the bottom
    text_widget.config(state=tk.DISABLED)  # Disable the widget again

def add_line_text_widget(text_widget):
    text_widget.config(state=tk.NORMAL)  # Temporarily enable the widget to modify it
    text_widget.insert(tk.END, '---------------\n')  # Add line
    text_widget.see(tk.END)  # Scroll to the bottom
    text_widget.config(state=tk.DISABLED)  # Disable the widget again

# CSV file configuration
csv_file = "output.csv"
csv_headers = ["Time", "Temperature", "Pressure", "Altitude", "Latitude", "Longitude"]

def read_serial_data(text_widget, stop_event, ser):
    kml, linestring = create_kml()
    coordinates = load_existing_data(csv_file)
    backup_csv_file, backup_kml_file = create_backup_files(csv_file, "live_track.kml")

    # Initialize sensor values
    time_value = None
    temperature_value = None
    pressure_value = None
    altitude_value = None
    latitude_value = None
    longitude_value = None

    try:
        while not stop_event.is_set():
            if ser.in_waiting > 0:
                data_line = ser.readline().decode('utf-8').rstrip()
                #print("Received data:", data_line)  # Debug print
                add_data_to_text_widget(text_widget, data_line)

                sensor_type, sensor_value = parse_data(data_line)
                # Assign the sensor values based on sensor_type
                if sensor_type == "Time":
                    time_value = sensor_value
                elif sensor_type == "Temperature":
                    temperature_value = sensor_value
                elif sensor_type == "Pressure":
                    pressure_value = sensor_value
                elif sensor_type == "Altitude":
                    altitude_value = sensor_value
                elif sensor_type == "Latitude":
                    latitude_value = sensor_value
                elif sensor_type == "Longitude":
                    longitude_value = sensor_value

                if all(v is not None for v in [time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value]):
                    new_coords = (float(longitude_value), float(latitude_value), float(altitude_value))
                    coordinates.append(new_coords)
                    #print("Updating KML...") #Debug
                    update_kml(kml, linestring, coordinates, new_coords)

                    # Append data to CSV file
                    #print("Appending to CSV...") #Debug
                    with open(csv_file, 'a', newline='') as f:
                        csv_writer = csv.writer(f)
                        csv_writer.writerow([time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value])

                    #print("Updating backup files...") #Debug
                    update_backup_files(backup_csv_file, backup_kml_file)

                    # Reset the values after writing to the CSV
                    time_value = temperature_value = pressure_value = altitude_value = latitude_value = longitude_value = None
                    add_line_text_widget(text_widget)
    except serial.SerialException as e:
        add_data_to_text_widget(text_widget, f"Serial error: {e}\n")
    except Exception as e:
        add_data_to_text_widget(text_widget, f"Error: {e}\n")
        print("Error:", e)  # Debug print
    finally:
        if ser.is_open:
            ser.close()  # Close the serial port when done



# Function to handle stop reading
def stop_reading(stop_event):
    stop_event.set()  # Signal the thread to stop


# Function to handle start reading
def start_reading(text_widget, stop_event):
    try:
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(csv_file):
            with open(csv_file, 'w', newline='') as f:
                csv_writer = csv.writer(f)
                csv_writer.writerow(csv_headers)

        # Create an initial KML file if it doesn't exist
        if not os.path.exists("live_track.kml"):
            kml, _ = create_kml()
            kml.save("live_track.kml")

        # Initialize the serial port
        ser = serial.Serial(port, baud_rate, timeout=1)
        stop_event.clear()
        threading.Thread(target=read_serial_data, args=(text_widget, stop_event, ser), daemon=True).start()
    except serial.SerialException as e:
        add_data_to_text_widget(text_widget, f"Serial error: {e}")
    except Exception as e:
        add_data_to_text_widget(text_widget, f"Error: {e}")

# Function to reset CSV
def reset_csv(text_widget):
    try:
        if os.path.exists(csv_file):
            os.remove(csv_file)
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(csv_headers)
        add_data_to_text_widget(text_widget, "CSV file has been reset.\n")
    except Exception as e:
        add_data_to_text_widget(text_widget, f"Error resetting CSV file: {e}\n")


# Tkinter UI setup
def setup_ui():
    root = tk.Tk()
    root.title("Vila2Sat Serial GUI")
    root.state('zoomed')

    # Top frame for buttons
    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X, pady=20)

    # Frame for Start and Stop buttons in the center
    center_frame = tk.Frame(top_frame)
    center_frame.pack(side=tk.TOP)

    # Text widget in the remaining space
    text_widget = tk.Text(root, state=tk.DISABLED)
    text_widget.pack(expand=True, fill=tk.BOTH)

    # Event object to control the reading thread
    stop_event = threading.Event()

    # Start button
    start_button = tk.Button(top_frame, text="Start Reading", command=lambda: start_reading(text_widget, stop_event))
    start_button.pack(side=tk.LEFT, padx=5)

    # Stop button
    stop_button = tk.Button(top_frame, text="Stop Reading", command=lambda: stop_reading(stop_event))
    stop_button.pack(side=tk.LEFT, padx=5)

    # Reset button aligned to the right and colored red
    reset_button = tk.Button(top_frame, text="Reset CSV", command=lambda: reset_csv(text_widget), bg='red', fg='white')
    reset_button.pack(side=tk.RIGHT, padx=10)

    root.mainloop()


if __name__ == "__main__":
    setup_ui()
