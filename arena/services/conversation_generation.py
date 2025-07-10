import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, LENGTH_OPTIONS, STYLE_OPTIONS

logger = logging.getLogger(__name__)

class ConversationGenerator:
    """Service for generating conversational content using LLM."""
    
    def __init__(self):
        self.client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def generate_conversation(
        self, 
        theme: str, 
        keywords: Optional[List[str]] = None, 
        length: str = "medium",
        style: str = "podcast"
    ) -> List[Dict[str, Any]]:
        """
        Generate a conversational script based on theme and keywords.
        
        Args:
            theme: Main topic or theme for the conversation
            keywords: Optional list of keywords to include
            length: Conversation length - "short", "medium", or "long"
            style: Conversation style - "podcast", "interview", "debate", "casual"
            
        Returns:
            List of conversation lines in format: [{"text": "...", "speaker_id": 0/1}, ...]
            
        Raises:
            Exception: If LLM service is not available or API call fails
        """
        if not self.is_available():
            raise Exception("LLM service not available. Please configure OPENAI_API_KEY.")
        
        # Build the prompt based on parameters
        prompt = self._build_prompt(theme, keywords, length, style)
        
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.8,  # Slightly creative but controlled
                max_tokens=2000,  # Sufficient for most conversations
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            if not content:
                raise Exception("Empty response from LLM")
            parsed_response = json.loads(content)
            
            # Validate and format the response
            script = self._validate_and_format_script(parsed_response)
            
            logger.info(f"Generated conversation with {len(script)} lines for theme: {theme}")
            return script
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise Exception("Failed to generate valid conversation script")
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise Exception(f"Failed to generate conversation: {str(e)}")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are an expert content creator specializing in generating engaging conversational content for text-to-speech systems.

Your task is to create natural, flowing conversations between two speakers based on user-provided themes and keywords. The conversations should:

1. Be engaging and natural-sounding when spoken aloud
2. Have clear speaker alternations with balanced participation
3. Include appropriate pauses and conversational flow
4. Be suitable for podcast-style or interview-style audio generation
5. Stay on topic while maintaining natural dialogue patterns

IMPORTANT: You must respond with valid JSON in this exact format:
{
  "conversation": [
    {"text": "Speaker text here", "speaker_id": 0},
    {"text": "Other speaker response", "speaker_id": 1},
    {"text": "Continuation...", "speaker_id": 0}
  ]
}

Guidelines:
- Use speaker_id 0 and 1 only
- Alternate speakers naturally (don't switch every line unless it makes sense)
- Keep individual lines between 10-50 words for natural speech
- Avoid overly complex sentences or technical jargon unless specifically requested
- Include natural conversational elements like acknowledgments, questions, and transitions"""

    def _build_prompt(
        self, 
        theme: str, 
        keywords: Optional[List[str]], 
        length: str, 
        style: str
    ) -> str:
        """Build the user prompt based on input parameters."""
        
        # Length specifications
        length_specs = {
            "short": "4-6 exchanges (8-12 total lines)",
            "medium": "6-10 exchanges (12-20 total lines)", 
            "long": "10-15 exchanges (20-30 total lines)"
        }
        
        # Style specifications
        style_specs = {
            "podcast": "informal, engaging podcast-style discussion",
            "interview": "structured interview with questions and detailed answers",
            "debate": "respectful debate with opposing viewpoints",
            "casual": "casual conversation between friends",
            "educational": "educational discussion explaining concepts",
            "news": "news-style discussion or analysis"
        }
        
        prompt = f"""Create a {style_specs.get(style, 'conversational')} about: {theme}

Length: {length_specs.get(length, length_specs['medium'])}
Style: {style}"""
        
        if keywords:
            prompt += f"\n\nPlease incorporate these keywords naturally: {', '.join(keywords)}"
        
        prompt += """\n\nRequirements:
- Generate engaging, natural dialogue suitable for text-to-speech
- Use speaker_id 0 for the first speaker, speaker_id 1 for the second
- Keep responses balanced between speakers
- Ensure each line flows well when spoken aloud
- Respond in valid JSON format only"""
        
        return prompt
    
    def _validate_and_format_script(self, parsed_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate and format the LLM response into proper script format."""
        
        if "conversation" not in parsed_response:
            raise Exception("Invalid response format: missing 'conversation' key")
        
        conversation = parsed_response["conversation"]
        
        if not isinstance(conversation, list) or len(conversation) < 2:
            raise Exception("Invalid conversation format: must be a list with at least 2 entries")
        
        validated_script = []
        
        for i, line in enumerate(conversation):
            if not isinstance(line, dict):
                raise Exception(f"Invalid line format at index {i}: must be a dictionary")
            
            if "text" not in line or "speaker_id" not in line:
                raise Exception(f"Invalid line format at index {i}: missing 'text' or 'speaker_id'")
            
            text = line["text"].strip()
            speaker_id = line["speaker_id"]
            
            if not text:
                continue  # Skip empty lines
            
            if speaker_id not in [0, 1]:
                raise Exception(f"Invalid speaker_id at index {i}: must be 0 or 1")
            
            validated_script.append({
                "text": text,
                "speaker_id": speaker_id
            })
        
        if len(validated_script) < 2:
            raise Exception("Conversation too short: must have at least 2 valid lines")
        
        return validated_script


# Global instance
_content_generator = None

def get_content_generator() -> ConversationGenerator:
    """Get the global content generator instance."""
    global _content_generator
    if _content_generator is None:
        _content_generator = ConversationGenerator()
    return _content_generator
