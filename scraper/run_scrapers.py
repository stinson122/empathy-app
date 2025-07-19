#!/usr/bin/env python3
"""
Script to run all scrapers in the correct order:
1. scraper_megathread.py
2. scraper_posts.py
3. scraper_combiner.py
"""

import os
import sys
import subprocess
from pathlib import Path

def run_script(script_name):
    """Run a Python script and return True if successful."""
    print(f"\n{'='*50}")
    print(f"Running {script_name}...")
    print(f"{'='*50}")
    
    try:
        # Run the script and capture output in real-time
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        
        # Print the output in real-time
        if result.stdout:
            print(result.stdout)
            
        print(f"\n{script_name} completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\nError running {script_name}:")
        print(e.output)
        return False
    except Exception as e:
        print(f"\nUnexpected error running {script_name}:")
        print(str(e))
        return False

def main():
    print("Starting scraper pipeline...")
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the scripts to run in order
    scripts = [
        'scraper_megathread.py',
        'scraper_posts.py',
        'scraper_combiner.py'
    ]
    
    # Run each script in order
    for script in scripts:
        script_path = os.path.join(script_dir, script)
        if not os.path.exists(script_path):
            print(f"Error: {script} not found at {script_path}")
            sys.exit(1)
            
        success = run_script(script_path)
        if not success:
            print(f"\nError: {script} failed. Stopping pipeline.")
            sys.exit(1)
    
    print("\nAll scrapers completed successfully!")

if __name__ == "__main__":
    main()
