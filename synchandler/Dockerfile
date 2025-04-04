# Use a lightweight Python image
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    python3-pip \
    skopeo \
    podman && \
    pip3 install flask boto3 oci && \
    apt-get clean

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Configure Podman to run in rootless mode
RUN mkdir -p /etc/containers && \
    echo '[engine]' > /etc/containers/containers.conf && \
    echo 'cgroup_manager = "cgroupfs"' >> /etc/containers/containers.conf && \
    echo 'events_logger = "file"' >> /etc/containers/containers.conf

# Install procps for ps command
# This is needed for checking if podman is still running - cmd = 'ps aux'
RUN apt-get update && apt-get install -y procps

# Create logs directory
RUN mkdir -p /app/logs

# Copy the application code
COPY handler.py /app/handler.py

# Set the working directory
WORKDIR /app

# Expose the port for the HTTP server
EXPOSE 8080

# Set the entrypoint
ENTRYPOINT ["python3", "handler.py"]