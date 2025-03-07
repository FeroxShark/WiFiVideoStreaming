import cv2
import socket
import ssl
import struct
import logging
import sys
import numpy as np
import threading
import time
import os

logging.basicConfig(level=logging.INFO)

class VideoReceiver:
    """
    Cliente para recibir streaming de VideoTransmitter.

    Características:
      - Reconexiones automáticas.
      - Hilo de recepción independiente.
      - Opción de grabar video local en fragmentos.
      - Muestra FPS de recepción.
      - Reconecta incluso durante la recepción.
      - Permite configurar color o escala de grises.
    """
    def __init__(
        self,
        server_ip='127.0.0.1',
        port=8485,
        use_ssl=False,
        certfile='cert.pem',
        max_reconnects=3,
        record_local=False,
        chunk_duration=30.0,
        display_fps=True,
        decode_color=True,
        enable_midstream_reconnect=True
    ):
        self.server_ip = server_ip
        self.port = port
        self.use_ssl = use_ssl
        self.certfile = certfile
        self.max_reconnects = max_reconnects
        self.record_local = record_local
        self.chunk_duration = chunk_duration
        self.display_fps = display_fps
        self.decode_color = decode_color
        self.enable_midstream_reconnect = enable_midstream_reconnect

        self.client_socket = None
        self.running = True
        self.HEADER_SIZE = 4
        self.QUIT_KEY = ord('q')

        self.receive_thread = None
        self.last_time = time.time()
        self.frame_count = 0
        self.fps = 0.0

        # Grabación en disco
        self.out = None
        self.local_record_index = 0
        self.local_record_start_time = 0.0

        self.color_flag = cv2.IMREAD_COLOR if self.decode_color else cv2.IMREAD_GRAYSCALE

    def _create_socket(self):
        base_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            if self.certfile:
                try:
                    context.load_verify_locations(self.certfile)
                except Exception as e:
                    logging.warning("No se pudo cargar el certificado: %s", e)
            return context.wrap_socket(base_socket, server_hostname=self.server_ip)
        else:
            return base_socket

    def _init_local_record(self, frame):
        if not self.record_local:
            return
        if self.out is not None:
            self.out.release()
        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        filename = f"receiver_backup_{self.local_record_index}.avi"
        # Si no es color, grabamos un frame de un solo canal.
        if not self.decode_color:
            # Convertir a BGR para no tener conflicto en la grabación.
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            h, w = frame.shape[:2]
        self.out = cv2.VideoWriter(filename, fourcc, 30, (w, h))
        self.local_record_start_time = time.time()
        logging.info("Iniciando grabación local: %s", filename)

    def _write_local_record(self, frame):
        if not self.record_local:
            return
        # Revisar chunking
        if time.time() - self.local_record_start_time >= self.chunk_duration:
            self.local_record_index += 1
            self._init_local_record(frame)
        if self.out:
            # Convertir a color si está en escala de grises para no corromper la grabación.
            if not self.decode_color:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            self.out.write(frame)

    def connect(self):
        """
        Intenta conectarse con el servidor hasta max_reconnects veces.
        """
        for attempt in range(self.max_reconnects):
            if not self.running:
                return False
            try:
                self.client_socket = self._create_socket()
                self.client_socket.connect((self.server_ip, self.port))
                logging.info("Conectado con %s:%s (intento %d)", self.server_ip, self.port, attempt + 1)
                return True
            except socket.error as e:
                logging.error("Fallo al conectar: %s (intento %d)", e, attempt + 1)
                time.sleep(2.0)
        logging.error("No se pudo conectar tras %d intentos.", self.max_reconnects)
        return False

    def _receive_exact_data(self, num_bytes):
        data = b""
        while len(data) < num_bytes and self.running:
            try:
                packet = self.client_socket.recv(num_bytes - len(data))
                if not packet:
                    return None
                data += packet
            except socket.error:
                return None
        return data

    def _attempt_reconnect_midstream(self):
        if self.enable_midstream_reconnect:
            logging.info("Intentando reconexión en pleno stream...")
            if self.client_socket:
                self.client_socket.close()
            return self.connect()
        return False

    def _receive_frame(self):
        """
        Lee un frame completo del socket o retorna None si hay error.
        """
        header_data = self._receive_exact_data(self.HEADER_SIZE)
        if not header_data:
            return None
        frame_size = struct.unpack("=I", header_data)[0]
        frame_data = self._receive_exact_data(frame_size)
        if not frame_data:
            return None
        np_frame = np.frombuffer(frame_data, dtype=np.uint8)
        return cv2.imdecode(np_frame, self.color_flag)

    def _receive_loop(self):
        while self.running:
            frame = self._receive_frame()
            if frame is None:
                logging.info("Desconexión durante la recepción del frame.")
                if not self._attempt_reconnect_midstream():
                    break
                else:
                    continue

            # FPS
            self.frame_count += 1
            if self.frame_count >= 30:
                now = time.time()
                dt = now - self.last_time
                self.fps = self.frame_count / dt if dt > 0 else 0.0
                self.frame_count = 0
                self.last_time = now

            # Grabar
            self._write_local_record(frame)

            # Mostrar
            display_name = "VideoReceiver"
            if self.display_fps:
                display_name += f" [FPS: {self.fps:.1f}]"

            cv2.imshow(display_name, frame)
            if cv2.waitKey(1) & 0xFF == self.QUIT_KEY:
                self.running = False
                break

    def start(self):
        if not self.connect():
            sys.exit(1)
        self.running = True

        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()

        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logging.info("Recepción interrumpida por el usuario.")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join()
        if self.out:
            self.out.release()
        if self.client_socket:
            self.client_socket.close()
        cv2.destroyAllWindows()
        logging.info("Receptor detenido.")

if __name__ == "__main__":
    logging.info("Iniciando VideoReceiver...")
    server_ip = input("Ingresa la IP del servidor: ") or '127.0.0.1'
    try:
        port = int(input("Ingresa el puerto: ") or '8485')
    except ValueError:
        logging.error("Puerto inválido.")
        sys.exit(1)

    receiver = VideoReceiver(
        server_ip=server_ip,
        port=port,
        use_ssl=False,
        certfile='cert.pem',
        max_reconnects=3,
        record_local=False,
        chunk_duration=10.0,
        display_fps=True,
        decode_color=True,
        enable_midstream_reconnect=True
    )

    receiver.start()
