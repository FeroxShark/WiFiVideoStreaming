# Wifi Video Streaming

Este repositorio demuestra una solución para transmitir y recibir video vía WiFi. Incluye:

- **VideoTransmitter** (transmitter.py):
  - Captura frames de la cámara.
  - Envía video por socket TCP.
  - Opciones avanzadas: compresión JPEG, SSL, reintentos de envío, grabación local, multicliente.

- **VideoReceiver** (receiver.py):
  - Se conecta al servidor.
  - Recibe y decodifica los frames.
  - Incluye reconexiones automáticas, grabación local en partes y visualización de FPS.

## Requisitos
Revisa el archivo [requirements.txt](./requirements.txt) para conocer las dependencias necesarias, e instálalas con:

```bash
pip install -r requirements.txt
```

## Uso
1. Ajusta la configuración en los scripts si es necesario (puertos, calidad, etc.).
2. En el dispositivo transmisor:
   - Ejecuta `python transmitter.py`.
   - Se abrirá la cámara y el socket.
3. En el dispositivo receptor:
   - Ejecuta `python receiver.py`.
   - Indica la IP del transmisor y el puerto.
4. ¡Listo! El receptor debería mostrar el video en tiempo real.

## Características
- **Transmisor**:
  - FPS configurable.
  - Calidad JPEG ajustable.
  - Grabación local con particionado (chunk_duration).
  - TLS/SSL opcional.
  - Varios clientes simultáneos.

- **Receptor**:
  - Hilo de recepción independiente.
  - Reintentos de conexión configurables.
  - Grabación local.
  - Reconexiones en caso de pérdida de conexión.
  - Visualización de FPS.

## Notas
- Proyecto de ejemplo, no destinado a producción sin mayores controles (seguridad, manejo de errores, etc.).
- Asegúrate de que tu firewall permita el puerto configurado.

## Contribuciones
¡Son bienvenidas! Haz un fork y envía un Pull Request.

## Licencia
Distribuido bajo [MIT License](./LICENSE).

