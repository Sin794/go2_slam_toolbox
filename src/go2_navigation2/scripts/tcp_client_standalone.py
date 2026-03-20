#!/usr/bin/env python3
import json
import os
import socket
import struct
import time

import yaml


class TcpClient:
    def __init__(self, config_path=None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(
                os.path.dirname(current_dir), "config", "tcp_config.yaml"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            self.host = config["nav_server"]["host"]
            self.port = config["nav_server"]["port"]
        except Exception as exc:
            print(f"Failed to load config: {exc}")
            self.host = "127.0.0.1"
            self.port = 5432

        self.socket = None
        self.connected = False

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to {self.host}:{self.port}")
        except Exception as exc:
            print(f"Connection failed: {exc}")
            self.connected = False

    def send_goal(self, goal_data):
        if not self.connected:
            print("Client is not connected")
            return False

        try:
            data = json.dumps(goal_data).encode()
            length = struct.pack("!I", len(data))
            self.socket.sendall(length + data)
            return True
        except Exception as exc:
            print(f"Failed to send goal: {exc}")
            return False

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.connected = False
            print("Connection closed")


def main():
    client = TcpClient()
    client.connect()
    if not client.connected:
        return

    try:
        while True:
            goal_data = {
                "position": {"x": 1.0, "y": 0.0, "z": 0.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            }
            if client.send_goal(goal_data):
                print("Goal sent")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        client.close()


if __name__ == "__main__":
    main()
