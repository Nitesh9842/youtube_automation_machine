import os
import argparse
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def get_credentials():
    """Get or refresh YouTube API credentials"""
    creds = None
    token_path = 'token.json'
    
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, 
            ["https://www.googleapis.com/auth/youtube.upload"])
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                # Delete invalid token and re-authenticate
                if os.path.exists(token_path):
                    os.remove(token_path)
                return None
        else:
            return None
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def authenticate_youtube():
    """Authenticate with YouTube API - creates new credentials if needed"""
    try:
        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        client_secrets_file = "client_secret.json"
        
        if not os.path.exists(client_secrets_file):
            raise Exception("client_secret.json file not found. Please download it from Google Cloud Console.")
        
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        
        # Use run_local_server for web-based auth
        credentials = flow.run_local_server(
            port=8080,
            prompt='consent',
            authorization_prompt_message='Please visit this URL to authorize the application: {url}',
            success_message='The auth flow is complete; you may close this window.',
            open_browser=True
        )
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
        
        return credentials
        
    except Exception as e:
        raise Exception(f"Authentication failed: {str(e)}")

def check_authentication():
    """Check if valid YouTube authentication exists"""
    try:
        creds = get_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False

def get_youtube_service():
    """Get authenticated YouTube service"""
    creds = get_credentials()
    if not creds:
        raise Exception("Not authenticated. Please run authentication first.")
    
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def upload_to_youtube(video_path, title, description, tags, privacy_status="unlisted", category_id="22"):
    """Upload video to YouTube with proper error handling"""
    try:
        # Verify file exists and is accessible
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        # Get file size for validation
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise Exception("Video file is empty")
        
        print(f"Uploading video: {os.path.basename(video_path)} ({file_size / 1024 / 1024:.2f} MB)")
        print(f"Privacy status: {privacy_status}")
        
        # Get YouTube service
        youtube = get_youtube_service()

        # Prepare video metadata
        video_metadata = {
            "snippet": {
                "title": title[:100],  # YouTube title limit
                "description": description[:5000],  # YouTube description limit
                "tags": tags[:500] if isinstance(tags, list) else [],  # YouTube tags limit
                "categoryId": str(category_id)
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        # Create media upload object
        media = MediaFileUpload(
            video_path, 
            chunksize=1024*1024,  # 1MB chunks
            resumable=True,
            mimetype="video/*"
        )

        # Create upload request
        request = youtube.videos().insert(
            part="snippet,status",
            body=video_metadata,
            media_body=media
        )

        # Execute upload with retry logic
        response = None
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"Upload attempt {retry_count + 1}/{max_retries}")
                response = request.execute()
                break
            except Exception as upload_error:
                retry_count += 1
                if retry_count >= max_retries:
                    raise upload_error
                print(f"Upload failed, retrying... Error: {str(upload_error)}")
        
        if not response or 'id' not in response:
            raise Exception("Upload completed but no video ID returned")
            
        video_id = response["id"]
        print(f"✅ Upload successful! Video ID: {video_id}")
        print(f"🔗 Video URL: https://www.youtube.com/watch?v={video_id}")
        
        return video_id
        
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        raise Exception(f"Failed to upload video: {str(e)}")

def get_channel_info():
    """Get information about the authenticated YouTube channel"""
    try:
        youtube = get_youtube_service()
        
        # Call the channels.list method to get the channel info
        request = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
            
        channel = response['items'][0]
        
        # Extract relevant information
        channel_info = {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'description': channel['snippet'].get('description', ''),
            'thumbnail': channel['snippet']['thumbnails'].get('default', {}).get('url', ''),
            'subscriberCount': channel['statistics'].get('subscriberCount', '0'),
            'videoCount': channel['statistics'].get('videoCount', '0'),
            'viewCount': channel['statistics'].get('viewCount', '0')
        }
        
        return channel_info
    except Exception as e:
        print(f"Error getting channel info: {e}")
        return None

def logout_youtube():
    """Revoke credentials and log out from YouTube"""
    token_path = 'token.json'
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path)
            
            # Revoke the token
            import google.oauth2.credentials
            import google.auth.transport.requests
            import requests
            
            transport = google.auth.transport.requests.Request()
            
            # Try to revoke the token
            try:
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': creds.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
            except Exception as e:
                print(f"Error revoking token: {e}")
            
            # Remove the token file
            os.remove(token_path)
            return True
    except Exception as e:
        print(f"Error during logout: {e}")
    
    return False

def main():
    parser = argparse.ArgumentParser(description='Upload a video to YouTube')
    parser.add_argument('--video-path', required=True, help='Path to the video file')
    parser.add_argument('--title', required=True, help='Title of the video')
    parser.add_argument('--description', default='', help='Description of the video')
    parser.add_argument('--tags', nargs='*', default=[], help='Tags for the video')
    parser.add_argument('--privacy', default='unlisted', choices=['private', 'unlisted', 'public'], 
                      help='Privacy setting (default: unlisted)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found at {args.video_path}")
        return
    
    try:
        video_id = upload_to_youtube(
            video_path=args.video_path,
            title=args.title,
            description=args.description,
            tags=args.tags,
            privacy_status=args.privacy
        )
        print(f"Video uploaded successfully! Video ID: {video_id}")
    except Exception as e:
        print(f"Error uploading video: {str(e)}")

if __name__ == "__main__":
    main()