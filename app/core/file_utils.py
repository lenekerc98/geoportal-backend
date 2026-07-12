import os
from urllib.parse import urlparse

def is_s3_path(path: str) -> bool:
    return path.startswith("s3://")

def get_s3_bucket_and_prefix(s3_url: str):
    parsed = urlparse(s3_url)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip('/')
    return bucket, prefix

def list_ortofotos(base_dir: str) -> list[str]:
    """
    Returns a list of valid orthophoto filenames in the given directory.
    Supports local paths and s3:// paths.
    """
    valid_extensions = ('.tif', '.tiff', '.ecw', '.jp2')
    
    if is_s3_path(base_dir):
        import boto3
        s3 = boto3.client('s3')
        bucket, prefix = get_s3_bucket_and_prefix(base_dir)
        
        try:
            # Paginator is safer if the bucket has >1000 items
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            archivos = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # We only want files directly in this prefix or subfolders?
                        # Usually, catalogacion just lists files in the directory.
                        filename = os.path.basename(key)
                        if filename.lower().endswith(valid_extensions):
                            archivos.append(filename)
            return archivos
        except Exception as e:
            print(f"Error reading S3 bucket {bucket}: {e}")
            return []
    else:
        if not os.path.exists(base_dir):
            return []
        return [f for f in os.listdir(base_dir) if f.lower().endswith(valid_extensions)]

def get_gdal_path(base_dir: str, filename: str = None) -> str:
    """
    Transforms a path to a format that GDAL understands.
    s3://bucket/path -> /vsis3/bucket/path
    """
    if is_s3_path(base_dir):
        bucket, prefix = get_s3_bucket_and_prefix(base_dir)
        # Ensure prefix doesn't end with slash if we are appending filename
        if prefix.endswith('/'):
            prefix = prefix[:-1]
        
        if filename:
            # In S3, we use forward slashes
            s3_key = f"{prefix}/{filename}" if prefix else filename
            return f"/vsis3/{bucket}/{s3_key}"
        else:
            return f"/vsis3/{bucket}/{prefix}"
    else:
        if filename:
            return os.path.join(base_dir, filename)
        return base_dir

def check_path_exists(base_dir: str) -> bool:
    """
    Checks if a local path or an S3 bucket/prefix exists.
    """
    if is_s3_path(base_dir):
        import boto3
        s3 = boto3.client('s3')
        bucket, prefix = get_s3_bucket_and_prefix(base_dir)
        try:
            # We just try to list one object to see if we have access/it exists
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
            # We don't check 'Contents' because the prefix itself might be valid even if empty,
            # but if the bucket doesn't exist or we have no permission, it throws an exception.
            return True
        except Exception as e:
            print(f"Error verifying S3 path {base_dir}: {e}")
            return False
    else:
        return os.path.exists(base_dir)
