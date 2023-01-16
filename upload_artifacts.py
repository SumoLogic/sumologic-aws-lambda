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
    "ap-northeast-3",
    "eu-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "eu-north-1",
    "sa-east-1",
    "ap-east-1",
    "me-south-1",
    "eu-south-1",
    "af-south-1",
    "me-central-1",
    "eu-central-2",
    "ap-southeast-3"
    ]

region_map = {
    "us-east-1" : "appdevzipfiles-us-east-1",
    "us-east-2" : "appdevzipfiles-us-east-2",
    "us-west-1" : "appdevzipfiles-us-west-1",
    "us-west-2" : "appdevzipfiles-us-west-2",
    "ap-south-1": "appdevzipfiles-ap-south-1",
    "ap-northeast-2":"appdevzipfiles-ap-northeast-2",
    "ap-southeast-1":"appdevzipfiles-ap-southeast-1",
    "ap-southeast-2":"appdevzipfiles-ap-southeast-2",
    "ap-northeast-1":"appdevzipfiles-ap-northeast-1",
    "ca-central-1": "appdevzipfiles-ca-central-1",
    "eu-central-1":"appdevzipfiles-eu-central-1",
    "eu-west-1":"appdevzipfiles-eu-west-1",
    "eu-west-2":"appdevzipfiles-eu-west-2",
    "eu-west-3":"appdevzipfiles-eu-west-3",
    "eu-north-1":"appdevzipfiles-eu-north-1s",
    "sa-east-1":"appdevzipfiles-sa-east-1",
    "ap-east-1":"appdevzipfiles-ap-east-1s",
    "af-south-1":"appdevzipfiles-af-south-1s",
    "eu-south-1":"appdevzipfiles-eu-south-1",
    "me-south-1":"appdevzipfiles-me-south-1s",
    "me-central-1": "appdevzipfiles-me-central-1",
    "eu-central-2":"appdevzipfiles-eu-central-2ss",
    "ap-northeast-3" :"appdevzipfiles-ap-northeast-3s",
    "ap-southeast-3": "appdevzipfiles-ap-southeast-3"
}


def get_bucket_name(region):
    return region_map[region]


def upload_code_in_multiple_regions(filepath, bucket_prefix):

    for region in regions:
        upload_code_in_S3(filepath, get_bucket_name(region), region)


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
