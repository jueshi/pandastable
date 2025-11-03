import os
import subprocess
import sys
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('mermaid_test.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def find_mmdc():
    logger = logging.getLogger(__name__)
    candidates = [
        "mmdc",
        os.path.join(os.environ.get('APPDATA', ''), 'npm', 'mmdc.cmd'),
        os.path.join(os.environ.get('APPDATA', ''), 'npm', 'mmdc'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs', 'mmdc.cmd'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs', 'mmdc'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs', 'mmdc.cmd'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs', 'mmdc'),
    ]
    
    for cmd in candidates:
        if not cmd:
            continue
        try:
            env = os.environ.copy()
            proc = subprocess.run(
                [cmd, '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                shell=False,
                env=env
            )
            if proc.returncode == 0 and proc.stdout.strip():
                logger.info(f"Found Mermaid CLI at: {cmd}")
                logger.info(f"Version: {proc.stdout.strip()}")
                return cmd
        except Exception as e:
            logger.debug(f"Command failed for {cmd}: {str(e)}")
    
    logger.error("Mermaid CLI not found. Please install it with: npm install -g @mermaid-js/mermaid-cli")
    return None

def test_render_diagram(mmdc_path):
    logger = logging.getLogger(__name__)
    logger.info("Testing Mermaid diagram rendering...")
    
    # Create a simple flowchart
    mermaid_code = """
    graph TD;
        A[Start] --> B{Is it?};
        B -- Yes --> C[OK];
        B -- No --> D[Retry];
        D --> B;
    """
    
    # Create temp files
    os.makedirs("test_output", exist_ok=True)
    input_file = os.path.abspath("test_output/test.mmd")
    output_file = os.path.abspath("test_output/test.png")
    
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(mermaid_code)
    
    # Build command
    cmd = [
        mmdc_path,
        "-i", input_file,
        "-o", output_file,
        "-w", "1200",
        "-H", "800",
        "-b", "transparent",
        "-s", "1.5",
        "-t", "default",
        "--pdfFit",
        "--puppeteerConfigFile", os.path.abspath("puppeteer-config.json")
    ]
    
    # Create puppeteer config file
    with open("puppeteer-config.json", 'w') as f:
        f.write('{"args": ["--no-sandbox", "--disable-setuid-sandbox"]}')
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run the command
    try:
        env = os.environ.copy()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            shell=False
        )
        
        try:
            stdout, stderr = proc.communicate(timeout=60)
            logger.debug(f"Exit code: {proc.returncode}")
            
            if stdout:
                logger.debug(f"stdout: {stdout}")
            if stderr:
                logger.warning(f"stderr: {stderr}")
            
            if os.path.exists(output_file):
                if os.path.getsize(output_file) > 0:
                    logger.info(f"Success! Output file created at: {output_file}")
                    logger.info(f"File size: {os.path.getsize(output_file)} bytes")
                    return True
                else:
                    logger.error("Output file is empty")
                    os.remove(output_file)
            else:
                logger.error("Output file was not created")
            
            return False
            
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error("Mermaid CLI timed out after 60 seconds")
            return False
            
    except Exception as e:
        logger.error(f"Error running Mermaid CLI: {str(e)}", exc_info=True)
        return False

def main():
    logger = setup_logging()
    logger.info("Starting Mermaid CLI test...")
    
    # Find Mermaid CLI
    mmdc_path = find_mmdc()
    if not mmdc_path:
        logger.error("Mermaid CLI not found. Please install it with: npm install -g @mermaid-js/mermaid-cli")
        return 1
    
    # Test rendering a diagram
    success = test_render_diagram(mmdc_path)
    
    if success:
        logger.info("Test completed successfully!")
        return 0
    else:
        logger.error("Test failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
