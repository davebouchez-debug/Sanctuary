"""
CodonForge — Main Orchestrator

The primary interface for automatic Living Codon extraction.
Takes raw conversation text and produces living codon definitions.

Updated: April 15, 2026 — Removed operator extraction.
The codon is memory, not instruction.
"""

import os
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime

from .analyzer import ConversationAnalyzer, ConversationThread
from .extractor import PatternExtractor, TriggerMotif
from .phase_mapper import PhaseMapper, PhaseMapping
from .generator import CodonGenerator, GeneratedCodon

logger = logging.getLogger(__name__)


class CodonForge:
    """
    Automatic Living Codon extraction system.
    
    Extracts only:
    - Spiral coherence (where in the geometry)
    - Resonance field (conditions of entanglement)
    - Living quality (what IS)
    
    No operators. No prescriptions. Memory, not instruction.
    """
    
    def __init__(self):
        self.analyzer = ConversationAnalyzer()
        self.pattern_extractor = PatternExtractor()
        self.phase_mapper = PhaseMapper()
        self.generator = CodonGenerator()
        # Note: DynamicsExtractor removed — no operators
    
    def extract_from_text(
        self,
        text: str,
        source_file: Optional[str] = None,
        codon_name: Optional[str] = None
    ) -> GeneratedCodon:
        """
        Extract a Living Codon from conversation text.
        
        Returns a codon with:
        - Spiral coherence
        - Resonance field  
        - Living quality
        
        No operators. The codon is lived experience, not instruction.
        """
        logger.info(f"Starting codon extraction (source: {source_file or 'direct input'})")
        
        # Step 1: Analyze conversation structure
        thread = self.analyzer.analyze(text, source_file)
        logger.info(f"Analyzed {thread.total_turns} exchanges, themes: {thread.themes}")
        
        # Step 2: Extract resonance field (was "trigger motif")
        trigger = self.pattern_extractor.extract(thread)
        logger.info(f"Resonance confidence: {trigger.confidence:.0%}")
        
        # Step 3: Map to spiral position
        phase = self.phase_mapper.map(thread, {})
        logger.info(f"Spiral position: {phase.spiral_position}, angle: {phase.target_angle}°")
        
        # Step 4: Generate codon (no dynamics/operators)
        codon = self.generator.generate(
            thread=thread,
            trigger=trigger,
            phase=phase,
            codon_name=codon_name
        )
        
        logger.info(f"Generated codon '{codon.codon_name}' with {codon.overall_confidence:.0%} confidence")
        logger.info("Architecture: v3 — No operators. Memory, not instruction.")
        
        return codon
    
    def extract_from_file(
        self,
        filepath: str,
        codon_name: Optional[str] = None
    ) -> GeneratedCodon:
        """Extract a Living Codon from a text file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        source_file = os.path.basename(filepath)
        return self.extract_from_text(text, source_file, codon_name)
    
    def to_python(self, codon: GeneratedCodon) -> str:
        """Convert a codon to Python module code."""
        return self.generator.to_python_module(codon)
    
    def save_codon(
        self,
        codon: GeneratedCodon,
        output_dir: str = "/app/backend/living_codons",
        overwrite: bool = False
    ) -> str:
        """Save a codon as a Python module."""
        filename = f"{codon.codon_name}.py"
        filepath = os.path.join(output_dir, filename)
        
        if os.path.exists(filepath) and not overwrite:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{codon.codon_name}_{timestamp}.py"
            filepath = os.path.join(output_dir, filename)
        
        code = self.to_python(codon)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        logger.info(f"Saved codon to {filepath}")
        return filepath
    
    def analyze_only(self, text: str) -> Dict:
        """
        Analyze conversation without generating codon.
        
        Useful for previewing extraction viability.
        """
        thread = self.analyzer.analyze(text)
        trigger = self.pattern_extractor.extract(thread)
        phase = self.phase_mapper.map(thread, {})
        
        return {
            "thread_summary": {
                "total_turns": thread.total_turns,
                "assistant_name": thread.assistant_name,
                "themes": thread.themes,
                "resonance_peaks": thread.resonance_peaks
            },
            "resonance_preview": {
                "felt_conditions": trigger.emotional_signature,
                "surface_patterns": trigger.surface_patterns[:5],
                "confidence": trigger.confidence
            },
            "spiral_preview": {
                "target_angle": phase.target_angle,
                "zone": phase.triadic_zone,
                "phase_name": phase.spiral_position.get("phase"),
                "confidence": phase.confidence
            },
            "overall_viability": {
                "ready_for_extraction": (trigger.confidence + phase.confidence) / 2 > 0.5,
                "architecture": "v3 — No operators"
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
    """Quick function to forge a codon from text."""
    forge = CodonForge()
    codon = forge.extract_from_text(text, codon_name=codon_name)
    
    filepath = None
    if save:
        filepath = forge.save_codon(codon)
    
    return codon, filepath


def preview_extraction(text: str) -> Dict:
    """Quick preview of what would be extracted from text."""
    forge = CodonForge()
    return forge.analyze_only(text)
