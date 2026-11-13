"""Download the MediaPipe hand landmark model (about 8 MB) into models/."""
import urllib.request

from gestures import config


def main():
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if config.HAND_MODEL_PATH.exists():
        print(f"Already downloaded: {config.HAND_MODEL_PATH}")
        return
    print(f"Downloading {config.HAND_MODEL_URL}")
    urllib.request.urlretrieve(config.HAND_MODEL_URL, config.HAND_MODEL_PATH)
    print(f"Saved to {config.HAND_MODEL_PATH}")


if __name__ == "__main__":
    main()
