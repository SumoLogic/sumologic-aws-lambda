#!/bin/bash

# Pull the Amazon lambda Linux image from Docker Hub
docker pull public.ecr.aws/lambda/python:3.12-x86_64

# Run the Amazon lambda Linux container in detached mode
docker run -d --name sumologic-app-utils public.ecr.aws/lambda/python:3.12-x86_64 lambda_function.lambda_handler

# Install dependencies inside the container
docker exec -it sumologic-app-utils /bin/bash -c "dnf install -y zip"

# Create a virtual environment and install dependencies
docker exec -it sumologic-app-utils /bin/bash -c "python3 -m venv temp-venv && source temp-venv/bin/activate && mkdir sumo_app_utils && cd sumo_app_utils && pip install crhelper jsonschema requests retrying -t ."

# Copy python file from host to container
docker cp src/. sumologic-app-utils:/var/task/sumo_app_utils

# Zip the contents of the sumologic-app-utils directory
docker exec -it sumologic-app-utils /bin/bash -c "cd sumo_app_utils && ls -l && zip -r ../sumo_app_utils.zip ."

# Copy the sumologic-app-utils.zip file from the container to the host
docker cp sumologic-app-utils://var/task/sumo_app_utils.zip ./sumo_app_utils.zip

# Stop and remove the container
docker stop sumologic-app-utils
docker rm sumologic-app-utils