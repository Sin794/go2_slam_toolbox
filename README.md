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
mkdir -p ~/go2_ws/src
cd ~/go2_ws/src
git clone <your-repo-url> unitree-go2-slam-toolbox
cd ..
colcon build
source install/setup.bash
```

如果你已经有自己的工作空间，把本仓库放进 `src/` 下编译即可。

## 运行前配置

公开发布后，最建议先检查这一份文件：

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
  cyclonedds_network_interface: ""
```

说明：

- 如果你的 `Unitree ROS 2` 依赖不在默认路径，改 `unitree_prefix`
- 如果你希望导航默认加载另一张地图，改 `default_map`
- 如果你想统一地图保存目录，改 `map_save_dir`
- 如果你的 CycloneDDS 需要绑定指定网口，例如 `enp2s0`，只改 `cyclonedds_network_interface`

也就是说，网口修改现在只需要改这一个文件，不用再去多个启动文件里找。

## 快速开始

### 1. 启动底层基线

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch go2_core go2_start.launch.py
```

这个启动文件会拉起：

- `go2_driver`
- `go2_robot_localization`
- `go2_perception`
- `rviz2`
- `slam_toolbox`

如果你临时不想启动 `slam_toolbox`，可以显式关闭：

```bash
ros2 launch go2_core go2_start.launch.py use_slamtoolbox:=false
```

### 2. 键盘控制机器人移动

新开一个终端：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

建议低速建图，先在安全、开阔环境完成传感器和坐标系检查。

### 3. 保存地图

只有在你显式使用 `use_slamtoolbox:=true`，并确认当前建图效果满足需求时，再执行保存地图。

建图完成后，再开一个终端执行：

```bash
source /opt/ros/humble/setup.bash
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

如果你想保存到别的位置，只需要把目标前缀换掉即可，例如：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run nav2_map_server map_saver_cli -f ~/my_maps/office_map
```

### 4. 使用已有地图启动导航

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch go2_navigation2 go2_nav2.launch.py nav_start_delay:=5.0
```

说明：

- 当前导航链路已经能启动
- 但如果地图本身来自实验性的 `PointCloud2 -> LaserScan` 建图结果，导航效果也会一起受影响
- 更稳妥的做法是先把底层驱动、TF、点云链路作为基线用起来，再决定是否继续沿用这套 2D 激光方案

默认地图路径来自：

- `src/base/go2_core/config/runtime_config.yaml` 里的 `default_map`

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

如果不想自动启动导航 RViz，可以这样：

```bash
ros2 launch go2_navigation2 go2_nav2.launch.py \
  nav_use_rviz:=false
```

### 5. 导航使用建议

导航启动后，建议按这个顺序操作：

1. 先不要立刻发送导航目标
2. 在 RViz 里使用 `2D Pose Estimate` 给机器人一个尽量准确的初始位姿
3. 等待 `amcl` 和局部代价地图稳定几秒
4. 再发送导航目标

补充说明：

- 当前导航启动文件默认会先启动定位，再延后启动 navigation controller，默认延时参数为 `nav_start_delay:=5.0`
- 实机上更稳妥的经验值可以先用 `nav_start_delay:=5.0`
- 如果你修改了 `src/` 下的启动文件或参数文件，需要重新执行 `colcon build --packages-select go2_navigation2`
- 如果你修改了 `go2_driver`，需要重新执行 `colcon build --packages-select go2_driver`
- `go2_driver` 现在已经修复了雷达位姿到 `base_footprint` 的朝向相关换算；旧地图如果总觉得和现场有系统性偏差，建议重新建图

## 常用话题与模块说明

- `go2_driver`
  负责底层状态、IMU、里程计等基础数据
- `go2_perception`
  负责点云处理与 `LaserScan` 实验链路生成
- `go2_core`
  负责整体启动编排与 `robot_localization` 参数组织
- `go2_slam`
  封装 `slam_toolbox` 在线建图启动
- `go2_navigation2`
  封装 Nav2 的定位与导航启动链路

## 适合继续完善的方向

- 补充更稳定的地图保存与加载流程
- 继续统一整理默认参数文件，减少环境差异带来的启动问题
- 增加更完整的 TF/话题说明文档
- 增加导航调参说明和实测效果
- 清理仓库中的构建产物后再公开发布

## 公开到 GitHub 前的建议

建议在发布前顺手处理这几项：

- 添加 `.gitignore`，忽略 `build/`、`install/`、`log/`
- 补充 `LICENSE`
- 将 `package.xml` 里的 `description`、`maintainer`、`license` 从 `TODO` 改成真实信息
- 检查 `runtime_config.yaml` 是否已经改成适合你自己机器的配置
- 如果仓库包含第三方代码或资源，确认对应许可证是否允许分发

## 参考

- Unitree Go2 官方开发文档
- ROS 2 Humble 官方文档
- `slam_toolbox`
- `Navigation2`

## 说明

这个项目更偏向个人学习整理版本，不保证在所有 Go2 固件、网络环境和传感器配置下都能直接运行。如果你在使用过程中修复了问题或完善了导航能力，欢迎继续补充。
