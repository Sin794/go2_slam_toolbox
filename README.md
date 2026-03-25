基于https://github.com/FishPlusDragon/unitree-go2-slam-toolbox

## 依赖

系统依赖可以先安装这些常用包：

```bash
sudo apt update
sudo apt install -y \
  ros-humble-robot-localization \
  ros-humble-slam-toolbox \
  ros-humble-nav2-bringup \
  ros-humble-navigation2 \
  ros-humble-teleop-twist-keyboard
```

如果编译期间还有缺包，再按报错补装对应的 `ros-humble-*` 包即可。


## 安装

如果你准备把这个仓库作为独立 ROS 2 工作空间使用，可以这样放置：

```bash
mkdir -p ~/go2_ws_toolbox/src
cd ~/go2_ws_toolbox/src
git clone https://github.com/Sin794/go2_slam_toolbox.git
cd ..
source ~/unitree_ros2/setup.sh
colcon build
source install/setup.bash
```

## 运行前配置

- `src/base/go2_core/config/runtime_config.yaml`

当前所有“环境相关的默认值”都会优先从这里读取，包括：

- `unitree_prefix`
- `default_map`
- `map_save_dir`
- `cyclonedds_network_interface`

示例：

```yaml
runtime:
  unitree_prefix: ~/unitree_ros2/cyclonedds_ws/install
  default_map: ~/go2_maps/test.yaml
  map_save_dir: ~/go2_maps
  cyclonedds_network_interface: "enp8s0"
```

说明：

- 如果你的 `Unitree ROS 2` 依赖不在默认路径，改 `unitree_prefix`
- 如果你希望导航默认加载另一张地图，改 `default_map`
- 如果你想统一地图保存目录，改 `map_save_dir`
- 如果你的 CycloneDDS 需要绑定指定网口，例如 `enp8s0`，只改 `cyclonedds_network_interface`


## 快速开始

### 1. 启动底层基线

```bash
source ~/unitree_ros2/setup.sh
source install/setup.bash
ros2 launch go2_core go2_start.launch.py
```

### 2. 键盘控制机器人移动

新开一个终端：

```bash
source ~/unitree_ros2/setup.sh
source install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

建议低速建图，先在安全、开阔环境完成传感器和坐标系检查。

### 3. 保存地图

建图完成后，再开一个终端执行：

```bash
source ~/unitree_ros2/setup.sh
source install/setup.bash
ros2 run nav2_map_server map_saver_cli -f ~/go2_maps/test
```

这条命令会生成两个文件：

- `~/go2_maps/test.pgm`
- `~/go2_maps/test.yaml`

如果目录不存在，先创建：

```bash
mkdir -p ~/go2_maps
```

### 4. 使用已有地图启动导航

```bash
source ~/unitree_ros2/setup.sh
source install/setup.bash
ros2 launch go2_navigation2 go2_nav2.launch.py
```

你也可以在启动时显式传参覆盖：

```bash
ros2 launch go2_navigation2 go2_nav2.launch.py \
  map:=/absolute/path/to/map.yaml
```

例如：

```bash
ros2 launch go2_navigation2 go2_nav2.launch.py \
  map:=~/go2_maps/test.yaml
```

