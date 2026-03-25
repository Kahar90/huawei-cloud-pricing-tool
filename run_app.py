#!/usr/bin/env python3
"""
Entry point for Huawei Cloud Pricing Tool.
Works both in development mode and as a PyInstaller bundled executable.
"""

import sys
import os
import time
import subprocess
import threading
import webbrowser
from pathlib import Path


def get_bundle_dir() -> str:
    """
    Get the base directory for the application.
    
    In PyInstaller bundle: sys._MEIPASS
    In development: directory containing this script
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        return sys._MEIPASS
    else:
        # Running in development mode
        return os.path.dirname(os.path.abspath(__file__))


def setup_environment():
    """
    Set up environment variables and paths for the application.
    Handles both development and PyInstaller bundled modes.
    """
    bundle_dir = get_bundle_dir()
    
    # Set environment variable so the app knows where to find data
    os.environ['STREAMLIT_APP_ROOT'] = bundle_dir
    
    # Add the app directory to Python path for imports
    app_dir = os.path.join(bundle_dir, 'app')
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    
    # In bundled mode, data files are at the root of the bundle
    # The mapping_engine.py uses os.path.dirname(__file__) which will resolve correctly
    # because the app folder structure is preserved with --add-data
    
    return bundle_dir


def open_browser(url: str, delay: float = 2.0):
    """
    Open the browser after a delay to allow the server to start.
    
    Args:
        url: The URL to open
        delay: Seconds to wait before opening browser
    """
    def _open_browser():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[WARNING] Could not open browser: {e}")
            print(f"[INFO] Please manually navigate to: {url}")
    
    thread = threading.Thread(target=_open_browser, daemon=True)
    thread.start()


def check_streamlit_installed() -> bool:
    """Check if streamlit is installed."""
    try:
        import streamlit
        return True
    except ImportError:
        return False


def run_streamlit_app(app_path: str, port: int = 8501, headless: bool = False):
    """
    Run the Streamlit application using streamlit.web.cli.
    
    Args:
        app_path: Path to the Streamlit app file
        port: Port to run the server on
        headless: Whether to run without opening browser (we handle browser separately)
    """
    try:
        from streamlit.web.cli import main as streamlit_main
    except ImportError:
        print("[ERROR] Streamlit is not installed.")
        print("[INFO] Please install requirements: pip install -r requirements.txt")
        sys.exit(1)
    
    # Construct the arguments for streamlit
    # We use --server.headless=true and open browser ourselves for better control
    args = [
        'streamlit',
        'run',
        app_path,
        '--server.port', str(port),
        '--server.address', 'localhost',
        '--server.headless', 'true',  # We handle browser opening
        '--browser.gatherUsageStats', 'false',
        '--global.developmentMode', 'false',
    ]
    
    # Override sys.argv for streamlit
    sys.argv = args
    
    # Print startup message
    url = f"http://localhost:{port}"
    print("=" * 60)
    print("  Huawei Cloud Pricing Tool")
    print("=" * 60)
    print(f"\n  Starting application...")
    print(f"  Local URL: {url}")
    print(f"\n  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    # Open browser if not headless
    if not headless:
        open_browser(url, delay=3.0)
    
    try:
        # Run streamlit
        streamlit_main()
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Received keyboard interrupt.")
        print("[SHUTDOWN] Stopping server...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Failed to start application: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    # Set up environment and paths
    bundle_dir = setup_environment()
    
    # Determine the path to the main app file
    app_path = os.path.join(bundle_dir, 'app', 'huawei_pricing_app.py')
    
    # Verify the app file exists
    if not os.path.exists(app_path):
        print(f"[ERROR] Application file not found: {app_path}")
        print(f"[INFO] Bundle directory: {bundle_dir}")
        print(f"[INFO] Current working directory: {os.getcwd()}")
        
        # Try to find the app file in alternative locations
        alt_paths = [
            os.path.join(os.getcwd(), 'app', 'huawei_pricing_app.py'),
            os.path.join(os.path.dirname(__file__), 'app', 'huawei_pricing_app.py'),
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                print(f"[INFO] Found app at alternative location: {alt_path}")
                app_path = alt_path
                break
        else:
            print("[ERROR] Could not find the application file.")
            sys.exit(1)
    
    # Check if streamlit is available
    if not check_streamlit_installed():
        print("[ERROR] Streamlit is not installed.")
        print("[INFO] Please run: pip install streamlit pandas openpyxl")
        sys.exit(1)
    
    # Run the Streamlit application
    try:
        run_streamlit_app(
            app_path=app_path,
            port=8501,
            headless=False
        )
    except Exception as e:
        print(f"[FATAL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
