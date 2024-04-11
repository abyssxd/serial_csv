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
from mysql.connector import pooling
import time
import queue
import threading

# Serial port configuration
port = "COM7"  # Change this to your Arduino's serial port
baud_rate = 9600

# Initialize a queue for MySQL operations
mysql_queue = queue.Queue()

# MySQL database configuration
mysql_config = {
    'host': 'fakeip',
    'port': 3306,
    'database': 'fakedb',
    'user': 'fakeuser',
    'password': 'fakepass@#'
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

def create_mysql_connection_pool(pool_name="mysql_pool", pool_size=5):
    pool = pooling.MySQLConnectionPool(pool_name=pool_name,
                                       pool_size=pool_size,
                                       pool_reset_session=True,
                                       **mysql_config)
    return pool

mysql_pool = create_mysql_connection_pool(pool_name="cansat_pool", pool_size=10)

def insert_data_to_mysql():
    while True:
        data = mysql_queue.get()
        if data is None:
            break  # Exit loop if None is received

        connection = None
        try:
            connection = mysql_pool.get_connection()
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO sensor_data
            (Time, Temperature, Pressure, Altitude, Latitude, Longitude, gps_altitude, gps_sats, gyro_x, gyro_y, gyro_z, bmp_status, gps_status, gyro_status, apc_status, servo_status, servo_rotation, sd_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, data)
            connection.commit()
        except Error as e:
            print(f"Error inserting data into MySQL database: {e}")
        finally:
            mysql_queue.task_done()
            if cursor:
                cursor.close()
            if connection:
                connection.close()  # Return the connection back to the pool

# Start the MySQL insertion thread
mysql_insertion_thread = threading.Thread(target=insert_data_to_mysql, daemon=True)
mysql_insertion_thread.start()


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
    try:
        sensor_type, sensor_value = data_line.split("=")
        return sensor_type.strip(), sensor_value.strip()
    except ValueError as e:
        print(f"Error parsing data_line '{data_line}': {e}")
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
csv_headers = ["Time", "Temperature", "Pressure", "Altitude", "Latitude", "Longitude", "gps_altitude", "gps_sats", "gyro_x", "gyro_y", "gyro_z", "bmp_status", "gps_status", "gyro_status", "apc_status", "servo_status", "servo_rotation", "sd_status"]

def read_serial_data(text_widget, stop_event, ser, csv_file):
    sensor_values = {key: None for key in csv_headers}  # Initialize sensor values
    kml, linestring = create_kml()
    coordinates = load_existing_data(csv_file)
    backup_csv_file, backup_kml_file = create_backup_files(csv_file, "live_track.kml")

    def process_and_insert_data(sensor_values):
        # Insert logic to process and insert data into MySQL and update KML/CSV here
        # For example, appending to CSV, updating KML, and inserting into MySQL
        new_coords = (float(sensor_values['Longitude']), float(sensor_values['Latitude']), float(sensor_values['Altitude']))
        coordinates.append(new_coords)
        update_kml(kml, linestring, coordinates, new_coords)
        
        with open(csv_file, 'a', newline='') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([sensor_values[header] for header in csv_headers])

        update_backup_files(backup_csv_file, backup_kml_file)

        if mysql_connection:
            data_for_mysql = tuple(sensor_values[header] for header in csv_headers)
            mysql_queue.put(data_for_mysql)

    try:
        while not stop_event.is_set():
            if ser.in_waiting > 0:
                data_line = ser.readline().decode('utf-8').rstrip()
                add_data_to_text_widget(text_widget, data_line)
                
                sensor_type, sensor_value = parse_data(data_line)
                if sensor_type in sensor_values:
                    sensor_values[sensor_type] = sensor_value
                    if all(value is not None for value in sensor_values.values()):
                        process_and_insert_data(sensor_values)
                        sensor_values = {key: None for key in csv_headers}  # Reset after processing
                else:
                    add_data_to_text_widget(text_widget, "Received malformed or unrecognized data line.")
    except serial.SerialException as e:
        add_data_to_text_widget(text_widget, f"Serial error: {e}\n")
    except Exception as e:
        add_data_to_text_widget(text_widget, f"Error: {e}\n")
    finally:
        if ser.is_open:
            ser.close()


# Function to handle stop reading
def stop_reading(stop_event):
    stop_event.set()  # Signal the thread to stop
    stop_mysql_thread()
    

def stop_mysql_thread():
    mysql_queue.put(None)  # Signal the thread to exit
    mysql_insertion_thread.join()


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
        threading.Thread(target=read_serial_data, args=(text_widget, stop_event, ser, csv_file), daemon=True).start()
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
