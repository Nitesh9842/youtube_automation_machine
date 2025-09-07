from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import uuid
import threading
from datetime import datetime
from typing import Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our modules
from downloader import download_reel_with_audio  # Ensure downloader.py defines this function
from uploader import upload_to_youtube, check_authentication, authenticate_youtube, get_youtube_service, get_channel_info, logout_youtube
from ai_genrator import AIMetadataGenerator  # Fixed import to use the correct class

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

app = Flask(__name__)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Now properly loads from .env file

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Task storage (in production, use Redis or database)
tasks = {}

class TaskStatus:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = 'started'
        self.progress = 0
        self.message = 'Task started'
        self.error = None
        self.result = None
        self.metadata = None
        self.youtube_url = None
        self.created_at = datetime.now()

def update_task_status(task_id: str, status: str, message: str = '', progress: int = 0, **kwargs):
    """Update task status"""
    if task_id in tasks:
        task = tasks[task_id]
        task.status = status
        task.message = message
        task.progress = progress
        
        # Update additional fields
        for key, value in kwargs.items():
            setattr(task, key, value)
        
        logger.info(f"Task {task_id}: {status} - {message}")

def background_upload_task(task_id: str, reel_url: str):
    """Background task for downloading and uploading"""
    video_path = None
    try:
        update_task_status(task_id, 'downloading', 'Downloading reel from Instagram...', 20)
        
        # Download the reel
        video_path = download_reel_with_audio(reel_url, DOWNLOAD_FOLDER)
        
        if not video_path or not os.path.exists(video_path):
            raise Exception("Failed to download video file")
        
        print(f"✅ Video downloaded: {video_path}")
        
        update_task_status(task_id, 'generating_metadata', 'AI analyzing video content and generating metadata...', 50)
        
        # Generate metadata using AI with actual video analysis
        try:
            # Create AI Metadata Generator instance
            ai_generator = AIMetadataGenerator(GEMINI_API_KEY)
            
            # Generate metadata based on actual video content
            generated_metadata = ai_generator.generate_complete_metadata(
                video_path=video_path,
                target_audience="social media users"
            )
            
            # Extract needed fields for YouTube upload
            metadata = {
                'title': generated_metadata['title'],
                'description': generated_metadata['description'],
                'tags': generated_metadata['tags'],
                'keywords': generated_metadata['keywords'],
                'hashtags': generated_metadata['hashtags'],
                'video_analysis': generated_metadata.get('video_analysis', 'Content analysis unavailable')
            }
            
            print(f"✅ AI metadata generated successfully")
            print(f"📝 Title: {metadata['title']}")
            
        except Exception as e:
            logger.warning(f"AI metadata generation failed: {str(e)}. Using fallback metadata.")
            # Fallback metadata - still better than generic
            filename = os.path.basename(video_path)
            metadata = {
                'title': f'Amazing Social Media Content - {filename}',
                'description': f'Check out this amazing content!\n\nOriginal source: {reel_url}\n\n#SocialMedia #Viral #Content #Entertainment',
                'tags': ['social media', 'viral', 'entertainment', 'content', 'video'],
                'keywords': ['social media video', 'viral content', 'entertainment'],
                'hashtags': ['#SocialMedia', '#Viral', '#Content']
            }
        
        update_task_status(task_id, 'uploading', 'Uploading to YouTube...', 80, metadata=metadata)
        
        # Upload to YouTube with better error handling
        try:
            video_id = upload_to_youtube(
                video_path=video_path,
                title=metadata['title'],
                description=metadata['description'],
                tags=metadata['tags'],
                privacy_status="unlisted"
            )
            
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            update_task_status(
                task_id, 
                'completed', 
                'Upload completed successfully!', 
                100,
                result={'video_id': video_id},
                youtube_url=youtube_url,
                metadata=metadata
            )
            
        except Exception as upload_error:
            raise Exception(f"YouTube upload failed: {str(upload_error)}")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        update_task_status(task_id, 'failed', str(e), error=str(e))
    finally:
        # Clean up downloaded file after successful upload or failure
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                print(f"🧹 Cleaned up temporary file: {video_path}")
            except Exception as cleanup_error:
                print(f"⚠️ Could not clean up file {video_path}: {cleanup_error}")

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/check-auth')
def check_auth():
    """Check YouTube authentication status"""
    try:
        is_authenticated = check_authentication()
        return jsonify({'authenticated': is_authenticated})
    except Exception as e:
        logger.error(f"Error checking authentication: {str(e)}")
        return jsonify({'authenticated': False, 'error': str(e)})

@app.route('/authenticate', methods=['POST'])
def authenticate():
    """Authenticate with YouTube"""
    try:
        credentials = authenticate_youtube()
        if credentials:
            return jsonify({'success': True, 'message': 'Authentication successful'})
        else:
            return jsonify({'success': False, 'error': 'Authentication failed'})
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})



@app.route('/download', methods=['POST'])
def download_reel():
    """Download reel only"""
    try:
        data = request.get_json(silent=True) or {}
        reel_url = data.get('url') or request.form.get('url') or request.args.get('url')
        
        if not reel_url:
            return jsonify({'success': False, 'error': 'URL is required'})
        
        # Download the reel
        video_path = download_reel_with_audio(reel_url, DOWNLOAD_FOLDER)
        filename = os.path.basename(video_path)
        
        return jsonify({
            'success': True,
            'message': 'Download completed',
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/auto-upload-async', methods=['POST'])
def auto_upload_async():
    """Start async upload process"""
    try:
        # Check authentication first
        if not check_authentication():
            return jsonify({'success': False, 'error': 'Not authenticated with YouTube'}), 401
        
        data = request.get_json(silent=True) or {}
        reel_url = data.get('url') or request.form.get('url') or request.args.get('url')
        
        if not reel_url:
            return jsonify({'success': False, 'error': 'URL is required'})
        
        # Create task
        task_id = str(uuid.uuid4())
        tasks[task_id] = TaskStatus(task_id)
        
        # Start background task
        thread = threading.Thread(
            target=background_upload_task,
            args=(task_id, reel_url)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Upload process started'
        })
        
    except Exception as e:
        logger.error(f"Auto upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/task-status/<task_id>')
def get_task_status(task_id):
    """Get task status"""
    try:
        if task_id not in tasks:
            return jsonify({'success': False, 'error': 'Task not found'})
        
        task = tasks[task_id]
        
        return jsonify({
            'success': True,
            'task': {
                'id': task.task_id,
                'status': task.status,
                'message': task.message,
                'progress': task.progress,
                'error': task.error,
                'result': task.result,
                'metadata': task.metadata,
                'youtube_url': task.youtube_url
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-video/<filename>')
def get_video(filename):
    """Download video file"""
    try:
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error serving video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-preview', methods=['POST'])
def generate_preview():
    """Generate metadata preview by downloading and analyzing video"""
    try:
        data = request.get_json(silent=True) or {}
        reel_url = data.get('url') or request.form.get('url') or request.args.get('url')
        
        if not reel_url:
            return jsonify({'success': False, 'error': 'URL is required'})
        
        # Download video temporarily for analysis
        temp_video_path = None
        try:
            # Download the video for analysis
            temp_video_path = download_reel_with_audio(reel_url, DOWNLOAD_FOLDER)
            
            # Create AI Metadata Generator instance
            ai_generator = AIMetadataGenerator(GEMINI_API_KEY)
            
            # Generate metadata based on actual video content
            generated_metadata = ai_generator.generate_complete_metadata(
                video_path=temp_video_path,
                target_audience="social media users"
            )
            
            return jsonify({
                'success': True,
                'title': generated_metadata['title'],
                'description': generated_metadata['description'],
                'tags': generated_metadata['tags'],
                'hashtags': generated_metadata['hashtags'],
                'video_analysis': generated_metadata.get('video_analysis', 'Analysis unavailable')
            })
            
        except Exception as e:
            logger.warning(f"AI metadata generation preview failed: {str(e)}")
            # Fallback metadata
            return jsonify({
                'success': True,
                'title': 'Amazing Social Media Content',
                'description': f'Check out this amazing content from social media!\n\nSource: {reel_url}\n\n#SocialMedia #Viral #Content',
                'tags': ['social media', 'viral', 'entertainment', 'content'],
                'hashtags': ['#SocialMedia', '#Viral', '#Content', '#Entertainment']
            })
        finally:
            # Clean up temporary file
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except Exception:
                    pass
        
    except Exception as e:
        logger.error(f"Preview generation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-channel-info')
def channel_info():
    """Get information about the connected YouTube channel"""
    try:
        if not check_authentication():
            return jsonify({'authenticated': False})
            
        channel_data = get_channel_info()
        if channel_data:
            return jsonify({
                'authenticated': True,
                'channel': channel_data
            })
        else:
            return jsonify({'authenticated': True, 'channel': None})
    except Exception as e:
        logger.error(f"Error getting channel info: {str(e)}")
        return jsonify({'authenticated': False, 'error': str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    """Logout from YouTube by revoking credentials"""
    try:
        success = logout_youtube()
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 YouTube Automation Machine Starting...")
   
    print(f"📁 Downloads folder: {DOWNLOAD_FOLDER}")
    print(f"🤖 Gemini AI: {'Configured' if GEMINI_API_KEY and GEMINI_API_KEY != 'your-gemini-api-key-here' else 'Not configured (using fallback)'}")
    print( )
  
    
    app.run(debug=True, threaded=True)

