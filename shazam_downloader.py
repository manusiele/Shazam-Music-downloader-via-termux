import json
import subprocess
import time
import os
import sys
import re
import shutil
import traceback

# Directory to save songs - with alternative options
PRIMARY_SAVE_FOLDER = "/storage/emulated/0/Music"
FALLBACK_SAVE_FOLDER = os.path.join(os.path.expanduser("~"), "storage/shared/Music")
INTERNAL_SAVE_FOLDER = os.path.join(os.path.expanduser("~"), "Music")

# Create a log file for debugging
LOG_FILE = os.path.join(os.path.expanduser("~"), "shazam_downloader.log")

def log_message(message):
    """Write message to log file and print to console"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    print(log_entry)
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Error writing to log: {e}")

# Determine the best save folder to use
def get_save_folder():
    """Determine the best folder to use for saving songs"""
    folders = [PRIMARY_SAVE_FOLDER, FALLBACK_SAVE_FOLDER, INTERNAL_SAVE_FOLDER]
    
    for folder in folders:
        try:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                log_message(f"Created directory: {folder}")
            
            # Test write permissions
            test_file = os.path.join(folder, ".test_write")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            
            log_message(f"Using save folder: {folder}")
            return folder
        except Exception as e:
            log_message(f"Cannot use folder {folder}: {e}")
    
    # If all else fails, use current directory
    log_message(f"All save folders failed, using current directory")
    return os.getcwd()

# Track detected songs to avoid duplicate notifications
detected_songs = set()

def display_progress_bar(progress):
    """
    Displays a custom formatted progress bar with complex characters in green and black.
    """
    bar_length = 50
    filled_length = int(bar_length * progress // 100)

    # ANSI escape codes for colors
    green = "\033[92m"  # Bright green
    black = "\033[30m"  # Black
    reset = "\033[0m"   # Reset to default color

    # Characters for the progress bar
    chars = ["█", "▓", "▒", "░"]

    # Create the filled part of the bar
    filled_bar = ''.join(chars[min(i // (bar_length // len(chars)), len(chars) - 1)] for i in range(filled_length))
    empty_bar = ''.join(chars[-1] for _ in range(bar_length - filled_length))

    # Combine the filled and empty parts
    bar = f"[{green}{filled_bar}{reset}{black}{empty_bar}{reset}]"

    # Display the progress percentage
    percent_display = f"{green}{progress:.1f}%{reset}"

    print(f"\rDOWNLOADING {bar} {percent_display}", end="", flush=True)

def check_termux_api():
    """Check if Termux API is installed"""
    try:
        # Try to directly use termux-notification with a simple command
        result = subprocess.run(["termux-notification", "--help"], 
                              capture_output=True, text=True)
        return True
    except FileNotFoundError:
        log_message("⚠️ Termux API not found. Please install it with: pkg install termux-api")
        return False
    except Exception as e:
        log_message(f"⚠️ Error checking Termux API: {e}")
        return False

def listen_for_shazam():
    """
    Continuously listens for new Shazam song detections.
    """
    log_message("\n🎧 Listening for Shazam song detection...\n")
    
    if not check_termux_api():
        log_message("❌ Cannot proceed without Termux API")
        return

    while True:
        try:
            output = subprocess.run(["termux-notification-list"], capture_output=True, text=True)
            
            if output.returncode != 0:
                log_message(f"Error running termux-notification-list: {output.stderr}")
                time.sleep(5)
                continue
                
            try:
                notifications = json.loads(output.stdout)
            except json.JSONDecodeError as e:
                log_message(f"❌ JSON Parsing Error: {e}")
                log_message(f"Raw output: {output.stdout[:100]}")  # Log first 100 chars to debug
                time.sleep(5)
                continue

            for notif in notifications:
                if notif.get("packageName") == "com.shazam.android":
                    title = notif.get("title", "").strip()
                    content = notif.get("content", "").strip()

                    if title and content:
                        song_name = f"{title} - {content}"

                        if song_name not in detected_songs:
                            detected_songs.add(song_name)  # Mark as detected
                            log_message(f"\n🎵 Detected Song: {song_name}")

                            # Remove previous notifications to keep it clean
                            try:
                                subprocess.run(["termux-notification-remove", "101"], check=False)
                                subprocess.run(["termux-notification-remove", "201"], check=False)
                                subprocess.run(["termux-notification-remove", "202"], check=False)
                            except Exception as e:
                                log_message(f"Error removing notifications: {e}")

                            # Notify user with a download option
                            try:
                                subprocess.run([
                                    "termux-notification",
                                    "--id", "200",
                                    "--title", "Song Detected ",
                                    "--content", f" '{song_name}'?",
                                    "--button1", "Download",
                                    "--button1-action", f"python {os.path.abspath(sys.argv[0])} --download \"{song_name}\"",
                                    "--priority", "high"
                                ])
                            except Exception as e:
                                log_message(f"Error creating notification: {e}")

            time.sleep(2)  # Short delay before checking again

        except Exception as e:
            log_message(f"❌ Error in listen_for_shazam: {e}")
            log_message(traceback.format_exc())
            time.sleep(5)

def check_yt_dlp():
    """Check if yt-dlp is installed and working"""
    try:
        version_output = subprocess.run(["yt-dlp", "--version"], 
                                       capture_output=True, text=True, check=True)
        log_message(f"Using yt-dlp version: {version_output.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_message(f"yt-dlp error: {e}")
        return False

def download_song(song_name):
    """
    Downloads a song using yt-dlp with real-time notifications and a custom progress bar.
    """
    log_message(f"\n📥 Downloading: {song_name}...")
    
    # Get the save folder - we do this every time in case storage permissions changed
    SAVE_FOLDER = get_save_folder()
    log_message(f"Save folder: {SAVE_FOLDER}")

    # Check for Termux API
    if not check_termux_api():
        log_message("❌ Cannot proceed without Termux API")
        return

    # Remove the song detection notification immediately
    try:
        subprocess.run(["termux-notification-remove", "200"], check=False)
    except Exception as e:
        log_message(f"Error removing notification: {e}")

    # Notify user about the download start
    try:
        subprocess.run([
            "termux-notification",
            "--id", "201",
            "--title", "INITIALIZING",
            "--content", f"://>  {song_name}",
            "--ongoing", "true",
            "--priority", "high"
        ])
    except Exception as e:
        log_message(f"Error creating notification: {e}")

    # Check if yt-dlp is installed
    if not check_yt_dlp():
        try:
            subprocess.run([
                "termux-notification",
                "--id", "202",
                "--title", "Download Error",
                "--content", "yt-dlp not installed or not working. Run 'pip install -U yt-dlp' first.",
                "--priority", "high"
            ])
        except Exception as e:
            log_message(f"Error creating notification: {e}")
        return

    search_query = f"ytsearch:{song_name}"

    # Create a temporary file to capture the download output
    output_file = os.path.join(os.path.expanduser("~"), "yt_dlp_output.txt")
    
    # Safer filename for output
    safe_filename = re.sub(r'[\\/*?:"<>|]', "_", song_name)
    output_path = os.path.join(SAVE_FOLDER, f"{safe_filename}.%(ext)s")
    
    log_message(f"Output path template: {output_path}")

    # Run yt-dlp with verbose output to help troubleshooting
    cmd = [
        "yt-dlp",
        "-v",                           # Verbose output
        "-x",                           # Extract audio
        "--audio-format", "mp3",        # Convert to MP3
        "--audio-quality", "0",         # Best quality
        "--newline",                    # Force newlines for progress parsing
        "--restrict-filenames",         # Restrict filenames to ASCII
        "--no-mtime",                   # Don't use modification time
        "--no-playlist",                # No playlists
        "--force-overwrites",           # Overwrite if necessary
        "-o", output_path,              # Output path
        search_query                    # Search query
    ]
    
    log_message(f"Running command: {' '.join(cmd)}")
    
    downloaded_file = None
    
    try:
        with open(output_file, "w", encoding="utf-8") as f_out:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered output
                encoding="utf-8"
            )

            # Track progress with less frequent notification updates
            last_update_time = 0
            last_progress = -1
            
            # Track if we're getting output
            last_output_time = time.time()
            
            while process.poll() is None:
                # Read output line by line with timeout protection
                line = ""
                try:
                    # Use a smaller timeout to keep checking if process is alive
                    line = process.stdout.readline()
                    if line:
                        last_output_time = time.time()
                        f_out.write(line)
                        f_out.flush()
                    else:
                        # No output, check if process is hanging
                        if time.time() - last_output_time > 30:  # 30 seconds with no output
                            log_message("No output for 30 seconds, process may be hanging")
                            break
                        time.sleep(0.1)  # Small sleep to prevent CPU thrashing
                        continue
                except Exception as e:
                    log_message(f"Error reading output: {e}")
                    time.sleep(0.5)
                    continue
                
                # Look for progress
                match = re.search(r"\[download\]\s+(\d+\.\d+)%", line)
                if match:
                    progress = float(match.group(1))
                    display_progress_bar(progress)
                    
                    # Only update notification every 5% change or every 2 seconds
                    current_time = time.time()
                    if (abs(progress - last_progress) >= 5 or 
                        current_time - last_update_time >= 2):
                        
                        last_progress = progress
                        last_update_time = current_time
                        
                        # Progress bar for notification
                        bar_length = 20
                        filled_length = int(bar_length * progress // 100)
                        bar = "█" * filled_length + "·" * (bar_length - filled_length)
                        indicator = "://>" if progress % 10 < 5 else ":\\>"
                        
                        try:
                            subprocess.run([
                                "termux-notification",
                                "--id", "201",
                                "--title", f"DOWNLOADING {progress:.1f}%",
                                "--content", f"{indicator} [{bar}]",
                                "--ongoing", "true",
                                "--priority", "high"
                            ])
                        except Exception as e:
                            log_message(f"Error updating notification: {e}")
                
                # Look for destination filename
                dest_match = re.search(r"\[download\] Destination: (.+)", line)
                if dest_match:
                    downloaded_file = dest_match.group(1)
                    log_message(f"Detected destination file: {downloaded_file}")
                
                # Also catch merger destination
                merger_match = re.search(r"\[Merger\].+: (.+)", line)
                if merger_match:
                    potential_file = merger_match.group(1)
                    if os.path.exists(potential_file):
                        downloaded_file = potential_file
                        log_message(f"Detected merged file: {downloaded_file}")
                        
                # Look for finished files (merging formats)
                finished_match = re.search(r"\[ffmpeg\] Merging formats into \"(.+)\"", line)
                if finished_match:
                    potential_file = finished_match.group(1)
                    if os.path.exists(potential_file):
                        downloaded_file = potential_file
                        log_message(f"Detected finished file: {downloaded_file}")
                        
                # Look for ExtractAudio destinations (important for MP3 conversion)
                extract_match = re.search(r"\[ExtractAudio\] Destination: (.+)", line)
                if extract_match:
                    potential_file = extract_match.group(1)
                    # Don't check if exists yet, as this is a destination file that might not exist yet
                    downloaded_file = potential_file
                    log_message(f"Detected audio extraction destination: {downloaded_file}")

        # Wait for process to finish with timeout
        try:
            return_code = process.wait(timeout=300)  # 5 minute timeout
            log_message(f"yt-dlp process returned with code {return_code}")
        except subprocess.TimeoutExpired:
            log_message("Process timed out after 5 minutes, killing it")
            process.kill()
            return_code = -1

    except Exception as e:
        log_message(f"Exception during download: {e}")
        log_message(traceback.format_exc())
        return_code = -1
        
    finally:
        # Make sure to remove the progress notification regardless of outcome
        try:
            subprocess.run(["termux-notification-remove", "201"], check=False)
        except Exception:
            pass

    # If we didn't find a downloaded file but the return code was successful,
    # try to locate file by pattern (more thorough search)
    if return_code == 0:
        log_message("Searching for downloaded file based on pattern...")
        try:
            found_file = False
            for file in os.listdir(SAVE_FOLDER):
                file_lower = file.lower()
                if safe_filename.lower() in file_lower:
                    if file_lower.endswith('.mp3'):
                        downloaded_file = os.path.join(SAVE_FOLDER, file)
                        log_message(f"Found MP3 file: {downloaded_file}")
                        found_file = True
                        break
            
            # If we still haven't found the file, check if a file was recently created in the folder
            if not found_file:
                log_message("Checking for recently created files...")
                now = time.time()
                most_recent_file = None
                most_recent_time = 0
                
                for file in os.listdir(SAVE_FOLDER):
                    if file.lower().endswith('.mp3'):
                        file_path = os.path.join(SAVE_FOLDER, file)
                        try:
                            file_time = os.path.getmtime(file_path)
                            if now - file_time < 60:  # File created in the last minute
                                if file_time > most_recent_time:
                                    most_recent_time = file_time
                                    most_recent_file = file_path
                        except Exception:
                            pass
                
                if most_recent_file:
                    downloaded_file = most_recent_file
                    log_message(f"Found recently created file: {downloaded_file}")
        except Exception as e:
            log_message(f"Error searching for file: {e}")

    # Check if file exists - add additional checks for MP3 conversion
    if downloaded_file:
        # Try with the original file path first
        if os.path.exists(downloaded_file):
            file_exists = True
        else:
            # If that doesn't exist, try with mp3 extension (common case)
            base_name = os.path.splitext(downloaded_file)[0]
            mp3_path = f"{base_name}.mp3"
            if os.path.exists(mp3_path):
                downloaded_file = mp3_path
                file_exists = True
                log_message(f"Found converted MP3 file: {downloaded_file}")
            else:
                file_exists = False
                
        if file_exists:
            file_size = os.path.getsize(downloaded_file)
            log_message(f"\n✅ Download Complete! File saved at: {downloaded_file}")
            log_message(f"File size: {file_size} bytes")
        
        # Ensure file exists and has content
        if file_size == 0:
            log_message("Warning: File has zero size!")
            
        # Ensure file extension is .mp3
        if not downloaded_file.lower().endswith('.mp3'):
            base_name = os.path.splitext(downloaded_file)[0]
            new_file = f"{base_name}.mp3"
            try:
                shutil.move(downloaded_file, new_file)
                downloaded_file = new_file
                log_message(f"Renamed to: {downloaded_file}")
            except Exception as e:
                log_message(f"Error renaming file: {e}")
        
        # Show completion notification
        try:
            subprocess.run([
                "termux-notification",
                "--id", "202",
                "--title", "Download Complete ✓",
                "--content", f"'{song_name}' saved to Music folder",
                "--button1", "Open",
                "--button1-action", f"termux-share {downloaded_file}",
                "--priority", "high"
            ])
        except Exception as e:
            log_message(f"Error creating completion notification: {e}")
        
        # Make media scanner aware of new file
        try:
            subprocess.run([
                "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                "-d", f"file://{downloaded_file}"
            ])
            log_message("Sent media scanner broadcast")
        except Exception as e:
            log_message(f"Media scanner error: {e}")
    else:
        log_message("\n❌ Download failed or file not found")
        
        # Check if temporary output file has error information
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                error_log = f.read()
                log_message(f"yt-dlp output excerpt: {error_log[-500:].strip()}")  # Last 500 chars
        except Exception as e:
            log_message(f"Error reading output file: {e}")
        
        try:
            subprocess.run([
                "termux-notification",
                "--id", "202",
                "--title", "Download Failed",
                "--content", f"Could not download '{song_name}'. Check logs.",
                "--button1", "View Log",
                "--button1-action", f"termux-share {LOG_FILE}",
                "--priority", "high"
            ])
        except Exception as e:
            log_message(f"Error creating failure notification: {e}")

def main():
    """Main function to handle command line arguments and startup"""
    # Get save folder only once at startup
    SAVE_FOLDER = get_save_folder()
    
    # Initialize log file
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== Shazam Downloader Log Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Python version: {sys.version}\n")
            f.write(f"Script path: {os.path.abspath(sys.argv[0])}\n")
            f.write(f"Save folder: {SAVE_FOLDER}\n")
            f.write(f"Command line: {' '.join(sys.argv)}\n\n")
    except Exception as e:
        print(f"Error initializing log: {e}")
    
    # Show startup notification
    try:
        subprocess.run([
            "termux-notification",
            "--id", "101",
            "--title", "Shazam Downloader Started",
            "--content", "Listening for Shazam detections...",
            "--ongoing", "true"
        ])
    except Exception as e:
        log_message(f"Error creating startup notification: {e}")
    
    # Handle command line arguments
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--download":
            if len(sys.argv) > 2:
                download_song(sys.argv[2])
            else:
                log_message("Error: No song name provided for download")
        else:
            listen_for_shazam()
    except Exception as e:
        log_message(f"Critical error: {e}")
        log_message(traceback.format_exc())

if __name__ == "__main__":
    main()
