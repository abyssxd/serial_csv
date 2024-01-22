# Serial to CSV converter
This is a converter that converts the incoming serial data sent by the Vila2Sat's CanSat into the CSV format so that the dashboard can read and display the data correctly.
# Setup
1. Install pyserial by running `pip install pyserial` 
2. Change the `port & baud rate` to yours in the `csv_conv.py` file
3. Modify the `data_parse` function if necessary
4. Connect the arduino, esp32 or anything that prints serial data
5. Run the file with `python csv_conv.py` & it should start showing the serial data & saving it in the csv file.
