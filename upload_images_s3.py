import boto3
import os

# CONFIGURACIÓN
LOCAL_FOLDER = "images_to_upload"  
BUCKET_NAME = "vj-image-input-jehosua"    
S3_PREFIX = "input/"

# Cliente S3 de boto3
s3 = boto3.client("s3")

def upload_images():
    count = 0
    for filename in os.listdir(LOCAL_FOLDER):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            local_path = os.path.join(LOCAL_FOLDER, filename)
            s3_key = f"{S3_PREFIX}{filename}"

            print(f"Uploading {filename} ...")

            s3.upload_file(local_path, BUCKET_NAME, s3_key)

            count += 1

    print(f"\Done. {count} images were uploaded to S3://{BUCKET_NAME}/{S3_PREFIX}")

if __name__ == "__main__":
    upload_images()
