# Shazam Music Downloader via Termux

A Python script that integrates with Shazam on Android to automatically detect songs and download them using yt-dlp, optimized for Termux environment.

## Features

- **Automatic Song Detection**: Monitors Shazam notifications to extract song and artist information
- **Network-Aware Downloading**: Adjusts download speed based on Wi-Fi or mobile data connection
- **Progress Notifications**: Real-time download progress via Termux notifications
- **Interactive Controls**: Notification buttons for playing downloaded songs or opening the download folder
- **Safe File Handling**: Sanitizes filenames to prevent path issues
- **Termux Integration**: Fully compatible with Termux API for notifications and system interactions

## Prerequisites

- **Termux** installed on Android device
- **Termux:API** app installed and configured
- **Python 3** installed in Termux
- **yt-dlp** for downloading audio
- **aria2c** for accelerated downloads
- **Shazam** app installed on the device

## Installation

1. **Install Termux and Termux:API**:
   - Download Termux from F-Droid or Google Play Store
   - Download Termux:API from the same source

2. **Update Termux packages**:
   ```bash
   pkg update && pkg upgrade
   ```

3. **Install required packages**:
   ```bash
   pkg install python git ffmpeg aria2
   ```

4. **Install yt-dlp**:
   ```bash
   pip install yt-dlp
   ```

5. **Grant storage permissions**:
   ```bash
   termux-setup-storage
   ```

6. **Clone or download this repository**:
   ```bash
   git clone https://github.com/yourusername/Shazam-Music-downloader-via-termux.git
   cd Shazam-Music-downloader-via-termux
   ```

## Usage

1. **Run the script**:
   ```bash
   python shazam_downloader.py
   ```

2. **Use Shazam to identify a song** on your device

3. **The script will detect the Shazam notification** and prompt you to download the song

4. **Choose to download** via the notification button or terminal input

5. **Monitor progress** through Termux notifications

6. **Access downloaded songs** in `/storage/emulated/0/Download/` folder

## How It Works

1. The script continuously monitors notifications from the Shazam app
2. When a song is detected, it extracts the song title and artist
3. Checks the current network type (Wi-Fi/Mobile) to optimize download settings
4. Searches YouTube for the official audio using yt-dlp
5. Downloads the audio as MP3 to the device's Download folder
6. Provides interactive notifications with progress updates and action buttons

## Network Optimization

- **Wi-Fi**: Uses 16 connections with 1MB chunks for faster downloads
- **Mobile Data**: Uses 4 connections with 500KB chunks to be data-conscious

## Notifications

The script uses Termux notifications to:
- Show download progress with a visual progress bar
- Display completion status with action buttons
- Allow playing the downloaded song directly
- Open the download folder

## Troubleshooting

- **No notifications detected**: Ensure Termux:API has notification access permissions
- **Download fails**: Check internet connection and yt-dlp installation
- **Storage access denied**: Run `termux-setup-storage` and grant permissions
- **Shazam notifications not appearing**: Make sure Shazam app notifications are enabled

## Dependencies

- `yt-dlp`: For YouTube audio extraction and downloading
- `aria2c`: For accelerated multi-threaded downloads
- `termux-api`: For notification and system integration
- `python3`: Runtime environment

## License

This project is open-source. Feel free to modify and distribute.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Disclaimer

This tool is for personal use only. Ensure you comply with YouTube's Terms of Service and local copyright laws when downloading content.