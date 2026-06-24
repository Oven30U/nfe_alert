"""Enhanced SQL Server connection diagnostics tool."""

import os
import re
import logging
import time
from typing import Dict, Optional, Any, List

# Third-party imports
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def mask_password(url: str) -> str:
    """
    Mask the password in a connection URL for safe logging.
    
    Args:
        url: The database connection URL string
        
    Returns:
        str: URL with password masked
    """
    if not url:
        return ""
    # Match password portion in the URL
    pattern = r'://([^:]+):([^@]+)@'
    return re.sub(pattern, r'://\1:********@', url)


def test_connection_variations(base_url: Optional[str] = None) -> Dict[str, bool]:
    """
    Test multiple variations of the connection string.
    
    Args:
        base_url: Base connection URL to test variations of
        
    Returns:
        Dict[str, bool]: Results of each variation attempt
    """
    if base_url is None:
        load_dotenv()
        base_url = os.getenv("DATABASE_URL", "")
    
    if not base_url:
        logger.error("DATABASE_URL environment variable is not set")
        return {"No URL provided": False}
    
    # Create variations of the connection string to test
    variations: Dict[str, str] = {
        "Original": base_url,
        "Encoded &": base_url.replace("T&L", "T%26L"),
        "Single backslash": re.sub(r'\\\\', r'\\', base_url),
        "No backslash": base_url.replace("\\", "/"),
        "With port": re.sub(r'@([^/\\]+)', r'@\1:1433', base_url),
    }
    
    results: Dict[str, bool] = {}
    
    for name, url in variations.items():
        logger.info(f"Testing variation: {name}")
        logger.info(f"Connection string: {mask_password(url)}")
        
        start_time = time.time()
        success = test_database_connection(url)
        elapsed = time.time() - start_time
        
        results[name] = success
        logger.info(f"Result: {'SUCCESS' if success else 'FAILED'} in {elapsed:.2f}s\n")
    
    return results


def test_database_connection(connection_url: str) -> bool:
    """
    Test connection to a database using SQLAlchemy.
    
    Args:
        connection_url: The database connection URL string
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    if not connection_url:
        logger.error("No connection URL provided")
        return False
    
    try:
        logger.info("Creating engine...")
        engine: Engine = create_engine(
            connection_url,
            connect_args={"timeout": 30}  # Increase timeout
        )
        
        logger.info("Attempting to connect...")
        with engine.connect() as connection:
            # Basic connectivity test
            result = connection.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"Basic query returned: {value}")
            
            # Get server version info
            version_info = connection.execute(text("SELECT @@VERSION")).scalar()
            logger.info(f"SQL Server version: {version_info.split()[0] if version_info else 'Unknown'}")
            
            # Try to get inspector to check for schema access
            try:
                insp = inspect(engine)
                schemas = insp.get_schema_names()
                logger.info(f"Available schemas: {', '.join(schemas[:5])}" + 
                           (f"... (and {len(schemas)-5} more)" if len(schemas) > 5 else ""))
            except Exception as e:
                logger.warning(f"Could not inspect schemas: {e}")
            
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Database connection error: {e}")
        # Extract more detailed error information
        error_info = str(e)
        if "08001" in error_info:
            logger.error("Server connection issue - check server name and instance")
        if "Login timeout expired" in error_info:
            logger.error("Connection timeout - server might be unreachable or firewall issue")
        if "password authentication failed" in error_info:
            logger.error("Authentication failed - check username and password")
        return False


if __name__ == "__main__":
    # Test all variations and show a summary
    results = test_connection_variations()
    
    logger.info("\n=== SUMMARY ===")
    for name, success in results.items():
        logger.info(f"{name}: {'SUCCESS' if success else 'FAILED'}")
    
    # Recommend the working variation
    working_variations = [name for name, success in results.items() if success]
    if working_variations:
        logger.info(f"\nRecommendation: Use the '{working_variations[0]}' connection string format")
    else:
        logger.info("\nAll connection attempts failed. Check server availability and credentials.")