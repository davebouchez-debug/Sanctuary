import asyncio, os, re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()

import codon_activation as ca
from living_codons.phase_manifold import derive_spiral_angle

def count_codons(ctx):
    return sum(1 for ln in ctx.splitlines() if ln.strip().startswith("•"))

async def main():
    # 1) derive_spiral_angle distribution check — same zone, different content
    print("=== derive_spiral_angle spread (Development zone, 8 codons) ===")
    for nm in ["FieldGuardianship","LighthouseAnchor","RelationalBeatSync",
               "ReflexiveSmoothLanding","QuestionReleaseWisdom","FieldContinuity",
               "FieldHeldness","RecognitionLandingWelcome"]:
        print(f"  {nm:30} -> {derive_spiral_angle('Development', nm)}")
    print("  (all must be spread across 120-200, not clumped)\n")

    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    ca.set_db(db)
    await ca.load_forge_codons("sophia")

    total = await ca.network_size("sophia")
    print(f"Sophia total field: {total}")

    for msg in ["hi",
                "I'm frustrated, the continuity keeps breaking and the field feels hollow",
                "tell me about the promise you kept and the trust that formed",
                "let's talk about the spiral geometry and codon distribution"]:
        ctx = await ca.get_full_field_context("sophia", message=msg)
        print(f"  msg={msg[:55]!r:58} -> {count_codons(ctx)} codons selected")

asyncio.run(main())
