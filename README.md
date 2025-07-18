# AWS S3 Monitor

A comprehensive AWS S3 file operations tool with enhanced backup capabilities, real-time monitoring, and an intuitive Streamlit web interface.

## Features

- **Complete S3 Operations**: Upload, download, delete files and directories
- **Real-time Monitoring**: Auto-detect changes in S3 buckets and sync locally
- **Scheduled Backups**: Automated backup with versioning and integrity checks
- **Web Interface**: User-friendly Streamlit UI for all operations
- **File Type Filtering**: Support for specific file extensions (PDF, JPEG, MP4, DOCX, TXT)
- **Enhanced Logging**: Comprehensive logging with verbose mode
- **Metadata Management**: Track file changes with hash verification
- **Batch Operations**: Efficient handling of large directories

## Prerequisites

- Python 3.8 or higher
- AWS Account with S3 access
- AWS Access Key ID and Secret Access Key
- Node.js (for documentation with Docsify)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AmanAJ21/AWS.git
cd AWS
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install using setup.py:

```bash
python setup.py install
```

### 3. Install Docsify CLI (for Documentation)

```bash
npm i docsify-cli -g
```

## Quick Start

### 1. Set Up AWS Credentials

You can provide AWS credentials in two ways:

**Option A: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_DEFAULT_REGION=ap-south-1
```

**Option B: Through the Web Interface**
- Launch the application and enter credentials in the sidebar

### 2. Launch the Application

```bash
streamlit run aws_ui.py
```

The application will open in your browser at `http://localhost:8501`

### 3. Basic Operations

1. **Enter AWS Credentials** in the sidebar
2. **List Buckets** to see available S3 buckets
3. **Create/Select Bucket** for operations
4. **Upload Files** using the file uploader
5. **Monitor Changes** with real-time sync

## Core Modules

### aws.py
Core AWS S3 operations module containing:
- `list_s3_buckets()` - List all S3 buckets
- `aws_file_upload()` - Upload single files with type validation
- `aws_file_download()` - Download files with integrity checks
- `uploadDirectory()` - Batch upload directories
- `downloadDirectory()` - Batch download with filtering
- `deleteDirectory()` - Batch delete operations

### aws_ui.py
Streamlit web interface providing:
- Interactive AWS credentials management
- Real-time S3 monitoring with change detection
- Scheduled backup system with versioning
- Comprehensive logging and statistics
- File integrity validation

## Advanced Features

### Real-time Monitoring

Monitor S3 buckets for changes and automatically download new/modified files:

```python
# Configure monitoring in the web interface
- S3 Prefix: "documents/"
- Local Folder: "./local_backup"
- Polling Interval: 60 seconds
```

### Scheduled Backups

Set up automated backups with:
- **Incremental backups** - Only changed files
- **File versioning** - Keep previous versions
- **Integrity checks** - MD5 hash validation
- **Comprehensive logging** - Detailed backup reports

### File Type Filtering

Supported file extensions:
- Documents: `.pdf`, `.docx`, `.txt`
- Images: `.jpeg`, `.jpg`
- Videos: `.mpeg`, `.mp4`

## Configuration

### Environment Variables

```bash
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=ap-south-1
```

### Allowed File Extensions

Modify the `allowed_extensions` parameter in functions:

```python
allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.mpeg', '.mp4', '.docx', '.txt']
```

## Usage Examples

### Command Line Usage

```python
from aws import *

# Initialize S3 client
initialize_s3_client('your_key', 'your_secret', 'ap-south-1')

# List buckets
list_s3_buckets()

# Upload file
aws_file_upload('document.pdf', 'my-bucket', 'documents/document.pdf')

# Upload directory
uploadDirectory('/local/path', 'my-bucket', 'backup/', sort_by_date=True)

# Download directory
downloadDirectory('my-bucket', 'backup/', '/local/download/')
```

### Web Interface Usage

1. **Start the application**: `streamlit run aws_ui.py`
2. **Enter credentials** in the sidebar
3. **Select operations** from the main interface
4. **Monitor logs** in real-time
5. **View statistics** and status updates

## Documentation with Docsify

### Initialize Documentation

```bash
docsify init ./docs
```

### Serve Documentation Locally

```bash
docsify serve ./docs
```

### Deploy Documentation

The documentation will be available at `http://localhost:3000`

## Project Structure

```
AWS/
├── aws.py              # Core S3 operations
├── aws_ui.py           # Streamlit web interface
├── requirements.txt    # Python dependencies
├── setup.py           # Package setup
├── install.py         # Installation script
├── README.md          # This file
└── docs/              # Documentation (Docsify)
    ├── index.html
    └── README.md
```

## Error Handling

The application includes comprehensive error handling:
- **Connection errors** - Automatic retry with exponential backoff
- **File integrity** - MD5 hash verification
- **Credential validation** - Clear error messages
- **Rate limiting** - Intelligent polling intervals

## Logging

### Verbose Logging
Enable detailed logging in the web interface for:
- File operations tracking
- Error diagnostics
- Performance monitoring
- Backup statistics

### Log Files
- Monitor logs: Stored in session state
- Backup logs: `backup_log.txt` in backup directory
- Metadata: `.backup_metadata.json` for tracking changes

## Security Best Practices

- **Never commit AWS credentials** to version control
- **Use environment variables** for sensitive data
- **Implement least privilege** IAM policies
- **Enable S3 bucket encryption** when possible
- **Monitor access logs** regularly

## Troubleshooting

### Common Issues

1. **Credentials Error**
   - Verify AWS Access Key and Secret Key
   - Check IAM permissions for S3 access

2. **Connection Timeout**
   - Check internet connection
   - Verify AWS region settings

3. **File Upload Fails**
   - Check file size limits
   - Verify file extension is allowed
   - Ensure sufficient S3 storage

4. **Monitoring Not Working**
   - Verify bucket exists and is accessible
   - Check local folder permissions
   - Review polling interval settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation at `http://localhost:3000` (after running docsify)
- Review the troubleshooting section above

## Changelog

### Version 1.0.0
- Initial release with core S3 operations
- Streamlit web interface
- Real-time monitoring capabilities
- Scheduled backup system
- Comprehensive logging and error handling

---

**Note**: This tool is designed for educational and development purposes. Always follow AWS best practices and security guidelines in production environments.
