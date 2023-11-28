import boto3

# Replace 'your_access_key' and 'your_secret_key' with your AWS credentials
# Or, you can use a configured AWS profile (https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration)
aws_access_key = 'AKIAZORESFWLVIBVAI6D'
aws_secret_key = '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'
region_name = 'us-east-2'

# Create an S3 client
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

# Specify the bucket name
bucket_name = 'file-share-coen317'

# List all objects in the bucket
response = s3.list_objects(Bucket=bucket_name)

# Print the object keys
for obj in response.get('Contents', []):
    print(obj['Key'])

