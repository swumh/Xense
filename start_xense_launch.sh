#!/bin/bash
# Xense ROS数据发布节点启动脚本
# 通用启动器，支持启动各种数据类型的ROS发布节点

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SRC_DIR="$SCRIPT_DIR/src"
PYTHON_SCRIPT="${SRC_DIR}/main.py"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 解析命令行参数
USE_NEW_TERMINAL=true
BACKGROUND=false
CONDA_ENV="xenseenv39"
PYTHON_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-new-terminal|-n)
            USE_NEW_TERMINAL=false
            shift
            ;;
        --background|-b)
            BACKGROUND=true
            USE_NEW_TERMINAL=false
            shift
            ;;
        --conda-env)
            CONDA_ENV="$2"
            shift 2
            ;;
        --script)
            PYTHON_SCRIPT="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [选项] [Python脚本参数]"
            echo ""
            echo "选项:"
            echo "  --no-new-terminal, -n  在当前终端中运行"
            echo "  --background, -b       在后台运行"
            echo "  --conda-env NAME      指定conda环境（默认: xenseenv39）"
            echo "  --script PATH         指定Python脚本（默认: src/main.py）"
            echo "  --help, -h            显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                          # 在新终端启动"
            echo "  $0 --sensor-id OG000266     # 指定传感器ID"
            echo "  $0 --config config.json     # 使用配置文件"
            exit 0
            ;;
        *)
            PYTHON_ARGS+=("$1")
            shift
            ;;
    esac
done

# 构建要在新终端中执行的命令
build_command() {
    # 将参数数组转换为字符串，正确处理引号
    local args_str=""
    for arg in "${PYTHON_ARGS[@]}"; do
        # 转义引号和特殊字符
        local escaped_arg=$(printf '%q' "$arg")
        args_str="${args_str} ${escaped_arg}"
    done
    
    cat <<EOF
# 激活conda环境
source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || \\
source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null || \\
source /opt/conda/etc/profile.d/conda.sh 2>/dev/null

if [ -z "\$CONDA_PREFIX" ]; then
    echo "错误: 未找到conda"
    read -n 1
    exit 1
fi

conda activate ${CONDA_ENV} 2>/dev/null || {
    echo "错误: 未找到环境 ${CONDA_ENV}"
    read -n 1
    exit 1
}

# 设置ROS环境
if [ -f "/opt/ros/noetic/setup.bash" ]; then
    source /opt/ros/noetic/setup.bash
elif [ -f "/opt/ros/melodic/setup.bash" ]; then
    source /opt/ros/melodic/setup.bash
elif [ -f "/opt/ros/foxy/setup.bash" ]; then
    source /opt/ros/foxy/setup.bash
else
    echo "警告: 未找到ROS"
    read -n 1
    exit 1
fi

# 检查roscore
if ! rostopic list &>/dev/null 2>&1; then
    echo "警告: roscore未运行，等待5秒..."
    sleep 5
fi

# 检查ROS Python依赖
if ! python3 -c "import rospy" 2>/dev/null; then
    pip install -q pyyaml rospkg catkin_pkg
fi

# 运行发布节点
cd "${SCRIPT_DIR}"
python3 "${PYTHON_SCRIPT}"${args_str}

echo ""
echo "节点已停止，按任意键关闭..."
read -n 1
EOF
}

# 判断运行方式
if [ "$USE_NEW_TERMINAL" = true ]; then
    print_info "启动ROS发布节点..."
    
    # 构建命令字符串
    CMD_STR=$(build_command)
    
    # 尝试不同的终端模拟器
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="Xense ROS发布节点" --window -- bash -c "$CMD_STR; exec bash" &
    elif command -v xterm &> /dev/null; then
        xterm -title "Xense ROS发布节点" -e bash -c "$CMD_STR; exec bash" &
    elif command -v konsole &> /dev/null; then
        konsole --title "Xense ROS发布节点" -e bash -c "$CMD_STR; exec bash" &
    elif command -v terminator &> /dev/null; then
        terminator --title="Xense ROS发布节点" -e "bash -c \"$CMD_STR; exec bash\"" &
    elif command -v xfce4-terminal &> /dev/null; then
        xfce4-terminal --title="Xense ROS发布节点" -e "bash -c \"$CMD_STR; exec bash\"" &
    else
        print_error "未找到支持的终端模拟器"
        USE_NEW_TERMINAL=false
    fi
    
    if [ "$USE_NEW_TERMINAL" = true ]; then
        sleep 1
        exit 0
    fi
fi

# 在当前终端运行或后台运行
if [ "$BACKGROUND" = true ]; then
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || \
    source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null || \
    source /opt/conda/etc/profile.d/conda.sh 2>/dev/null
    
    conda activate ${CONDA_ENV}
    
    if [ -f "/opt/ros/noetic/setup.bash" ]; then
        source /opt/ros/noetic/setup.bash
    elif [ -f "/opt/ros/melodic/setup.bash" ]; then
        source /opt/ros/melodic/setup.bash
    fi
    
    cd "$SCRIPT_DIR"
    nohup python3 "$PYTHON_SCRIPT" "${PYTHON_ARGS[@]}" > "$SCRIPT_DIR/xense.log" 2>&1 &
    XENSE_PID=$!
    echo $XENSE_PID > "$SCRIPT_DIR/xense.pid"
    print_info "后台启动，PID: $XENSE_PID"
    print_info "日志: $SCRIPT_DIR/xense.log"
else
    # 在当前终端直接运行
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || \
    source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null || \
    source /opt/conda/etc/profile.d/conda.sh 2>/dev/null
    
    if [ -z "$CONDA_PREFIX" ]; then
        print_error "未找到conda"
        exit 1
    fi
    
    conda activate ${CONDA_ENV}
    
    if [ -f "/opt/ros/noetic/setup.bash" ]; then
        source /opt/ros/noetic/setup.bash
    elif [ -f "/opt/ros/melodic/setup.bash" ]; then
        source /opt/ros/melodic/setup.bash
    fi
    
    if command -v rostopic &> /dev/null && ! rostopic list &>/dev/null 2>&1; then
        print_error "roscore未运行"
        sleep 2
    fi
    
    cd "$SCRIPT_DIR"
    python3 "$PYTHON_SCRIPT" "${PYTHON_ARGS[@]}"
fi
