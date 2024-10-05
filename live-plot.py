import socket
import threading
import time
from collections import deque

import matplotlib.animation as animation
import matplotlib.pyplot as plt

# Configuration constants
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 500 # Data points
TIME_WINDOW = 30  # Seconds

# Data buffers for plotting
x_data = deque(maxlen=BUFFER_SIZE)
y_data = deque(maxlen=BUFFER_SIZE)

# Setup plot
fig, ax = plt.subplots()
line, = ax.plot([], [], lw=2)
ax.set_xlim(0, TIME_WINDOW)
ax.set_ylim(0, 300)
ax.set_xlabel('Time (seconds)')
ax.set_ylabel('Distance (cm)')
ax.set_title('Real-time Distance Measurements')

start_time = time.time()

def extract_value(message):
  try:
    return float(message.rstrip('#').split(':')[1])
  except (ValueError, IndexError):
    return None

def update(frame):
  if x_data[-1] > TIME_WINDOW:
    ax.set_xlim(x_data[-1] - TIME_WINDOW, x_data[-1])
  line.set_data(x_data, y_data)
  return line,

def init():
  line.set_data([0], [0])
  return line,

def receive_messages(client_socket):
  while True:
    try:
      message = client_socket.recv(1024).decode('utf-8')
      if not message:
        break
      new_distance = extract_value(message)
      if new_distance:
        x_data.append(time.time() - start_time)
        y_data.append(new_distance)
    except:
      break

if __name__ == "__main__":
  client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client.connect((HOST, PORT))
  threading.Thread(target=receive_messages, args=(client,)).start()

  ani = animation.FuncAnimation(fig, update, init_func=init, blit=False, interval=100, repeat=False, cache_frame_data=False)

  plt.show()
  client.close()
