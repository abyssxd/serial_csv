import serial
import csv
import simplekml
import shutil
import os
from datetime import datetime

# Serial port configuration
port = "COM6"  # Change this to your Arduino's serial port
baud_rate = 9600

#Create the KML File with certain settings
def create_kml():
    kml = simplekml.Kml()
    linestring = kml.newlinestring(name="Vila2Sat_Track")
    linestring.style.linestyle.color = simplekml.Color.red
    linestring.style.linestyle.width = 4
    linestring.style.linestyle.height = 4
    linestring.altitudemode = simplekml.AltitudeMode.absolute
    return kml, linestring

#Fuction that updates the kml, this is called in the read_serial_data() function so that it updates everytime there's a new serial data
def update_kml(kml, linestring, coordinates, last_coordinate):
    linestring.coords = coordinates
    linestring.altitudemode = simplekml.AltitudeMode.absolute
    linestring.extrude = 0
    linestring.tessellate = 0

    kml.lookat.longitude = last_coordinate[0]
    kml.lookat.latitude = last_coordinate[1]
    kml.lookat.altitude = last_coordinate[2] + 10
    kml.lookat.heading = 0
    kml.lookat.tilt = 45
    kml.lookat.range = 20
    kml.lookat.altitudemode = simplekml.AltitudeMode.absolute

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
                    lat, lon, alt = float(row[5]), float(row[6]), float(row[3])
                    coordinates.append((lon, lat, alt))
                except ValueError:
                    continue  # Skip rows with invalid data
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


# CSV file configuration
csv_file = "output.csv"
csv_headers = ["Time", "Temperature", "Pressure", "Altitude", "Latitude", "Longitude"] #Define the headers for the CSV

def read_serial_data():

    kml, linestring = create_kml()
    coordinates = load_existing_data(csv_file)

    backup_csv_file, backup_kml_file = create_backup_files(csv_file, "live_track.kml")


    with serial.Serial(port, baud_rate, timeout=1) as ser, open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)  # Writing the header

        # Initialize variables
        sensor_values = {key: None for key in csv_headers}
        
        # Initialize variables
        time_value = None
        temperature_value = None
        pressure_value = None
        altitude_value = None
        latitude_value = None
        longitude_value = None

        try:
            while True:
                if ser.in_waiting > 0:
                    data_line = ser.readline().decode('utf-8').rstrip()

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

                    if time_value is not None and temperature_value is not None and pressure_value is not None and altitude_value is not None and latitude_value is not None and longitude_value is not None:
                        altitude_value_float = float(altitude_value)
                        coordinates.append((float(longitude_value), float(latitude_value), altitude_value_float))  # Altitude is 0
                        update_kml(linestring, coordinates)
                        writer.writerow([time_value, temperature_value, pressure_value, altitude_value, latitude_value, longitude_value]) #Write it in the csv file in the desired order (must match csv_headers order)
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

                        update_backup_files(backup_csv_file, backup_kml_file)
                        
        except KeyboardInterrupt: #Don't press anything and don't mess it uppp!!!
            print("Data collection stopped by user.")
            update_backup_files(backup_csv_file, backup_kml_file)

#Parse the data, check what data it is, split it and remove the Data= and only save the value to the corresponding row in the csv
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

if __name__ == "__main__":
    read_serial_data()
