import os
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def _load_runtime_config(go2_core_pkg):
    config_path = os.path.join(go2_core_pkg, "config", "runtime_config.yaml")
    defaults = {
        "unitree_prefix": os.path.expanduser("~/unitree_ros2/cyclonedds_ws/install"),
        "default_map": os.path.expanduser("~/go2_maps/test.yaml"),
        "map_save_dir": os.path.expanduser("~/go2_maps"),
        "cyclonedds_network_interface": "",
    }

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as config_file:
            loaded = yaml.safe_load(config_file) or {}
        runtime = loaded.get("runtime", {})
        defaults.update({k: v for k, v in runtime.items() if v is not None})

    for key, value in defaults.items():
        if isinstance(value, str):
            defaults[key] = os.path.expandvars(os.path.expanduser(value))

    return defaults


def _build_cyclonedds_uri(interface_name):
    if not interface_name:
        return None
    return (
        "<CycloneDDS><Domain><General><Interfaces>"
        f'<NetworkInterface name="{interface_name}" priority="default" multicast="default" />'
        "</Interfaces></General></Domain></CycloneDDS>"
    )


def generate_launch_description():
    nav2_pkg = get_package_share_directory("go2_navigation2")
    bringup_pkg = get_package_share_directory("nav2_bringup")
    go2_core_pkg = get_package_share_directory("go2_core")
    go2_driver_pkg = get_package_share_directory("go2_driver")
    go2_perception_pkg = get_package_share_directory("go2_perception")
    runtime_config = _load_runtime_config(go2_core_pkg)
    cyclonedds_uri = _build_cyclonedds_uri(runtime_config["cyclonedds_network_interface"])

    use_sim_time = LaunchConfiguration("use_sim_time")
    map_yaml_path = LaunchConfiguration("map")
    nav2_param_path = LaunchConfiguration("params_file")
    start_tcp_bridge = LaunchConfiguration("start_tcp_bridge")
    tcp_config_path = LaunchConfiguration("tcp_config")
    nav_use_rviz = LaunchConfiguration("nav_use_rviz")
    nav_start_delay = LaunchConfiguration("nav_start_delay")
    unitree_prefix = LaunchConfiguration("unitree_prefix")
    use_robot_localization = LaunchConfiguration("use_robot_localization")

    rviz_config_dir = os.path.join(bringup_pkg, "rviz", "nav2_default_view.rviz")

    use_sim_time_arg = DeclareLaunchArgument("use_sim_time", default_value="false")
    map_arg = DeclareLaunchArgument(
        "map",
        default_value=runtime_config["default_map"],
    )
    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=os.path.join(nav2_pkg, "config", "nav2_params.yaml"),
    )
    start_tcp_bridge_arg = DeclareLaunchArgument(
        "start_tcp_bridge",
        default_value="false",
    )
    tcp_config_arg = DeclareLaunchArgument(
        "tcp_config",
        default_value=os.path.join(nav2_pkg, "config", "tcp_config.yaml"),
    )
    use_rviz_arg = DeclareLaunchArgument("nav_use_rviz", default_value="true")
    nav_start_delay_arg = DeclareLaunchArgument(
        "nav_start_delay",
        default_value="5.0",
    )
    unitree_prefix_arg = DeclareLaunchArgument(
        "unitree_prefix",
        default_value=runtime_config["unitree_prefix"],
    )
    use_robot_localization_arg = DeclareLaunchArgument(
        "use_robot_localization",
        default_value="false",
    )

    unitree_ld_library = SetEnvironmentVariable(
        name="LD_LIBRARY_PATH",
        value=[
            unitree_prefix,
            "/unitree_go/lib:",
            unitree_prefix,
            "/unitree_api/lib:",
            unitree_prefix,
            "/unitree_hg/lib:",
            unitree_prefix,
            "/rmw_cyclonedds_cpp/lib:",
            unitree_prefix,
            "/cyclonedds/lib:",
            EnvironmentVariable("LD_LIBRARY_PATH", default_value=""),
        ],
    )
    unitree_pythonpath = SetEnvironmentVariable(
        name="PYTHONPATH",
        value=[
            unitree_prefix,
            "/unitree_go/local/lib/python3.10/dist-packages:",
            unitree_prefix,
            "/unitree_api/local/lib/python3.10/dist-packages:",
            unitree_prefix,
            "/unitree_hg/local/lib/python3.10/dist-packages:",
            EnvironmentVariable("PYTHONPATH", default_value=""),
        ],
    )
    cyclonedds_env = (
        SetEnvironmentVariable(name="CYCLONEDDS_URI", value=cyclonedds_uri)
        if cyclonedds_uri
        else None
    )

    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg, "launch", "localization_launch.py")
        ),
        launch_arguments={
            "map": map_yaml_path,
            "params_file": nav2_param_path,
            "use_sim_time": use_sim_time,
        }.items(),
    )

    nav2_launch = TimerAction(
        period=nav_start_delay,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(bringup_pkg, "launch", "navigation_launch.py")
                ),
                launch_arguments={
                    "params_file": nav2_param_path,
                    "use_sim_time": use_sim_time,
                }.items(),
            )
        ],
    )

    go2_robot_localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(go2_core_pkg, "launch", "go2_robot_localization.launch.py")
        ),
        condition=IfCondition(use_robot_localization),
    )

    go2_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(go2_driver_pkg, "launch", "driver.launch.py")
        ),
        launch_arguments={"use_rviz": "false"}.items(),
    )

    cloud_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(go2_perception_pkg, "launch", "go2_pointcloud.launch.py")
        )
    )

    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config_dir],
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
        condition=IfCondition(nav_use_rviz),
    )

    nav2_tcp_bridge = Node(
        package="go2_navigation2",
        executable="navigation_command_tcpbridge.py",
        name="nav2_tcp_bridge",
        output="screen",
        parameters=[{"config_path": tcp_config_path}],
        condition=IfCondition(start_tcp_bridge),
    )

    return LaunchDescription(
        [
            use_sim_time_arg,
            map_arg,
            params_file_arg,
            start_tcp_bridge_arg,
            tcp_config_arg,
            use_rviz_arg,
            nav_start_delay_arg,
            unitree_prefix_arg,
            use_robot_localization_arg,
            unitree_ld_library,
            unitree_pythonpath,
            *([cyclonedds_env] if cyclonedds_env is not None else []),
            go2_driver_launch,
            go2_robot_localization,
            cloud_launch,
            localization_launch,
            nav2_launch,
            rviz2,
            nav2_tcp_bridge,
        ]
    )
