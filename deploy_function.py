import boto3
import os
from argparse import ArgumentParser

regions = [
    "us-east-2",
    "us-east-1",
    "us-west-1",
    "us-west-2",
    "ap-south-1",
    "ap-northeast-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ca-central-1",
    # "cn-north-1",
    # "ap-northeast-3", #giving errror
    "eu-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "eu-north-1",
    "sa-east-1",
    "ap-east-1",
    "me-south-1",
    "eu-south-1",
    "af-south-1"
    ]


def get_bucket_name(bucket_prefix, region):
    if region in ("eu-north-1", "me-south-1", "ap-east-1", "af-south-1"):
        return '%s-%ss' % (bucket_prefix, region)
    return '%s-%s' % (bucket_prefix, region)


def upload_code_in_multiple_regions(filepath, bucket_prefix):

    for region in regions:
        upload_code_in_S3(filepath, get_bucket_name(bucket_prefix, region), region)


def create_buckets(bucket_prefix):
    for region in regions:
        s3 = boto3.client('s3', region)
        bucket_name = get_bucket_name(bucket_prefix, region)
        try:
            if region == "us-east-1":
                response = s3.create_bucket(Bucket=bucket_name) # the operation is idempotent
            else:
                response = s3.create_bucket(Bucket=bucket_name,
                                            CreateBucketConfiguration={
                                                'LocationConstraint': region
                                            })
            print("Creating bucket", region, response)
        except Exception as e:
            print(bucket_name, region)
            print(e)



def upload_code_in_S3(filepath, bucket_name, region):
    print("Uploading zip file in S3", region)
    s3 = boto3.client('s3', region)
    filename = os.path.basename(filepath)
    s3.upload_file(filepath, bucket_name, filename,
                   ExtraArgs={'ACL': 'public-read'})


def upload_cftemplate(templatepath, bucket_name, region='us-east-1'):
    print("Uploading template file in S3")
    s3 = boto3.client('s3', region)
    filename = os.path.basename(templatepath)
    s3.upload_file(templatepath, bucket_name, filename,
                   ExtraArgs={'ACL': 'public-read'})


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument("-t", "--templatefile", dest="templatefile",
                        help="CF template")

    parser.add_argument("-z", "--zipfile", dest="zipfile",
                        help="deployment package")

    parser.add_argument("-d", "--deployment", dest="deployment", default="dev",
                        help="aws account type")

    args = parser.parse_args()
    if args.deployment == "prod":
        zip_bucket_prefix = "appdevzipfiles"
        template_bucket = "appdev-cloudformation-templates"
    else:
        zip_bucket_prefix = "appdevstore"
        template_bucket = "cf-templates-5d0x5unchag-us-east-1"

    # create_buckets(zip_bucket_prefix)
    print(args)
    if args.templatefile:
        if not os.path.isfile(args.templatefile):
            raise Exception("templatefile does not exists")
        else:
            upload_cftemplate(args.templatefile, template_bucket)

    if args.zipfile:
        if not os.path.isfile(args.zipfile):
            raise Exception("zipfile does not exists")
        else:
            upload_code_in_multiple_regions(args.zipfile, zip_bucket_prefix)

    print("Deployment Successfull: ALL files copied to %s" % args.deployment)
