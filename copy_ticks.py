import os
import shutil
from pathlib import Path

def main():
    # Define paths
    current_dir = Path(__file__).resolve().parent
    files_dir = current_dir.parents[1] / "Files"
    gold_dir = current_dir / "gold"
    
    # Define file names
    csv_filename = "gold_market_ticks.csv"
    
    # Source and destination paths
    source_path = files_dir / csv_filename
    dest_path = gold_dir / csv_filename
    
    print(f"[INFO] Looking for {csv_filename} in {files_dir}...")
    
    # Check if source file exists
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}")
        print("Make sure you have run data.mq5 in MT5 first.")
        return
        
    # Ensure destination directory exists
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Copying to {dest_path}...")
    
    try:
        # Copy the file
        shutil.copy2(source_path, dest_path)
        print(f"✅ Successfully copied {csv_filename} to gold directory.")
        
        # Optionally print file size to confirm
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"📊 File size: {size_mb:.2f} MB")
        
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")

if __name__ == "__main__":
    main()
