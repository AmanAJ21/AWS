import boto3
import os

# Global S3 client variable - will be initialized when credentials are provided
s3 = None

def initialize_s3_client(aws_access_key_id, aws_secret_access_key, region_name):
    """Initialize the S3 client with provided credentials"""
    global s3
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )
    return s3

def get_s3_client_from_env():
    """Initialize S3 client from environment variables if available"""
    global s3
    try:
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        if aws_access_key_id and aws_secret_access_key:
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            return s3
    except Exception as e:
        print(f"Error initializing S3 client from environment: {e}")
    return None

def list_s3_buckets():
    """
    List all S3 buckets in the account
    """
    try:
        print("Retrieving list of S3 buckets...")
        # Retrieve the list of existing buckets
        response = s3.list_buckets()
        
        # Output the bucket names
        print('Existing buckets:')
        if 'Buckets' in response and response['Buckets']:
            for bucket in response['Buckets']:
                print(f'  - {bucket["Name"]} (Created: {bucket["CreationDate"]})')
        else:
            print('  No buckets found.')
        return True
        
    except Exception as e:
        print(f"Error listing S3 buckets: {e}")
        return False
        
def create_bucket():
    
    try:
        response = s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': region_name
            }
        )
        print(f"Bucket '{bucket_name}' created successfully in region '{region_name}'.")
    except Exception as e:
        print(f"Error creating bucket: {e}")

def aws_file_upload(filename, bucket, object_name=None, allowed_extensions=None):
    # Default allowed file extensions
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.mpeg', '.mp4', '.docx', '.txt']
    
    # Normalize extensions to lowercase
    allowed_extensions = [ext.lower() for ext in allowed_extensions]
    
    try:
        # Check if file exists
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' does not exist.")
            return False
        
        # Check if it's a file (not a directory)
        if not os.path.isfile(filename):
            print(f"Error: '{filename}' is not a file.")
            return False
        
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            print(f"Error: File type '{file_ext}' not allowed. Allowed types: {', '.join(allowed_extensions)}")
            return False
        
        # If object_name is not specified, use the filename
        if object_name is None:
            object_name = os.path.basename(filename)
        
        print(f"Uploading {filename} to {bucket}/{object_name}...")
        response = s3.upload_file(filename, bucket, object_name)
        print(f"Successfully uploaded {filename} to {bucket}/{object_name}")
        list_files_in_bucket(bucket)
        return True
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return False
    except Exception as e:
        print(f"Error uploading file '{filename}': {e}")
        return False


def aws_file_download(filename, bucket, object_name=None):
  
    try:
        # If object_name is not specified, use the filename
        if object_name is None:
            object_name = os.path.basename(filename)
        
        # Create directory if it doesn't exist
        local_dir = os.path.dirname(filename)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        print(f"Downloading {bucket}/{object_name} to {filename}...")
        response = s3.download_file(bucket, object_name, filename)
        print(f"Successfully downloaded {bucket}/{object_name} to {filename}")
        return True
        
    except s3.exceptions.NoSuchKey:
        print(f"Error: Object '{object_name}' not found in bucket '{bucket}'.")
        return False
    except s3.exceptions.NoSuchBucket:
        print(f"Error: Bucket '{bucket}' does not exist.")
        return False
    except Exception as e:
        print(f"Error downloading file '{object_name}' from bucket '{bucket}': {e}")
        return False

def aws_file_delete(filename, bucket):
  
    try:
        print(f"Deleting {bucket}/{filename}...")
        response = s3.delete_object(Bucket=bucket, Key=filename)
        print(f"Successfully deleted {bucket}/{filename}")
        list_files_in_bucket(bucket)
        return True
        
    except s3.exceptions.NoSuchBucket:
        print(f"Error: Bucket '{bucket}' does not exist.")
        return False
    except Exception as e:
        print(f"Error deleting file '{filename}' from bucket '{bucket}': {e}")
        return False

def list_files_in_bucket(bucket):
  
    try:
        print(f"\nListing files in bucket '{bucket}':")
        response = s3.list_objects_v2(Bucket=bucket)
        
        if 'Contents' in response:
            print(f"Found {len(response['Contents'])} objects:")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} (Size: {obj['Size']} bytes, Modified: {obj['LastModified']})")
        else:
            print("Bucket is empty.")
        return True
        
    except s3.exceptions.NoSuchBucket:
        print(f"Error: Bucket '{bucket}' does not exist.")
        return False
    except Exception as e:
        print(f"Error listing files in bucket '{bucket}': {e}")
        return False

def uploadDirectory(path, bucket, object_name, allowed_extensions=None, sort_by_date=False):
    import os
    from datetime import datetime
    
    # Default allowed file extensions
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.mpeg', '.mp4', '.docx', '.txt']
    
    # Normalize extensions to lowercase
    allowed_extensions = [ext.lower() for ext in allowed_extensions]
    
    # Check if path exists and is a directory
    if not os.path.exists(path):
        print(f"Error: Path '{path}' does not exist.")
        return
    
    if not os.path.isdir(path):
        print(f"Error: Path '{path}' is not a directory.")
        return
    
    # Collect all files with allowed extensions
    files_to_upload = []
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # Check if file extension is allowed
                if file_ext in allowed_extensions:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    files_to_upload.append((file_path, mod_time))
                else:
                    print(f"Skipping {file_path} - unsupported file type ({file_ext})")
        
        # Sort files by date if requested
        if sort_by_date:
            files_to_upload.sort(key=lambda x: x[1], reverse=True)  # Most recent first
            print("Files sorted by modification date (newest first)")
        
        # Upload files
        for file_path, mod_time in files_to_upload:
            # Create relative path for S3 object key
            relative_path = os.path.relpath(file_path, path)
            
            # Create date-based folder structure if sorting by date
            if sort_by_date:
                file_date = datetime.fromtimestamp(mod_time)
                date_folder = file_date.strftime("%Y/%m/%d")
                s3_key = f"{object_name}/{date_folder}/{os.path.basename(file_path)}"
            else:
                s3_key = f"{object_name}/{relative_path.replace(os.sep, '/')}"
            
            print(f"Uploading {file_path} to {s3_key}")
            s3.upload_file(file_path, bucket, s3_key)
        
        print(f"Successfully uploaded {len(files_to_upload)} files from directory '{path}' to bucket '{bucket}'")
        list_files_in_bucket(bucket)
    except Exception as e:
        print(f"Error uploading directory: {e}")

def downloadDirectory(bucket, object_prefix, local_path, allowed_extensions=None, sort_by_date=False):

    from datetime import datetime
    
    # Default allowed file extensions
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.mpeg', '.mp4', '.docx', '.txt']
    
    # Normalize extensions to lowercase
    allowed_extensions = [ext.lower() for ext in allowed_extensions]
    
    try:
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)
        
        # List all objects with the given prefix
        response = s3.list_objects_v2(Bucket=bucket, Prefix=object_prefix)
        
        if 'Contents' not in response:
            print(f"No objects found with prefix '{object_prefix}' in bucket '{bucket}'")
            return
        
        # Filter objects by allowed extensions and collect with metadata
        files_to_download = []
        for obj in response['Contents']:
            object_key = obj['Key']
            file_ext = os.path.splitext(object_key)[1].lower()
            
            # Check if file extension is allowed
            if file_ext in allowed_extensions:
                files_to_download.append((obj, object_key))
            else:
                print(f"Skipping {object_key} - unsupported file type ({file_ext})")
        
        # Sort files by date if requested
        if sort_by_date:
            files_to_download.sort(key=lambda x: x[0]['LastModified'], reverse=True)
            print("Files sorted by modification date (newest first)")
        
        # Download each filtered object
        for obj, object_key in files_to_download:
            # Remove prefix from object key to get relative path
            relative_path = object_key.replace(object_prefix, '', 1).lstrip('/')
            
            if relative_path:  # Skip if it's just the prefix itself
                if sort_by_date:
                    # Create date-based folder structure
                    file_date = obj['LastModified']
                    date_folder = file_date.strftime("%Y/%m/%d")
                    local_file_path = os.path.join(local_path, date_folder, os.path.basename(relative_path))
                else:
                    local_file_path = os.path.join(local_path, relative_path)
                
                # Create subdirectories if needed
                local_dir = os.path.dirname(local_file_path)
                if local_dir:
                    os.makedirs(local_dir, exist_ok=True)
                
                print(f"Downloading {object_key} to {local_file_path}")
                s3.download_file(bucket, object_key, local_file_path)
        
        print(f"Successfully downloaded {len(files_to_download)} files from bucket '{bucket}' to '{local_path}'")
        
    except Exception as e:
        print(f"Error downloading directory: {e}")

def deleteDirectory(bucket, object_prefix, allowed_extensions=None):
  
    # Default allowed file extensions
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.mpeg', '.mp4', '.docx', '.txt']
    
    # Normalize extensions to lowercase
    allowed_extensions = [ext.lower() for ext in allowed_extensions]
    
    try:
        # List all objects with the given prefix
        response = s3.list_objects_v2(Bucket=bucket, Prefix=object_prefix)
        
        if 'Contents' not in response:
            print(f"No objects found with prefix '{object_prefix}' in bucket '{bucket}'")
            return
        
        # Filter objects by allowed extensions and prepare for deletion
        objects_to_delete = []
        for obj in response['Contents']:
            object_key = obj['Key']
            file_ext = os.path.splitext(object_key)[1].lower()
            
            # Check if file extension is allowed
            if file_ext in allowed_extensions:
                objects_to_delete.append({'Key': object_key})
            else:
                print(f"Skipping {object_key} - unsupported file type ({file_ext})")
        
        if not objects_to_delete:
            print(f"No files with allowed extensions found to delete in prefix '{object_prefix}'")
            return
        
        # Delete objects in batches (S3 allows up to 1000 objects per request)
        batch_size = 1000
        for i in range(0, len(objects_to_delete), batch_size):
            batch = objects_to_delete[i:i + batch_size]
            
            delete_response = s3.delete_objects(
                Bucket=bucket,
                Delete={
                    'Objects': batch,
                    'Quiet': False
                }
            )
            
            # Print deleted objects
            if 'Deleted' in delete_response:
                for deleted_obj in delete_response['Deleted']:
                    print(f"Deleted: {deleted_obj['Key']}")
            
            # Print any errors
            if 'Errors' in delete_response:
                for error in delete_response['Errors']:
                    print(f"Error deleting {error['Key']}: {error['Message']}")
        
        print(f"Successfully deleted {len(objects_to_delete)} files with prefix '{object_prefix}' from bucket '{bucket}'")
        list_files_in_bucket(bucket)
        
    except Exception as e:
        print(f"Error deleting directory: {e}")


def delete_bucket(bucket):
    objects = s3.list_objects_v2(Bucket = bucket)["Contents"]
    objects = list(map(lambda x: {"Key":x["Key"]},objects))
    s3.delete_objects(Bucket = bucket, Delete = {"Objects":objects})
        
if __name__ == "__main__":
    print("=== AWS S3 File Operations Demo ===")
    
    # Basic S3 operations
    #create_bucket()
   # list_s3_buckets()
    
    # Enhanced single file operations with file type filtering:
    
    # Upload single file (default allowed: pdf, jpeg, mpeg, docx, txt)
    #aws_file_upload('aws.docx', '24030142003', 'documents/aws.docx')
    
    # Download single file
    #aws_file_download('downloaded_aws.docx', '24030142003', 'documents/aws.docx')
    
    # Delete single file
    #aws_file_delete('documents/aws.docx', '24030142003')
    
    # Enhanced Directory operations with file type filtering and date sorting:
    
    # Upload directory with default file types (pdf, jpeg, jpg, mpeg, mp4, docx, txt)
    #uploadDirectory('D:/document', '24030142003', 'Document')
    
    # Upload directory with date sorting (organizes files by date in S3: YYYY/MM/DD/filename)
    #uploadDirectory('D:/document', '24030142003', 'Document', sort_by_date=True)
    
    # Download directory with default file types
    #downloadDirectory('24030142003', 'Document/', 'D:/downloaded_document')
    
    # Download directory with date sorting (organizes files by date locally: YYYY/MM/DD/filename)
    #downloadDirectory('24030142003', 'Document/', 'D:/downloaded_document', sort_by_date=True)
    
   
    # Delete directory with default file types
    #deleteDirectory('24030142003', 'Document/')
  
    #delete_bucket('24030142003')
    list_s3_buckets()
    # List all files in bucket
    #list_files_in_bucket('24030142003')
    
    
    #print("\n=== Demo Complete ===\n")
