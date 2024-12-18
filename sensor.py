#!/usr/bin/env python3

import argparse
import logging
import socket
import threading
import time
from collections import deque
from datetime import datetime

import serial

from BicycleSensor import BicycleSensor, configure

HOST = '0.0.0.0'
PORT = 12345

# Thread-safe list to manage connected clients
clients = []
clients_lock = threading.Lock()

def broadcast(message):
  '''Send a message to all connected clients.'''
  with clients_lock:
    for client in clients:
      try:
        client.sendall(message)
      except:
        clients.remove(client)  # Remove disconnected clients
        logging.warning("Client disconnected")

def start_server():
  '''Start the TCP server and accept incoming clients.'''
  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.bind((HOST, PORT))
  server.listen()

  logging.info(f"Server is listening on {HOST}:{PORT}")

  while True:
    client_socket, _ = server.accept()
    #client_socket.settimeout(10)  # Set a timeout for client sockets
    with clients_lock:
      clients.append(client_socket)
    logging.info("New client connected")

class BicycleLidar(BicycleSensor):
  def write_header(self):
    self.write_to_file('time,unix_timestamp,distance,strength,temp')

  def write_measurement(self):
    '''Write the measurement to file and broadcast to clients.'''
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    unix_timestamp = time.time()  # Unix timestamp
    self.write_to_file(f'{current_time},{unix_timestamp},{self._distance},{self._strength},{self._temp}')
    broadcast(f'lidar1:{self._distance:.1f}#'.encode('utf-8'))

  def worker_main(self):
    '''Main worker function to handle sensor data and server operations.'''
    self._distance = None
    self._strength = None
    self._temp = None

    # Start the server in a background thread
    threading.Thread(target=start_server, daemon=True).start()

    try:
      with serial.Serial('/dev/ttyUSB0', 115200, timeout=1) as ser:
        # Initialize the sensor
        cmd = [0x5a, 0x05, 0x07, 0x00, 0x66]
        for c in cmd:
          ser.write(c)

        Q = deque([0x59] * 9)
        while self._alive:
          b = ser.read()
          Q.rotate(-1)
          Q[0] = ord(b)

          if Q[0] == 0x59 and Q[1] == 0x59:
            # Parse the sensor data: distance, strength, temp
            dist = (Q[3] * 256) + Q[2]
            strength = (Q[5] * 256) + Q[4]
            temp = (Q[7] * 256) + Q[6]
            checksum = sum([Q[i] for i in range(8)]) % 256

            if checksum == Q[8]:
              self._distance = dist
              self._strength = strength
              self._temp = temp
    except serial.SerialException as e:
      logging.error(f"Serial communication error: {e}")

if __name__ == '__main__':
  # Setup argument parser
  PARSER = argparse.ArgumentParser(
    description='Bicycle Lidar Sensor',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
  PARSER.add_argument('--name', type=str, required=True, help='[required] name of the sensor')
  PARSER.add_argument('--loglevel', type=str, default='INFO', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
  PARSER.add_argument('--measurement-frequency', type=float, default=1.0, help='Frequency of sensor measurements in 1/s')
  PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
  PARSER.add_argument('--upload-interval', type=float, default=300.0, help='Interval between uploads in seconds')
  ARGS = PARSER.parse_args()

  # Configure logging
  configure('bicyclelidar.log', stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel)

  # Start the BicycleLidar sensor
  sensor = BicycleLidar(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval, use_worker_thread=True)
  sensor.main()
