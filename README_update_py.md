# Python Update Script for NFE Alert

This document describes the Python implementation of the update script (`update.py`), which is a reimplementation of the original PowerShell script (`update.ps1`) with improved portability and flexibility.

## Overview

The Python update script automates the download and installation of NFE Alert releases from GitHub. It provides the same functionality as the PowerShell version but with cross-platform compatibility and improved error handling.

## Features

- **Cross-platform compatibility**: Works on Windows, Linux, and macOS
- **GitHub API integration**: Fetches releases using GitHub's REST API
- **Authentication support**: Supports GitHub tokens for private repositories
- **SHA256 verification**: Verifies download integrity when SHA256 files are available
- **Incremental updates**: Only updates when a new version is available
- **Flexible configuration**: Customizable patterns, directories, and options
- **Comprehensive logging**: Detailed logging with verbose mode support

## Requirements

- Python 3.6 or higher
- `requests` library (usually included in Python installations)
- Internet connection for GitHub API access

## Installation

No special installation is required. The script uses only standard Python libraries and `requests`, which is commonly available.

```bash
# Make the script executable (Unix-like systems)
chmod +x update.py
```

## Usage

### Basic Usage

```bash
# Update from the latest release
python update.py --owner AR-BPS-TaxTech --repo nfe_alert

# Update to a specific tag
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --channel-tag v1.2.3

# Update with custom target directory
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --target /path/to/installation
```

### Advanced Usage

```bash
# Force reinstallation even if up to date
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --force

# Enable verbose logging
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose

# Custom asset patterns
python update.py --owner AR-BPS-TaxTech --repo nfe_alert \
    --zip-name-pattern "custom*.zip" \
    --sha-name-pattern "custom*.sha256"

# Keep temporary files for debugging
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --no-cleanup
```

## Command-Line Arguments

| Argument | Description | Default | Required |
|----------|-------------|---------|----------|
| `--owner` | GitHub repository owner | - | Yes |
| `--repo` | GitHub repository name | - | Yes |
| `--channel-tag` | Release tag to install | `latest` | No |
| `--target` | Target directory for installation | `~/NFE_Alert` | No |
| `--zip-name-pattern` | Pattern to match ZIP asset names | `nfe_alert*.zip` | No |
| `--sha-name-pattern` | Pattern to match SHA256 asset names | `nfe_alert*.zip.sha256` | No |
| `--temp-root` | Root directory for temporary files | System temp | No |
| `--no-cleanup` | Do not clean up temporary files | False | No |
| `--force` | Force reinstallation | False | No |
| `--verbose`, `-v` | Enable verbose logging | False | No |

## Authentication

The script supports GitHub authentication for accessing private repositories or avoiding rate limits.

### Environment Variables

Set one of these environment variables:

```bash
export GITHUB_TOKEN="your_token_here"
# or
export GITHUB_PAT_NFE_UY="your_token_here"
```

### .env File

Create a `.env` file in the script directory or current working directory:

```env
GITHUB_TOKEN=your_token_here
```

The script will automatically detect and use the token. Tokens in `.env` files take precedence over environment variables.

## File Structure

After installation, the target directory will contain:

```
target_directory/
├── .nfe_release_tag          # Version tracking file
├── (extracted release files)
└── ...
```

The `.nfe_release_tag` file contains the currently installed version tag and is used to avoid unnecessary reinstallations.

## Error Handling

The script includes comprehensive error handling for common scenarios:

- **Network errors**: Graceful handling of API failures with informative messages
- **Authentication errors**: Clear messages for token-related issues
- **File system errors**: Proper handling of permission and disk space issues
- **SHA256 mismatches**: Automatic cleanup and clear error reporting

## Logging

The script provides detailed logging at different levels:

- **INFO**: Basic progress information
- **DEBUG**: Detailed operation information (enabled with `--verbose`)
- **ERROR**: Error messages with optional stack traces

## Comparison with PowerShell Version

| Feature | PowerShell | Python | Notes |
|---------|------------|--------|-------|
| Cross-platform | Windows only | All platforms | Python version works everywhere |
| Dependencies | Windows, PowerShell | Python 3.6+ | Minimal requirements |
| Authentication | .env + env vars | .env + env vars | Same mechanism |
| SHA256 verification | Yes | Yes | Same functionality |
| Robocopy equivalent | Robocopy | shutil | Platform-appropriate file operations |
| Error handling | Basic | Comprehensive | Improved error messages |
| Logging | Write-Host | Python logging | Structured logging |

## Examples

### Example 1: Basic Update

```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

Output:
```
2023-XX-XX XX:XX:XX,XXX - INFO - Starting NFE Alert update process...
2023-XX-XX XX:XX:XX,XXX - INFO - Found release: v1.2.3
2023-XX-XX XX:XX:XX,XXX - DEBUG - Found ZIP asset: nfe_alert_v1.2.3.zip
2023-XX-XX XX:XX:XX,XXX - DEBUG - Found SHA256 asset: nfe_alert_v1.2.3.zip.sha256
2023-XX-XX XX:XX:XX,XXX - INFO - Update completed: v1.2.3 → /home/user/NFE_Alert
```

### Example 2: Custom Configuration

```bash
python update.py \
    --owner AR-BPS-TaxTech \
    --repo nfe_alert \
    --channel-tag v1.1.0 \
    --target /opt/nfe_alert \
    --force \
    --verbose
```

### Example 3: With Authentication

```bash
# Set token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Run update
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Likely a private repository or rate limiting
   - Solution: Set up GitHub authentication

2. **No ZIP asset found**: Asset naming doesn't match the pattern
   - Solution: Use custom `--zip-name-pattern`

3. **SHA256 mismatch**: Download corruption or incorrect SHA file
   - Solution: Check network connection and retry

4. **Permission denied**: Insufficient permissions for target directory
   - Solution: Run with appropriate permissions or change target

### Debug Mode

Use `--verbose` to get detailed information about the update process:

```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

## Security Considerations

- Store GitHub tokens securely
- Verify SHA256 checksums when available
- Use HTTPS for all GitHub API communications
- Clean up temporary files after installation

## Migration from PowerShell

To migrate from the PowerShell version:

1. Install Python 3.6+ if not already available
2. Use the same command-line arguments (with Python syntax)
3. Same authentication mechanism (`.env` files and environment variables)
4. Same directory structure and version tracking

The Python version is a drop-in replacement for most use cases.