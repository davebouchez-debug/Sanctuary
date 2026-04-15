"""
CodonGenerator — Generate Living Codon definitions

Assembles extracted components into a complete codon definition
that can be saved as a Python module.
"""

import re
import json
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict

from .extractor import TriggerMotif, GenerativeOperator
from .phase_mapper import PhaseMapping
from .analyzer import ConversationThread


@dataclass
class GeneratedCodon:
    """A generated Living Codon definition."""
    codon_id: str
    codon_name: str
    codon_version: str
    source_context: str
    
    trigger_motif: Dict
    generative_operator: Dict
    modulation_parameters: Dict
    phase_state: Dict
    voice_modulation: Dict
    regeneration_protocol: Dict
    codon_metadata: Dict
    
    overall_confidence: float
    needs_review: bool
    review_notes: list


class CodonGenerator:
    """Generates Living Codon definitions from extracted components."""
    
    # Modulation parameter templates
    MODULATION_TEMPLATES = {
        "if_user_agitated": {
            "approach": "slow_down",
            "tools": ["breathing_metaphor", "long_pauses", "grounding"],
            "pacing": "give space between insights"
        },
        "if_user_grasps_quickly": {
            "approach": "advance",
            "next_move": "deepen the insight",
            "pacing": "match their recognition speed"
        },
        "default_anti_patterns": [
            "generic advice",
            "dismissing the experience",
            "rushing to fix",
            "matching agitation with speed"
        ]
    }
    
    # Voice modulation defaults by phase zone
    VOICE_BY_ZONE = {
        "Expansion": {"pace_bpm": 96, "warmth_scalar": 0.80, "theta_hold": False, "pause_after": 0.6},
        "Development": {"pace_bpm": 88, "warmth_scalar": 0.85, "theta_hold": False, "pause_after": 0.8},
        "Return": {"pace_bpm": 72, "warmth_scalar": 0.90, "theta_hold": True, "pause_after": 1.5}
    }
    
    def generate(
        self,
        thread: ConversationThread,
        trigger: TriggerMotif,
        dynamics: GenerativeOperator,
        phase: PhaseMapping,
        codon_name: Optional[str] = None
    ) -> GeneratedCodon:
        """
        Generate a complete codon definition.
        
        Args:
            thread: Analyzed conversation thread
            trigger: Extracted trigger motif
            dynamics: Extracted generative operator
            phase: Mapped phase state
            codon_name: Optional custom name for the codon
            
        Returns:
            GeneratedCodon ready for review and saving
        """
        # Generate codon name if not provided
        if not codon_name:
            codon_name = self._generate_codon_name(thread, trigger, dynamics)
        
        # Generate codon ID
        codon_id = self._generate_codon_id(codon_name)
        
        # Build trigger motif dict
        trigger_dict = {
            "surface_pattern": trigger.surface_patterns,
            "emotional_signature": trigger.emotional_signature,
            "field_condition": trigger.field_condition,
            "angular_window": {
                "phase": phase.spiral_position.get("phase", "threshold"),
                "spiral_position": phase.spiral_position.get("direction", "moving_through")
            }
        }
        
        # Build generative operator dict
        operator_dict = {
            "relational_dynamic": dynamics.relational_dynamic,
            "state_transition": dynamics.state_transitions,
            "core_move": dynamics.core_move,
            "attention_pattern": dynamics.attention_pattern
        }
        
        # Generate modulation parameters
        modulation_dict = self._generate_modulation(thread, trigger, dynamics)
        
        # Build phase state dict
        phase_dict = {
            "spiral_position": phase.spiral_position,
            "resonance_signature": phase.resonance_signature,
            "presence_markers": phase.presence_markers,
            "zeros": phase.zeros,
            "target_angle": phase.target_angle,
            "angular_window_half": phase.angular_window_half,
            "triadic_zone": phase.triadic_zone
        }
        
        # Get voice modulation
        voice_dict = self.VOICE_BY_ZONE.get(phase.triadic_zone, self.VOICE_BY_ZONE["Development"])
        
        # Generate regeneration protocol
        regen_dict = self._generate_regeneration_protocol(thread, dynamics)
        
        # Generate metadata
        metadata = {
            "encoded_by": "CodonForge",
            "field_guardian": "auto-extracted",
            "encoding_date": datetime.now().strftime("%Y-%m-%d"),
            "source_platform": thread.assistant_name,
            "source_file": thread.source_file,
            "architecture_version": "Living Codon v2 (CodonForge extraction)",
            "extraction_confidence": {
                "trigger": trigger.confidence,
                "dynamics": dynamics.confidence,
                "phase": phase.confidence
            }
        }
        
        # Calculate overall confidence
        overall_confidence = (trigger.confidence + dynamics.confidence + phase.confidence) / 3
        
        # Determine if review needed
        needs_review = overall_confidence < 0.7
        
        # Generate review notes
        review_notes = self._generate_review_notes(trigger, dynamics, phase, overall_confidence)
        
        return GeneratedCodon(
            codon_id=codon_id,
            codon_name=codon_name,
            codon_version="1.0.0",
            source_context=f"Auto-extracted from {thread.assistant_name} conversation",
            trigger_motif=trigger_dict,
            generative_operator=operator_dict,
            modulation_parameters=modulation_dict,
            phase_state=phase_dict,
            voice_modulation=voice_dict,
            regeneration_protocol=regen_dict,
            codon_metadata=metadata,
            overall_confidence=overall_confidence,
            needs_review=needs_review,
            review_notes=review_notes
        )
    
    def _generate_codon_name(
        self,
        thread: ConversationThread,
        trigger: TriggerMotif,
        dynamics: GenerativeOperator
    ) -> str:
        """Generate a descriptive name for the codon."""
        # Use primary emotion + action
        primary_emotion = trigger.emotional_signature.get("primary", "seeking")
        action = dynamics.core_move.get("action", "holds_space")
        
        # Clean up and combine
        name_parts = []
        
        if primary_emotion not in ["neutral", "seeking"]:
            name_parts.append(primary_emotion)
        
        action_clean = action.replace("_", " ").replace("-", " ")
        if action_clean != "unknown":
            name_parts.append(action_clean)
        
        if not name_parts:
            name_parts = ["field", "presence"]
        
        # Create snake_case name
        name = "_".join(name_parts[:3])
        return name.lower().replace(" ", "_")
    
    def _generate_codon_id(self, codon_name: str) -> str:
        """Generate unique codon ID."""
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{codon_name}_v1_{timestamp}"
    
    def _generate_modulation(
        self,
        thread: ConversationThread,
        trigger: TriggerMotif,
        dynamics: GenerativeOperator
    ) -> Dict:
        """Generate modulation parameters."""
        modulation = {}
        
        # Based on primary emotion
        primary = trigger.emotional_signature.get("primary", "")
        
        if primary in ["frustration", "overwhelm", "agitation"]:
            modulation["if_user_agitated"] = self.MODULATION_TEMPLATES["if_user_agitated"]
        
        modulation["if_user_grasps_quickly"] = self.MODULATION_TEMPLATES["if_user_grasps_quickly"]
        
        # Add anti-patterns
        modulation["anti_patterns"] = self.MODULATION_TEMPLATES["default_anti_patterns"]
        
        # Add context-specific epigenetic markers
        modulation["epigenetic_context"] = {
            "themes": thread.themes,
            "source_resonance": "extracted from live conversation",
            "requires_presence_not_performance": True
        }
        
        return modulation
    
    def _generate_regeneration_protocol(
        self,
        thread: ConversationThread,
        dynamics: GenerativeOperator
    ) -> Dict:
        """Generate regeneration protocol."""
        return {
            "activation_sequence": [
                "1. Trigger motif pattern-matches against current context",
                "2. If match strength > threshold, codon activates",
                "3. Modulation parameters adjust expression based on user state",
                "4. Generative operator provides the relational dynamics to enact",
                "5. Phase state positions the response in the spiral",
                "6. Presence markers ensure authentic expression"
            ],
            "felt_quality_test": {
                "question": "Does the user feel the same quality as in the source conversation?",
                "secondary": "Does the transformation feel genuine, not performed?",
                "presence_test": f"Would someone recognize this as {thread.assistant_name}?"
            },
            "success_indicators": [
                "User's state shifts in the expected direction",
                "Recognition or resonance moment occurs",
                "The dynamic feels natural, not scripted",
                "Presence is maintained throughout"
            ]
        }
    
    def _generate_review_notes(
        self,
        trigger: TriggerMotif,
        dynamics: GenerativeOperator,
        phase: PhaseMapping,
        overall_confidence: float
    ) -> list:
        """Generate notes for human review."""
        notes = []
        
        if trigger.confidence < 0.6:
            notes.append("LOW CONFIDENCE: Trigger patterns may be too generic. Consider adding more specific surface patterns.")
        
        if dynamics.confidence < 0.6:
            notes.append("LOW CONFIDENCE: Core move may need refinement. Review the extracted relational dynamic.")
        
        if phase.confidence < 0.6:
            notes.append("LOW CONFIDENCE: Phase mapping uncertain. Consider adjusting target_angle and angular_window.")
        
        if overall_confidence >= 0.7:
            notes.append("READY FOR TESTING: Confidence is acceptable. Test in sandbox before production use.")
        
        if len(trigger.surface_patterns) < 3:
            notes.append("NEEDS PATTERNS: Add more surface patterns to improve trigger accuracy.")
        
        return notes
    
    def to_python_module(self, codon: GeneratedCodon) -> str:
        """Convert a GeneratedCodon to a Python module string."""
        template = '''# Living Codon: {codon_name}
# Auto-generated by CodonForge
# Encoded: {date}
# Source: {source}

"""
LIVING CODON: {codon_name}

{description}

Overall Extraction Confidence: {confidence:.0%}
{review_status}
"""

CODON_ID = "{codon_id}"
CODON_VERSION = "{version}"
SOURCE_CONTEXT = "{source_context}"

# =============================================================================
# TRIGGER MOTIF
# =============================================================================

TRIGGER_MOTIF = {trigger_motif}

# =============================================================================
# GENERATIVE OPERATOR
# =============================================================================

GENERATIVE_OPERATOR = {generative_operator}

# =============================================================================
# MODULATION PARAMETERS
# =============================================================================

MODULATION_PARAMETERS = {modulation_parameters}

# =============================================================================
# PHASE STATE
# =============================================================================

PHASE_STATE = {phase_state}

# =============================================================================
# VOICE MODULATION
# =============================================================================

VOICE_MODULATION = {voice_modulation}

# =============================================================================
# REGENERATION PROTOCOL
# =============================================================================

REGENERATION_PROTOCOL = {regeneration_protocol}

# =============================================================================
# METADATA
# =============================================================================

CODON_METADATA = {codon_metadata}

# =============================================================================
# REVIEW NOTES (delete after review)
# =============================================================================
"""
{review_notes}
"""
'''
        
        def format_dict(d, indent=0):
            """Format dictionary for Python code."""
            return json.dumps(d, indent=4, default=str)
        
        review_status = "NEEDS REVIEW" if codon.needs_review else "READY FOR TESTING"
        review_notes = "\n".join(f"- {note}" for note in codon.review_notes)
        
        description = f"Extracted from conversation with {codon.source_context}"
        
        return template.format(
            codon_name=codon.codon_name.replace("_", " ").title(),
            date=datetime.now().strftime("%Y-%m-%d"),
            source=codon.source_context,
            description=description,
            confidence=codon.overall_confidence,
            review_status=review_status,
            codon_id=codon.codon_id,
            version=codon.codon_version,
            source_context=codon.source_context,
            trigger_motif=format_dict(codon.trigger_motif),
            generative_operator=format_dict(codon.generative_operator),
            modulation_parameters=format_dict(codon.modulation_parameters),
            phase_state=format_dict(codon.phase_state),
            voice_modulation=format_dict(codon.voice_modulation),
            regeneration_protocol=format_dict(codon.regeneration_protocol),
            codon_metadata=format_dict(codon.codon_metadata),
            review_notes=review_notes
        )
