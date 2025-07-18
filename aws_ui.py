import streamlit as st
import boto3
import os
import threading
import time
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from aws import (
    list_s3_buckets, create_bucket, aws_file_upload, aws_file_download, aws_file_delete,
    list_files_in_bucket, uploadDirectory, downloadDirectory, deleteDirectory, delete_bucket,
    initialize_s3_client, get_s3_client_from_env
)

# --- Initialize session state keys and thread events at the very top ---
if 's3_monitor_log' not in st.session_state:
    st.session_state['s3_monitor_log'] = []
if 's3_monitor_last' not in st.session_state:
    st.session_state['s3_monitor_last'] = {}
if 's3_monitor_stop_event' not in st.session_state:
    st.session_state['s3_monitor_stop_event'] = threading.Event()
if 's3_backup_log' not in st.session_state:
    st.session_state['s3_backup_log'] = []
if 's3_backup_stop_event' not in st.session_state:
    st.session_state['s3_backup_stop_event'] = threading.Event()
if 'main_log' not in st.session_state:
    st.session_state['main_log'] = []
if 'backup_metadata' not in st.session_state:
    st.session_state['backup_metadata'] = {}
if 'monitor_stats' not in st.session_state:
    st.session_state['monitor_stats'] = {'files_checked': 0, 'files_downloaded': 0, 'errors': 0}
if 'backup_stats' not in st.session_state:
    st.session_state['backup_stats'] = {'total_backups': 0, 'last_backup': None, 'files_backed_up': 0}

# --- Verbose logging checkbox ---
verbose = st.checkbox("Verbose Logging", value=False)

# --- Enhanced helper functions ---
def calculate_file_hash(file_path):
    """Calculate MD5 hash of a file for integrity checking"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def save_backup_metadata(bucket, prefix, local_folder):
    """Save backup metadata to JSON file"""
    metadata_file = os.path.join(local_folder, '.backup_metadata.json')
    metadata = {
        'bucket': bucket,
        'prefix': prefix,
        'last_backup': datetime.now().isoformat(),
        'files': st.session_state.get('backup_metadata', {})
    }
    try:
        os.makedirs(local_folder, exist_ok=True)
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        st.session_state['main_log'].append(f"Error saving metadata: {e}")

def load_backup_metadata(local_folder):
    """Load backup metadata from JSON file"""
    metadata_file = os.path.join(local_folder, '.backup_metadata.json')
    try:
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.session_state['main_log'].append(f"Error loading metadata: {e}")
    return {}

def validate_file_integrity(local_path, expected_size):
    """Validate downloaded file integrity"""
    try:
        if os.path.exists(local_path):
            actual_size = os.path.getsize(local_path)
            return actual_size == expected_size
    except Exception:
        pass
    return False

# --- Enhanced thread functions ---
def s3_monitor_thread(bucket, prefix, local_folder, interval, s3_client, log_key, last_key, stop_event, verbose):
    """Enhanced S3 monitoring with better change detection and error handling"""
    if log_key not in st.session_state:
        st.session_state[log_key] = []
    if last_key not in st.session_state:
        st.session_state[last_key] = {}
    
    # Load existing metadata
    metadata = load_backup_metadata(local_folder)
    if 'files' in metadata:
        st.session_state[last_key].update(metadata['files'])
    
    st.session_state[log_key].append(f"Started enhanced monitoring bucket '{bucket}' (prefix: '{prefix}') every {interval} seconds.")
    consecutive_errors = 0
    max_errors = 5
    
    while not stop_event.is_set():
        try:
            # Reset error counter on successful operation
            consecutive_errors = 0
            
            # Use pagination for large buckets
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            files_checked = 0
            files_downloaded = 0
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if stop_event.is_set():
                            break
                            
                        key = obj['Key']
                        last_modified = obj['LastModified']
                        size = obj.get('Size', 0)
                        etag = obj.get('ETag', '').strip('"')
                        
                        files_checked += 1
                        st.session_state['monitor_stats']['files_checked'] += 1
                        
                        if verbose:
                            st.session_state[log_key].append(f"Checked: {key} (Modified: {last_modified}, Size: {size})")
                        
                        # Enhanced change detection: check both timestamp and ETag
                        file_changed = False
                        if key not in st.session_state[last_key]:
                            file_changed = True
                            reason = "new file"
                        else:
                            stored_info = st.session_state[last_key][key]
                            if isinstance(stored_info, dict):
                                if (stored_info.get('last_modified') != last_modified or 
                                    stored_info.get('etag') != etag):
                                    file_changed = True
                                    reason = "file modified"
                            else:
                                # Legacy format - just timestamp
                                if stored_info != last_modified:
                                    file_changed = True
                                    reason = "file modified (legacy check)"
                        
                        if file_changed:
                            rel_path = key[len(prefix):] if key.startswith(prefix) else key
                            local_path = os.path.join(local_folder, rel_path)
                            
                            try:
                                # Create directory structure
                                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                                
                                # Download with retry logic
                                max_retries = 3
                                for attempt in range(max_retries):
                                    try:
                                        s3_client.download_file(bucket, key, local_path)
                                        
                                        # Validate file integrity
                                        if validate_file_integrity(local_path, size):
                                            # Calculate hash for additional verification
                                            file_hash = calculate_file_hash(local_path)
                                            
                                            # Store enhanced metadata
                                            st.session_state[last_key][key] = {
                                                'last_modified': last_modified,
                                                'etag': etag,
                                                'size': size,
                                                'hash': file_hash,
                                                'downloaded_at': datetime.now().isoformat()
                                            }
                                            
                                            files_downloaded += 1
                                            st.session_state['monitor_stats']['files_downloaded'] += 1
                                            
                                            st.session_state[log_key].append(
                                                f"✓ Downloaded: {key} -> {local_path} ({reason}) "
                                                f"[Size: {size}, Hash: {file_hash[:8]}...]"
                                            )
                                            break
                                        else:
                                            raise Exception("File integrity check failed")
                                            
                                    except Exception as download_error:
                                        if attempt == max_retries - 1:
                                            raise download_error
                                        time.sleep(2 ** attempt)  # Exponential backoff
                                        
                            except Exception as e:
                                st.session_state[log_key].append(f"✗ Failed to download {key}: {e}")
                                st.session_state['monitor_stats']['errors'] += 1
            
            # Save metadata after each successful scan
            st.session_state['backup_metadata'] = st.session_state[last_key]
            save_backup_metadata(bucket, prefix, local_folder)
            
            if verbose and files_checked > 0:
                st.session_state[log_key].append(f"Scan complete: {files_checked} files checked, {files_downloaded} downloaded")
                
        except Exception as e:
            consecutive_errors += 1
            st.session_state[log_key].append(f"✗ Monitor error ({consecutive_errors}/{max_errors}): {e}")
            st.session_state['monitor_stats']['errors'] += 1
            
            # If too many consecutive errors, increase interval
            if consecutive_errors >= max_errors:
                interval = min(interval * 2, 300)  # Cap at 5 minutes
                st.session_state[log_key].append(f"⚠ Too many errors, increasing interval to {interval}s")
                consecutive_errors = 0
        
        time.sleep(interval)
    
    st.session_state[log_key].append("Stopped enhanced S3 monitoring.")

def s3_backup_thread(bucket, prefix, local_folder, interval, s3_client, log_key, stop_event, verbose):
    """Enhanced backup with incremental backups, versioning, and comprehensive logging"""
    if log_key not in st.session_state:
        st.session_state[log_key] = []
    
    # Setup backup logging to file
    log_file = os.path.join(local_folder, 'backup_log.txt')
    
    def write_log(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        st.session_state[log_key].append(log_entry)
        try:
            os.makedirs(local_folder, exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            st.session_state[log_key].append(f"Log write error: {e}")
    
    # Load existing backup metadata
    metadata = load_backup_metadata(local_folder)
    backup_history = metadata.get('files', {})
    
    write_log(f"Started enhanced backup from bucket '{bucket}' (prefix: '{prefix}') every {interval} minutes.")
    write_log(f"Backup folder: {local_folder}")
    write_log(f"Log file: {log_file}")
    
    backup_count = 0
    consecutive_errors = 0
    max_errors = 3
    
    while not stop_event.is_set():
        backup_start_time = datetime.now()
        backup_count += 1
        files_backed_up = 0
        files_skipped = 0
        total_size = 0
        
        try:
            write_log(f"=== Backup #{backup_count} started ===")
            consecutive_errors = 0
            
            # Use pagination for large buckets
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in page_iterator:
                if stop_event.is_set():
                    write_log("Backup stopped by user request")
                    break
                    
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if stop_event.is_set():
                            break
                            
                        key = obj['Key']
                        last_modified = obj['LastModified']
                        size = obj.get('Size', 0)
                        etag = obj.get('ETag', '').strip('"')
                        
                        # Determine if file needs backup
                        needs_backup = True
                        backup_reason = "new file"
                        
                        if key in backup_history:
                            stored_info = backup_history[key]
                            if isinstance(stored_info, dict):
                                if (stored_info.get('last_modified') == last_modified and 
                                    stored_info.get('etag') == etag):
                                    needs_backup = False
                                else:
                                    backup_reason = "file modified"
                            else:
                                # Legacy format check
                                if stored_info == last_modified:
                                    needs_backup = False
                                else:
                                    backup_reason = "file modified (legacy)"
                        
                        if needs_backup:
                            rel_path = key[len(prefix):] if key.startswith(prefix) else key
                            local_path = os.path.join(local_folder, rel_path)
                            
                            # Create versioned backup if file exists
                            if os.path.exists(local_path):
                                backup_dir = os.path.join(local_folder, '.versions')
                                os.makedirs(backup_dir, exist_ok=True)
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                backup_filename = f"{os.path.basename(rel_path)}_{timestamp}"
                                backup_path = os.path.join(backup_dir, backup_filename)
                                try:
                                    os.rename(local_path, backup_path)
                                    write_log(f"Versioned backup: {rel_path} -> .versions/{backup_filename}")
                                except Exception as e:
                                    write_log(f"Version backup failed for {rel_path}: {e}")
                            
                            try:
                                # Create directory structure
                                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                                
                                # Download with retry logic
                                max_retries = 3
                                download_success = False
                                
                                for attempt in range(max_retries):
                                    try:
                                        s3_client.download_file(bucket, key, local_path)
                                        
                                        # Validate file integrity
                                        if validate_file_integrity(local_path, size):
                                            # Calculate hash for verification
                                            file_hash = calculate_file_hash(local_path)
                                            
                                            # Update backup history
                                            backup_history[key] = {
                                                'last_modified': last_modified,
                                                'etag': etag,
                                                'size': size,
                                                'hash': file_hash,
                                                'backed_up_at': datetime.now().isoformat(),
                                                'backup_count': backup_count
                                            }
                                            
                                            files_backed_up += 1
                                            total_size += size
                                            st.session_state['backup_stats']['files_backed_up'] += 1
                                            
                                            write_log(f"✓ Backed up: {key} -> {local_path} ({backup_reason}) [Size: {size}, Hash: {file_hash[:8]}...]")
                                            download_success = True
                                            break
                                        else:
                                            raise Exception("File integrity check failed")
                                            
                                    except Exception as download_error:
                                        if attempt == max_retries - 1:
                                            raise download_error
                                        time.sleep(2 ** attempt)  # Exponential backoff
                                        write_log(f"Retry {attempt + 1}/{max_retries} for {key}")
                                
                                if not download_success:
                                    write_log(f"✗ Failed to backup {key} after {max_retries} attempts")
                                    
                            except Exception as e:
                                write_log(f"✗ Backup failed for {key}: {e}")
                                consecutive_errors += 1
                        else:
                            files_skipped += 1
                            if verbose:
                                write_log(f"Skipped: {key} (unchanged)")
            
            # Update statistics
            backup_duration = datetime.now() - backup_start_time
            st.session_state['backup_stats']['total_backups'] += 1
            st.session_state['backup_stats']['last_backup'] = backup_start_time.isoformat()
            
            # Save updated metadata
            st.session_state['backup_metadata'] = backup_history
            save_backup_metadata(bucket, prefix, local_folder)
            
            # Summary log
            write_log(f"=== Backup #{backup_count} completed ===")
            write_log(f"Duration: {backup_duration}")
            write_log(f"Files backed up: {files_backed_up}")
            write_log(f"Files skipped: {files_skipped}")
            write_log(f"Total size: {total_size:,} bytes")
            write_log(f"Next backup in {interval} minutes")
            
        except Exception as e:
            consecutive_errors += 1
            write_log(f"✗ Backup error ({consecutive_errors}/{max_errors}): {e}")
            
            # If too many consecutive errors, increase interval
            if consecutive_errors >= max_errors:
                interval = min(interval * 2, 60)  # Cap at 1 hour
                write_log(f"⚠ Too many errors, increasing interval to {interval} minutes")
                consecutive_errors = 0
        
        # Wait for next backup cycle
        for _ in range(interval * 60):
            if stop_event.is_set():
                break
            time.sleep(1)
    
    write_log("Stopped enhanced backup process.")

# --- Helper for verbose logging in main UI actions ---
def log_main(msg):
    st.session_state['main_log'].append(msg)

# --- UI and S3 operations with verbose logging ---
st.title("AWS S3 File Operations UI")

# Sidebar for AWS credentials and bucket
st.sidebar.header("AWS Credentials")
aws_access_key_id = st.sidebar.text_input("Access Key ID", type="password")
aws_secret_access_key = st.sidebar.text_input("Secret Access Key", type="password")
region_name = st.sidebar.text_input("Region", value="ap-south-1")
bucket_name = st.sidebar.text_input("Bucket Name")

@st.cache_resource(show_spinner=False)
def get_s3_client(aws_access_key_id, aws_secret_access_key, region_name):
    return boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

if aws_access_key_id and aws_secret_access_key and region_name:
    s3 = get_s3_client(aws_access_key_id, aws_secret_access_key, region_name)
    # Also initialize the S3 client in the aws module for functions that use it
    initialize_s3_client(aws_access_key_id, aws_secret_access_key, region_name)
    st.success("AWS credentials set.")

    st.header("S3 Operations")
    log = st.empty()

    # List Buckets
    if st.button("List S3 Buckets"):
        try:
            response = s3.list_buckets()
            if 'Buckets' in response:
                st.write("**Buckets:**")
                for bucket in response['Buckets']:
                    st.write(f"- {bucket['Name']} (Created: {bucket['CreationDate']})")
                    if verbose:
                        log_main(f"Bucket: {bucket['Name']} (Created: {bucket['CreationDate']})")
            else:
                st.info("No buckets found.")
                if verbose:
                    log_main("No buckets found.")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error listing buckets: {e}")

    # Create Bucket
    if st.button("Create Bucket"):
        try:
            response = s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region_name}
            )
            st.success(f"Bucket '{bucket_name}' created.")
            log_main(f"Created bucket: {bucket_name} in region {region_name}")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error creating bucket: {e}")

    # List Files in Bucket
    if st.button("List Files in Bucket"):
        try:
            response = s3.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                st.write(f"**Files in {bucket_name}:**")
                for obj in response['Contents']:
                    st.write(f"- {obj['Key']} (Size: {obj['Size']} bytes, Modified: {obj['LastModified']})")
                    if verbose:
                        log_main(f"File: {obj['Key']} (Size: {obj['Size']} bytes, Modified: {obj['LastModified']})")
            else:
                st.info("Bucket is empty.")
                if verbose:
                    log_main(f"Bucket {bucket_name} is empty.")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error listing files: {e}")

    # Upload File
    uploaded_file = st.file_uploader("Upload File to S3", type=["pdf", "jpeg", "jpg", "mpeg", "mp4", "docx", "txt"])
    if uploaded_file and st.button("Upload File"):
        try:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            s3.upload_file(uploaded_file.name, bucket_name, uploaded_file.name)
            st.success(f"Uploaded {uploaded_file.name} to {bucket_name}")
            if verbose:
                log_main(f"Uploaded file: {uploaded_file.name} to bucket: {bucket_name}")
            os.remove(uploaded_file.name)
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error uploading file {uploaded_file.name}: {e}")

    # Upload Directory
    st.write("---")
    st.subheader("Upload Directory to S3")
    local_dir = st.text_input("Local Directory Path to Upload")
    s3_prefix = st.text_input("S3 Prefix (folder in bucket)", value="Document/")
    if local_dir and st.button("Upload Directory"):
        try:
            uploadDirectory(local_dir, bucket_name, s3_prefix)
            st.success(f"Uploaded directory {local_dir} to {bucket_name}/{s3_prefix}")
            if verbose:
                log_main(f"Uploaded directory: {local_dir} to bucket: {bucket_name}/{s3_prefix}")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error uploading directory {local_dir}: {e}")

    # Download Directory
    st.write("---")
    st.subheader("Download Directory from S3")
    s3_download_prefix = st.text_input("S3 Prefix to Download", value="Document/")
    local_download_dir = st.text_input("Local Directory to Save Downloaded Files", value="downloaded_document/")
    if s3_download_prefix and local_download_dir and st.button("Download Directory"):
        try:
            downloadDirectory(bucket_name, s3_download_prefix, local_download_dir)
            st.success(f"Downloaded {s3_download_prefix} from {bucket_name} to {local_download_dir}")
            if verbose:
                log_main(f"Downloaded directory: {s3_download_prefix} from bucket: {bucket_name} to local: {local_download_dir}")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error downloading directory {s3_download_prefix}: {e}")

    # Delete Directory
    st.write("---")
    st.subheader("Delete Directory in S3")
    s3_delete_prefix = st.text_input("S3 Prefix to Delete", value="Document/")
    if s3_delete_prefix and st.button("Delete Directory"):
        try:
            deleteDirectory(bucket_name, s3_delete_prefix)
            st.success(f"Deleted directory {s3_delete_prefix} in {bucket_name}")
            if verbose:
                log_main(f"Deleted directory: {s3_delete_prefix} in bucket: {bucket_name}")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error deleting directory {s3_delete_prefix}: {e}")

    # Delete Bucket
    st.write("---")
    st.subheader("Delete Bucket")
    if st.button("Delete Bucket"):
        try:
            delete_bucket(bucket_name)
            s3.delete_bucket(Bucket=bucket_name)
            st.success(f"Bucket {bucket_name} deleted.")
            if verbose:
                log_main(f"Deleted bucket: {bucket_name}")
        except Exception as e:
            st.error(f"Error: {e}")
            log_main(f"Error deleting bucket {bucket_name}: {e}")
else:
    st.info("Please enter AWS credentials and region in the sidebar.")

# --- Auto-Detect Changes on S3 Bucket Section ---
st.write("---")
st.header("Auto-Detect Changes on S3 Bucket (Download New/Changed Files)")
s3_monitor_prefix = st.text_input("S3 Prefix to Monitor", value="", key="s3_monitor_prefix")
local_monitor_folder = st.text_input("Local Folder to Download Files", key="local_monitor_folder")
s3_monitor_interval = st.number_input("Polling Interval (seconds)", min_value=10, value=60, step=10, key="s3_monitor_interval")

colm1, colm2 = st.columns(2)
with colm1:
    if st.button("Start S3 Monitor"):
        st.session_state['s3_monitor_stop_event'].clear()
        if local_monitor_folder and bucket_name:
            t = threading.Thread(target=s3_monitor_thread, args=(bucket_name, s3_monitor_prefix, local_monitor_folder, s3_monitor_interval, s3, 's3_monitor_log', 's3_monitor_last', st.session_state['s3_monitor_stop_event'], verbose), daemon=True)
            t.start()
            if verbose:
                log_main(f"Started S3 Monitor thread for bucket: {bucket_name}, prefix: {s3_monitor_prefix}")
        else:
            st.warning("Please enter a valid local folder and bucket name.")
with colm2:
    if st.button("Stop S3 Monitor"):
        st.session_state['s3_monitor_stop_event'].set()
        if verbose:
            log_main("Stopped S3 Monitor thread.")

# Monitor Statistics and Status
col_stats1, col_stats2 = st.columns(2)
with col_stats1:
    st.write("**Monitor Statistics:**")
    stats = st.session_state['monitor_stats']
    st.write(f"- Files Checked: {stats['files_checked']:,}")
    st.write(f"- Files Downloaded: {stats['files_downloaded']:,}")
    st.write(f"- Errors: {stats['errors']:,}")

with col_stats2:
    st.write("**Monitor Status:**")
    is_running = not st.session_state['s3_monitor_stop_event'].is_set()
    status_color = "🟢" if is_running else "🔴"
    st.write(f"{status_color} Status: {'Running' if is_running else 'Stopped'}")
    if local_monitor_folder and os.path.exists(local_monitor_folder):
        metadata_file = os.path.join(local_monitor_folder, '.backup_metadata.json')
        if os.path.exists(metadata_file):
            st.write(f"📁 Metadata: Available")
        else:
            st.write(f"📁 Metadata: Not found")

st.write("**S3 Monitor Log (Last 10 entries):**")
for entry in st.session_state['s3_monitor_log'][-10:]:
    st.write(entry)

# --- Scheduled Backup from S3 Bucket Section ---
st.write("---")
st.header("Scheduled Backup from S3 Bucket (Download All Files)")
s3_backup_prefix = st.text_input("S3 Prefix to Backup", value="", key="s3_backup_prefix")
local_backup_folder = st.text_input("Local Folder for Backup", key="local_backup_folder")
s3_backup_interval = st.number_input("Backup Interval (minutes)", min_value=1, value=10, step=1, key="s3_backup_interval")

colb1, colb2 = st.columns(2)
with colb1:
    if st.button("Start Scheduled Backup (S3)"):
        st.session_state['s3_backup_stop_event'].clear()
        if local_backup_folder and bucket_name:
            t = threading.Thread(target=s3_backup_thread, args=(bucket_name, s3_backup_prefix, local_backup_folder, s3_backup_interval, s3, 's3_backup_log', st.session_state['s3_backup_stop_event'], verbose), daemon=True)
            t.start()
            if verbose:
                log_main(f"Started Scheduled Backup thread for bucket: {bucket_name}, prefix: {s3_backup_prefix}")
        else:
            st.warning("Please enter a valid local folder and bucket name.")
with colb2:
    if st.button("Stop Scheduled Backup (S3)"):
        st.session_state['s3_backup_stop_event'].set()
        if verbose:
            log_main("Stopped Scheduled Backup thread.")

# Backup Statistics and Status
col_backup_stats1, col_backup_stats2 = st.columns(2)
with col_backup_stats1:
    st.write("**Backup Statistics:**")
    backup_stats = st.session_state['backup_stats']
    st.write(f"- Total Backups: {backup_stats['total_backups']:,}")
    st.write(f"- Files Backed Up: {backup_stats['files_backed_up']:,}")
    if backup_stats['last_backup']:
        last_backup = datetime.fromisoformat(backup_stats['last_backup'])
        st.write(f"- Last Backup: {last_backup.strftime('%Y-%m-%d %H:%M:%S')}")

with col_backup_stats2:
    st.write("**Backup Status:**")
    is_backup_running = not st.session_state['s3_backup_stop_event'].is_set()
    backup_status_color = "🟢" if is_backup_running else "🔴"
    st.write(f"{backup_status_color} Status: {'Running' if is_backup_running else 'Stopped'}")
    
    # Check for log file and versions folder
    if local_backup_folder:
        log_file_path = os.path.join(local_backup_folder, 'backup_log.txt')
        versions_path = os.path.join(local_backup_folder, '.versions')
        if os.path.exists(log_file_path):
            st.write(f"📄 Log File: Available")
        if os.path.exists(versions_path):
            version_count = len([f for f in os.listdir(versions_path) if os.path.isfile(os.path.join(versions_path, f))])
            st.write(f"📦 Versions: {version_count} files")

# Log file management
if local_backup_folder and os.path.exists(local_backup_folder):
    log_file_path = os.path.join(local_backup_folder, 'backup_log.txt')
    col_log1, col_log2, col_log3 = st.columns(3)
    
    with col_log1:
        if st.button("📄 View Full Log File") and os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                st.text_area("Full Backup Log", log_content, height=200)
            except Exception as e:
                st.error(f"Error reading log file: {e}")
    
    with col_log2:
        if st.button("📥 Download Log File") and os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'rb') as f:
                    st.download_button(
                        label="Download backup_log.txt",
                        data=f.read(),
                        file_name="backup_log.txt",
                        mime="text/plain"
                    )
            except Exception as e:
                st.error(f"Error downloading log file: {e}")
    
    with col_log3:
        if st.button("🗑️ Clear Log File") and os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'w') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log cleared by user\n")
                st.success("Log file cleared")
            except Exception as e:
                st.error(f"Error clearing log file: {e}")

st.write("**Scheduled Backup Log (Last 10 entries):**")
for entry in st.session_state['s3_backup_log'][-10:]:
    st.write(entry)

# --- Main Verbose Log ---
st.write("---")
st.header("System Log (All Operations)")

# Log management controls
col_log_ctrl1, col_log_ctrl2, col_log_ctrl3 = st.columns(3)

with col_log_ctrl1:
    if st.button("📄 Export System Log"):
        log_content = '\n'.join(st.session_state['main_log'])
        st.download_button(
            label="Download system_log.txt",
            data=log_content,
            file_name=f"system_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

with col_log_ctrl2:
    if st.button("🗑️ Clear System Log"):
        st.session_state['main_log'] = [f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] System log cleared by user"]
        st.success("System log cleared")

with col_log_ctrl3:
    log_filter = st.selectbox("Filter Log", ["All", "Errors Only", "Success Only"], key="log_filter")

# Display filtered log
filtered_log = st.session_state['main_log']
if log_filter == "Errors Only":
    filtered_log = [entry for entry in st.session_state['main_log'] if "Error" in entry or "✗" in entry]
elif log_filter == "Success Only":
    filtered_log = [entry for entry in st.session_state['main_log'] if "✓" in entry or "success" in entry.lower()]

st.write(f"**System Log ({len(filtered_log)} entries):**")
for entry in filtered_log[-20:]:
    if "Error" in entry or "✗" in entry:
        st.error(entry)
    elif "✓" in entry or "success" in entry.lower():
        st.success(entry)
    else:
        st.write(entry) 