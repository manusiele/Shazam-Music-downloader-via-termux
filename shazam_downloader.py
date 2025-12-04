import os
import re
import subprocess
import json

def sanitize_filename(name):
    """Removes special characters to prevent file path issues."""
    return re.sub(r'[<>:"/\\|?*]', '', name)

def get_network_type():
    """Checks if the device is on Wi-Fi or Mobile Data."""
    try:
        result = subprocess.run(['termux-wifi-connectioninfo'], capture_output=True, text=True)
        return "wifi" if "ip" in result.stdout else "mobile"
    except:
        return "unknown"

def show_notification(title, content, progress=0, ongoing=True, buttons=None):
    """Displays Termux notification with optional buttons."""
    progress_bar = f"[{'█' * (progress // 10)}{'-' * (10 - (progress // 10))}] {progress}%"
    command = f'''termux-notification --id 101 \
        --title "{title}" \
        --content "{progress_bar} - {content}" \
        --priority high --ongoing {('--button1 "Cancel" --button1-action "killall yt-dlp"' if ongoing else '')} \
        --color "#00FF00" --bg-color "#000000"'''
    
    if buttons:
        for i, (label, action) in enumerate(buttons.items(), start=1):
            command += f' --button{i} "{label}" --button{i}-action "{action}"'
    
    os.system(command)

def fetch_shazam_notification():
    """Fetches the latest notification from Shazam and extracts song info."""
    try:
        result = subprocess.run(['termux-notification-list'], capture_output=True, text=True)
        notifications = json.loads(result.stdout)

        for notification in notifications:
            if "Shazam" in notification.get("app_name", ""):
                content = notification.get("content", "")
                match = re.search(r'(.+) - (.+)', content)
                if match:
                    return {"song": match.group(1).strip(), "artist": match.group(2).strip()}
    except:
        pass
    return None

def download_song(song, artist, network_type):
    """Downloads a song from YouTube to Internal Storage Download folder."""
    search_query = f"{song} {artist} official audio"
    print(f"Searching YouTube for: {search_query}")

    storage_path = "/storage/emulated/0/Download/"
    os.makedirs(storage_path, exist_ok=True)

    safe_song = sanitize_filename(song)
    file_path = os.path.join(storage_path, f"{safe_song}.mp3")

    # Select download speed based on network type
    aria_args = "-x 16 -s 16 -k 1M" if network_type == "wifi" else "-x 4 -s 4 -k 500K"

    # Start notification
    show_notification("Downloading...", song, progress=0)

    # Use yt-dlp with aria2c for fast downloading
    process = subprocess.Popen(
        ['yt-dlp', f'ytsearch1:{search_query}', '--extract-audio', '--audio-format', 'mp3',
         '--external-downloader', 'aria2c', '--external-downloader-args', aria_args,
         '-o', file_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    for line in process.stdout:
        if "ETA" in line:
            match = re.search(r'(\d+)%', line)
            if match:
                progress = int(match.group(1))
                show_notification("Downloading...", song, progress=progress)

    process.wait()

    # Show "Download Complete" notification
    show_notification("Download Complete ✅", f"Saved to {storage_path}", progress=100, ongoing=False,
                      buttons={"▶ Play": f"am start -a android.intent.action.VIEW -d file://{file_path}",
                               "📂 Open Folder": "am start -a android.intent.action.VIEW -d file:///storage/emulated/0/Download"})

def handle_shazam_detection():
    """Monitors Shazam notifications and prompts the user to download."""
    detected_song = fetch_shazam_notification()
    if not detected_song:
        return

    song, artist = detected_song["song"], detected_song["artist"]
    network_type = get_network_type()

    os.system(f'''termux-notification --id 200 \
        --title "Song Detected 🎵" \
        --content "{song} - {artist}" \
        --button1 "Download" --button1-action "python download_song.py '{song}' '{artist}'" \
        --button2 "Ignore" --button2-action "exit" \
        --color "#00FF00" --bg-color "#000000"''')

    user_choice = input(f"Download '{song}' by {artist}? (yes/no): ").strip().lower()
    
    if user_choice == "yes":
        download_song(song, artist, network_type)

# Run live detection
handle_shazam_detection()
