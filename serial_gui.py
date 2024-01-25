import serial
import csv
import simplekml
import shutil
import os
from datetime import datetime
import tkinter as tk
import threading

# Serial port configuration
port = "COM3"  # Change this to your Arduino's serial port
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

    #Lookat config, used to set how the camera looks at the coordinates of the cansat.
    lookat = simplekml.LookAt(longitude=last_coordinate[0],
                              latitude=last_coordinate[1],
                              altitude=last_coordinate[2] + 10,
                              heading=0,
                              tilt=45,
                              range=20,
                              altitudemode=simplekml.AltitudeMode.absolute)
    
    kml.document.lookat = lookat # add the lookat falues from earlier to the kml document
    kml.save("live_track.kml") # save the kml file

# Check if the csv file is empty
def is_csv_empty(file_path):
    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header
        return not any(reader)  # Check if there's any data after the header

#load existing csv data if the csv file exists and add them to the kml file.
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

# a backup system just in case.
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

# function update the backup files
def update_backup_files(backup_csv_file, backup_kml_file):
    shutil.copy("output.csv", backup_csv_file)
    shutil.copy("live_track.kml", backup_kml_file)

# function to parse the incoming serial data coming from the cansat
# the data is sent like "Temperature= 25" and it strips the "Temperature= " & saves just the numeric value into the temperature row in the csv file
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

#Fuction to add the incoming serial data to the text field/widget in the tkinter gui
def add_data_to_text_widget(text_widget, data):
    text_widget.config(state=tk.NORMAL)  # Temporarily enable the widget to modify it
    text_widget.insert(tk.END, data + '\n')  # Add data
    text_widget.see(tk.END)  # Scroll to the bottom
    text_widget.config(state=tk.DISABLED)  # Disable the widget again

# CSV file configuration
csv_file = "output.csv"
csv_headers = ["Time", "Temperature", "Pressure", "Altitude", "Latitude", "Longitude"]

#fuction to start reading the serial data
def read_serial_data(text_widget, stop_event):
    kml, linestring = create_kml()
    coordinates = load_existing_data(csv_file)
    backup_csv_file, backup_kml_file = create_backup_files(csv_file, "live_track.kml")

    try: #try and except to print an error int the text widget if something's wrong with the serial reader
        ser = serial.Serial(port, baud_rate, timeout=1)
        with ser, open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(csv_headers)

            # Initialize variables that store the values of the sensor & gps dta.
            time_value = None
            temperature_value = None
            pressure_value = None
            altitude_value = None
            latitude_value = None
            longitude_value = None

            while not stop_event.is_set():
                if ser.in_waiting > 0:
                    data_line = ser.readline().decode('utf-8').rstrip()
                    add_data_to_text_widget(text_widget, data_line)

                sensor_type, sensor_value = parse_data(data_line)
                    #Assign the sensor values
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

                # Make sure these values aren't none/null so that it doesn't fuck up anything
                if time_value is not None and temperature_value is not None and pressure_value is not None and altitude_value is not None and latitude_value is not None and longitude_value is not None:
                    altitude_value_float = float(altitude_value)
                    new_coords = (float(longitude_value), float(latitude_value), altitude_value_float)
                    coordinates.append(new_coords)  # Altitude is 0

                    # Update KML
                    update_kml(kml, linestring, coordinates, new_coords)
                        
                    # Open CSV, append data, close CSV
                    with open(csv_file, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value])
                        
                    # Print data
                    print("Data processed and saved")

                    # Update backup files
                    update_backup_files(backup_csv_file, backup_kml_file)

                    # Print the amazing values
                    print("-----------------------")
                    print(f"Time: {time_value}, Temperature: {temperature_value}, Pressure: {pressure_value}, Altitude: {altitude_value}") #Print seperate lines so its more clear in the console aswell ig
                    print(f"Time: {time_value}, Latitude: {latitude_value}, Longitude: {longitude_value}")
                    print("-----------------------")
                    
                    # Reset the values after writing to the CSV
                    time_value = None
                    temperature_value = None
                    pressure_value = None
                    altitude_value = None
                    latitude_value = None
                    longitude_value = None

                    # Update the backup files
                    update_backup_files(backup_csv_file, backup_kml_file)

    except serial.SerialException as e:
        add_data_to_text_widget(text_widget, f"Serial error: {e}")
    except Exception as e:
        add_data_to_text_widget(text_widget, f"Error: {e}")


# function to reset the csv file with the button
def reset_csv():
    global csv_file, csv_headers
    if os.path.exists(csv_file):
        os.remove(csv_file)
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)

# Tkinter UI setup
def setup_ui():
    root = tk.Tk()
    root.title("Vila2Sat Serial GUI")

    # Open in full-screen mode
    if os.name == 'nt':  # For Windows
        root.state('zoomed')
    else:  # For MacOS and Linux
        root.attributes('-fullscreen', True)

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

    # Start and Stop buttons
    start_button = tk.Button(center_frame, text="Start Reading", command=lambda: threading.Thread(target=read_serial_data, args=(text_widget, stop_event), daemon=True).start())
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = tk.Button(center_frame, text="Stop Reading", command=lambda: stop_event.set())
    stop_button.pack(side=tk.LEFT, padx=5)

    # Reset button aligned to the right
    reset_button = tk.Button(top_frame, text="Reset CSV", command=reset_csv, bg='red', fg='white')
    reset_button.pack(side=tk.RIGHT, padx=10)

    root.mainloop()


if __name__ == "__main__":
    setup_ui()
