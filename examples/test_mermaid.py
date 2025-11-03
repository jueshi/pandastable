import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mermaid_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MermaidTest')

def check_mmdc():
    """Check if mmdc is available and return its path."""
    # Common locations to check for mmdc
    possible_paths = [
        'mmdc',  # In PATH
        os.path.join(os.environ.get('APPDATA', ''), 'npm/mmdc.cmd'),
        os.path.join(os.environ.get('APPDATA', ''), 'npm/mmdc'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs/mmdc.cmd'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs/mmdc.cmd'),
    ]
    
    for path in possible_paths:
        try:
            logger.info(f"Trying mmdc at: {path}")
            result = subprocess.run(
                [path, '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Found mmdc at: {path}")
                logger.info(f"Version: {result.stdout.strip()}")
                return path
            else:
                logger.warning(f"mmdc at {path} returned non-zero: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error checking {path}: {str(e)}")
    
    logger.error("Could not find mmdc in any of the expected locations")
    return None

def main():
    logger.info("=== Starting Mermaid CLI Test ===")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Check PATH environment variable
    path_env = os.environ.get('PATH', '')
    logger.info("PATH environment variable:")
    for path in path_env.split(os.pathsep):
        logger.info(f"  - {path}")
    
    # Check for mmdc
    mmdc_path = check_mmdc()
    
    if mmdc_path:
        logger.info("Mermaid CLI is properly installed and accessible!")
        logger.info(f"Path: {mmdc_path}")
    else:
        logger.error("Mermaid CLI is not properly installed or accessible")
        logger.error("Please install it using: npm install -g @mermaid-js/mermaid-cli")

if __name__ == "__main__":
    main()
