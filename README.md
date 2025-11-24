# Cloud vs On-Premises Image Processing Pipeline

This project implements a **reproducible experiment** to compare:

- **On-Premises image processing** (Python + Pillow)
- **Cloud-based serverless processing** (AWS Lambda + S3)

The goal is to evaluate **performance, scalability, and stability** of both approaches using the **same image dataset** and a fully automated pipeline.

---

## ✨ Key Features

- On-premises image processing using **Pillow** (resize + recompression).
- Cloud processing via **AWS Lambda** triggered by **S3 events**.
- Unified **master orchestrator** that:
  - Cleans previous results (local + S3).
  - Runs on-premises processing.
  - Uploads images to S3.
  - Waits for Lambda to finish.
  - Downloads metrics and generates comparison plots.
- Metrics captured for each image:
  - Original size (bytes)
  - New size (bytes)
  - Processing time (ms)
  - Timestamp
  - Source: `cloud` or `on_prem`
- Plots for:
  - Average processing time
  - Distribution (boxplot)
  - Size vs time (scatter)
  - Total processing time

---

## 🏗️ High-Level Architecture

### On-Premises Pipeline

1. Read input images from `images_to_upload/`.
2. Process each image with `onprem_images/local_image_proc.py`:
   - Convert to RGB
   - Resize to 800x600
   - Recompress as JPEG
3. Save processed images to `onprem_images/output_local/`.
4. Log metrics to `onprem_images/metrics/local_metrics.csv`.

### Cloud (AWS Serverless) Pipeline

1. Upload images to **S3 input bucket** (e.g. `vj-image-input-jehosua`).
2. `s3:ObjectCreated` event triggers **AWS Lambda**.
3. Lambda downloads the image, runs CPU-bound processing on the bytes.
4. Lambda writes the processed output and metrics to **S3 output bucket** (e.g. `vj-image-output-jehosua`), appending to `metrics/lambda_metrics.csv`.

### Orchestrator

The script `master_pipeline.py` coordinates the entire experiment:

1. Optional cleanup of previous runs.
2. Executes on-premises processing.
3. Uploads images to S3 (triggers Lambda).
4. Waits until Lambda metrics file appears in S3.
5. Runs `compare_cloud_onprem_metrics.py` to:
   - Download cloud metrics.
   - Merge with on-prem metrics.
   - Generate comparison plots in `metrics/charts/`.


<img width="661" height="452" alt="onpremises drawio" src="https://github.com/user-attachments/assets/fd308267-ed61-4867-b515-647d0a1b7871" />
<img width="921" height="506" alt="Cloud drawio" src="https://github.com/user-attachments/assets/189de641-c036-4ad4-84a6-676270f739a9" />

---

## 📁 Repository Structure

```text
.
├── images_to_upload/                # Input images for both pipelines
├── master_pipeline.py               # Main orchestrator script
├── upload_images_s3.py              # Uploads images to S3 input bucket
├── compare_cloud_onprem_metrics.py  # Downloads metrics & generates plots
├── onprem_images/
│   ├── local_image_proc.py          # On-prem image processing (Pillow)
│   ├── metrics/
│   │   └── local_metrics.csv        # On-prem metrics (generated)
│   └── output_local/                # On-prem processed images (generated)
├── metrics/
│   ├── lambda_metrics.csv           # Cloud metrics (downloaded from S3)
│   └── charts/                      # Comparison plots (generated)
└── README.md
