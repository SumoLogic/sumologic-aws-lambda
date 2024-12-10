#!/bin/bash

# Pull the Amazon Linux image from Docker Hub
# aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
docker pull public.ecr.aws/lambda/python:3.13-x86_64

# Run the Amazon Linux container in detached mode
docker run -d --name telemetry public.ecr.aws/lambda/python:3.13-x86_64 lambda_function.lambda_handler

# Install dependencies inside the container
docker exec -it telemetry /bin/bash -c "dnf install -y zip"

# Create a virtual environment and install dependencies
docker exec -it telemetry /bin/bash -c "python3 -m venv temp-venv && source temp-venv/bin/activate && mkdir telemetry && cd telemetry && pip install crhelper sumologic-appclient-sdk future_fstrings setuptools -t ."

# Copy python file from host to container
docker cp ./lambda_function.py telemetry:/var/task/telemetry
docker cp ./metadata.yaml telemetry:/var/task/telemetry

# Zip the contents of the telemetry directory
docker exec -it telemetry /bin/bash -c "cd telemetry && ls -l && zip -r ../telemetry.zip ."

# Copy the telemetry.zip file from the container to the host
docker cp telemetry:/var/task/telemetry.zip ./telemetry.zip

# Stop and remove the container
docker stop telemetry
docker rm telemetry