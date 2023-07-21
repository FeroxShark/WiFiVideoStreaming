import cv2
import socket
import pickle
import struct
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Named constants for better readability
PAYLOAD_SIZE = struct.calcsize("L")
QUIT_CHAR = 'q'
QUIT_KEY = ord(QUIT_CHAR)

def get_local_ip():
    """Function to get the local IP address."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        logging.error("Error getting local IP address: %s", e)
        sys.exit(1)

def get_port_from_user():
    """Function to get the port from the user."""
    while True:
        try:
            port = int(input("Please enter the port you want to use: "))
            if 1 <= port <= 65535:  # Valid port numbers are between 1 and 65535
                return port
            else:
                logging.error("Port number must be between 1 and 65535.")
        except ValueError:
            logging.error("Invalid port number. Please enter a valid number.")

def create_server_socket(ip, port):
    """Function to create the server socket."""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((ip, port))  # Bind to the socket
        server_socket.listen(5)  # Listen for incoming connections
        return server_socket
    except socket.error as e:
        logging.error("Error creating socket: %s", e)
        sys.exit(1)

def accept_connection(server_socket):
    """Function to accept the incoming connection."""
    try:
        client_socket, addr = server_socket.accept()
        return client_socket, addr
    except socket.error as e:
        logging.error("Error accepting connection: %s", e)
        sys.exit(1)

def receive_data(client_socket, size):
    """Function to receive data from the client socket."""
    data = b''  # Store the frame data here
    while len(data) < size:
        try:
            packet = client_socket.recv(size - len(data))  # Only receive the remaining bytes
            if not packet:
                return None
            data += packet
        except socket.error as e:
            logging.error("Error receiving data: %s", e)
            sys.exit(1)
    return data

def main():
    # Get the local IP address and port number
    local_ip = get_local_ip()
    logging.info("Your local IP address is: %s", local_ip)
    port = get_port_from_user()
    receive_size = True

    # Create the server socket
    server_socket = create_server_socket(local_ip, port)

    while True:
        # Accept the incoming connection
        client_socket, addr = accept_connection(server_socket)

        while True:
            if receive_size:
                # Receive the message size
                data = receive_data(client_socket, PAYLOAD_SIZE)
                if data is None:
                    logging.info("Connection closed.")
                    break
                packed_msg_size = data[:PAYLOAD_SIZE]
                data = data[PAYLOAD_SIZE:]
                msg_size = struct.unpack("L", packed_msg_size)[0]
                receive_size = False  # Only receive the size once

            # Receive the frame data
            data = receive_data(client_socket, msg_size)
            if data is None:
                logging.info("Connection closed.")
                break
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # Deserialize the frame
            try:
                frame = pickle.loads(frame_data)
            except pickle.UnpicklingError:
                logging.error("Error unpickling frame data.")
                break

            # Display the frame
            cv2.imshow('frame', frame)

            if cv2.waitKey(1) & 0xFF == QUIT_KEY:
                break

        # Close the client socket
        client_socket.close()

    # Close the server socket when no longer needed
    try:
        server_socket.close()
    except Exception as e:
        logging.error("Error closing server socket: %s", e)

    # Close the OpenCV window
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()