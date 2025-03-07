import cv2
import socket
import ssl
import struct
import logging
import threading
import time
import os
from queue import Queue

logging.basicConfig(level=logging.INFO)

class VideoTransmitter:
    def __init__(
        self,
        cam_index=0,
        host='0.0.0.0',
        port=8485,
        quality=90,
        max_fps=30,
        queue_size=10,
        send_retries=3,
        record_local=False,
        use_ssl=False,
        certfile='cert.pem',
        keyfile='key.pem',
        chunk_duration=30.0,
        use_cuda=False,
        allow_multiple_clients=True
    ):
        self.cam_index = cam_index
        self.host = host
        self.port = port
        self.quality = quality
        self.max_fps = max_fps
        self.queue_size = queue_size
        self.send_retries = send_retries
        self.record_local = record_local
        self.use_ssl = use_ssl
        self.certfile = certfile
        self.keyfile = keyfile
        self.chunk_duration = chunk_duration
        self.use_cuda = use_cuda
        self.allow_multiple_clients = allow_multiple_clients

        self.cap = None
        self.base_socket = None
        self.server_socket = None
        self.clients = []  # (socket, addr, thread)

        self.capture_thread = None
        self.capture_running = False
        self.frames_queue = Queue(maxsize=self.queue_size)

        self.last_frame_time = 0.0

        self.local_record_index = 0
        self.local_record_start_time = 0.0
        self.out = None

        self.running = True  # Para bucles de reconexión

    def _init_camera(self):
        # Permite usar GPU de OpenCV si se desea (experimental)
        camera = cv2.VideoCapture(self.cam_index)
        if not camera.isOpened():
            logging.error("No se pudo abrir la cámara (índice %s).", self.cam_index)
            return None
        return camera

    def _capture_frames(self, camera):
        self.capture_running = True
        self.local_record_start_time = time.time()
        while self.capture_running:
            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            if elapsed < (1.0 / self.max_fps):
                time.sleep((1.0 / self.max_fps) - elapsed)

            ret, frame = camera.read()
            self.last_frame_time = time.time()
            if not ret:
                logging.error("Error al capturar frame.")
                break

            if self.record_local:
                self._write_local_record(frame)

            # Broadcast a todos los clientes
            if not self.frames_queue.full():
                self.frames_queue.put(frame)

    def _write_local_record(self, frame):
        if not self.out:
            self._init_new_record_file(frame)
        if (time.time() - self.local_record_start_time) >= self.chunk_duration:
            self.out.release()
            self.local_record_index += 1
            self._init_new_record_file(frame)
            self.local_record_start_time = time.time()

        if self.out:
            self.out.write(frame)

    def _init_new_record_file(self, frame):
        frame_height, frame_width = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        filename = f"backup_{self.local_record_index}.avi"
        self.out = cv2.VideoWriter(filename, fourcc, self.max_fps, (frame_width, frame_height))
        logging.info("Iniciando grabación local: %s", filename)

    def _handle_client(self, client_socket, addr):
        # Hilo por cliente para enviar frames
        logging.info("Hilo de cliente iniciado para %s", addr)
        while self.running:
            if not self.capture_running:
                time.sleep(0.1)
                continue

            if not self.frames_queue.empty():
                frame = self.frames_queue.get()

                success, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                if not success:
                    logging.error("Error al codificar frame")
                    continue

                data = encoded_frame.tobytes()
                # Reintentos con backoff
                for attempt in range(self.send_retries):
                    try:
                        time.sleep((2 ** attempt) * 0.1)  # backoff exponencial
                        msg_size = struct.pack("=I", len(data))
                        client_socket.sendall(msg_size + data)
                        break
                    except socket.error as e:
                        logging.error("Fallo al enviar frame a %s (intento %d): %s", addr, attempt + 1, e)
                        if attempt == self.send_retries - 1:
                            logging.error("Cliente %s desconectado permanentemente.", addr)
                            client_socket.close()
                            return
            else:
                time.sleep(0.01)

    def start(self):
        # Iniciar cámara
        camera = self._init_camera()
        if not camera:
            return

        frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if frame_width <= 0 or frame_height <= 0:
            logging.error("Dimensiones de cámara inválidas: %dx%d", frame_width, frame_height)
            camera.release()
            return

        # Iniciar socket servidor
        try:
            self.base_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.base_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if self.use_ssl:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
                self.server_socket = context.wrap_socket(self.base_socket, server_side=True)
            else:
                self.server_socket = self.base_socket

            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(2.0)
            logging.info("Servidor en %s:%s", self.host, self.port)
        except socket.error as e:
            logging.error("Error al crear el socket: %s", e)
            camera.release()
            return

        # Iniciar hilo de captura
        self.capture_thread = threading.Thread(target=self._capture_frames, args=(camera,), daemon=True)
        self.capture_thread.start()

        try:
            # Aceptar múltiples clientes en un bucle
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logging.info("Nuevo cliente desde %s", addr)
                    client_thread = threading.Thread(target=self._handle_client, args=(client_socket, addr), daemon=True)
                    client_thread.start()
                    self.clients.append((client_socket, addr, client_thread))

                    if not self.allow_multiple_clients:
                        break

                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error("Error aceptando cliente: %s", e)
                    break
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self.capture_running = False

        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join()

        for (client_socket, addr, thr) in self.clients:
            try:
                client_socket.close()
            except:
                pass
            if thr.is_alive():
                thr.join(timeout=1)

        if self.out:
            self.out.release()
            self.out = None

        if self.server_socket:
            self.server_socket.close()
        if self.base_socket:
            self.base_socket.close()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        logging.info("Transmisor detenido.")

if __name__ == '__main__':
    try:
        cam_index = int(input("Ingresa el índice de la cámara a utilizar: "))
    except ValueError:
        logging.error("Índice de cámara inválido.")
        exit(1)

    transmitter = VideoTransmitter(
        cam_index=cam_index,
        host='0.0.0.0',
        port=8485,
        quality=90,
        max_fps=30,
        queue_size=10,
        send_retries=3,
        record_local=True,
        use_ssl=False,
        chunk_duration=10.0,
        use_cuda=False,
        allow_multiple_clients=True
    )

    try:
        transmitter.start()
    except KeyboardInterrupt:
        logging.info("Interrumpido por el usuario.")
        transmitter.stop()
    except Exception as e:
        logging.error("Error en la ejecución: %s", e)
        transmitter.stop()
