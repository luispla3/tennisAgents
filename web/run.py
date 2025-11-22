"""
Script to run the TennisAgents web server
"""
import uvicorn
import sys
import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()

# Change to the web directory to ensure relative paths work
os.chdir(script_dir)

# Add the web directory to Python path
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=[str(script_dir)]
    )

