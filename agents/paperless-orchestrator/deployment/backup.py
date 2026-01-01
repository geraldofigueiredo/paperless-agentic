"""
Standalone script for backing up Paperless-NGX documents to a cloud provider.

This script orchestrates the export of documents from the Paperless-NGX Docker
container and uploads the resulting archive to either AWS S3 or Google Cloud Storage.
"""
import os
import subprocess
import datetime
import boto3
from google.cloud import storage
from dotenv import load_dotenv

def _run_command(command: list[str]):
    """Runs a command and streams its output."""
    print(f"[INFO] Running command: {' '.join(command)}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in iter(process.stdout.readline, ""):
        print(f"[CMD] {line.strip()}")
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}")

def _get_exported_filename() -> str:
    """Generates the expected filename for the exported archive."""
    # This is a simplified assumption. The actual filename might vary.
    # A more robust solution would be to find the latest zip file in the export dir.
    return "paperless-export.zip"

import boto3
from botocore.exceptions import NoCredentialsError

def backup_to_s3(export_path: str, bucket_name: str, region: str):
    """Uploads the exported archive to an AWS S3 bucket."""
    print("\n--- Starting AWS S3 Backup ---")
    
    s3_client = boto3.client("s3", region_name=region)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    object_key = f"paperless-backup_{timestamp}.zip"
    
    try:
        print(f"[INFO] Uploading {export_path} to s3://{bucket_name}/{object_key}")
        s3_client.upload_file(export_path, bucket_name, object_key)
        print("[SUCCESS] Backup to S3 complete.")
    except FileNotFoundError:
        print(f"[ERROR] The file was not found: {export_path}")
    except NoCredentialsError:
        print("[ERROR] AWS credentials not found. Please configure them in your .env file or environment.")
    except Exception as e:
        print(f"[ERROR] An error occurred during S3 upload: {e}")

def backup_to_gcs(export_path: str, bucket_name: str, credentials_path: str):
    """Uploads the exported archive to a Google Cloud Storage bucket."""
    print("\n--- Starting Google Cloud Storage Backup ---")
    
    try:
        storage_client = storage.Client.from_service_account_json(credentials_path)
        bucket = storage_client.bucket(bucket_name)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        blob_name = f"paperless-backup_{timestamp}.zip"
        blob = bucket.blob(blob_name)

        print(f"[INFO] Uploading {export_path} to gs://{bucket_name}/{blob_name}")
        blob.upload_from_filename(export_path)
        print("[SUCCESS] Backup to GCS complete.")
        
    except FileNotFoundError:
        print(f"[ERROR] The file was not found: {export_path} or credentials at {credentials_path}")
    except Exception as e:
        print(f"[ERROR] An error occurred during GCS upload: {e}")

def main():
    """Main backup orchestration function."""
    print("--- Initializing Paperless-NGX Backup ---")
    load_dotenv()

    # 1. Trigger the document export within the Docker container
    print("\n[STEP 1] Triggering document export in Docker container...")
    try:
        export_command = [
            "docker-compose",
            "-f",
            "../../infra/docker-compose.yml", # Assumes script is run from deployment dir
            "exec",
            "paperless_ngx",
            "document_exporter",
            "../export",
        ]
        _run_command(export_command)
        print("[SUCCESS] Document export command finished.")
    except Exception as e:
        print(f"[ERROR] Failed to run document exporter: {e}")
        return

    # 2. Identify the exported file
    export_dir = "../../infra/export" # Relative path to the export volume
    exported_file = _get_exported_filename()
    local_export_path = os.path.join(export_dir, exported_file)

    if not os.path.exists(local_export_path):
        print(f"[ERROR] Exported file not found at: {local_export_path}")
        print("[INFO] Please check the docker-compose logs for the exact filename.")
        return
    
    print(f"\n[STEP 2] Found exported file: {local_export_path}")

    # 3. Upload to the selected cloud provider
    provider = os.getenv("BACKUP_PROVIDER")
    bucket = os.getenv("BACKUP_BUCKET_NAME")

    print(f"\n[STEP 3] Starting upload to {provider}...")

    if provider == "S3":
        aws_region = os.getenv("AWS_REGION")
        if not all([bucket, aws_region]):
            print("[ERROR] For S3, BACKUP_BUCKET_NAME and AWS_REGION must be set.")
            return
        backup_to_s3(local_export_path, bucket, aws_region)

    elif provider == "GCS":
        gcs_creds = os.getenv("GCS_SERVICE_ACCOUNT_FILE")
        if not all([bucket, gcs_creds]):
            print("[ERROR] For GCS, BACKUP_BUCKET_NAME and GCS_SERVICE_ACCOUNT_FILE must be set.")
            return
        backup_to_gcs(local_export_path, bucket, gcs_creds)

    else:
        print(f"[ERROR] Unknown or unsupported BACKUP_PROVIDER: '{provider}'")
        print("[INFO] Please set BACKUP_PROVIDER to 'S3' or 'GCS' in your .env file.")

    print("\n--- Backup Script Finished ---")


if __name__ == "__main__":
    main()
