#!/bin/bash

# Check if python and pip are installed
if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed. Please install it and try again."
    exit
fi

if ! command -v pip3 &> /dev/null
then
    echo "Pip3 is not installed. Please install it and try again. If you are using Ubuntu, you can install it with 'sudo apt install python3-pip'."
    exit
fi

# Create the application directory if it does not exist
APP_PATH="/opt/pvpccheap"
if [ ! -d "$APP_PATH" ]; then
    sudo mkdir -p "$APP_PATH"
fi

# Install necessary packages
pip3 install --user wheel

# Creates a group and user for the application if they don't exist
sudo getent group pvpccheap || sudo groupadd -r pvpccheap
sudo getent passwd pvpccheap || sudo useradd -r -g pvpccheap -d /opt/pvpccheap -s /sbin/nologin -c "PVPC Cheap user" pvpccheap

# Copy the package file to the application directory and set the permissions
sudo cp dist/pvpccheap-0.1-py3-none-any.whl /opt/pvpccheap/
sudo chown pvpccheap:pvpccheap /opt/pvpccheap/pvpccheap-0.1-py3-none-any.whl

# Assign permissions to the application folder
APP_PATH="/opt/pvpccheap"
sudo chown -R pvpccheap:pvpccheap "$APP_PATH"
sudo chmod -R 750 "$APP_PATH"

sudo -H -u pvpccheap python3 -m venv /opt/pvpccheap/venv
# Activate virtual environment and install package
sudo -H -u pvpccheap bash -c "source /opt/pvpccheap/venv/bin/activate && /opt/pvpccheap/venv/bin/pip install /opt/pvpccheap/pvpccheap-0.1-py3-none-any.whl"

# Install systemd unit file
sudo cp pvpccheap/configs/pvpccheap.service /etc/systemd/system/pvpccheap.service
# Enable and activate systemd unit
sudo systemctl enable pvpccheap.service
sudo systemctl start pvpccheap.service

# Print success message
echo "PVPC Cheap has been installed successfully."