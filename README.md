# YouTube Automation Machine with AI Content Generation

An intelligent system that downloads Instagram Reels and automatically uploads them to YouTube with AI-generated titles, descriptions, hashtags, and keywords using Google's Gemini AI.

## 🌟 Features

- **Instagram Reel Downloading**: Download reels with original audio
- **AI Content Generation**: Automatically generate engaging titles, descriptions, and tags using Gemini AI
- **YouTube Auto Upload**: Seamless upload to YouTube with proper metadata
- **Real-time Progress Tracking**: Watch the process unfold step by step
- **Web Interface**: Clean, modern UI for easy operation

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Gemini AI API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

### 3. Set up YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Download the `client_secret.json` file
6. Place it in the project root directory

### 4. Configure Environment

Create a `.env` file:
```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 5. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## 🚀 Usage

1. **Authenticate**: Click "Login to YouTube" to connect your account
2. **Preview**: Enter Instagram URL and click "Preview Metadata" to see AI-generated content
3. **Download Only**: Just download the reel without uploading
4. **Auto Upload**: Full automation - download, generate metadata, and upload to YouTube

## 🤖 AI Features

The Gemini AI analyzes video frames and generates:

- **Engaging Titles**: 3 optimized title options (max 60 chars)
- **SEO Descriptions**: 200-300 word compelling descriptions
- **Smart Tags**: 15-20 relevant YouTube tags
- **Keywords**: SEO-optimized keywords for discoverability

## 📁 Project Structure

```
youtube automation ai/
├── app.py                  # Main Flask application
├── downloader.py          # Instagram reel downloader
├── uploader.py            # YouTube uploader
├── ai_genrator.py         # AI content generation
├── client_secret.json     # YouTube API credentials
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── static/
│   ├── css/
│   │   └── style.css      # Styling
│   └── js/
│       └── app.js         # Frontend JavaScript
├── templates/
│   └── index.html         # Main web interface
└── downloads/             # Downloaded videos (auto-created)
```

## ⚠️ Important Notes

- **Legal Compliance**: Only download content you have permission to use
- **Content Policy**: Ensure content follows YouTube's community guidelines
- **Rate Limits**: Be mindful of API rate limits
- **Privacy**: Videos are uploaded as private by default

## 🔧 Configuration Options

Edit `app.py` to customize:
- Download folder location
- Video privacy settings
- Number of frames for AI analysis
- Task cleanup intervals

## 📊 Monitoring

The application provides real-time updates:
- Download progress
- AI processing status
- Upload progress
- Error handling

## 🎯 Tips for Best Results

1. **Quality URLs**: Use direct Instagram reel URLs
2. **Good Content**: AI works best with clear, engaging content
3. **Regular Auth**: Re-authenticate YouTube if upload fails
4. **Monitor Quotas**: Keep track of YouTube API usage

## 🐛 Troubleshooting

**Common Issues:**
- **Authentication Failed**: Re-download `client_secret.json`
- **AI Generation Failed**: Check Gemini API key and quotas
- **Download Failed**: Verify Instagram URL format
- **Upload Failed**: Check YouTube API quotas and authentication

## 🔄 Updates & Maintenance

- Regularly update dependencies
- Monitor API key quotas
- Clean up old downloaded files
- Backup authentication tokens
