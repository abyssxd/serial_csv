import serial
import csv
import time

# Serial port configuration
port = "COM6"  # Change this to your Arduino's serial port
baud_rate = 9600

# CSV file configuration
csv_file = "output.csv"
csv_headers = ["Timestamp", "PPM", "Temperature"]

def read_serial_data():
    with serial.Serial(port, baud_rate, timeout=1) as ser, open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)  # Writing the header

        ppm_value = None
        temperature_value = None

        try:
            while True:
                if ser.in_waiting > 0:
                    data_line = ser.readline().decode('utf-8').rstrip()
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                    sensor_type, sensor_value = parse_data(data_line)
                    if sensor_type == "PPM":
                        ppm_value = sensor_value
                    elif sensor_type == "Temperature":
                        temperature_value = sensor_value

                    if ppm_value is not None and temperature_value is not None:
                        writer.writerow([timestamp, ppm_value, temperature_value])
                        print(f"{timestamp}, PPM: {ppm_value}, Temperature: {temperature_value}")
                        # Reset the values after writing to the CSV
                        ppm_value = None
                        temperature_value = None
                        
        except KeyboardInterrupt:
            print("Data collection stopped by user.")

def parse_data(data_line):
    if "PPM=" in data_line:
        return "PPM", data_line.split("PPM=")[-1].strip()
    elif "Temperature=" in data_line:
        return "Temperature", data_line.split("Temperature=")[-1].strip()
    return None, None

if __name__ == "__main__":
    read_serial_data()