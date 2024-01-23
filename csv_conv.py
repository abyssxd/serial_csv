import serial
import csv
import simplekml
#import time

# Serial port configuration
port = "COM6"  # Change this to your Arduino's serial port
baud_rate = 9600

#Create the KML File with certain settings
def create_kml():
    kml = simplekml.Kml()
    linestring = kml.newlinestring(name="Vila2Sat_Track")
    linestring.style.linestyle.color = simplekml.Color.red
    linestring.style.linestyle.width = 4
    linestring.style.linestyle.width = 4
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

# CSV file configuration
csv_file = "output.csv"
csv_headers = ["Time", "Temperature", "Pressure", "Altitude", "Latitude", "Longitude"] #Define the headers for the CSV

def read_serial_data():

    kml, linestring = create_kml()
    coordinates = []

    with serial.Serial(port, baud_rate, timeout=1) as ser, open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)  # Writing the header

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
                    #timestamp = time.strftime("%Y-%m-%d %H:%M:%S") | not gonna use this

                    sensor_type, sensor_value = parse_data(data_line)
                    #Assign the sensor values
                    if sensor_type == "Time":
                        time_value = sensor_value
                    #elif sensor_type == "PPM":
                    #    ppm_value = sensor_value | was using a MQ-7 to test in class
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

                    if time_value is not None and temperature_value is not None and pressure_value is not None and altitude_value is not None and humidity_value is not None and latitude_value is not None and longitude_value is not None:
                        coordinates.append((float(longitude_value), float(latitude_value), altitude_value))  # Altitude is 0
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
                        
        except KeyboardInterrupt: #Don't press anything and don't mess it uppp!!!
            print("Data collection stopped by user.")

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