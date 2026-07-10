# app/services/cos_client.py
import ibm_boto3
from ibm_botocore.client import Config as CosConfig
from app.utils.config import Config
import os


def get_cos_client():
    return ibm_boto3.client(
        's3',
        ibm_api_key_id=Config.COS_API_KEY,
        ibm_service_instance_id=Config.COS_INSTANCE_ID,
        config=CosConfig(signature_version='oauth'),
        endpoint_url=Config.COS_ENDPOINT
    )


def upload_resume(file_bytes: bytes, filename: str) -> str:
    """
    Upload resume PDF to COS bucket.
    Returns the object key (filename stored in COS).
    """
    cos = get_cos_client()
    object_key = f"resumes/{filename}"

    cos.put_object(
        Bucket=Config.COS_BUCKET,
        Key=object_key,
        Body=file_bytes,
        ContentType="application/pdf"
    )
    return object_key


def download_resume(object_key: str) -> bytes:
    """Download resume bytes from COS."""
    cos = get_cos_client()
    response = cos.get_object(
        Bucket=Config.COS_BUCKET,
        Key=object_key
    )
    return response["Body"].read()


def list_resumes() -> list[str]:
    """List all uploaded resumes in COS bucket."""
    cos = get_cos_client()
    response = cos.list_objects_v2(
        Bucket=Config.COS_BUCKET,
        Prefix="resumes/"
    )
    contents = response.get("Contents", [])
    return [obj["Key"] for obj in contents]


def delete_resume(object_key: str):
    """Delete a resume from COS."""
    cos = get_cos_client()
    cos.delete_object(
        Bucket=Config.COS_BUCKET,
        Key=object_key
    )