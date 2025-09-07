import instaloader
import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def extract_shortcode(reel_url: str) -> str:
    """Extract shortcode from Instagram URL"""
    path = urlparse(reel_url).path.strip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"reel", "p"}:
        return parts[1]
    return parts[-1] if parts else ""

def download_reel_with_audio(reel_url: str, sessionid: str, download_dir: str = "downloads") -> str:
    """Download Instagram Reel with audio"""
    try:
        L = instaloader.Instaloader()

        # 🔑 Use sessionid from environment
        L.context._session.cookies.set("sessionid", sessionid, domain=".instagram.com")

        shortcode = extract_shortcode(reel_url)
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        video_url = post.video_url
        if not video_url and post.typename == "GraphSidecar":
            for node in post.get_sidecar_nodes():
                if node.is_video:
                    video_url = node.video_url
                    break

        if not video_url:
            raise Exception("No video URL found for this post")

        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, f"reel_{shortcode}.mp4")

        print("⬇️ Downloading video with audio...")
        r = requests.get(video_url, stream=True)
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filepath

    except Exception as e:
        raise Exception(f"Failed to download reel: {str(e)}")

def main():
    print("Instagram Reel Downloader with Audio")
    print("="*40)

    try:
        reel_url = input("Enter Instagram reel URL: ").strip()
        if not reel_url:
            print("No URL provided")
            return

        # Get sessionid from environment variable (now loaded from .env)
        sessionid = os.getenv("IG_SESSIONID")
        if not sessionid:
            raise Exception("No IG_SESSIONID found! Please set in .env file.")

        video_path = download_reel_with_audio(reel_url, sessionid)

        print(f"\n✅ Successfully downloaded with audio!")
        print(f"📁 File location: {video_path}")
        print(f"📊 File size: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTips:")
        print("- Make sure IG_SESSIONID is set in the .env file")
        print("- If expired, grab a new sessionid from Chrome cookies")

if __name__ == "__main__":
    main()
