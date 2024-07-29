#!/bin/bash

# Pull the Amazon Linux image from Docker Hub
docker pull amazonlinux

# Run the Amazon Linux container in detached mode
docker run -d --name telemetry amazonlinux tail -f /dev/null

# Install Python, pip, and other dependencies inside the container
docker exec -it telemetry /bin/bash -c "yum update -y && yum install -y python3-pip zip && python3 -m pip install virtualenv"

# Create a virtual environment and install dependencies
docker exec -it telemetry /bin/bash -c "python3 -m venv temp-venv && source temp-venv/bin/activate && mkdir telemetry && cd telemetry && pip install crhelper sumologic-appclient-sdk future_fstrings setuptools -t ."

# Copy python file from host to container
docker cp ./lambda_function.py telemetry:/telemetry

# Zip the contents of the telemetry directory
docker exec -it telemetry /bin/bash -c "cd telemetry && ls -l && zip -r ../telemetry.zip ."

# Copy the telemetry.zip file from the container to the host
docker cp telemetry:/telemetry.zip ./telemetry.zip

# Stop and remove the container
docker stop telemetry
docker rm telemetry