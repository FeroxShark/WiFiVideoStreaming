# Wifi Video Streaming

## Description
This project is a Python implementation of a simple live video transmitter from one device to another over WiFi. It uses the OpenCV library for video handling, and sockets for communication between devices.

The project is divided into two parts: one for video transmission and another for reception. 

The transmitter opens a camera via OpenCV, captures each frame, encodes it into JPEG format to reduce its size, serializes it with pickle, and then sends it over a socket to a receiver device.

The receiver waits for incoming connections, receives the serialized and encoded frame, deserializes it with pickle, decodes it back to its original format, and then displays it on the screen.

## Requirements
* Python 3.x
* OpenCV
* numpy
* sockets

## How to use
1. Clone this repository on your local machine.
2. Make sure you have the necessary libraries installed.
3. Run the transmitter script on the device that will act as the video source. You can specify the index of the camera you want to use.
4. Run the receiver script on the device to which you want to transmit the video.
5. Enter the IP address and port of the transmitter when prompted.
6. Enjoy the live video stream.

## Warnings
This is a simple project and is meant to be a proof of concept. It may not be robust enough for serious production use.

## Contributions
Contributions are welcome. Please fork the repository and propose your changes via a Pull Request.

## License
This project is under the MIT license. Please refer to the `LICENSE` file for more details.
