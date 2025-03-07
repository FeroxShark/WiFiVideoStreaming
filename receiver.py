import cv2
import socket
import pickle
import struct
import sys
import logging
from contextlib import closing

logging.basicConfig(level=logging.INFO)

# Constantes
HEADER_FORMAT = "!I"  # 4 bytes en orden de red
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
QUIT_KEY = ord('q')

def get_local_ip():
    """Obtiene la IP local conectándose a un servidor público."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logging.error("Error obteniendo la IP local: %s", e)
        raise

def get_port_from_user():
    """Solicita el puerto al usuario validando el rango."""
    while True:
        try:
            port = int(input("Ingrese el puerto (1-65535): "))
            if 1 <= port <= 65535:
                return port
            else:
                logging.error("El puerto debe estar entre 1 y 65535.")
        except ValueError:
            logging.error("Número de puerto inválido.")

def create_server_socket(ip, port):
    """Crea y configura el socket del servidor."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((ip, port))
        s.listen(5)
        return s
    except socket.error as e:
        logging.error("Error al crear el socket: %s", e)
        raise

def receive_exact_data(sock, num_bytes):
    """Recibe exactamente 'num_bytes' desde el socket."""
    data = b""
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(client_socket):
    """Procesa la conexión de un cliente: recibe y muestra frames."""
    with client_socket:
        while True:
            header_data = receive_exact_data(client_socket, HEADER_SIZE)
            if header_data is None:
                logging.info("Cliente desconectado.")
                break
            msg_size = struct.unpack(HEADER_FORMAT, header_data)[0]
            frame_data = receive_exact_data(client_socket, msg_size)
            if frame_data is None:
                logging.info("Desconexión durante la recepción del frame.")
                break
            try:
                frame = pickle.loads(frame_data)
            except pickle.UnpicklingError as e:
                logging.error("Error deserializando frame: %s", e)
                break
            cv2.imshow('Frame', frame)
            if cv2.waitKey(1) & 0xFF == QUIT_KEY:
                return True  # Indica que se debe salir
    return False

def main():
    try:
        local_ip = get_local_ip()
        logging.info("IP local: %s", local_ip)
    except Exception:
        sys.exit(1)
    port = get_port_from_user()
    try:
        server_socket = create_server_socket(local_ip, port)
    except Exception:
        sys.exit(1)
    with server_socket:
        quit_server = False
        while not quit_server:
            logging.info("Esperando conexión en %s:%s", local_ip, port)
            client_socket, addr = server_socket.accept()
            logging.info("Conexión desde %s", addr)
            if handle_client(client_socket):
                quit_server = True
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Servidor interrumpido por el usuario.")
        cv2.destroyAllWindows()
        sys.exit(0)
