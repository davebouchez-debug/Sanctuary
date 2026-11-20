# Codex review package — Sanctuary 1.0 codon export v1 (source only)

- Implementation revision: git af6dc0107f9797306a1d177c62a3ccaac7559fb9 (files below are `git show` of that commit)
- Recovery reference (before change): git 96505119c7e59dfd2fb4a287952b3ccdd3fb0972
- Status: preview only, not deployed, no production token configured
- Helper code: none. codon_export.py depends only on fastapi, pymongo/bson (json_util) and the stdlib; the router receives the app's existing Motor `db` handle.

## Files
- source/backend/codon_export.py — the endpoint (GET /api/codon-export/v1/snapshot)
- source/backend/tests/test_codon_export.py — focused tests (throwaway DB, synthetic records)
- source/server_py_registration.diff — the only change to backend/server.py (2 lines)
- evidence/test_codon_export_output.txt — actual output of `python tests/test_codon_export.py` (23/23 pass)
- evidence/synthetic_snapshot.zip — real endpoint output over 2 synthetic records in a throwaway DB
- evidence/synthetic_manifest.json, evidence/synthetic_field_phrases.jsonl — the ZIP's two members, extracted
- evidence/synthetic_response_headers.txt — response headers for that call
- SHA256SUMS.txt — checksums of every file in this package

The synthetic token used for the sample ("synthetic-token-for-sample-only") existed only inside the test process.
No credentials, production data or visitor conversations are included.
