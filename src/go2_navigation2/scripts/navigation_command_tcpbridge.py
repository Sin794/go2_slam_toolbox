#!/usr/bin/env python3
import json
import socket
import struct
import threading

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node


class Nav2TcpBridge(Node):
    def __init__(self):
        super().__init__("nav2_tcp_bridge")

        default_config_path = (
            get_package_share_directory("go2_navigation2") + "/config/tcp_config.yaml"
        )
        config_path = self.declare_parameter("config_path", default_config_path).value

        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        self.host = config["nav_server"]["host"]
        self.port = config["nav_server"]["port"]
        self.max_retries = 3
        self.current_goal = None
        self.retry_count = 0

        self._action_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

        self.tcp_thread = threading.Thread(target=self.tcp_server_loop, daemon=True)
        self.tcp_thread.start()

        self.get_logger().info(
            f"Nav2 TCP Bridge started on {self.host}:{self.port}"
        )

    def tcp_server_loop(self):
        while rclpy.ok():
            self.get_logger().info("Waiting for TCP client...")
            client_socket, addr = self.server_socket.accept()
            self.get_logger().info(f"Client connected: {addr}")

            try:
                while True:
                    length_data = client_socket.recv(4)
                    if not length_data:
                        break

                    length = struct.unpack("!I", length_data)[0]
                    data = b""
                    while len(data) < length:
                        chunk = client_socket.recv(length - len(data))
                        if not chunk:
                            break
                        data += chunk

                    if not data:
                        break

                    goal_data = json.loads(data.decode())
                    goal_msg = NavigateToPose.Goal()
                    goal_msg.pose.header.frame_id = "map"
                    goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
                    goal_msg.pose.pose.position.x = goal_data["position"]["x"]
                    goal_msg.pose.pose.position.y = goal_data["position"]["y"]
                    goal_msg.pose.pose.position.z = goal_data["position"]["z"]
                    goal_msg.pose.pose.orientation.x = goal_data["orientation"]["x"]
                    goal_msg.pose.pose.orientation.y = goal_data["orientation"]["y"]
                    goal_msg.pose.pose.orientation.z = goal_data["orientation"]["z"]
                    goal_msg.pose.pose.orientation.w = goal_data["orientation"]["w"]

                    self.retry_count = 0
                    self.current_goal = goal_msg

                    if not self._action_client.wait_for_server(timeout_sec=5.0):
                        self.get_logger().error("NavigateToPose action server is not ready")
                        continue

                    self.send_navigation_goal(goal_msg)

            except Exception as exc:
                self.get_logger().error(f"TCP bridge error: {exc}")
            finally:
                client_socket.close()
                self.get_logger().info("Client disconnected")

    def send_navigation_goal(self, goal_msg):
        future = self._action_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback
        )
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info("Goal rejected")
            return

        self.get_logger().info("Goal accepted")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f"Distance remaining: {feedback.distance_remaining:.2f} m"
        )

    def get_result_callback(self, future):
        status = future.result().status
        if status == 4:
            self.get_logger().info("Navigation succeeded")
            self.retry_count = 0
            self.current_goal = None
            return

        self.get_logger().warning(f"Navigation failed with status {status}")
        if self.retry_count < self.max_retries and self.current_goal is not None:
            self.retry_count += 1
            self.get_logger().info(f"Retrying goal, attempt {self.retry_count}")
            self.send_navigation_goal(self.current_goal)
            return

        self.get_logger().error("Navigation failed after retries")
        self.retry_count = 0
        self.current_goal = None


def main(args=None):
    rclpy.init(args=args)
    node = Nav2TcpBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
