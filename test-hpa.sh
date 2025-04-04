#!/bin/bash
# filepath: /home/opc/code/dpreg/imagesyncdeployment/test-hpa.sh


ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$AWS_REPO_NAME"
OCIR_REPO="mel.ocir.io/${OCIR_TENANCY}/dppoc/test-repo"
TEST_DURATION=600  # 10 minutes
NUM_PARALLEL=3     # Number of parallel operations
DELAY=5           # Seconds between operations

# Create timestamp tag
START_TIME=$(date +%s)
echo "=== Starting HPA test at $(date) ==="
echo "This test will run for $TEST_DURATION seconds with $NUM_PARALLEL parallel operations"

# Function to login to repos
function login_to_repos() {
  echo "Logging in to ECR..."
  aws ecr get-login-password --region us-west-2 | podman login --username AWS --password-stdin $ECR_REPO
  
  echo "Logging in to OCIR..."
  podman login mel.ocir.io --username "$OCIR_USERNAME" --password "$OCIR_PASSWORD"
}

# Function to create and push a test image
function push_test_image() {
  local tag="test-$1"
  
  # Create a simple test image with random content
  mkdir -p /tmp/test-image
  dd if=/dev/urandom of=/tmp/test-image/random-data bs=1M count=$((1 + $RANDOM % 5))
  
  # Create a simple Dockerfile
  cat > /tmp/test-image/Dockerfile << EOF
FROM alpine:latest
COPY random-data /data
CMD ["sleep", "infinity"]
EOF

  # Build and push
  echo "Building test image with tag $tag..."
  cd /tmp/test-image
  podman build -t $ECR_REPO:$tag .
  
  echo "Pushing image with tag $tag to ECR..."
  podman push $ECR_REPO:$tag
  
  # Clean up
  podman rmi $ECR_REPO:$tag
  rm -rf /tmp/test-image
}

# Function to directly hit the API (simulating ECR events)
function call_sync_api() {
  local tag="test-$1"
  
  # Create JSON payload
  cat > /tmp/payload.json << EOF
{
  "account": "$AWS_ACCOUNT_ID",
  "region": "$AWS_REGION",
  "detail": {
    "action-type": "PUSH",
    "repository-name": "$AWS_REPO_NAME",
    "image-tag": "$tag"
  }
}
EOF

  # Call the API
  echo "Calling sync API for tag $tag..."
  curl -X POST $SERVICE_URL \
    -H "Content-Type: application/json" \
    -d @/tmp/payload.json
}

# Login to both registries
login_to_repos

# Run the test for specified duration
END_TIME=$((START_TIME + TEST_DURATION))
COUNTER=0

while [ $(date +%s) -lt $END_TIME ]; do
  # Launch multiple operations in parallel
  for i in $(seq 1 $NUM_PARALLEL); do
    COUNTER=$((COUNTER+1))
    
    # Choose between actual push or API call
    if [ $((COUNTER % 2)) -eq 0 ]; then
      # For even counters, do actual push (more resource intensive)
      push_test_image $COUNTER &
    else
      # For odd counters, call API directly
      call_sync_api $COUNTER &
    fi
  done
  
  # Wait for operations to complete
  wait
  
  echo "Completed batch of $NUM_PARALLEL operations. Total operations: $COUNTER"
  echo "Current time: $(date)"
  
  # Get current HPA status
  echo "Current HPA status:"
  kubectl get hpa image-sync-hpa
  
  # Get pod resource usage
  echo "Pod resource usage:"
  kubectl top pods | grep image-sync
  
  # Sleep before next batch
  echo "Waiting $DELAY seconds before next batch..."
  sleep $DELAY
done

echo "=== Test completed at $(date) ==="
echo "Total operations performed: $COUNTER"
echo "Final HPA status:"
kubectl get hpa image-sync-hpa