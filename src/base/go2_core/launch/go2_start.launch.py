import os
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
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

    #获取各功能包
    go2_driver_pkg = get_package_share_directory("go2_driver")
    go2_core_pkg = get_package_share_directory("go2_core")
    go2_slam_pkg = get_package_share_directory("go2_slam")
    go2_perception_pkg = get_package_share_directory("go2_perception")
    runtime_config = _load_runtime_config(go2_core_pkg)
    cyclonedds_uri = _build_cyclonedds_uri(runtime_config["cyclonedds_network_interface"])
    unitree_prefix = LaunchConfiguration("unitree_prefix")
    
    # 添加启动开关
    use_slamtoolbox = DeclareLaunchArgument(
        name="use_slamtoolbox",
        default_value="true"
    )
    unitree_prefix_arg = DeclareLaunchArgument(
        "unitree_prefix",
        default_value=runtime_config["unitree_prefix"],
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

    # 里程计融合imu
    go2_robot_localization = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(go2_core_pkg, "launch", "go2_robot_localization.launch.py")
            )
        )

    # 启动驱动包
    go2_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(go2_driver_pkg, "launch", "driver.launch.py")
        )   
    )

    # 点云处理
    go2_pointcloud_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(go2_perception_pkg, "launch", "go2_pointcloud.launch.py")
            )
        )

    # slam-toolbox 配置
    go2_slamtoolbox_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(go2_slam_pkg, "launch", "go2_slamtoolbox.launch.py")
            ),
            condition=IfCondition(LaunchConfiguration('use_slamtoolbox'))
        )

    # 包含rviz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(go2_core_pkg, "rviz2", "display.rviz")],
        output='screen'
    )

    return LaunchDescription([
        use_slamtoolbox,
        unitree_prefix_arg,
        unitree_ld_library,
        unitree_pythonpath,
        *([cyclonedds_env] if cyclonedds_env is not None else []),
        go2_driver_launch,
        go2_robot_localization,
        go2_pointcloud_launch,
        go2_slamtoolbox_launch,
        rviz_node
    ])
