import streamlit as st
import os
import re
import subprocess
import shutil
import sys
import time
from typing import Tuple, List

# --- Core Business Logic (Adapted from Insta.py) ---

def check_instaloader() -> bool:
    """Check if instaloader is installed."""
    try:
        # Running a simple command to check for presence and version
        subprocess.run(
            ['instaloader', '--version'],
            capture_output=True, text=True, check=True,
            # Use startupinfo for Windows to hide console window
            startupinfo=subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW) if sys.platform == "win32" else None
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def extract_shortcode(url: str) -> str:
    """Extract the shortcode from various Instagram post URL formats."""
    patterns = [
        r'instagram\.com\/p\/([a-zA-Z0-9_-]+)',
        r'instagram\.com\/reel\/([a-zA-Z0-9_-]+)',
        r'\/p\/([a-zA-Z0-9_-]+)',
        r'\/reel\/([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid Instagram post URL format.")

def download_content(shortcode: str) -> Tuple[bool, str]:
    """
    Download Instagram content using the instaloader command-line tool.
    
    Returns a tuple of (success, message_or_error).
    """
    try:
        command = [
            'instaloader',
            '--dirname-pattern={target}',
            '--filename-pattern={profile}_{date_utc:%Y-%m-%d}_{shortcode}',
            '--no-metadata-json',
            '--no-captions',
            '--no-profile-pic',
            '--no-compress-json',
            '--post-filter="not is_sponsored"', # Skip sponsored posts
            '--',
            f'-{shortcode}'
        ]

        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        # Use Popen to run the process in the background
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            startupinfo=subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW) if sys.platform == "win32" else None
        )

        # Simulate progress while the process is running
        for i in range(95):
            if process.poll() is not None:
                break # Process finished early
            status_placeholder.info(f"🚀 Downloading content for shortcode: `{shortcode}`...")
            progress_bar.progress(i + 1)
            time.sleep(0.1)

        # Wait for the process to complete and get output
        stdout, stderr = process.communicate()
        progress_bar.progress(100)
        
        if process.returncode == 0:
            status_placeholder.info("✅ Download process completed.")
            return True, "Download successful!"
        else:
            # Try to find a meaningful error message
            error_message = stderr.strip()
            if "Private" in error_message:
                return False, "This post is private or requires a login."
            if "404 Not Found" in error_message:
                 return False, "This post could not be found (404 Error)."
            return False, f"Download failed: {error_message}"

    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"

def move_and_collect_files(target_folder: str) -> List[str]:
    """
    Move downloaded files to the specified folder and return their new paths.
    """
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    current_dir = os.getcwd()
    moved_files_paths = []

    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        # Instaloader creates a directory named after the profile
        if os.path.isdir(item_path) and item != target_folder and not item.startswith('.'):
            try:
                for file in os.listdir(item_path):
                    source_path = os.path.join(item_path, file)
                    destination_path = os.path.join(target_folder, file)
                    
                    # Handle potential file conflicts by renaming
                    if os.path.exists(destination_path):
                        base, ext = os.path.splitext(file)
                        counter = 1
                        while os.path.exists(destination_path):
                            new_name = f"{base}_{counter}{ext}"
                            destination_path = os.path.join(target_folder, new_name)
                            counter += 1
                            
                    shutil.move(source_path, destination_path)
                    moved_files_paths.append(destination_path)
                # Clean up the empty directory
                shutil.rmtree(item_path)
            except OSError as e:
                st.warning(f"Could not process directory {item}: {e}")
    
    return moved_files_paths

# --- Streamlit User Interface ---

def main():
    # --- Page Configuration ---
    st.set_page_config(
        page_title="Insta Downloader",
        page_icon="🔥",
        layout="centered",
        initial_sidebar_state="auto"
    )

    # --- Header ---
    st.title("🔥 Insta Downloader")
    st.markdown("A clean and modern interface to download your favorite Instagram posts and reels.")

    # --- Dependency Check ---
    if not check_instaloader():
        st.error("❌ Instaloader is not installed or not found in your system's PATH.")
        st.info("Please install it by running the following command in your terminal:")
        st.code("pip install instaloader", language="bash")
        return

    st.write("") # Spacer

    # --- Download Form ---
    with st.form(key="download_form"):
        url = st.text_input(
            "Instagram Post URL",
            placeholder="https://www.instagram.com/p/C6vX4w1yA3e/",
            label_visibility="collapsed"
        )
        output_folder = st.text_input(
            "Output Folder Name", 
            value="insta_downloads",
            help="Downloaded files will be saved in this folder."
        )
        submit_button = st.form_submit_button(label="📥 Download Content", use_container_width=True)

    # --- Logic on Form Submission ---
    if submit_button:
        if not url:
            st.warning("Please enter an Instagram URL.")
        else:
            try:
                shortcode = extract_shortcode(url)
                
                with st.spinner("Preparing to download..."):
                    time.sleep(1) # Give a feeling of preparation
                
                # --- Download & Process ---
                success, message = download_content(shortcode)
                
                if success:
                    with st.spinner("Moving files and cleaning up..."):
                        moved_files = move_and_collect_files(output_folder)
                    
                    st.success(f"🎉 Success! {len(moved_files)} file(s) saved to `{output_folder}`.")
                    
                    # --- Display Downloaded Media ---
                    if moved_files:
                        st.markdown("---")
                        st.subheader("Downloaded Media:")
                        for file_path in moved_files:
                            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                                st.image(file_path, use_column_width=True)
                            elif file_path.lower().endswith('.mp4'):
                                st.video(file_path)
                else:
                    st.error(f"❌ Download Failed: {message}")

            except ValueError as e:
                st.error(f"Invalid URL: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()