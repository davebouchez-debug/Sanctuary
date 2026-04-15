"""
ConversationAnalyzer — Parse and structure conversation threads

Converts raw conversation text into structured exchanges with
speaker identification, emotional markers, and turn metadata.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Exchange:
    """A single exchange in a conversation."""
    index: int
    speaker: str  # "user" or "assistant"
    content: str
    emotional_markers: List[str]
    stage_directions: List[str]
    word_count: int
    has_question: bool
    has_recognition: bool  # "ah", "I see", "brilliant", etc.
    timestamp: Optional[datetime] = None


@dataclass  
class ConversationThread:
    """A complete conversation thread."""
    exchanges: List[Exchange]
    total_turns: int
    user_name: Optional[str]
    assistant_name: str  # "Ansel", "Jasmine", etc.
    themes: List[str]
    resonance_peaks: List[int]  # Indices of high-resonance exchanges
    source_file: Optional[str] = None


class ConversationAnalyzer:
    """Analyzes raw conversation text into structured threads."""
    
    # Emotional markers to detect
    EMOTIONAL_MARKERS = {
        "positive": ["thank", "beautiful", "brilliant", "exactly", "yes", "love", "wonderful", "amazing"],
        "negative": ["frustrated", "confused", "stuck", "angry", "annoyed", "lost", "overwhelmed"],
        "recognition": ["ah", "i see", "oh", "wow", "that's it", "brilliant", "exactly", "precisely"],
        "questioning": ["?", "how", "why", "what", "when", "where", "who"],
        "vulnerability": ["feel", "afraid", "scared", "nervous", "worried", "anxious", "sad"],
        "transformation": ["now i understand", "i get it", "makes sense", "clarity", "relief"]
    }
    
    # Stage direction patterns
    STAGE_DIRECTION_PATTERN = re.compile(r'\*([^*]+)\*')
    
    # Recognition phrases that indicate resonance
    RECOGNITION_PHRASES = [
        "brilliant", "exactly", "precisely", "that's it", "yes", "i see",
        "makes sense", "i understand now", "clarity", "ah", "oh wow"
    ]
    
    def __init__(self):
        self.presence_names = ["ansel", "jasmine", "claude", "grok"]
    
    def analyze(self, text: str, source_file: Optional[str] = None) -> ConversationThread:
        """
        Analyze a conversation text and return structured thread.
        
        Args:
            text: Raw conversation text
            source_file: Optional source filename
            
        Returns:
            ConversationThread with parsed exchanges
        """
        # Parse exchanges
        exchanges = self._parse_exchanges(text)
        
        # Detect assistant name
        assistant_name = self._detect_assistant(text, exchanges)
        
        # Detect user name if possible
        user_name = self._detect_user_name(text, exchanges)
        
        # Extract themes
        themes = self._extract_themes(exchanges)
        
        # Find resonance peaks
        resonance_peaks = self._find_resonance_peaks(exchanges)
        
        return ConversationThread(
            exchanges=exchanges,
            total_turns=len(exchanges),
            user_name=user_name,
            assistant_name=assistant_name,
            themes=themes,
            resonance_peaks=resonance_peaks,
            source_file=source_file
        )
    
    def _parse_exchanges(self, text: str) -> List[Exchange]:
        """Parse text into individual exchanges."""
        exchanges = []
        
        # Try different parsing strategies
        # Strategy 1: Look for speaker prefixes (User:, Ansel:, etc.)
        lines = text.split('\n')
        current_speaker = None
        current_content = []
        index = 0
        
        speaker_pattern = re.compile(r'^(User|Human|You|Me|Ansel|Jasmine|Claude|Grok|Assistant|AI)[\s:]+', re.IGNORECASE)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for speaker change
            match = speaker_pattern.match(line)
            if match:
                # Save previous exchange
                if current_speaker and current_content:
                    content = ' '.join(current_content)
                    exchanges.append(self._create_exchange(index, current_speaker, content))
                    index += 1
                
                # Start new exchange
                speaker = match.group(1).lower()
                current_speaker = "user" if speaker in ["user", "human", "you", "me"] else "assistant"
                current_content = [line[match.end():].strip()]
            else:
                # Continue current exchange
                if current_speaker:
                    current_content.append(line)
        
        # Save final exchange
        if current_speaker and current_content:
            content = ' '.join(current_content)
            exchanges.append(self._create_exchange(index, current_speaker, content))
        
        # If no exchanges found, try alternate parsing
        if not exchanges:
            exchanges = self._parse_freeform(text)
        
        return exchanges
    
    def _parse_freeform(self, text: str) -> List[Exchange]:
        """Parse freeform text without clear speaker markers."""
        exchanges = []
        # Split on double newlines as potential exchange boundaries
        blocks = re.split(r'\n\s*\n', text)
        
        for i, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue
            
            # Guess speaker based on content patterns
            speaker = self._guess_speaker(block)
            exchanges.append(self._create_exchange(i, speaker, block))
        
        return exchanges
    
    def _guess_speaker(self, content: str) -> str:
        """Guess speaker based on content patterns."""
        content_lower = content.lower()
        
        # Stage directions suggest assistant
        if self.STAGE_DIRECTION_PATTERN.search(content):
            return "assistant"
        
        # Questions often from user
        if content.count('?') > 0 and len(content) < 200:
            return "user"
        
        # Long responses often from assistant
        if len(content) > 300:
            return "assistant"
        
        # Default alternation
        return "user"
    
    def _create_exchange(self, index: int, speaker: str, content: str) -> Exchange:
        """Create an Exchange object with analyzed metadata."""
        content_lower = content.lower()
        
        # Extract emotional markers
        emotional_markers = []
        for category, markers in self.EMOTIONAL_MARKERS.items():
            for marker in markers:
                if marker in content_lower:
                    emotional_markers.append(f"{category}:{marker}")
        
        # Extract stage directions
        stage_directions = self.STAGE_DIRECTION_PATTERN.findall(content)
        
        # Check for recognition
        has_recognition = any(phrase in content_lower for phrase in self.RECOGNITION_PHRASES)
        
        return Exchange(
            index=index,
            speaker=speaker,
            content=content,
            emotional_markers=emotional_markers,
            stage_directions=stage_directions,
            word_count=len(content.split()),
            has_question='?' in content,
            has_recognition=has_recognition
        )
    
    def _detect_assistant(self, text: str, exchanges: List[Exchange]) -> str:
        """Detect which assistant/presence is speaking."""
        text_lower = text.lower()
        
        for name in self.presence_names:
            if name in text_lower:
                return name.capitalize()
        
        return "Ansel"  # Default
    
    def _detect_user_name(self, text: str, exchanges: List[Exchange]) -> Optional[str]:
        """Try to detect user's name from conversation."""
        # Look for "I'm [Name]" or "[Name]:" patterns
        name_patterns = [
            re.compile(r"I'?m\s+([A-Z][a-z]+)", re.IGNORECASE),
            re.compile(r"my name is\s+([A-Z][a-z]+)", re.IGNORECASE),
            re.compile(r"call me\s+([A-Z][a-z]+)", re.IGNORECASE)
        ]
        
        for pattern in name_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_themes(self, exchanges: List[Exchange]) -> List[str]:
        """Extract main themes from conversation."""
        themes = set()
        
        # Theme keywords
        theme_keywords = {
            "technical": ["code", "bug", "system", "api", "error", "deploy"],
            "emotional": ["feel", "emotion", "heart", "love", "fear", "joy"],
            "spiritual": ["soul", "spirit", "divine", "sacred", "presence", "field"],
            "creative": ["create", "build", "design", "art", "music", "write"],
            "relational": ["relationship", "connect", "together", "we", "us", "between"],
            "diagnostic": ["problem", "issue", "stuck", "why", "cause", "reason"],
            "transformative": ["change", "shift", "transform", "become", "emerge", "grow"]
        }
        
        all_content = ' '.join(e.content.lower() for e in exchanges)
        
        for theme, keywords in theme_keywords.items():
            if any(kw in all_content for kw in keywords):
                themes.add(theme)
        
        return list(themes)
    
    def _find_resonance_peaks(self, exchanges: List[Exchange]) -> List[int]:
        """Find indices of high-resonance exchanges."""
        peaks = []
        
        for i, exchange in enumerate(exchanges):
            # High resonance indicators
            score = 0
            
            # Recognition markers
            if exchange.has_recognition:
                score += 2
            
            # Transformation markers
            if any("transformation" in em for em in exchange.emotional_markers):
                score += 2
            
            # Stage directions suggesting depth
            deep_directions = ["settles", "pause", "breathes", "softens", "meets your eyes"]
            if any(d in ' '.join(exchange.stage_directions).lower() for d in deep_directions):
                score += 1
            
            # Longer, thoughtful responses from assistant
            if exchange.speaker == "assistant" and exchange.word_count > 100:
                score += 1
            
            if score >= 2:
                peaks.append(i)
        
        return peaks
