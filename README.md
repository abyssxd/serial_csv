# Vila2Sat Serial
- This is literally a serial monitor.
- Converts the incoming serial data sent by the Vila2Sat's CanSat into the CSV format for the Vila2Sat Dashboard.
- Converts the incoming serial data sent by the Vila2Sat's CanSat into the KML format to track the Vila2Sat Cansat in Google Earth 3D View.

## Integrated Terminal Serial Monitor
This uses its own serial monitor using `pyserial`, it makes the serial monitor show up in the terminal you run the converter in, and while its being monitored, it updates and saves to the output csv file.
- Use `python serial` to open the terminal serial monitor (both save and update the csv & kml files)

## Integrated GUI Serial Monitor
This uses its own serial monitor using `pyserial`, it makes the serial monitor show up in the terminal you run the converter in, and while its being monitored, it updates and saves to the output csv file.
- Use `python serial_gui` to open the GUI serial monitor (both save and update the csv & kml files)
### Vila2Sat Serial GUI
![lv_0_20240423192634](https://github.com/abyssxd/vila2sat_serial/assets/57658642/bdd441de-afb6-4ffe-a328-baaa17033094)

## Google Earth Screenshots
***This track was made using fake data for visual representation.***
### Camera View
- Will add soon.
### Overview
- Will add soon.

## DashBoard
You can find the Vila2Sat Dashboard this converts the data for here -> https://github.com/abyssxd/cansat_vila2sat

## Setup
1. Install pyserial by running `pip install pyserial`, Install simplekml by running `pip install simplekml` & finally install TtkThemes with `pip install ttkthemes`
2. Change the `port & baud rate` to yours in the `csv_conv.py` file.
3. Modify the `data_parse` function if necessary.
4. Connect the arduino, esp32 or anything that prints serial data.
5. Run the file with `python csv_conv.py` & it should start showing the serial data & saving it in the csv file.

Shield: [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg
