#!bash/bin

if [ ! -f securityhub_deps.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip install -r ../requirements.txt -t ./
    zip -r ../securityhub_deps.zip .
    cd ..
fi

declare -a regions=("us-east-2" "us-east-1" "us-west-1" "us-west-2" "ap-south-1" "ap-northeast-2" "ap-southeast-1" "ap-southeast-2" "ap-northeast-1" "ca-central-1" "eu-central-1" "eu-west-1" "eu-west-2" "eu-west-3" "sa-east-1")

for i in "${regions[@]}"
do
    echo "Deploying layer in $i"
    bucket_name="appdevzipfiles-$i"
    aws s3 cp securityhub_deps.zip s3://$bucket_name/ --region $i

    aws lambda publish-layer-version --layer-name securityhub_deps --description "contains securityhub solution dependencies" --license-info "MIT" --content S3Bucket=$bucket_name,S3Key=securityhub_deps.zip --compatible-runtimes python3.7 python3.6 --region $i

    aws lambda add-layer-version-permission --layer-name securityhub_deps  --statement-id securityhub-deps --version-number 1 --principal '*' --action lambda:GetLayerVersion --region $i
done

# aws lambda remove-layer-version-permission --layer-name securityhub_deps --version-number 1 --statement-id securityhub-deps --region us-east-1
# aws lambda get-layer-version-policy --layer-name securityhub_deps --region us-east-1
