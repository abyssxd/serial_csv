import serial
import csv
import simplekml
import shutil
import os
from datetime import datetime
import tkinter as tk
import threading
import mysql.connector
from mysql.connector import Error
import time

# Serial port configuration
port = "COM4"  # Change this to your Arduino's serial port
baud_rate = 9600

# MySQL database configuration
mysql_config = {
    'host': 'localhost',
    'database': 'pogmc_cansat',
    'user': 'pogmc_cansat',
    'password': 'fakePassword12'
}

def rename_old_table_and_create_new(connection):
    cursor = connection.cursor()
    epoch_time = str(int(time.time()))
    new_table_name = "sensor_data_" + epoch_time
    
    # Check if the old table exists and rename it
    cursor.execute("SHOW TABLES LIKE 'sensor_data'")
    result = cursor.fetchone()
    if result:
        rename_query = f"RENAME TABLE sensor_data TO {new_table_name}"
        cursor.execute(rename_query)
        print(f"Old table renamed to {new_table_name}")
    
    # Create a new sensor_data table with the necessary schema
    create_table_query = """
    CREATE TABLE sensor_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        Time VARCHAR(255),
        Temperature DOUBLE,
        Pressure DOUBLE,
        Altitude DOUBLE,
        Latitude DOUBLE,
        Longitude DOUBLE,
        gps_altitude DOUBLE,
        gps_sats INT,
        gyro_x DOUBLE,
        gyro_y DOUBLE,
        gyro_z DOUBLE,
        gyro_acc_x DOUBLE,
        gyro_acc_y DOUBLE,
        gyro_acc_z DOUBLE,
        gyro_temp DOUBLE,
        bmp_status INT,
        gps_status INT,
        gyro_status INT,
        apc_status INT,
        servo_status INT,
        servo_rotation DOUBLE,
        sd_status INT
    )
    """
    cursor.execute(create_table_query)
    print("New sensor_data table created.")

    cursor.close()

# Function to connect to MySQL database
def connect_to_mysql():
    try:
        connection = mysql.connector.connect(**mysql_config)
        if connection.is_connected():
            print("Connected to MySQL database")
            rename_old_table_and_create_new(connection)
            return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

# Function to insert data into MySQL database
def insert_data_to_mysql(connection, data):
    try:
        cursor = connection.cursor()
        insert_query = "INSERT INTO sensor_data (Time, Temperature, Pressure, Altitude, Latitude, Longitude, gps_altitude, gps_sats, gyro_x, gyro_y, gyro_z, gyro_acc_z, gyro_temp, bmp_status, gps_status, gyro_status, apc_status, servo_status, servo_rotation, sd_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_query, data)
        connection.commit()
        cursor.close()
        print("Data inserted into MySQL database")
    except Error as e:
        print(f"Error inserting data into MySQL database: {e}")

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
    shutil.copy("sheet.csv", backup_csv_file)
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
    elif "gps_sats=" in data_line:
        return "gps_sats", data_line.split("gps_sats=")[-1].strip()
    elif "gps_sats=" in data_line:
        return "gps_sats", data_line.split("gps_sats=")[-1].strip()
    elif "gps_altitude=" in data_line:
        return "gps_altitude", data_line.split("gps_altitude=")[-1].strip()
    elif "gyro_x=" in data_line:
        return "gyro_x", data_line.split("gyro_x=")[-1].strip()
    elif "gyro_y=" in data_line:
        return "gyro_y", data_line.split("gyro_y=")[-1].strip()
    elif "gyro_z=" in data_line:
        return "gyro_z", data_line.split("gyro_z=")[-1].strip()
    elif "gyro_acc_x=" in data_line:
        return "gyro_acc_x", data_line.split("gyro_acc_x=")[-1].strip()
    elif "gyro_acc_y=" in data_line:
        return "gyro_acc_y", data_line.split("gyro_acc_y=")[-1].strip()
    elif "gyro_acc_z=" in data_line:
        return "gyro_acc_z", data_line.split("gyro_acc_z=")[-1].strip()
    elif "gyro_temp=" in data_line:
        return "gyro_temp", data_line.split("gyro_temp=")[-1].strip()
    elif "bmp_status=" in data_line:
        return "bmp_status", data_line.split("bmp_status=")[-1].strip()
    elif "gps_status=" in data_line:
        return "gps_status", data_line.split("gps_status=")[-1].strip()
    elif "gyro_status=" in data_line:
        return "gyro_status", data_line.split("gyro_status=")[-1].strip()
    elif "apc_status=" in data_line:
        return "apc_status", data_line.split("apc_status=")[-1].strip()
    elif "servo_status=" in data_line:
        return "servo_status", data_line.split("servo_status=")[-1].strip()
    elif "servo_rotation=" in data_line:
        return "servo_rotation", data_line.split("servo_rotation=")[-1].strip()
    elif "sd_status=" in data_line:
        return "sd_status", data_line.split("sd_status=")[-1].strip()
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
csv_file = "sheet.csv"
csv_headers = ["Time", "Temperature", "Pressure", "Altitude", "Latitude", "Longitude", "gps_altitude", "gps_sats", "gyro_x", "gyro_y", "gyro_z", "gyro_acc_x", "gyro_acc_y", "gyro_acc_z", "gyro_temp", "bmp_status", "gps_status", "gyro_status", "apc_status", "servo_status", "servo_rotation", "sd_status"]

def read_serial_data(text_widget, stop_event, ser):
    kml, linestring = create_kml()
    coordinates = load_existing_data(csv_file)
    backup_csv_file, backup_kml_file = create_backup_files(csv_file, "live_track.kml")

    #Connect to mysql database
    mysql_connection = connect_to_mysql()

    # Initialize sensor values
    time_value = temperature_value = pressure_value = altitude_value = latitude_value = longitude_value = gps_altitude = gps_sats = gyro_x_value = gyro_y_value = gyro_z_value = gyro_acc_x_value = gyro_acc_y_value = gyro_acc_z_value = gyro_temp_value = bmp_status_value = gps_status_value = gyro_status_value = apc_status_value = servo_status_value = servo_rotation_value = sd_status_value = None

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
                elif sensor_type == "gps_altitude":
                    gps_altitude = sensor_value
                elif sensor_type == "gps_sats":
                    gps_sats = sensor_value
                elif sensor_type == "gyro_x":
                    gyro_x_value = sensor_value
                elif sensor_type == "gyro_y":
                    gyro_y_value = sensor_value
                elif sensor_type == "gyro_z":
                    gyro_z_value = sensor_value
                elif sensor_type == "gyro_acc_x":
                    gyro_acc_x_value = sensor_value
                elif sensor_type == "gyro_acc_y":
                    gyro_acc_y_value = sensor_value
                elif sensor_type == "gyro_acc_z":
                    gyro_acc_z_value = sensor_value
                elif sensor_type == "gyro_temp":
                    gyro_temp_value = sensor_value
                elif sensor_type == "bmp_status":
                    bmp_status_value = sensor_value
                elif sensor_type == "gps_status":
                    gps_status_value = sensor_value
                elif sensor_type == "gyro_status":
                    gyro_status_value = sensor_value
                elif sensor_type == "apc_status":
                    apc_status_value = sensor_value
                elif sensor_type == "servo_status":
                    servo_status_value = sensor_value
                elif sensor_type == "servo_rotation":
                    servo_rotation_value = sensor_value
                elif sensor_type == "sd_status":
                    sd_status_value = sensor_value

                if all(v is not None for v in [time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value, gps_altitude, gps_sats, gyro_x_value, gyro_y_value, gyro_z_value, gyro_acc_x_value, gyro_acc_y_value, gyro_acc_z_value, gyro_temp_value, bmp_status_value, gps_status_value, gyro_status_value, apc_status_value, servo_status_value, servo_rotation_value, sd_status_value]):
                    new_coords = (float(longitude_value), float(latitude_value), float(altitude_value))
                    coordinates.append(new_coords)
                    #print("Updating KML...") #Debug
                    update_kml(kml, linestring, coordinates, new_coords)


                # Insert data into MySQL database
                data_for_mysql = (time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value, gps_altitude, gps_sats, gyro_x_value, gyro_y_value, gyro_z_value, gyro_acc_x_value, gyro_acc_y_value, gyro_acc_z_value, gyro_temp_value, bmp_status_value, gps_status_value, gyro_status_value, apc_status_value, servo_status_value, servo_rotation_value, sd_status_value)
                if mysql_connection:
                    insert_data_to_mysql(mysql_connection, data_for_mysql)

                    # Append data to CSV file
                    #print("Appending to CSV...") #Debug
                    with open(csv_file, 'a', newline='') as f:
                        csv_writer = csv.writer(f)
                        csv_writer.writerow([time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value, gps_altitude, gps_sats, gyro_x_value, gyro_y_value, gyro_z_value, gyro_acc_x_value, gyro_acc_y_value, gyro_acc_z_value, gyro_temp_value, bmp_status_value, gps_status_value, gyro_status_value, apc_status_value, servo_status_value, servo_rotation_value, sd_status_value])

                    #print("Updating backup files...") #Debug
                    update_backup_files(backup_csv_file, backup_kml_file)

                    # Reset the values after writing to the CSV
                    time_value = temperature_value = pressure_value = altitude_value = latitude_value = longitude_value = gps_altitude = gps_sats = gyro_x_value = gyro_y_value = gyro_z_value = gyro_acc_x_value = gyro_acc_y_value = gyro_acc_z_value = gyro_temp_value = bmp_status_value = gps_status_value = gyro_status_value = apc_status_value = servo_status_value = servo_rotation_value = sd_status_value = None


                    add_line_text_widget(text_widget)
    except serial.SerialException as e:
        add_data_to_text_widget(text_widget, f"Serial error: {e}\n")
    except Exception as e:
        add_data_to_text_widget(text_widget, f"Error: {e}\n")
        print("Error:", e)  # Debug print
    finally:
        if ser.is_open:
            ser.close()  # Close the serial port when done
        if mysql_connection:
            mysql_connection.close()


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
