import cv2
import numpy as np
import socket
import struct
import pickle

class VideoTransmitter:
    def __init__(self, cam_index, host='0.0.0.0', port=8485, quality=90):
        self.cam_index = cam_index
        self.host = host
        self.port = port
        self. Quality = quality
        self. Cap = None
        self.server_socket = None
        self.conn = None
        self.addr = None

    def start(self):
        # Create a socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self. Host, self.port))
            server_socket.listen()

            print(f'Server listening on: {socket.gethostbyname(socket.gethostname())}:{self.port}')

            # Accept the client connection
            self.conn, self.addr = server_socket.accept()

            # Start the video capture
            self.cap = cv2.VideoCapture(self.cam_index)

            if not self.cap.isOpened():
                print("Error opening the camera")
                return

            while True:
                # Capture a frame
                ret, frame = self.cap.read()

                if not ret:
                    print("Error reading the frame")
                    break

                # Reduce the quality of the frame with JPEG encoding
                result, frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality])
                data = pickle.dumps(frame, 0)
                # First send the size of the frame
                message_size = struct.pack("=I", len(data))

                # Send data
                try:
                    self.conn.sendall(message_size + data)
                except Exception as e:
                    print("Error sending data:", str(e))
                    self.conn, self.addr = server_socket.accept()
                    print("New connection accepted from:", self.addr)

    def stop(self):
        # Close all resources
        cv2.destroyAllWindows()
        if self.cap is not None:
            self.cap.release()
        if self.conn is not None:
            self.conn.close()
        print("Transmitter stopped.")

# Ask the user which camera to use
cam_index = int(input("Enter the index of the camera you want to use: "))

transmitter = VideoTransmitter(cam_index)
try:
    transmitter.start()
finally:
    transmitter. Stop()