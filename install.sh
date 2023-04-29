#!/bin/bash

set -e

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

# Change to directory where the script is located
cd "$(dirname "$0")"

# Create the application directory if it does not exist
APP_PATH="/opt/pvpccheap"
if [ ! -d "$APP_PATH" ]; then
    sudo mkdir -p "$APP_PATH"
fi

# Creates a group and user for the application if they don't exist
sudo getent group pvpccheap || sudo groupadd -r pvpccheap
sudo getent passwd pvpccheap || sudo useradd -r -g pvpccheap -d /opt/pvpccheap -s /sbin/nologin -c "PVPC Cheap user" pvpccheap

# Copy the package file to the application directory and set the permissions
sudo chown pvpccheap: /opt/pvpccheap

# Install the package in the application directory using pip
# shellcheck disable=SC2144
if [ -e dist/*.whl ]; then
    sudo -u pvpccheap pip install --target /opt/pvpccheap dist/*.whl
elif [ -e dist/*.tar.gz ]; then
    sudo -u pvpccheap pip install --target /opt/pvpccheap dist/*.tar.gz
else
    echo "Doesn't exist any package to install. Be sure to build the package before running this script."
    exit 1
fi

# Install systemd unit file
sudo cp pvpccheap/configs/pvpccheap.service /etc/systemd/system/pvpccheap.service
# Enable and activate systemd unit
sudo systemctl enable pvpccheap.service
sudo systemctl start pvpccheap.service

# Print success message
echo "PVPC Cheap has been installed successfully."