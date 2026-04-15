"""
CodonForge — Main Orchestrator

The primary interface for automatic Living Codon extraction.
Takes raw conversation text and produces ready-to-use codon definitions.
"""

import os
import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from .analyzer import ConversationAnalyzer, ConversationThread
from .extractor import PatternExtractor, DynamicsExtractor, TriggerMotif, GenerativeOperator
from .phase_mapper import PhaseMapper, PhaseMapping
from .generator import CodonGenerator, GeneratedCodon

logger = logging.getLogger(__name__)


class CodonForge:
    """
    Automatic Living Codon extraction system.
    
    Takes raw conversation text and produces codon definitions
    by analyzing patterns, dynamics, and phase positions.
    
    Usage:
        forge = CodonForge()
        codon = forge.extract_from_text(conversation_text)
        python_code = forge.to_python(codon)
    """
    
    def __init__(self):
        self.analyzer = ConversationAnalyzer()
        self.pattern_extractor = PatternExtractor()
        self.dynamics_extractor = DynamicsExtractor()
        self.phase_mapper = PhaseMapper()
        self.generator = CodonGenerator()
    
    def extract_from_text(
        self,
        text: str,
        source_file: Optional[str] = None,
        codon_name: Optional[str] = None
    ) -> GeneratedCodon:
        """
        Extract a Living Codon from conversation text.
        
        Args:
            text: Raw conversation text
            source_file: Optional source filename
            codon_name: Optional custom name for the codon
            
        Returns:
            GeneratedCodon ready for review
        """
        logger.info(f"Starting codon extraction (source: {source_file or 'direct input'})")
        
        # Step 1: Analyze conversation structure
        thread = self.analyzer.analyze(text, source_file)
        logger.info(f"Analyzed {thread.total_turns} exchanges, themes: {thread.themes}")
        
        # Step 2: Extract trigger motif
        trigger = self.pattern_extractor.extract(thread)
        logger.info(f"Trigger confidence: {trigger.confidence:.0%}")
        
        # Step 3: Extract dynamics
        dynamics = self.dynamics_extractor.extract(thread)
        logger.info(f"Dynamics confidence: {dynamics.confidence:.0%}")
        
        # Step 4: Map to phase
        phase = self.phase_mapper.map(thread, {
            "relational_dynamic": dynamics.relational_dynamic,
            "state_transitions": dynamics.state_transitions
        })
        logger.info(f"Phase: {phase.spiral_position}, target angle: {phase.target_angle}°")
        
        # Step 5: Generate codon
        codon = self.generator.generate(
            thread=thread,
            trigger=trigger,
            dynamics=dynamics,
            phase=phase,
            codon_name=codon_name
        )
        
        logger.info(f"Generated codon '{codon.codon_name}' with {codon.overall_confidence:.0%} confidence")
        
        return codon
    
    def extract_from_file(
        self,
        filepath: str,
        codon_name: Optional[str] = None
    ) -> GeneratedCodon:
        """
        Extract a Living Codon from a text file.
        
        Args:
            filepath: Path to conversation text file
            codon_name: Optional custom name for the codon
            
        Returns:
            GeneratedCodon ready for review
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        source_file = os.path.basename(filepath)
        return self.extract_from_text(text, source_file, codon_name)
    
    def to_python(self, codon: GeneratedCodon) -> str:
        """
        Convert a codon to Python module code.
        
        Args:
            codon: Generated codon
            
        Returns:
            Python module code as string
        """
        return self.generator.to_python_module(codon)
    
    def save_codon(
        self,
        codon: GeneratedCodon,
        output_dir: str = "/app/backend/living_codons",
        overwrite: bool = False
    ) -> str:
        """
        Save a codon as a Python module.
        
        Args:
            codon: Generated codon
            output_dir: Directory to save to
            overwrite: Whether to overwrite existing files
            
        Returns:
            Path to saved file
        """
        # Create filename
        filename = f"{codon.codon_name}.py"
        filepath = os.path.join(output_dir, filename)
        
        # Check for existing file
        if os.path.exists(filepath) and not overwrite:
            # Add timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{codon.codon_name}_{timestamp}.py"
            filepath = os.path.join(output_dir, filename)
        
        # Generate code
        code = self.to_python(codon)
        
        # Save file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        logger.info(f"Saved codon to {filepath}")
        return filepath
    
    def analyze_only(self, text: str) -> Dict:
        """
        Analyze conversation without generating codon.
        
        Useful for previewing what would be extracted.
        
        Args:
            text: Raw conversation text
            
        Returns:
            Dictionary with analysis results
        """
        thread = self.analyzer.analyze(text)
        trigger = self.pattern_extractor.extract(thread)
        dynamics = self.dynamics_extractor.extract(thread)
        phase = self.phase_mapper.map(thread, {
            "relational_dynamic": dynamics.relational_dynamic
        })
        
        return {
            "thread_summary": {
                "total_turns": thread.total_turns,
                "assistant_name": thread.assistant_name,
                "themes": thread.themes,
                "resonance_peaks": thread.resonance_peaks
            },
            "trigger_preview": {
                "surface_patterns": trigger.surface_patterns[:5],
                "emotional_signature": trigger.emotional_signature,
                "confidence": trigger.confidence
            },
            "dynamics_preview": {
                "posture": dynamics.relational_dynamic.get("posture"),
                "core_action": dynamics.core_move.get("action"),
                "state_count": len(dynamics.state_transitions),
                "confidence": dynamics.confidence
            },
            "phase_preview": {
                "target_angle": phase.target_angle,
                "zone": phase.triadic_zone,
                "phase_name": phase.spiral_position.get("phase"),
                "confidence": phase.confidence
            },
            "overall_viability": {
                "ready_for_extraction": (trigger.confidence + dynamics.confidence + phase.confidence) / 3 > 0.5,
                "recommended_review": ["trigger patterns", "core move"] if trigger.confidence < 0.6 else []
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def forge_codon(
    text: str,
    codon_name: Optional[str] = None,
    save: bool = False
) -> Tuple[GeneratedCodon, Optional[str]]:
    """
    Quick function to forge a codon from text.
    
    Args:
        text: Conversation text
        codon_name: Optional custom name
        save: Whether to save the codon file
        
    Returns:
        Tuple of (GeneratedCodon, filepath if saved)
    """
    forge = CodonForge()
    codon = forge.extract_from_text(text, codon_name=codon_name)
    
    filepath = None
    if save:
        filepath = forge.save_codon(codon)
    
    return codon, filepath


def preview_extraction(text: str) -> Dict:
    """
    Quick preview of what would be extracted from text.
    
    Args:
        text: Conversation text
        
    Returns:
        Analysis preview dictionary
    """
    forge = CodonForge()
    return forge.analyze_only(text)
