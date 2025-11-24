import os
import boto3
import pandas as pd
import matplotlib.pyplot as plt

# ========== CONFIGURATION ==========

# S3 (AWS metrics)
S3_BUCKET = "vj-image-output-jehosua"
S3_KEY = "metrics/lambda_metrics.csv"
AWS_REGION = "us-east-2"

# Local folders
LOCAL_FOLDER = "metrics"   # where lambda_metrics will be downloaded
CHARTS_FOLDER = os.path.join(LOCAL_FOLDER, "charts")

# On-prem metrics file location (your local path)
ONPREM_METRICS_FILE = r"onprem_images\metrics\local_metrics.csv"

# Where AWS metrics will be stored locally
AWS_METRICS_FILE = os.path.join(LOCAL_FOLDER, "lambda_metrics.csv")

# ====================================


def ensure_dirs():
    os.makedirs(LOCAL_FOLDER, exist_ok=True)
    os.makedirs(CHARTS_FOLDER, exist_ok=True)


def download_aws_metrics():
    print(f"Downloading AWS metrics from S3: s3://{S3_BUCKET}/{S3_KEY}")
    s3 = boto3.client("s3", region_name=AWS_REGION)

    try:
        s3.download_file(S3_BUCKET, S3_KEY, AWS_METRICS_FILE)
        print(f"[OK] AWS metrics downloaded to: {AWS_METRICS_FILE}")
    except Exception as e:
        print("[ERROR] Error downloading AWS metrics:", e)
        print("       Check your bucket name, object key, and credentials.")
        raise


def load_dataframes():
    if not os.path.exists(AWS_METRICS_FILE):
        raise FileNotFoundError(f"lambda_metrics.csv not found at: {AWS_METRICS_FILE}")

    if not os.path.exists(ONPREM_METRICS_FILE):
        raise FileNotFoundError(f"local_metrics.csv not found at: {ONPREM_METRICS_FILE}")

    df_cloud = pd.read_csv(AWS_METRICS_FILE)
    df_local = pd.read_csv(ONPREM_METRICS_FILE)

    df_cloud["source"] = "cloud"
    df_local["source"] = "on_prem"

    # Ensure numeric types
    df_cloud["proc_ms"] = pd.to_numeric(df_cloud["proc_ms"])
    df_local["proc_ms"] = pd.to_numeric(df_local["proc_ms"])

    df_cloud["orig_size"] = pd.to_numeric(df_cloud["orig_size"])
    df_local["orig_size"] = pd.to_numeric(df_local["orig_size"])

    df = pd.concat([df_cloud, df_local], ignore_index=True)

    return df_cloud, df_local, df


def plot_average_time(df):
    avg = df.groupby("source")["proc_ms"].mean()

    plt.figure()
    avg.plot(kind="bar", color=["#1f77b4", "#ff7f0e"])
    plt.ylabel("Average processing time (ms)")
    plt.title("Average Processing Time: Cloud vs On-Prem")
    plt.xticks(rotation=0)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()

    out = os.path.join(CHARTS_FOLDER, "avg_time.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print("Chart saved:", out)


def plot_boxplot_time(df):
    plt.figure()
    df.boxplot(column="proc_ms", by="source", grid=True)
    plt.ylabel("Processing time (ms)")
    plt.title("Distribution of Processing Times")
    plt.suptitle("")
    plt.tight_layout()

    out = os.path.join(CHARTS_FOLDER, "boxplot_time.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print("Chart saved:", out)


def plot_size_vs_time(df):
    plt.figure()
    colors = {"cloud": "#1f77b4", "on_prem": "#ff7f0e"}

    for src, sub in df.groupby("source"):
        plt.scatter(sub["orig_size"], sub["proc_ms"], label=src, alpha=0.7, color=colors[src])

    plt.xlabel("Image size (bytes)")
    plt.ylabel("Processing time (ms)")
    plt.title("Image Size vs Processing Time")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()

    out = os.path.join(CHARTS_FOLDER, "size_vs_time.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print("Chart saved:", out)


def plot_total_time(df):
    total = df.groupby("source")["proc_ms"].sum() / 1000.0  # seconds

    plt.figure()
    total.plot(kind="bar", color=["#1f77b4", "#ff7f0e"])
    plt.ylabel("Total processing time (seconds)")
    plt.title("Total Processing Time for All Images")
    plt.xticks(rotation=0)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()

    out = os.path.join(CHARTS_FOLDER, "total_time.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print("Chart saved:", out)


def main():
    ensure_dirs()
    download_aws_metrics()
    df_cloud, df_local, df = load_dataframes()

    print("\nQuick summary:")
    print(df.groupby("source")["proc_ms"].describe())

    print("\nGenerating charts...")
    plot_average_time(df)
    plot_boxplot_time(df)
    plot_size_vs_time(df)
    plot_total_time(df)

    print("\nDone! Charts generated in:", CHARTS_FOLDER)


if __name__ == "__main__":
    main()
