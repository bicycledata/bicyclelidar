#!/usr/bin/env python3

import argparse
import time
from collections import deque

import serial

from BicycleSensor import BicycleSensor, configure


class BicycleLidar(BicycleSensor):
  def write_header(self):
    self.write_to_file('time, distance [cm], strength, temp')

  def write_measurement(self):
    self.write_to_file(f'{str(time.time())}, {self._distance}, {self._strength}, {self._temp}')

  def worker_main(self):
    self._distance = None
    self._strength = None
    self._temp = None

    with serial.Serial('/dev/ttyUSB0', 115200, timeout=1) as ser:
      # Not sure if this should be removed though
      cmd = [0x5a, 0x05, 0x07, 0x00, 0x66]
      for c in cmd:
        ser.write(c)

      Q = deque([0x59]*9)
      while self._alive:
        b = ser.read()
        Q.rotate(-1)
        Q[0] = ord(b)

        if Q[0] == 0x59 and Q[1] == 0x59:
          #Dist_L Dist_H Strength_L Strength_H Temp_L Temp_H Checksum
          dist = (Q[3] * 256) + Q[2]
          strength = (Q[5] * 256) + Q[4]
          temp = (Q[7] * 256) + Q[6]
          checksum = sum([Q[i] for i in range(8)]) % 256
          if checksum == Q[8]:
            self._distance = dist
            self._strength = strength
            self._temp = temp


if __name__ == '__main__':
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

  sensor = BicycleLidar(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval, use_worker_thread=True)
  sensor.main()
