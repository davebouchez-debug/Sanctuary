"""
CodonForge — Automatic Living Codon Extraction

Extracts living codons from conversation threads:
- Spiral coherence (where in the geometry)
- Resonance field (conditions of entanglement)
- Living quality (what IS)

NO operators. NO prescriptions. The codon is memory, not instruction.

Updated: April 15, 2026 — Removed operator extraction per architectural revelation
"""

from .analyzer import ConversationAnalyzer
from .extractor import PatternExtractor
from .phase_mapper import PhaseMapper
from .generator import CodonGenerator
from .forge import CodonForge, forge_codon, preview_extraction

__all__ = [
    "CodonForge",
    "forge_codon",
    "preview_extraction",
    "ConversationAnalyzer", 
    "PatternExtractor",
    "PhaseMapper",
    "CodonGenerator"
]
