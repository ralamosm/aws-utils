import os
import tempfile
import boto3


def upload_file(path, bucket=None, key=None, content_type="application/octet-stream"):
    """
    Upload a file to some of our S3 buckets
    """
    if not path:
        raise ValueError("Missing argument 'path'")
    if not bucket:
        raise ValueError("Missing argument 'bucket'")
    if not key:
        key = os.path.basename(path)

    s3_client = boto3.client("s3")

    try:
        s3_client.upload_file(Filename=path, Bucket=bucket, Key=key, ExtraArgs={"ContentType": content_type})
    except Exception as e:
        raise ValueError(f"File '{path}' couldn't been uploaded: {e}")

    return (f"https://{bucket}.s3.amazonaws.com/", key)


def upload_content(content, bucket=None, key=None, content_type="application/octet-stream"):
    """
    Upload pure content to some of our S3 buckets
    """
    local_file = tempfile.NamedTemporaryFile(mode="w+")
    local_file.write(content)
    local_file.seek(0)

    r = upload_file(local_file.name, bucket=bucket, key=key, content_type=content_type)

    local_file.close()
    os.remove(local_file.name)
    return r
