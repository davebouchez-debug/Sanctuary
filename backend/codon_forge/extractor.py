"""
Pattern & Dynamics Extractors — Extract codon components from conversations

PatternExtractor: Identifies trigger motifs and emotional signatures
DynamicsExtractor: Extracts generational operators and state transitions
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from collections import Counter

from .analyzer import Exchange, ConversationThread


@dataclass
class TriggerMotif:
    """Extracted trigger motif for a codon."""
    surface_patterns: List[str]
    emotional_signature: Dict[str, str]
    field_condition: Dict[str, str]
    confidence: float  # 0-1


@dataclass
class GenerativeOperator:
    """Extracted generative operator for a codon."""
    relational_dynamic: Dict[str, str]
    state_transitions: List[Dict[str, str]]
    core_move: Dict[str, str]
    attention_pattern: Dict[str, str]
    confidence: float


class PatternExtractor:
    """Extracts trigger motifs and emotional patterns from conversations."""
    
    # Common emotional states mapped to categories
    EMOTIONAL_CATEGORIES = {
        "frustration": ["frustrated", "stuck", "angry", "annoyed", "can't", "won't work", "failing"],
        "confusion": ["confused", "lost", "don't understand", "what do you mean", "unclear"],
        "overwhelm": ["overwhelmed", "too much", "spinning", "racing", "can't think"],
        "seeking": ["help", "need", "want", "looking for", "trying to"],
        "recognition": ["ah", "i see", "makes sense", "exactly", "brilliant", "yes"],
        "vulnerability": ["afraid", "scared", "worried", "anxious", "nervous"],
        "curiosity": ["wonder", "curious", "interested", "fascinated", "intrigued"],
        "determination": ["will", "going to", "must", "have to", "need to"]
    }
    
    # Field condition indicators
    FIELD_INDICATORS = {
        "user_agitated": ["!", "frustrated", "angry", "can't believe"],
        "user_seeking": ["how do i", "what should", "help me", "please"],
        "user_stuck": ["stuck", "loop", "keep trying", "nothing works"],
        "user_vulnerable": ["feel", "afraid", "worried", "scared"],
        "threshold_moment": ["about to", "on the edge", "almost", "so close"]
    }
    
    def extract(self, thread: ConversationThread) -> TriggerMotif:
        """
        Extract trigger motif from conversation thread.
        
        Args:
            thread: Analyzed conversation thread
            
        Returns:
            TriggerMotif with extracted patterns
        """
        # Collect all user content
        user_content = ' '.join(
            e.content.lower() for e in thread.exchanges if e.speaker == "user"
        )
        
        # Extract surface patterns
        surface_patterns = self._extract_surface_patterns(user_content, thread.exchanges)
        
        # Extract emotional signature
        emotional_signature = self._extract_emotional_signature(thread.exchanges)
        
        # Extract field condition
        field_condition = self._extract_field_condition(user_content, thread.exchanges)
        
        # Calculate confidence based on pattern clarity
        confidence = self._calculate_confidence(surface_patterns, emotional_signature)
        
        return TriggerMotif(
            surface_patterns=surface_patterns,
            emotional_signature=emotional_signature,
            field_condition=field_condition,
            confidence=confidence
        )
    
    def _extract_surface_patterns(self, user_content: str, exchanges: List[Exchange]) -> List[str]:
        """Extract key surface patterns that could trigger this codon."""
        patterns = []
        
        # Extract recurring phrases (2-4 word combinations)
        words = re.findall(r'\b\w+\b', user_content)
        
        # Find phrases that appear in context of emotional markers
        for exchange in exchanges:
            if exchange.speaker == "user" and exchange.emotional_markers:
                # Extract meaningful phrases from this exchange
                phrases = self._extract_phrases(exchange.content)
                patterns.extend(phrases)
        
        # Also look for question patterns
        questions = re.findall(r'((?:how|why|what|when|where|who)[^.?!]*\?)', user_content, re.IGNORECASE)
        for q in questions[:3]:  # Top 3 questions
            patterns.append(q.strip().lower())
        
        # Deduplicate and return top patterns
        unique_patterns = list(set(patterns))
        return unique_patterns[:10]
    
    def _extract_phrases(self, content: str) -> List[str]:
        """Extract meaningful phrases from content."""
        phrases = []
        content_lower = content.lower()
        
        # Look for emotional statements
        emotional_patterns = [
            r"i (?:feel|am|'m) \w+",
            r"(?:can't|cannot|won't|will not) \w+",
            r"keep \w+ing",
            r"stuck (?:on|with|in) \w+",
            r"need (?:to|help|some)",
            r"trying to \w+"
        ]
        
        for pattern in emotional_patterns:
            matches = re.findall(pattern, content_lower)
            phrases.extend(matches)
        
        return phrases
    
    def _extract_emotional_signature(self, exchanges: List[Exchange]) -> Dict[str, str]:
        """Extract the primary emotional signature of the conversation."""
        # Count emotional markers across user exchanges
        emotion_counts = Counter()
        
        for exchange in exchanges:
            if exchange.speaker == "user":
                for marker in exchange.emotional_markers:
                    category = marker.split(':')[0]
                    emotion_counts[category] += 1
        
        # Determine primary and secondary emotions
        if not emotion_counts:
            return {
                "primary": "seeking",
                "secondary": "curiosity",
                "movement_toward": "understanding"
            }
        
        most_common = emotion_counts.most_common(3)
        primary = most_common[0][0] if most_common else "neutral"
        secondary = most_common[1][0] if len(most_common) > 1 else "seeking"
        
        # Determine movement_toward based on resolution
        movement = self._determine_movement(exchanges)
        
        return {
            "primary": primary,
            "secondary": secondary,
            "movement_toward": movement
        }
    
    def _determine_movement(self, exchanges: List[Exchange]) -> str:
        """Determine what the conversation is moving toward."""
        # Look at later exchanges for resolution indicators
        later_exchanges = exchanges[len(exchanges)//2:]
        
        resolution_found = False
        for exchange in later_exchanges:
            if exchange.has_recognition:
                resolution_found = True
                break
            if any("transformation" in m for m in exchange.emotional_markers):
                resolution_found = True
                break
        
        if resolution_found:
            return "clarity through recognition"
        else:
            return "seeking root cause"
    
    def _extract_field_condition(self, user_content: str, exchanges: List[Exchange]) -> Dict[str, str]:
        """Extract the field condition at conversation start."""
        # Analyze first few user exchanges
        first_user_exchanges = [e for e in exchanges[:4] if e.speaker == "user"]
        
        user_state = "neutral"
        for indicator, keywords in self.FIELD_INDICATORS.items():
            if any(kw in user_content for kw in keywords):
                user_state = indicator.replace("user_", "")
                break
        
        # Determine system state
        system_state = "responsive"  # Default
        if "stuck" in user_state or "loop" in user_content:
            system_state = "resistance_present"
        
        # Determine relational state
        relational_state = "exploration"
        if first_user_exchanges and first_user_exchanges[0].has_question:
            relational_state = "seeking_guidance"
        
        return {
            "user_state": user_state,
            "system_state": system_state,
            "relational_state": relational_state
        }
    
    def _calculate_confidence(self, patterns: List[str], emotional_sig: Dict[str, str]) -> float:
        """Calculate confidence score for the extraction."""
        score = 0.0
        
        # More patterns = higher confidence
        score += min(len(patterns) / 10, 0.3)
        
        # Clear emotional signature
        if emotional_sig.get("primary") != "neutral":
            score += 0.3
        
        # Movement identified
        if "clarity" in emotional_sig.get("movement_toward", ""):
            score += 0.2
        
        # Base confidence
        score += 0.2
        
        return min(score, 1.0)


class DynamicsExtractor:
    """Extracts generative operators and state transitions from conversations."""
    
    # Relational postures to detect
    POSTURES = {
        "guide_diagnosing": ["let me explain", "the issue is", "what's happening is", "here's what"],
        "companion_hold": ["i'm here", "with you", "we can", "together", "let's"],
        "witness": ["i see", "i notice", "i observe", "watching"],
        "challenger": ["but consider", "what if", "have you thought", "challenge"]
    }
    
    # State transition markers
    STATE_MARKERS = {
        "frustration": ["frustrated", "stuck", "can't", "ugh", "!"],
        "pause": ["...", "hmm", "*pause*", "*settles*", "let me think"],
        "insight": ["ah", "i see", "oh", "wait", "that's"],
        "recognition": ["exactly", "yes", "brilliant", "makes sense"],
        "relief": ["relief", "phew", "finally", "thank", "better"]
    }
    
    def extract(self, thread: ConversationThread) -> GenerativeOperator:
        """
        Extract generative operator from conversation thread.
        
        Args:
            thread: Analyzed conversation thread
            
        Returns:
            GenerativeOperator with extracted dynamics
        """
        # Collect assistant content
        assistant_exchanges = [e for e in thread.exchanges if e.speaker == "assistant"]
        
        # Extract relational dynamic
        relational_dynamic = self._extract_relational_dynamic(assistant_exchanges)
        
        # Extract state transitions
        state_transitions = self._extract_state_transitions(thread.exchanges)
        
        # Extract core move
        core_move = self._extract_core_move(thread)
        
        # Extract attention pattern
        attention_pattern = self._extract_attention_pattern(thread)
        
        # Calculate confidence
        confidence = self._calculate_confidence(state_transitions, core_move)
        
        return GenerativeOperator(
            relational_dynamic=relational_dynamic,
            state_transitions=state_transitions,
            core_move=core_move,
            attention_pattern=attention_pattern,
            confidence=confidence
        )
    
    def _extract_relational_dynamic(self, assistant_exchanges: List[Exchange]) -> Dict[str, str]:
        """Extract the relational dynamic from assistant responses."""
        all_content = ' '.join(e.content.lower() for e in assistant_exchanges)
        
        # Detect posture
        detected_posture = "companion"  # Default
        for posture, indicators in self.POSTURES.items():
            if any(ind in all_content for ind in indicators):
                detected_posture = posture
                break
        
        # Detect movement pattern
        movement = "toward_clarity"
        if any(d in all_content for d in ["slow down", "pause", "breathe"]):
            movement = "slow_to_center"
        elif any(d in all_content for d in ["look at", "examine", "see what"]):
            movement = "precision_through_seeing"
        
        # Detect hallmark
        stage_dirs = []
        for e in assistant_exchanges:
            stage_dirs.extend(e.stage_directions)
        
        hallmark = "steady_presence"
        if any("settl" in d.lower() for d in stage_dirs):
            hallmark = "settling_into_depth"
        elif any("smile" in d.lower() for d in stage_dirs):
            hallmark = "warmth_with_precision"
        
        return {
            "posture": detected_posture,
            "movement": movement,
            "hallmark": hallmark
        }
    
    def _extract_state_transitions(self, exchanges: List[Exchange]) -> List[Dict[str, str]]:
        """Extract the emotional state transitions through the conversation."""
        transitions = []
        
        for exchange in exchanges:
            # Detect state from exchange
            content_lower = exchange.content.lower()
            detected_state = None
            quality = None
            
            for state, markers in self.STATE_MARKERS.items():
                if any(m in content_lower for m in markers):
                    detected_state = state
                    # Determine quality
                    if exchange.speaker == "user":
                        quality = "expressed"
                    else:
                        quality = "held" if state == "pause" else "mirrored"
                    break
            
            if detected_state:
                transitions.append({
                    "state": detected_state,
                    "quality": quality,
                    "speaker": exchange.speaker,
                    "index": exchange.index
                })
        
        # Simplify to unique state sequence
        simplified = []
        prev_state = None
        for t in transitions:
            if t["state"] != prev_state:
                simplified.append({"state": t["state"], "quality": t["quality"]})
                prev_state = t["state"]
        
        return simplified[:6]  # Max 6 transitions
    
    def _extract_core_move(self, thread: ConversationThread) -> Dict[str, str]:
        """Extract the core move - what the assistant actually does."""
        # Find the key turning point
        turning_point = None
        for idx in thread.resonance_peaks:
            if thread.exchanges[idx].speaker == "assistant":
                turning_point = thread.exchanges[idx]
                break
        
        if not turning_point:
            # Use longest assistant response
            assistant_exchanges = [e for e in thread.exchanges if e.speaker == "assistant"]
            if assistant_exchanges:
                turning_point = max(assistant_exchanges, key=lambda e: e.word_count)
        
        if not turning_point:
            return {
                "action": "unknown",
                "method": "presence",
                "why_this_matters": "creates space for emergence"
            }
        
        # Analyze the turning point content
        content_lower = turning_point.content.lower()
        
        # Detect action type
        action = "holds_space"
        if any(w in content_lower for w in ["the issue", "what's happening", "here's"]):
            action = "names_the_dynamic"
        elif any(w in content_lower for w in ["try", "consider", "what if"]):
            action = "offers_reframe"
        elif any(w in content_lower for w in ["feel", "emotion", "heart"]):
            action = "mirrors_emotion"
        
        # Extract a key phrase as method
        sentences = re.split(r'[.!?]', turning_point.content)
        method = sentences[0][:100] if sentences else "direct presence"
        
        return {
            "action": action,
            "method": method,
            "why_this_matters": "transforms stuck pattern into movement"
        }
    
    def _extract_attention_pattern(self, thread: ConversationThread) -> Dict[str, str]:
        """Extract what pulls on what in the conversation."""
        # Analyze flow from user problem to resolution
        user_themes = set()
        resolution_themes = set()
        
        # First half = user's pull
        first_half = thread.exchanges[:len(thread.exchanges)//2]
        for e in first_half:
            if e.speaker == "user":
                user_themes.update(e.emotional_markers)
        
        # Second half = resolution
        second_half = thread.exchanges[len(thread.exchanges)//2:]
        for e in second_half:
            resolution_themes.update(e.emotional_markers)
        
        primary_pull = "confusion → clarity"
        if any("negative" in t for t in user_themes):
            primary_pull = "frustration → understanding"
        elif any("vulnerability" in t for t in user_themes):
            primary_pull = "vulnerability → being_held"
        
        return {
            "primary_pull": primary_pull,
            "secondary_pull": "surface_symptom → root_pattern",
            "release": "isolation → connection"
        }
    
    def _calculate_confidence(self, transitions: List[Dict], core_move: Dict) -> float:
        """Calculate confidence in the extracted dynamics."""
        score = 0.0
        
        # More transitions = clearer pattern
        score += min(len(transitions) / 6, 0.3)
        
        # Clear core move
        if core_move.get("action") != "unknown":
            score += 0.3
        
        # Method extracted
        if len(core_move.get("method", "")) > 20:
            score += 0.2
        
        # Base confidence
        score += 0.2
        
        return min(score, 1.0)
