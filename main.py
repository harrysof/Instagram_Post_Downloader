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
        subprocess.run(
            ['instaloader', '--version'],
            capture_output=True, text=True, check=True,
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
            '--post-filter=not is_sponsored',
            '--',
            f'-{shortcode}'
        ]

        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            startupinfo=subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW) if sys.platform == "win32" else None
        )

        # Simulate progress while the process is running
        for i in range(95):
            if process.poll() is not None:
                break
            status_placeholder.info(f"🚀 Downloading content for shortcode: `{shortcode}`...")
            progress_bar.progress(i + 1)
            time.sleep(0.1)

        stdout, stderr = process.communicate()
        progress_bar.progress(100)
        
        if process.returncode == 0:
            status_placeholder.success("✅ Download process completed.")
            return True, "Download successful!"
        else:
            error_message = stderr.strip()
            if "Private" in error_message or "Login required" in error_message:
                return False, "This post is private or requires a login."
            if "404" in error_message or "not found" in error_message.lower():
                return False, "This post could not be found (404 Error)."
            if "Rate limit" in error_message:
                return False, "Instagram rate limit reached. Please try again later."
            return False, f"Download failed: {error_message if error_message else 'Unknown error'}"

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
        initial_sidebar_state="collapsed"
    )

    # --- Custom CSS for better styling ---
    st.markdown("""
        <style>
        .main {
            padding-top: 2rem;
        }
        .stButton>button {
            background: linear-gradient(90deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%);
            color: white;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 2rem;
            transition: transform 0.2s;
        }
        .stButton>button:hover {
            transform: scale(1.02);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Header ---
    st.title("🔥 Insta Downloader")
    st.markdown("A clean and modern interface to download your favorite Instagram posts and reels.")
    st.markdown("---")

    # --- Dependency Check ---
    if not check_instaloader():
        st.error("❌ **Instaloader is not installed or not found in your system's PATH.**")
        st.info("📦 Please install it by running the following command in your terminal:")
        st.code("pip install instaloader", language="bash")
        
        with st.expander("ℹ️ Installation Instructions"):
            st.markdown("""
            **Windows:**
            1. Open Command Prompt or PowerShell
            2. Run: `pip install instaloader`
            
            **macOS/Linux:**
            1. Open Terminal
            2. Run: `pip3 install instaloader`
            
            **After installation:**
            - Refresh this page
            - Make sure instaloader is in your system PATH
            """)
        return

    st.success("✅ Instaloader is installed and ready!")
    st.write("")

    # --- Download Form ---
    with st.form(key="download_form", clear_on_submit=False):
        url = st.text_input(
            "📱 Instagram Post URL",
            placeholder="https://www.instagram.com/p/C6vX4w1yA3e/ or https://www.instagram.com/reel/...",
            help="Paste the full URL of the Instagram post or reel you want to download"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            output_folder = st.text_input(
                "📁 Output Folder Name", 
                value="insta_downloads",
                help="Downloaded files will be saved in this folder."
            )
        with col2:
            st.write("")
            st.write("")
        
        submit_button = st.form_submit_button(
            label="📥 Download Content", 
            use_container_width=True,
            type="primary"
        )

    # --- Logic on Form Submission ---
    if submit_button:
        if not url:
            st.warning("⚠️ Please enter an Instagram URL.")
        else:
            try:
                shortcode = extract_shortcode(url)
                st.info(f"🔍 Detected shortcode: `{shortcode}`")
                
                # --- Download & Process ---
                success, message = download_content(shortcode)
                
                if success:
                    with st.spinner("📦 Moving files and cleaning up..."):
                        moved_files = move_and_collect_files(output_folder)
                    
                    st.success(f"🎉 **Success!** {len(moved_files)} file(s) saved to `{output_folder}`")
                    
                    # --- Display Downloaded Media ---
                    if moved_files:
                        st.markdown("---")
                        st.subheader("📸 Downloaded Media:")
                        
                        for file_path in moved_files:
                            file_name = os.path.basename(file_path)
                            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                            
                            with st.container():
                                st.caption(f"**{file_name}** ({file_size:.2f} MB)")
                                
                                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                                    st.image(file_path, use_column_width=True)
                                elif file_path.lower().endswith(('.mp4', '.mov')):
                                    st.video(file_path)
                                else:
                                    st.info(f"File downloaded: {file_name}")
                                
                                st.write("")
                    
                    # Show download path
                    abs_path = os.path.abspath(output_folder)
                    st.info(f"📂 Files saved to: `{abs_path}`")
                else:
                    st.error(f"❌ **Download Failed:** {message}")
                    
                    with st.expander("💡 Troubleshooting Tips"):
                        st.markdown("""
                        **Common issues:**
                        - **Private account**: You may need to log in to Instaloader
                        - **Rate limiting**: Wait a few minutes and try again
                        - **Invalid URL**: Make sure you copied the full post URL
                        - **Post deleted**: The content may no longer be available
                        
                        **To login to Instaloader:**
                        ```bash
                        instaloader --login YOUR_USERNAME
                        ```
                        """)

            except ValueError as e:
                st.error(f"❌ **Invalid URL:** {e}")
                st.info("Please make sure you're using a valid Instagram post or reel URL.")
            except Exception as e:
                st.error(f"❌ **An unexpected error occurred:** {e}")
    
    # --- Footer ---
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 1rem;'>
            <small>Made with ❤️ using Streamlit • Please respect content creators' rights</small>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
