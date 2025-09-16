#!/usr/bin/env python3
"""
Example usage of update.py for NFE Alert
This script demonstrates how to use the Python update script in practice.
"""

import subprocess
import sys
from pathlib import Path

def run_update_example():
    """Run the update script with example parameters."""
    
    # Path to the update script
    script_dir = Path(__file__).parent
    update_script = script_dir / "update.py"
    
    # Example 1: Basic update with verbose output
    print("Example 1: Basic update with verbose logging")
    print("-" * 50)
    
    cmd = [
        sys.executable, str(update_script),
        "--owner", "AR-BPS-TaxTech",
        "--repo", "nfe_alert",
        "--verbose",
        "--target", "/tmp/example_nfe_installation"
    ]
    
    print("Command to run:")
    print(" ".join(cmd))
    print()
    print("Note: This would normally download the latest release from GitHub.")
    print("For private repositories, ensure GITHUB_TOKEN is set.")
    print()
    
    # Example 2: Force update to specific version
    print("Example 2: Force update to specific version")
    print("-" * 50)
    
    cmd_specific = [
        sys.executable, str(update_script),
        "--owner", "AR-BPS-TaxTech", 
        "--repo", "nfe_alert",
        "--channel-tag", "v1.2.0",  # Specific version
        "--force",  # Force even if same version
        "--verbose",
        "--target", "/opt/nfe_alert"
    ]
    
    print("Command to run:")
    print(" ".join(cmd_specific))
    print()
    
    # Example 3: With environment setup
    print("Example 3: Complete setup with authentication")
    print("-" * 50)
    
    setup_commands = [
        "# Set up GitHub token for private repository access",
        "export GITHUB_TOKEN='your_github_token_here'",
        "",
        "# Or create a .env file",
        "echo 'GITHUB_TOKEN=your_github_token_here' > .env",
        "",
        "# Run the update",
        " ".join([
            "python update.py",
            "--owner AR-BPS-TaxTech",
            "--repo nfe_alert", 
            "--target ~/nfe_alert",
            "--verbose"
        ])
    ]
    
    for cmd in setup_commands:
        print(cmd)
    
    print()
    print("Comparison with PowerShell version:")
    print("-" * 50)
    
    powershell_cmd = (
        "update.ps1 -Owner AR-BPS-TaxTech -Repo nfe_alert "
        "-Target ~/nfe_alert -Verbose"
    )
    
    python_cmd = (
        "python update.py --owner AR-BPS-TaxTech --repo nfe_alert "
        "--target ~/nfe_alert --verbose"
    )
    
    print(f"PowerShell: {powershell_cmd}")
    print(f"Python:     {python_cmd}")
    print()
    
    print("Benefits of Python version:")
    print("- Cross-platform compatibility (Windows, Linux, macOS)")
    print("- Better error handling and logging")
    print("- No dependency on PowerShell or Windows-specific tools")
    print("- Consistent behavior across different operating systems")
    print("- Easier integration with Python-based workflows")

if __name__ == "__main__":
    run_update_example()