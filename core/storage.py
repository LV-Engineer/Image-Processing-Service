import boto3

from core.config import settings

s3_client = boto3.client(
    's3',
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id or None,
    aws_secret_access_key=settings.aws_secret_access_key or None,
)

def upload_file(key: str, data: bytes, content_type: str) -> None:
    s3_client.put_object(Bucket=settings.aws_s3_bucket, Key=key, Body=data, ContentType=content_type)

def download_file(key: str) -> bytes:
    response = s3_client.get_object(Bucket=settings.aws_s3_bucket, Key=key)
    body: bytes = response['Body'].read()
    return body

def delete_file(key: str) -> None:
    s3_client.delete_object(Bucket=settings.aws_s3_bucket, Key=key)
