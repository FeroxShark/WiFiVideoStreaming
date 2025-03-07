import cv2
import socket
import struct

class VideoTransmitter:
    def __init__(self, cam_index, host='0.0.0.0', port=8485, quality=90):
        self.cam_index = cam_index
        self.host = host
        self.port = port
        self.quality = quality
        self.cap = None
        self.server_socket = None
        self.client_socket = None

    def start(self):
        # Iniciar captura de video
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            print("Error al abrir la cámara")
            return

        # Crear y configurar el socket servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Servidor escuchando en: {socket.gethostbyname(socket.gethostname())}:{self.port}")

        # Aceptar conexión de cliente
        self.client_socket, addr = self.server_socket.accept()
        print("Conexión establecida con:", addr)

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error al capturar el frame")
                    break

                # Codificar el frame a JPEG
                success, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                if not success:
                    print("Error al codificar el frame")
                    continue

                data = encoded_frame.tobytes()
                # Enviar tamaño y datos del frame
                message_size = struct.pack("=I", len(data))
                self.client_socket.sendall(message_size + data)
        except Exception as e:
            print("Excepción:", e)
        finally:
            self.stop()

    def stop(self):
        if self.cap:
            self.cap.release()
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        cv2.destroyAllWindows()
        print("Transmisor detenido.")

if __name__ == '__main__':
    try:
        cam_index = int(input("Ingresa el índice de la cámara a utilizar: "))
    except ValueError:
        print("Índice de cámara inválido.")
        exit(1)

    transmitter = VideoTransmitter(cam_index)
    try:
        transmitter.start()
    except KeyboardInterrupt:
        print("Interrumpido por el usuario.")
        transmitter.stop()
