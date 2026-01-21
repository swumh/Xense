#!/bin/bash
# ================================================
# Xense SDK Ubuntu >= 1.6.7的xensesdk，需先执行此脚本
# 详情见文档：
# https://xensesdk-cn.readthedocs.io/zh-cn/latest/XenseSDK/usr/Installation.html#tag-xensesdkinstallation
# ================================================

# 1) 创建组（若已存在不会报错）
sudo groupadd -f xense

# 如果规则文件已存在，先删除（可选）
if [ -f '/etc/udev/rules.d/99-xense.rules' ]; then
    echo "Udev rule already exists, removing old one..."
    sudo rm /etc/udev/rules.d/99-xense.rules
fi

# 2) 写 udev 规则（匹配 vendor id 3938，适用于所有当前和将来 Xense 设备）
sudo tee /etc/udev/rules.d/99-xense.rules > /dev/null <<EOF
# 99-xense.rules - allow users in 'xense' group to access Xense Robotics USB devices
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="3938", MODE="0660", GROUP="${USER}"
EOF

# 3) 重新加载 udev 规则并触发（使规则生效）
sudo udevadm control --reload-rules
sudo udevadm trigger


echo "Xense udev rule installed. Please reboot"