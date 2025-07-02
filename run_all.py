import os
import subprocess
import sys
import shutil
import argparse
from dotenv import load_dotenv
load_dotenv()

def install_dependencies(force=False):
    """Install required packages."""
    if force or not os.path.exists("requirements.txt"):
        create_requirements_file()
    
    if force:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("Dependencies reinstalled.")
        except subprocess.CalledProcessError:
            print("Failed to reinstall dependencies.")
            sys.exit(1)
    else:
        print("Skipping dependency installation (already done). Use --reinstall to force reinstall.")

def create_requirements_file():
    """Create requirements.txt if it doesn't exist."""
    requirements = [
        "selenium",
        "webdriver-manager",
        "google-generativeai",
        "colorama",
        "pandas",
        "matplotlib",
        "fake-useragent",
        "python-dotenv"
    ]
    
    if not os.path.exists("requirements.txt"):
        with open("requirements.txt", "w") as f:
            f.write("\n".join(requirements))
        print("Created requirements.txt")

def setup_environment():
    """Create .env file if it doesn't exist."""
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("# Microsoft Rewards Agent Environment Variables\n")
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
            f.write("EDGE_DRIVER_PATH=auto\n")
            f.write("DEBUG_MODE=False\n")
            f.write("LOG_LEVEL=INFO\n")
            f.write("MAX_SEARCH_CYCLES=54\n")
            f.write("MIN_DELAY=10\n")
            f.write("MAX_DELAY=59\n")
        print(".env file created. Please update GEMINI_API_KEY before running.")
    else:
        print("Skipping environment setup (already exists).")

def main():
    """Main function to set up and run the application."""
    parser = argparse.ArgumentParser(description="Microsoft Rewards Agent Setup and Runner")
    parser.add_argument("--reinstall", action="store_true", help="Reinstall dependencies")
    args = parser.parse_args()

    print("Starting Microsoft Rewards Agent setup...")

    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    # Set up environment
    setup_environment()

    # Install dependencies
    install_dependencies(force=args.reinstall)

    # Run the GUI application
    try:
        subprocess.run([sys.executable, "gui.py"], check=True)
    except subprocess.CalledProcessError:
        print("Failed to start the GUI application.")
        print("Trying to run the command-line version instead...")
        subprocess.run([sys.executable, "ai_search_agent.py"])

if __name__ == "__main__":
    main()