import json
import logging
import os
import subprocess
import oci
from flask import Flask, request, jsonify
from threading import Thread

# Initialize Flask app
app = Flask(__name__)

# Configure logging to write to a file
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    handlers=[
        logging.FileHandler("/app/logs/image_sync.log"),  # Log to a file
        logging.StreamHandler()  # Also log to the console (optional)
    ]
)

logger = logging.getLogger(__name__)  # Create a logger instance

def run_command(command):
    """Runs a shell command and logs output."""
    ## TODO - stop logging the password in the logs
    logger.debug(f"Running command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        raise Exception(f"Command failed: {result.stderr}")
    logger.debug(f"Command output: {result.stdout.strip()}")
    return result.stdout.strip()

def authenticate_ecr(account_id, region):
    """Authenticate to AWS ECR."""
    logger.info("Authenticating with Amazon ECR...")
    password = run_command(f"aws ecr get-login-password --region {region}")
    run_command(f"echo {password} | podman login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com")

def authenticate_ocir(region_key, oci_tenancy, oci_username, oci_auth_token):
    """Authenticate to Oracle OCIR."""
    logger.info("Authenticating with Oracle OCIR...")
    run_command(f"podman login {region_key}.ocir.io -u {oci_tenancy}/{oci_username} -p {oci_auth_token}")


def sync_image(repo, tag, aws_account_id, aws_region, oci_tenancy, oci_repo_region_key):
    """Copy an image from ECR to OCIR using skopeo."""
    ecr_url = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{repo}:{tag}"
    ocir_url = f"{oci_repo_region_key}.ocir.io/{oci_tenancy}/{repo}:{tag}"

    logger.info(f"Copying image from ECR to OCIR: {ecr_url} -> {ocir_url}")
    
    # Get AWS ECR credentials
    aws_password = run_command(f"aws ecr get-login-password --region {aws_region}")
    
    # Get OCIR credentials
    oci_username = os.environ.get('OCI_USERNAME')
    oci_auth_token = os.environ.get('OCI_AUTH_TOKEN')
    oci_creds = f"{oci_tenancy}/{oci_username}:{oci_auth_token}"
    
    # Use skopeo to copy the image directly
    run_command(f"skopeo copy --src-creds AWS:{aws_password} --dest-creds {oci_creds} " +
                f"docker://{ecr_url} docker://{ocir_url}")

    logger.info("Image sync completed successfully!")
    

def syncImageHandler(repo, tag, aws_account_id, region):
    """Sync image from AWS ECR to OCI."""
    logger.info(f"Processing image: {repo}:{tag}")
    
    try:
        # Extract environment variables
        account_id = aws_account_id
        oci_repo_region_key = os.environ.get('OCI_REPO_REGION_KEY')
        oci_tenancy = os.environ.get('OCI_TENANCY')
        oci_username = os.environ.get('OCI_USERNAME')
        oci_auth_token = os.environ.get('OCI_AUTH_TOKEN')

        if not all([oci_repo_region_key, oci_tenancy, oci_username, oci_auth_token]):
            raise ValueError("Missing required environment variables: OCI_REPO_REGION_KEY, OCI_TENANCY, OCI_USERNAME, OCI_AUTH_TOKEN")
        aws_region = region
        

        #for each region in oci_repo_region_key
        oci_repo_region_key = oci_repo_region_key.split(',')
        for region in oci_repo_region_key:
            
            logger.info(f"Syncing image to region: {region}")
            # Sync the image
            authenticate_ecr(account_id, aws_region)
            authenticate_ocir(region, oci_tenancy, oci_username, oci_auth_token)
            sync_image(repo, tag, account_id, aws_region, oci_tenancy, oci_repo_region_key=region)
            logger.info(f"Image {repo}:{tag} synced successfully to {region}")
        

    except KeyError as e:
        logger.error(f"Error extracting data: {e}")
        return {"statusCode": 400, "body": "Invalid event format"}

    logger.info("Image copied successfully!")
    return True

@app.route('/sync', methods=['POST'])
def handler():
    """HTTP handler for syncing images."""
    def async_task(body):
        """Perform the sync task asynchronously."""
        try:
            action_type = body['detail']['action-type']
            if action_type == "PUSH":
                syncImageHandler(body['detail']['repository-name'], body['detail']['image-tag'], body['account'], body['region'])
                logger.info(f"Image {body['detail']['repository-name']}:{body['detail']['image-tag']} synced successfully")
        except Exception as ex:
                logger.error(f"Error during async task: {ex}")

    try:
        body = request.get_json()
        logger.info(f"Received event: {json.dumps(body, indent=2)}")

        
        # Start the async task
        thread = Thread(target=async_task, args=(body,))
        thread.start()

        return jsonify({"status": "success", "message": "Task is running asynchronously"}), 200

    except (Exception, ValueError) as ex:
        logger.error(f"Error processing request: {ex}")
        return jsonify({"status": "error", "message": str(ex)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)