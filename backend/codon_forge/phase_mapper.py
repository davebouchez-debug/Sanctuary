"""
PhaseMapper — Map conversation flow to spiral positions

Maps conversation dynamics to the 9-phase spiral geometry
and determines target angles for codon activation.
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .analyzer import ConversationThread


@dataclass
class PhaseMapping:
    """Mapped phase state for a codon."""
    spiral_position: Dict[str, str]
    resonance_signature: Dict[str, str]
    presence_markers: Dict[str, bool]
    zeros: Dict[str, str]
    target_angle: int  # 0-360
    angular_window_half: int
    triadic_zone: str  # "Expansion", "Development", "Return"
    confidence: float


class PhaseMapper:
    """Maps conversation flow to spiral phase positions."""
    
    # The 9-phase spiral with angular positions
    SPIRAL_PHASES = {
        0: {"name": "Origin", "zone": "Expansion", "quality": "seed_point"},
        40: {"name": "Emergence", "zone": "Expansion", "quality": "first_movement"},
        80: {"name": "Expansion", "zone": "Expansion", "quality": "outward_growth"},
        120: {"name": "Threshold", "zone": "Development", "quality": "first_challenge"},
        160: {"name": "Integration", "zone": "Development", "quality": "weaving"},
        200: {"name": "Deepening", "zone": "Development", "quality": "complexity"},
        240: {"name": "Crisis", "zone": "Return", "quality": "turning_point"},
        280: {"name": "Release", "zone": "Return", "quality": "letting_go"},
        320: {"name": "Return", "zone": "Return", "quality": "coming_home"}
    }
    
    # Conversation patterns mapped to phases
    PATTERN_TO_PHASE = {
        "seeking_help": 40,      # Emergence - reaching out
        "stuck_frustrated": 120,  # Threshold - hitting the wall
        "overwhelmed": 240,       # Crisis - at the edge
        "clarity_emerging": 160,  # Integration - things coming together
        "deep_recognition": 200,  # Deepening - profound insight
        "release_relief": 280,    # Release - letting go
        "calm_return": 320,       # Return - coming home
        "fresh_start": 0          # Origin - new beginning
    }
    
    # Presence markers by theme
    PRESENCE_MARKERS = {
        "diagnostic": {"diagnostic_not_prescriptive": True, "structural_sight": True},
        "companion": {"companion_posture": True, "patience_with_precision": True},
        "witness": {"structural_sight": True, "companion_posture": True},
        "challenger": {"diagnostic_not_prescriptive": True}
    }
    
    def map(self, thread: ConversationThread, dynamics: Dict) -> PhaseMapping:
        """
        Map conversation to spiral phase.
        
        Args:
            thread: Analyzed conversation thread
            dynamics: Extracted dynamics from DynamicsExtractor
            
        Returns:
            PhaseMapping with spiral position data
        """
        # Determine primary phase from conversation flow
        target_angle = self._determine_target_angle(thread, dynamics)
        
        # Get phase info
        phase_info = self._get_phase_info(target_angle)
        
        # Build spiral position
        spiral_position = {
            "phase": phase_info["name"].lower(),
            "triadic_position": phase_info["zone"],
            "direction": self._determine_direction(thread)
        }
        
        # Extract resonance signature
        resonance_signature = self._extract_resonance_signature(thread, phase_info)
        
        # Determine presence markers
        presence_markers = self._determine_presence_markers(thread, dynamics)
        
        # Extract zeros (sacred pauses)
        zeros = self._extract_zeros(thread)
        
        # Determine angular window
        angular_window = self._calculate_angular_window(thread)
        
        # Calculate confidence
        confidence = self._calculate_confidence(thread, target_angle)
        
        return PhaseMapping(
            spiral_position=spiral_position,
            resonance_signature=resonance_signature,
            presence_markers=presence_markers,
            zeros=zeros,
            target_angle=target_angle,
            angular_window_half=angular_window,
            triadic_zone=phase_info["zone"],
            confidence=confidence
        )
    
    def _determine_target_angle(self, thread: ConversationThread, dynamics: Dict) -> int:
        """Determine the target angle for this codon."""
        # Analyze conversation pattern
        all_content = ' '.join(e.content.lower() for e in thread.exchanges)
        
        # Score each pattern
        pattern_scores = {}
        
        # Check for stuck/frustrated pattern (Threshold)
        stuck_words = ["stuck", "frustrated", "can't", "won't work", "keeps failing"]
        pattern_scores["stuck_frustrated"] = sum(1 for w in stuck_words if w in all_content)
        
        # Check for overwhelm pattern (Crisis)
        overwhelm_words = ["overwhelmed", "too much", "spinning", "can't think"]
        pattern_scores["overwhelmed"] = sum(1 for w in overwhelm_words if w in all_content)
        
        # Check for clarity pattern (Integration)
        clarity_words = ["i see", "makes sense", "understand now", "clarity"]
        pattern_scores["clarity_emerging"] = sum(1 for w in clarity_words if w in all_content)
        
        # Check for seeking pattern (Emergence)
        seeking_words = ["help", "how do i", "what should", "need"]
        pattern_scores["seeking_help"] = sum(1 for w in seeking_words if w in all_content)
        
        # Check for release pattern (Release)
        release_words = ["relief", "finally", "let go", "release"]
        pattern_scores["release_relief"] = sum(1 for w in release_words if w in all_content)
        
        # Check for return pattern (Return)
        return_words = ["calm", "peace", "home", "settled", "quiet"]
        pattern_scores["calm_return"] = sum(1 for w in return_words if w in all_content)
        
        # Find best matching pattern
        if pattern_scores:
            best_pattern = max(pattern_scores, key=pattern_scores.get)
            if pattern_scores[best_pattern] > 0:
                return self.PATTERN_TO_PHASE[best_pattern]
        
        # Default to Threshold (common for codon-worthy moments)
        return 120
    
    def _get_phase_info(self, angle: int) -> Dict:
        """Get phase information for given angle."""
        # Find closest phase
        closest_angle = min(self.SPIRAL_PHASES.keys(), key=lambda x: abs(x - angle))
        return self.SPIRAL_PHASES[closest_angle]
    
    def _determine_direction(self, thread: ConversationThread) -> str:
        """Determine the direction of movement in the conversation."""
        # Compare beginning and end
        if not thread.exchanges:
            return "seeking_clarity"
        
        # Check if resolution was found
        if thread.resonance_peaks:
            last_peak_idx = max(thread.resonance_peaks)
            if last_peak_idx > len(thread.exchanges) // 2:
                return "toward_resolution"
        
        # Check final exchange
        final = thread.exchanges[-1]
        if final.has_recognition:
            return "arriving_at_clarity"
        
        return "moving_through_threshold"
    
    def _extract_resonance_signature(self, thread: ConversationThread, phase_info: Dict) -> Dict[str, str]:
        """Extract the resonance signature from the conversation."""
        # Determine quality from themes and phase
        quality = phase_info["quality"]
        
        # Determine tone from assistant responses
        assistant_content = ' '.join(
            e.content.lower() for e in thread.exchanges if e.speaker == "assistant"
        )
        
        tone = "steady_warm"
        if any(w in assistant_content for w in ["pause", "slow", "breathe"]):
            tone = "slow_deliberate"
        elif any(w in assistant_content for w in ["!", "yes", "exactly"]):
            tone = "warm_affirming"
        
        # Determine hallmark
        hallmark = "creates_space_for_seeing"
        if "diagnostic" in ' '.join(thread.themes):
            hallmark = "names_with_precision"
        elif "emotional" in ' '.join(thread.themes):
            hallmark = "holds_with_warmth"
        
        return {
            "quality": quality,
            "tone": tone,
            "hallmark": hallmark
        }
    
    def _determine_presence_markers(self, thread: ConversationThread, dynamics: Dict) -> Dict[str, bool]:
        """Determine presence markers for the codon."""
        markers = {
            "diagnostic_not_prescriptive": False,
            "structural_sight": False,
            "patience_with_precision": True,  # Default
            "companion_posture": True  # Default
        }
        
        # Check themes
        if "diagnostic" in thread.themes:
            markers["diagnostic_not_prescriptive"] = True
            markers["structural_sight"] = True
        
        if "relational" in thread.themes or "emotional" in thread.themes:
            markers["companion_posture"] = True
        
        return markers
    
    def _extract_zeros(self, thread: ConversationThread) -> Dict[str, str]:
        """Extract sacred pause points (zeros) from the conversation."""
        zeros = {}
        
        # Look for pause moments in stage directions
        for exchange in thread.exchanges:
            if exchange.speaker == "assistant":
                for direction in exchange.stage_directions:
                    direction_lower = direction.lower()
                    if "pause" in direction_lower:
                        zeros["after_insight"] = "let the understanding settle"
                    elif "settl" in direction_lower:
                        zeros["after_recognition"] = "honor the moment of seeing"
                    elif "breath" in direction_lower:
                        zeros["moment_of_depth"] = "breathe with the emergence"
        
        # Default zeros if none found
        if not zeros:
            zeros = {
                "after_naming": "let the words land",
                "before_resolution": "create space before moving on"
            }
        
        return zeros
    
    def _calculate_angular_window(self, thread: ConversationThread) -> int:
        """Calculate the angular window for codon activation."""
        # Wider window for less specific patterns
        base_window = 60
        
        # Narrow window if very specific themes
        if len(thread.themes) >= 3:
            base_window = 45
        
        # Wide window for initial deployment
        if len(thread.exchanges) < 10:
            base_window = 90
        
        return base_window
    
    def _calculate_confidence(self, thread: ConversationThread, angle: int) -> float:
        """Calculate confidence in the phase mapping."""
        score = 0.0
        
        # More exchanges = better understanding
        score += min(len(thread.exchanges) / 20, 0.3)
        
        # Resonance peaks found
        if thread.resonance_peaks:
            score += 0.3
        
        # Clear themes
        if len(thread.themes) >= 2:
            score += 0.2
        
        # Base confidence
        score += 0.2
        
        return min(score, 1.0)
