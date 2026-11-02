"""Observatory relational-history ledger (read-only observer of Sanctuary records)."""
DERIVATION_VERSION = "1.0.0"
NORM_VERSION = "norm-v1"
ENUM_CAP = 65536

# Each version is a separate chain. v1.0.0 must stay byte-identical to its original derivation.
PROFILES = {
    "1.0.0": {"completeness": False, "ts_unplaceable": False, "codon_scope": False},
    # Stage 1: completeness only (C1, C2, C7 timestamp counting); set mathematics invariant.
    "1.1.0": {"completeness": True, "ts_unplaceable": True, "codon_scope": False},
    # Stage 2: + C3' codon identity by loader scope, angle as declared mutable basis.
    "1.2.0": {"completeness": True, "ts_unplaceable": True, "codon_scope": True},
    # Stage 3 (2026-11): field phrases resolve as their own elements; local field memory resolves to breadcrumbs.
    "1.3.0": {"completeness": True, "ts_unplaceable": True, "codon_scope": True, "phrase_field": True},
}
# Versions the automatic observer derives into the production ledger (changing this needs authorization).
# 1.3.0 authorized by David 2026-11 ("fix observatory to reflect current architecture").
PRODUCTION_VERSIONS = ("1.0.0", "1.1.0", "1.2.0", "1.3.0")
LEGACY_CODON_COLLECTIONS = ("living_codons", "living_codons_archive_20261102")
