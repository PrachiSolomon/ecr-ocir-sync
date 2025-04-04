# ECR to OCIR Image Synchronization Service

A Kubernetes-based service that automatically synchronizes container images from AWS Elastic Container Registry (ECR) to Oracle Cloud Infrastructure Registry (OCIR) across multiple regions.

## Features

- **Multi-Region Synchronization**: Push images to multiple OCIR regions simultaneously
- **Auto-Scaling**: Horizontal Pod Autoscaling (HPA) based on CPU utilization
- **Efficient Transfers**: Uses Skopeo for direct streaming between registries
- **Webhook Integration**: Responds to ECR image push/delete events
- **Asynchronous Processing**: Non-blocking API with background workers
- **Large Image Support**: Handles images up to 40GB in size
- **Stateful Storage**: Dedicated storage per pod for reliable operations
- **Monitoring**: Comprehensive logging and performance metrics

## Architecture

This service runs in Kubernetes as a StatefulSet with the following components:

- **Flask API Server**: Receives webhook events from ECR
- **Skopeo**: Efficiently copies images between registries
- **Persistent Volumes**: Provides dedicated storage for large image operations
- **HPA**: Automatically scales based on workload

## Prerequisites

- Kubernetes cluster (tested on OKE - Oracle Kubernetes Engine)
- Access to AWS ECR and Oracle OCIR
- kubectl CLI configured for your cluster
- AWS and OCI credentials
- Storage class supporting ReadWriteOnce volumes (e.g., oci-bv)

## Building the Docker Image

### 1. Clone the repository

```bash
git clone https://github.com/PrachiSolomon/ecr-ocir-sync.git
cd ecr-ocir-sync
```

### 2. Create Kubernetes secrets

```bash
# Create AWS credentials secret
kubectl create secret generic aws-credentials \
  --from-literal=access-key-id=YOUR_AWS_ACCESS_KEY \
  --from-literal=secret-access-key=YOUR_AWS_SECRET_KEY \
  --from-literal=default-region=us-west-2

# Create OCI credentials secret
kubectl create secret generic oci-credentials \
  --from-literal=OCI_TENANCY=YOUR_TENANCY \
  --from-literal=OCI_USERNAME=YOUR_USERNAME \
  --from-literal=OCI_AUTH_TOKEN=YOUR_AUTH_TOKEN \
  --from-literal=OCI_REGION=YOUR_REGION \ # example ap-melbourne-1
  --from-literal=OCI_REPO_REGION_KEY=YOUR_REGIONS  # Comma-separated list of regions, exmaple mel,syd 
```

### 3. Deploy the StatefulSet

```bash
kubectl apply -f statefulset.yaml
```

### 4. Deploy the Service

```bash
kubectl apply -f service.yaml
```

### 5. Configure HPA

```bash
kubectl apply -f image-sync-hpa.yaml
```

## Configuration

### Environment Variables

| Variable             | Description                                | Default           |
|----------------------|--------------------------------------------|-------------------|
| `OCI_TENANCY`        | Your OCI tenancy namespace                | `your tenancy namespace`    |
| `OCI_USERNAME`       | OCI username for registry authentication  | `your username` |
| `OCI_AUTH_TOKEN`     | Auth token for OCI registry               | -                 |
| `OCI_REPO_REGION_KEY`| Comma-separated list of region keys (e.g., `mel,syd`) | `mel` |
| `OCI_REGION`         | OCI region                                | `example ap-melbourne-1`  |
| `AWS_ACCESS_KEY_ID`  | AWS access key                            | -                 |
| `AWS_SECRET_ACCESS_KEY`| AWS secret access key                   | -                 |
| `AWS_DEFAULT_REGION` | AWS default region                        | `example us-west-2`       |

### Kubernetes Resources

The StatefulSet is configured with:
- 3 replicas by default
- Resource requests/limits for predictable performance
- Persistent volume claims for image operations
- Skopeo configuration volumes

## Usage

### API Endpoints

#### POST /sync

Triggers image synchronization between ECR and OCIR.

**Request Body:**

```json
{
"account": "<AWS_ACCOUNT_ID>",
    "region": "<AWS_REGION>",
    "detail": {
        "action-type": "PUSH",
        "repository-name": "<REPOSITORY_NAME>",
        "image-tag": "<IMAGE_TAG>"
    }
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Task is running asynchronously"
}
```

### AWS EventBridge Integration

To automatically trigger synchronization when an image is pushed to ECR:

1. Create an EventBridge rule in AWS that matches ECR image push events
2. Set the target to be an HTTPS endpoint pointing to your service's `/sync` endpoint

## Testing

A test script is provided to simulate ECR events and load test the service. This script creates and pushes test images, simulates ECR events, and monitors HPA behavior.

Setting up test environment
First, configure the required environment variables:
```
# AWS configuration
export AWS_ACCOUNT_ID="your-aws-account-id"
export AWS_REGION="us-west-2"
export AWS_REPO_NAME="your-repo-name"  

# OCIR configuration
export OCIR_TENANCY="your-oci-tenancy"
export OCIR_USERNAME="your-tenancy/your-username@example.com"
export OCIR_PASSWORD="your-auth-token"

# Service URL - internal K8s service or external endpoint
export SERVICE_URL="http://image-sync:8080/sync"  # Use appropriate URL
```
Running the test
Execute the script:

```bash
./test-hpa.sh
```

The script performs the following:

- Logs in to both ECR and OCIR repositories
- Creates randomized test images and pushes them to ECR
- Sends direct API calls to your sync service
- Monitors HPA scaling and resource usage
- Runs tests in parallel to simulate load
- Reports detailed metrics throughout the test

## Customizing the test**

You can adjust the test parameters by modifying these variables at the beginning of the script:

```
TEST_DURATION=600  # Duration in seconds (10 minutes by default)
NUM_PARALLEL=3     # Number of parallel operations
DELAY=5            # Seconds between operation batches
```

## Performance Considerations

- **Storage Requirements**: Ensure each pod has at least 20-40GB storage for large images
- **Network Bandwidth**: For 40GB images, transfers may take 15-20 minutes depending on bandwidth
- **CPU Scaling**: The HPA is configured to scale at 70% CPU utilization, adjust as needed
- **Concurrent Operations**: Each pod can handle one image sync operation at a time

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Skopeo](https://github.com/containers/skopeo) for container image operations
- Oracle Cloud Infrastructure and AWS teams
- The Kubernetes community for HPA and StatefulSet capabilities


````
