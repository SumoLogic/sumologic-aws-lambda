import boto3
import argparse


VERSION = "v1.3.0"
AWS_PROFILE = "prod"

REGION_MAPPING = {
    "us-east-1": "appdevzipfiles-us-east-1",
    "us-east-2": "appdevzipfiles-us-east-2",
    "us-west-1": "appdevzipfiles-us-west-1",
    "us-west-2": "appdevzipfiles-us-west-2",
    "ap-south-1": "appdevzipfiles-ap-south-1",
    "ap-northeast-2": "appdevzipfiles-ap-northeast-2",
    "ap-southeast-1": "appdevzipfiles-ap-southeast-1",
    "ap-southeast-2": "appdevzipfiles-ap-southeast-2",
    "ap-northeast-1": "appdevzipfiles-ap-northeast-1",
    "ca-central-1": "appdevzipfiles-ca-central-1",
    "eu-central-1": "appdevzipfiles-eu-central-1",
    "eu-west-1": "appdevzipfiles-eu-west-1",
    "eu-west-2": "appdevzipfiles-eu-west-2",
    "eu-west-3": "appdevzipfiles-eu-west-3",
    "eu-north-1": "appdevzipfiles-eu-north-1s",
    "sa-east-1": "appdevzipfiles-sa-east-1",
    "ap-east-1": "appdevzipfiles-ap-east-1s",
    "af-south-1": "appdevzipfiles-af-south-1s",
    "eu-south-1": "appdevzipfiles-eu-south-1",
    "me-south-1": "appdevzipfiles-me-south-1s",
    "me-central-1": "appdevzipfiles-me-central-1",
    "eu-central-2": "appdevzipfiles-eu-central-2ss",
    "ap-northeast-3": "appdevzipfiles-ap-northeast-3s",
    "ap-southeast-3": "appdevzipfiles-ap-southeast-3"
}

def get_bucket_name(region):
    return REGION_MAPPING.get(region, None)


def create_bucket(region):
    """Create an S3 bucket in the specified region."""
    s3 = boto3.client("s3", region_name=region)
    bucket_name = get_bucket_name(region)

    if not bucket_name:
        print(f"No bucket mapping found for region: {region}")
        return

    try:
        if region == "us-east-1":
            response = s3.create_bucket(Bucket=bucket_name)
        else:
            response = s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"Bucket created: {bucket_name} in {region}", response)
    except Exception as e:
        print(f"Error creating bucket {bucket_name}: {e}")


def upload_code_to_s3(region):
    """Upload the zip file to the specified S3 bucket."""
    filename = "cloudwatchlogs-with-dlq.zip"
    boto3.setup_default_session(profile_name=AWS_PROFILE)
    s3 = boto3.client("s3", region_name=region)
    bucket_name = get_bucket_name(region)

    if not bucket_name:
        print(f"No bucket mapping found for region: {region}")
        return

    try:
        s3.upload_file(
            filename, bucket_name, f"cloudwatchLogsDLQ/{VERSION}/{filename}",
            ExtraArgs={"ACL": "public-read"}
        )
        print(f"Uploaded {filename} to S3 bucket ({bucket_name}) in region ({region})")
    except Exception as e:
        print(f"Error uploading {filename} to {bucket_name}: {e}")


def upload_code_in_multiple_regions(regions):
    """Upload code to all or specified regions."""
    # for region in regions:
    #     create_bucket(region)

    for region in regions:
        upload_code_to_s3(region)


def deploy(args):
    """Deploy production artifacts to S3."""
    if args.region == "all":
        upload_code_in_multiple_regions(REGION_MAPPING.keys())
    elif args.region in REGION_MAPPING.keys():
        upload_code_to_s3(args.region)
    else:
        print("Invalid region. Please provide a valid AWS region or use 'all'.")

    boto3.setup_default_session(profile_name=AWS_PROFILE)
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "appdev-cloudformation-templates"

    template_files = [
        "DLQLambdaCloudFormation.json",
        "DLQLambdaCloudFormationWithSecuredEndpoint.json"
    ]

    for filename in template_files:
        try:
            s3.upload_file(
                filename, bucket_name, filename,
                ExtraArgs={"ACL": "public-read"}
            )
            print(f"Uploaded {filename} to {bucket_name}")
        except Exception as e:
            print(f"Error uploading {filename}: {e}")

    print("Deployment Successful: All files copied to Sumocontent")


def main():
    parser = argparse.ArgumentParser(description="Deploy files to S3")
    parser.add_argument(
        "-r", "--region", type=str, help="Specify a region or use 'all' to deploy to all configured regions"
    )
    args = parser.parse_args()
    deploy(args)



if __name__ == "__main__":
    main()