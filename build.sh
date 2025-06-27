# #!/usr/bin/env bash

# # Exit immediately if a command exits with a non-zero status.
# set -e

# echo "--- Starting custom build script ---"

# echo "--- Installing system dependencies for mysqlclient ---"
# # Update package list
# sudo apt-get update

# # Install libmysqlclient-dev which provides the necessary headers for mysqlclient
# # This is crucial for mysqlclient to compile.
# sudo apt-get install -y libmysqlclient-dev

# echo "--- System dependencies for mysqlclient installed. ---"

# echo "--- Setting up Python 3.11 virtual environment ---"
# # Render's default Python executable might still be 3.13 if not explicitly linked.
# # We explicitly use the python3.11 executable to create the venv.
# # Ensure python3.11 is available on Render's build image (it usually is if runtime.txt works).
# /usr/bin/python3.11 -m venv venv_custom_build
# source venv_custom_build/bin/activate
# echo "--- Python 3.11 virtual environment activated. ---"

# # Upgrade pip and setuptools within the new venv
# pip install --upgrade pip setuptools wheel

# echo "--- Installing Python dependencies from requirements.txt ---"
# # Install Python packages within the activated Python 3.11 venv
# pip install -r requirements.txt

# echo "--- Python dependencies installed. ---"

# # Important: After this script runs, Render will typically use the activated venv
# # for subsequent commands like `gunicorn app:app`.
#!/usr/bin/env bash
#!/usr/bin/env bash
set -eo pipefail

echo "=== Installing Python Packages ==="
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "=== Build Completed Successfully ==="