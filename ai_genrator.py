import google.generativeai as genai
import os
import json
from typing import Dict, List, Optional
import cv2
from datetime import datetime
from dotenv import load_dotenv
import base64
import tempfile
from PIL import Image
import numpy as np

# Load environment variables from .env file
load_dotenv()

class AIMetadataGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI Metadata Generator with Gemini 2.0 Flash"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY in .env file or pass it as parameter.")
        
        genai.configure(api_key=self.api_key) # type: ignore
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp') # type: ignore
    
    def extract_video_frames(self, video_path: str, num_frames: int = 3) -> List[str]:
        """Extract representative frames from video for AI analysis"""
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frames = []
            
            # Extract frames at regular intervals
            for i in range(num_frames):
                frame_number = int((i + 1) * frame_count / (num_frames + 1))
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Convert to PIL Image
                    pil_image = Image.fromarray(frame_rgb)
                    # Resize for efficient processing
                    pil_image = pil_image.resize((512, 512), Image.Resampling.LANCZOS)
                    frames.append(pil_image)
            
            cap.release()
            return frames
            
        except Exception as e:
            print(f"Error extracting frames: {e}")
            return []
    
    def analyze_video_content(self, video_path: str) -> str:
        """Analyze video content using AI vision to understand what's in the video frames"""
        try:
            # Extract video frames
            frames = self.extract_video_frames(video_path, 3)  # Increased to 3 frames for better coverage
            if not frames:
                return "Unable to analyze video content"
            
            # Analyze frames for text and visual content
            combined_analysis = []
            
            for i, frame in enumerate(frames):
                prompt = f"""
                Analyze this video frame {i+1} and describe what you see in detail. Focus on:
                1. Any visible text in the frame
                2. Main subject/person and their actions
                3. Setting/location 
                4. Key objects or activities visible
                5. Overall mood and style
                
                Extract any text that appears in the image if present.
                Provide detailed analysis of what's shown in the frame.
                """
                
                response = self.model.generate_content([prompt, frame])
                combined_analysis.append(response.text.strip())
            
            # Combine analyses from all frames
            final_prompt = f"""
            Based on the following analyses of different frames from a video, provide a comprehensive understanding of what the video is about:
            
            FRAME ANALYSES:
            {' '.join(combined_analysis)}
            
            Create a concise summary that captures the essence of this video, focusing especially on any text that appears in the frames.
            """
            
            final_response = self.model.generate_content(final_prompt)
            return final_response.text.strip()
            
        except Exception as e:
            print(f"Error analyzing video content: {e}")
            return "Video content analysis unavailable"
    
    def generate_title(self, video_analysis: str) -> str:
        """Generate engaging YouTube shorts title with hashtags based on text and visual content"""
        prompt = f"""
        Based on this video analysis, create a catchy YouTube Shorts title:
        
        VIDEO CONTENT: {video_analysis}
        
        Requirements:
        - Make it extremely engaging, click-worthy and optimized for high CTR
        - Keep it under 60 characters including hashtags
        - Include 2-3 relevant hashtags directly in the title
        - Focus on the most intriguing aspect of the video, especially any text that appears in the video
        - Use trending language patterns popular in viral shorts
        - Consider using emojis strategically
        - Make it provocative but not clickbait
        
        The title should follow formats that are proven to work for viral shorts.
        Return only the title with hashtags, nothing else.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip().replace('"', '').replace("'", "")
        except Exception as e:
            print(f"Error generating title: {e}")
            return "🔥 Viral Moment You Won't Believe! #shorts #viral #trending"
    
    def generate_description(self, video_analysis: str) -> str:
        """Generate YouTube shorts description optimized for virality based on text and visual content"""
        prompt = f"""
        Create a YouTube Shorts description based on this video analysis:
        
        VIDEO CONTENT: {video_analysis}
        
        Structure the description exactly like this:
        
        1. Write exactly 3-5 lines of engaging, high-emotion description that creates curiosity
        2. Add a line break then write "Keywords:" followed by exactly 20 trending keywords separated by commas
        3. Add a line break then write "Hashtags:" followed by exactly 15 viral hashtags (MUST include #shorts, #viral, #trending and other relevant ones)
        4. Add a line break then add this call-to-action: "👉 Follow for more content like this! 🔔 Turn on notifications!"
        5. Add this copyright disclaimer: "⚠️ Copyright Disclaimer: All rights to respective owners."
        
        Make the description extremely engaging and optimized for Shorts algorithm with high-emotion language patterns.
        Focus on keywords and hashtags that are currently trending for short-form viral content.
        If there was any text in the video, incorporate it into the description.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating description: {e}")
            return self._fallback_description()
    
    def generate_tags_and_keywords(self, video_analysis: str) -> Dict:
        """Generate optimized tags and keywords specifically for viral shorts"""
        prompt = f"""
        Based on this video analysis, generate optimized tags and keywords for a viral YouTube Short:
        
        VIDEO CONTENT: {video_analysis}
        
        Provide your response as JSON with these exact fields:
        1. "tags": List of 30 tags optimized for YouTube search algorithm (keep each under 30 characters)
        2. "keywords": List of 40 relevant keywords (single words or short phrases) related to the content
        3. "trending_keywords": List of 15 currently trending keywords related to the content
        
        Tags should include general category terms, specific content descriptors, and trending terms.
        Format the response as valid JSON only - no explanation or other text.
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            print(f"Error generating tags and keywords: {e}")
            return {
                "tags": ["shorts", "viral", "trending"],
                "keywords": ["viral video", "trending content", "shorts"],
                "trending_keywords": ["viral shorts", "trending now"]
            }
    
    def _fallback_description(self) -> str:
        """Fallback description when AI generation fails"""
        return """Amazing video content that will keep you entertained!
Watch this incredible moment captured on video.
Perfect for sharing with friends and family.
Don't forget to like and subscribe for more content.
This video showcases some really cool stuff.
You won't believe what happens in this video.
Make sure to watch until the end.
Comment below what you think about this.
Share this video if you enjoyed it.
Thanks for watching our content!

Keywords: viral video, trending content, amazing moments, entertainment, social media, short video, funny clips, must watch, incredible, awesome, cool stuff, viral clips, trending now, popular video, engaging content, shareable, entertaining, video content, social sharing, watch now

Hashtags: #shorts #viral #trending #amazing #entertainment #video #content #socialmedia #funny #cool #awesome #mustwatch #incredible #popular #engaging #shareable #entertaining #videooftheday #trend #viral2024 #shortsvideo #viralshorts #trendingshorts #amazingvideo #viralcontent #shortsfeed #explore #fyp #foryou #viralmoment

⚠️ Copyright Disclaimer: This content is used for educational and entertainment purposes. All rights belong to their respective owners. If you are the owner and want this removed, please contact us."""
    
    def generate_complete_metadata(self, video_path: str, **kwargs) -> Dict:
        """Generate complete metadata package based on video frame analysis"""
        
        print("🤖 Analyzing video frames with AI...")
        video_analysis = self.analyze_video_content(video_path)
        print(f"📹 Video analysis complete")
        
        print("🎯 Generating viral shorts title with hashtags...")
        title = self.generate_title(video_analysis)
        
        print("📝 Generating description optimized for shorts...")
        description = self.generate_description(video_analysis)
        
        print("🏷️ Generating optimized tags and keywords...")
        tags_keywords = self.generate_tags_and_keywords(video_analysis)
        
        # Extract hashtags from description
        description_lines = description.split('\n')
        hashtags = []
        keywords = []
        
        for line in description_lines:
            if line.startswith('Hashtags:'):
                hashtags_text = line.replace('Hashtags:', '').strip()
                hashtags = [tag.strip() for tag in hashtags_text.split() if tag.startswith('#')]
            elif line.startswith('Keywords:'):
                keywords_text = line.replace('Keywords:', '').strip()
                keywords = [kw.strip() for kw in keywords_text.split(',')]
        
        metadata = {
            "video_analysis": video_analysis,
            "title": title,
            "description": description,
            "tags": tags_keywords.get("tags", []),
            "hashtags": hashtags,
            "keywords": tags_keywords.get("keywords", []),
            "trending_keywords": tags_keywords.get("trending_keywords", []),
            "generated_at": datetime.now().isoformat()
        }
        
        return metadata
    
    def save_metadata(self, metadata: Dict, output_path: str):
        """Save metadata to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"Metadata saved to: {output_path}")
        except Exception as e:
            print(f"Error saving metadata: {e}")

# Example usage
if __name__ == "__main__":
    # Initialize the generator (API key will be loaded from .env)
    generator = AIMetadataGenerator()
    
    # Example video processing
    video_path = r"c:\Users\DELL\OneDrive\Desktop\youtube automation ai\sample_video.mp4"
    
    # Generate complete metadata
    metadata = generator.generate_complete_metadata(video_path=video_path)
    
    # Print results
    print("Generated Metadata:")
    print("-" * 50)
    print(f"Title: {metadata['title']}")
    print(f"\nDescription:\n{metadata['description']}")
    
    # Save to file
    output_file = r"c:\Users\DELL\OneDrive\Desktop\youtube automation ai\metadata_output.json"
    generator.save_metadata(metadata, output_file)