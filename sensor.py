import time
from collections import deque
from multiprocessing.connection import Connection

import serial
from serial.serialutil import EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from bicycleinit.BicycleSensor import BicycleSensor


def main(bicycleinit: Connection, name: str, args: dict):
  sensor = BicycleSensor(bicycleinit, name, args)

  port = args.get('port', '/dev/ttyUSB0')
  try:
    ser = serial.Serial(port, baudrate=115200, parity=PARITY_NONE, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE, timeout=1.0)
  except serial.SerialException as e:
    sensor.send_msg(f'Error opening serial port {port}: {e}')
    return

  sensor.write_header(['distance [cm]', 'strength', 'temperature'])
  try:
    # Initialize the sensor
    cmd = [0x5a, 0x05, 0x07, 0x00, 0x66]
    for c in cmd:
      ser.write(c)

    measurement_frequency = args.get('measurement_frequency', 1.0)
    measurement_interval = 1.0 / measurement_frequency
    last_measurement_time = time.time()

    Q = deque([0x59] * 9)
    while True:
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
          current_time = time.time()
          if current_time - last_measurement_time >= measurement_interval and dist != 65535:
            sensor.write_measurement([dist, strength, temp])
            last_measurement_time = current_time
  except KeyboardInterrupt:
    pass
  except serial.SerialException as e:
    sensor.send_msg(f'Error reading from serial port: {e}')
  except Exception as e:
    sensor.send_msg(f'Error reading from serial port: {e}')
  finally:
    ser.close()
    sensor.shutdown()

if __name__ == "__main__":
  main(None, "bicyclelidar", {'port': '/dev/ttyUSB0', 'measurement_frequency': 1.0})
