#!/usr/bin/env bash
# File: pi5_sender_node/install_pi5_fastboot.sh
# Description: Configures Raspberry Pi 5 for <5s fast boot and installs the sender service
# License: MIT
set -e

echo "[*] Stripping any OS filesystem metadata or temporary files..."
find . /boot/firmware /opt/diode-node -name '._*' -o -name '.DS_Store' -o -name 'Thumbs.db' -delete 2>/dev/null || true
rm -rf /boot/firmware/.Spotlight-V100 /boot/firmware/.fseventsd /boot/firmware/.Trashes 2>/dev/null || true

echo "[*] Installing core Python & camera dependencies..."
apt-get update
apt-get install -y python3-picamera2 python3-opencv python3-nacl python3-serial
apt-get install -y hailo-all || echo "[i] hailo-all not available on this board (e.g. Pi 4 or non-Hailo OS); using CPU ONNX / Motion fallback."

echo "[*] Installing sender_node.py and generate_keys.py to /opt/diode-node..."
mkdir -p /opt/diode-node /etc/trailcam
cp sender_node.py /opt/diode-node/sender_node.py
cp generate_keys.py /opt/diode-node/generate_keys.py
chmod +x /opt/diode-node/sender_node.py /opt/diode-node/generate_keys.py

if [ -f "./node_key.json" ] && [ ! -f "/etc/trailcam/node_key.json" ]; then
    echo "[*] Installing pre-generated node_key.json to /etc/trailcam/node_key.json..."
    cp ./node_key.json /etc/trailcam/node_key.json
    chmod 600 /etc/trailcam/node_key.json
fi

if [ ! -f "/etc/trailcam/node.env" ]; then
    cat << 'EOF' > /etc/trailcam/node.env
# Field Camera Node Configuration (/etc/trailcam/node.env)
# Note: NODE_ID is automatically loaded from /etc/trailcam/node_key.json unless overridden here.
NODE_KEY_FILE=/etc/trailcam/node_key.json
ALLOW_EXAMPLE_KEYS=0
LOCAL_IP=10.10.0.10
RECEIVER_IP=10.10.0.100
UDP_PORT=5514
EOF
    chmod 600 /etc/trailcam/node.env
fi

echo "[*] Installing systemd early-boot unit..."
cp diode-node.service /etc/systemd/system/diode-node.service
systemctl daemon-reload
systemctl enable diode-node.service

echo "[*] Disabling Wi-Fi, Bluetooth, unnecessary services & serial login console for <5s RF-silent fast boot..."
systemctl disable systemd-networkd-wait-online.service NetworkManager-wait-online.service || true
systemctl disable --now wpa_supplicant.service bluetooth.service hciuart.service ModemManager.service avahi-daemon.service || true
systemctl disable triggerhappy.service cron.service rsyslog.service || true
systemctl stop serial-getty@ttyAMA0.service serial-getty@serial0.service || true
systemctl disable serial-getty@ttyAMA0.service serial-getty@serial0.service || true
if command -v rfkill >/dev/null 2>&1; then
    rfkill block wifi bluetooth || true
fi

BOOT_CFG="/boot/firmware/config.txt"
if [ ! -f "$BOOT_CFG" ] && [ -f "/boot/config.txt" ]; then
    BOOT_CFG="/boot/config.txt"
fi
if [ -f "$BOOT_CFG" ]; then
    echo "[*] Configuring PL011 UART0 (Pins 8/10) and hardware Wi-Fi/BT RF-disable overlays in $BOOT_CFG..."
    grep -q "^dtparam=uart0=on" "$BOOT_CFG" || echo "dtparam=uart0=on" >> "$BOOT_CFG"
    grep -q "^enable_uart=1" "$BOOT_CFG" || echo "enable_uart=1" >> "$BOOT_CFG"
    grep -q "^dtoverlay=disable-wifi" "$BOOT_CFG" || echo "dtoverlay=disable-wifi" >> "$BOOT_CFG"
    grep -q "^dtoverlay=disable-bt" "$BOOT_CFG" || echo "dtoverlay=disable-bt" >> "$BOOT_CFG"
fi

CMDLINE_CFG="/boot/firmware/cmdline.txt"
if [ ! -f "$CMDLINE_CFG" ] && [ -f "/boot/cmdline.txt" ]; then
    CMDLINE_CFG="/boot/cmdline.txt"
fi
if [ -f "$CMDLINE_CFG" ]; then
    sed -i 's/console=serial0,[0-9]* //g; s/console=ttyAMA0,[0-9]* //g' "$CMDLINE_CFG" || true
fi

echo "[*] Done! Next: run 'python3 /opt/diode-node/generate_keys.py --node <NODE_ID> --write-node-key /etc/trailcam/node_key.json' if not yet provisioned, then enable OverlayFS in raspi-config."
