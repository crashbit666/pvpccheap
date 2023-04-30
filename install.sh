Este es el script de instalacion:
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
if [ ! -d "/opt/pvpccheap" ]; then
    sudo mkdir -p /opt/pvpccheap
fi

# Creates a group and user for the application if they don't exist
sudo getent group pvpccheap || sudo groupadd -r pvpccheap
sudo getent passwd pvpccheap || sudo useradd -r -g pvpccheap -d /opt/pvpccheap -s /sbin/nologin -c "PVPC Cheap user" pvpccheap

# Set the owner of the application directory to the user created
sudo chown pvpccheap: /opt/pvpccheap

# Create a virtual environment in the application directory
sudo -u pvpccheap python3 -m venv /opt/pvpccheap/venv

# Change permissions to the whl and tar.gz files
sudo chown pvpccheap: dist/*.whl
sudo chown pvpccheap: dist/*.tar.gz

# Install the package in the virtual environment using pip
installed=0
for package in dist/*.whl dist/*.tar.gz; do
    if [ -e "${package}" ]; then
        sudo -u pvpccheap bash -c "source /opt/pvpccheap/venv/bin/activate && pip install '${package}'"
        installed=1
    fi
done

if [ $installed -eq 0 ]; then
    echo "Doesn't exist any package to install. Be sure to build the package before running this script."
    exit 1
fi

if [ $installed -eq 0 ]; then
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