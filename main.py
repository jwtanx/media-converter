"""Entry point for YouTube Downloader."""

from privacy import apply_privacy_environment

apply_privacy_environment()

from app import main

if __name__ == "__main__":
    main()
