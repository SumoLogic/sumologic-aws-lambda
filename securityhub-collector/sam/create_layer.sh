mkdir python
cd python
pip install -r ../requirements.txt -t ./
zip -r ../securityhub_deps.zip .
cd ..
aws s3 cp securityhub_deps.zip s3://appdevstore/ --region us-east-1

aws lambda publish-layer-version --layer-name securityhub_deps --description "contains securityhub solution dependencies" --license-info "MIT" --content S3Bucket=appdevstore,S3Key=securityhub_deps.zip --compatible-runtimes python3.7 python3.6 --region us-east-1

aws lambda add-layer-version-permission --layer-name securityhub_deps  --statement-id securityhub-deps --version-number 3 --principal '*' --action lambda:GetLayerVersion --region us-east-1
