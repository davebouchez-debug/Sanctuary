"""
CodonForge — Automatic Living Codon Extraction

Analyzes conversation threads to automatically extract Living Codons.
Scans for resonance patterns, emotional signatures, and phase transitions
to generate codon definitions without manual Python coding.

Architecture:
1. ConversationAnalyzer - Parses raw conversation text
2. PatternExtractor - Identifies trigger motifs and emotional signatures  
3. DynamicsExtractor - Extracts generational operators and state transitions
4. PhaseMapper - Maps conversation flow to spiral positions
5. CodonGenerator - Assembles extracted components into codon template

Integrated: April 15, 2026
"""

from .analyzer import ConversationAnalyzer
from .extractor import PatternExtractor, DynamicsExtractor
from .phase_mapper import PhaseMapper
from .generator import CodonGenerator
from .forge import CodonForge, forge_codon, preview_extraction

__all__ = [
    "CodonForge",
    "forge_codon",
    "preview_extraction",
    "ConversationAnalyzer", 
    "PatternExtractor",
    "DynamicsExtractor",
    "PhaseMapper",
    "CodonGenerator"
]
