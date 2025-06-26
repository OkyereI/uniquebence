#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Installing system dependencies for mysqlclient ---"
# Update package list
sudo apt-get update

# Install libmysqlclient-dev which provides the necessary headers for mysqlclient
sudo apt-get install -y libmysqlclient-dev

echo "--- System dependencies for mysqlclient installed. ---"

# Continue with the standard Python build process
# Render typically handles `pip install -r requirements.txt` automatically after `build.sh`
# but if you need to explicitly run it, you can add it here.
# For most Python web services, Render runs `pip install -r requirements.txt` after this script.
