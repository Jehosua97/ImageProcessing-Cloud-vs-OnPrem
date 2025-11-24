import os
import time
import subprocess
import shutil
import boto3
from botocore.exceptions import ClientError

# ========== CONFIGURATION ==========

AWS_REGION = "us-east-2"

# Buckets
INPUT_BUCKET = "vj-image-input-jehosua"
OUTPUT_BUCKET = "vj-image-output-jehosua"
METRICS_KEY = "metrics/lambda_metrics.csv"

# Local paths (relative to project root)
ONPREM_OUTPUT_DIR = r"onprem_images\output_local"
ONPREM_METRICS_FILE = r"onprem_images\metrics\local_metrics.csv"

AWS_LOCAL_METRICS_DIR = "metrics"   # used by compare_cloud_onprem_metrics.py
AWS_LOCAL_METRICS_FILE = os.path.join(AWS_LOCAL_METRICS_DIR, "lambda_metrics.csv")

# Scripts to execute in order
SCRIPTS = {
    "local": r"onprem_images\local_image_proc.py",
    "upload": r"upload_images_s3.py",
    "compare": r"compare_cloud_onprem_metrics.py",
}

# Global flags
CLEAN_PREVIOUS_RUN = True

# How long to wait for Lambda metrics
WAIT_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 180  # 3 minutes

# ====================================


def banner(title: str):
    """Print a simple visual banner."""
    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60 + "\n")


def clean_local_results():
    """Clean local outputs and metrics from previous runs."""
    banner("CLEANING LOCAL RESULTS")

    # Delete local on-prem processed images
    if os.path.isdir(ONPREM_OUTPUT_DIR):
        print(f"Removing local on-prem output folder: {ONPREM_OUTPUT_DIR}")
        try:
            for f in os.listdir(ONPREM_OUTPUT_DIR):
                path = os.path.join(ONPREM_OUTPUT_DIR, f)
                if os.path.isfile(path):
                    os.remove(path)
        except Exception as e:
            print("  Warning: could not clean on-prem output:", e)
    else:
        print(f"On-prem output folder does not exist yet: {ONPREM_OUTPUT_DIR}")

    # Delete local on-prem metrics file
    if os.path.isfile(ONPREM_METRICS_FILE):
        print(f"Removing local on-prem metrics file: {ONPREM_METRICS_FILE}")
        try:
            os.remove(ONPREM_METRICS_FILE)
        except Exception as e:
            print("  Warning: could not delete on-prem metrics file:", e)
    else:
        print(f"On-prem metrics file not found: {ONPREM_METRICS_FILE}")

    # Delete local AWS metrics and charts
    if os.path.isdir(AWS_LOCAL_METRICS_DIR):
        print(f"Removing local AWS metrics/charts folder: {AWS_LOCAL_METRICS_DIR}")
        try:
            shutil.rmtree(AWS_LOCAL_METRICS_DIR)
        except Exception as e:
            print("  Warning: could not delete metrics folder:", e)
    else:
        print(f"AWS metrics folder not found locally: {AWS_LOCAL_METRICS_DIR}")

    print("Local cleanup finished.")


def clean_s3_results():
    """Clean S3 output (processed images + metrics) from previous runs."""
    banner("CLEANING S3 RESULTS")

    s3 = boto3.client("s3", region_name=AWS_REGION)

    def delete_prefix(bucket, prefix):
        print(f"Deleting objects with prefix '{prefix}' in bucket '{bucket}'...")
        try:
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            to_delete = []
            for page in pages:
                contents = page.get("Contents", [])
                for obj in contents:
                    to_delete.append({"Key": obj["Key"]})
                    if len(to_delete) == 1000:
                        s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
                        to_delete = []

            if to_delete:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})

            print(f"  Done clearing prefix '{prefix}'.")
        except ClientError as e:
            print(f"  Warning: error cleaning prefix '{prefix}': {e}")

    # Clear processed images in output bucket
    delete_prefix(OUTPUT_BUCKET, "processed/")

    # Delete metrics file
    print(f"Deleting metrics object s3://{OUTPUT_BUCKET}/{METRICS_KEY} if it exists...")
    try:
        s3.delete_object(Bucket=OUTPUT_BUCKET, Key=METRICS_KEY)
        print("  Metrics object deleted (or did not exist).")
    except ClientError as e:
        print(f"  Warning: could not delete metrics object: {e}")

    print("S3 cleanup finished.")


def run_script(label: str, script_name: str):
    """Run a python script and show visual progress."""
    banner(f"RUNNING {label.upper()} SCRIPT")
    if not os.path.isfile(script_name):
        raise FileNotFoundError(f"Script not found: {script_name}")

    print(f"Executing: python {script_name}\n")

    result = subprocess.run(
        ["python", script_name],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print("----- STDOUT -----")
        print(result.stdout)
    if result.stderr:
        print("----- STDERR -----")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Script {script_name} failed with exit code {result.returncode}"
        )

    print(f"{label} script finished successfully.")


def wait_for_lambda_metrics():
    """Wait until Lambda metrics file appears in S3 (up to MAX_WAIT_SECONDS)."""
    banner("WAITING FOR LAMBDA METRICS FROM AWS")

    s3 = boto3.client("s3", region_name=AWS_REGION)

    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        try:
            s3.head_object(Bucket=OUTPUT_BUCKET, Key=METRICS_KEY)
            print(f"Metrics file found in S3: s3://{OUTPUT_BUCKET}/{METRICS_KEY}")
            return
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                print(f"Metrics not ready yet, waiting {WAIT_INTERVAL_SECONDS} seconds...")
                time.sleep(WAIT_INTERVAL_SECONDS)
                elapsed += WAIT_INTERVAL_SECONDS
            else:
                print(f"Error checking metrics file: {e}")
                raise

    print(
        f"Timeout: metrics file not found after {MAX_WAIT_SECONDS} seconds.\n"
        "The comparison script may fail if no metrics are available."
    )


def main():
    banner("MASTER PIPELINE START")

    if CLEAN_PREVIOUS_RUN:
        clean_local_results()
        clean_s3_results()
    else:
        print("Skipping cleanup of previous run (CLEAN_PREVIOUS_RUN = False).")

    # 1) Run local on-prem processing
    run_script("on-prem processing", SCRIPTS["local"])

    # 2) Upload images to AWS S3 (this will trigger Lambda)
    run_script("S3 upload (triggers Lambda)", SCRIPTS["upload"])

    # 3) Wait for Lambda to process and write metrics in S3
    wait_for_lambda_metrics()

    # 4) Run comparison + chart generation
    run_script("metrics comparison", SCRIPTS["compare"])

    banner("PIPELINE FINISHED")
    print("Cloud vs On-Prem metrics and charts are now available.")
    print(f"Check the '{AWS_LOCAL_METRICS_DIR}\\charts' folder for generated PNG graphs.")


if __name__ == "__main__":
    main()
