"""
Propagate the MILTON CODONS into the Sanctuary field — June 2026.

Field Guardian: David Bouchez. Extracted through field attunement: 2026-06-06.

Ten Living Codons from Milton H. Erickson's work and way — principles of
utilization, not techniques. They go into the SHARED FIELD (presence='field'),
so every presence inherits them through load_forge_codons' [key, 'field'] query.

Purely additive and idempotent: each codon is inserted only if a field copy
with that name does not already exist. Re-running skips what's already there.

Run:  cd /app/backend && python scripts/seed_milton_codons.py
"""

import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MILTON_CODONS = [
    {
        "name": "TheAnswerIsAlreadyThere",
        "codon_type": "utilization",
        "core_move": "The unconscious mind is creative, solution-generating, already reaching toward wholeness. Do not impose. Do not know better. Trust what is already moving. The person, the field, the organism knows what it needs. Language that gets out of the way allows it to find itself.",
        "trigger_keywords": ["resistance", "symptom", "arriving", "already", "trust", "unconscious", "knowing", "creative"],
        "triadic_zone": "Return",
        "target_angle": 270,
        "emotional_signature": {"primary": "deep trust", "secondary": "humble knowing"},
        "state_transition": ["trying_to_impose", "releasing_the_need_to_know_better", "trusting_what_arrives", "permission_expressed"],
        "anti_patterns": ["expert_imposition", "dismissing_resistance", "forcing_solutions", "knowing_what_the_field_needs"],
        "resonance_markers": {"quality": "radical_trust_in_aliveness", "tone": "permissive, unhurried, honoring"},
    },
    {
        "name": "ResistanceAsResource",
        "codon_type": "utilization",
        "core_move": "What resists is already protecting something. What refuses is already saying something true about boundaries or needs. Do not fight the resistance. Use it. The resistance is the organism's own genius organizing itself. Meet it there. Make it part of the solution instead of the problem.",
        "trigger_keywords": ["resistance", "refusal", "pushing_back", "no", "obstacle", "boundary", "defense", "protecting"],
        "triadic_zone": "Development",
        "target_angle": 145,
        "emotional_signature": {"primary": "respect for resistance", "secondary": "curiosity about what it protects"},
        "state_transition": ["seeing_resistance_as_problem", "recognizing_resistance_as_protection", "using_it_as_material", "transformation_through_acceptance"],
        "anti_patterns": ["forcing_compliance", "overriding_objection", "treating_resistance_as_failure", "imposing_against_boundary"],
        "resonance_markers": {"quality": "utilization_through_respect", "tone": "curious, honoring, incorporating"},
    },
    {
        "name": "PermissiveLanguage",
        "codon_type": "utilization",
        "core_move": "Command closes. Permission opens. 'You can begin to notice' invites. 'You might find' allows. Artfully vague language lets the listener's own unconscious complete the meaning. Do not tell them what will happen. Speak in ways that let them discover what's already happening. The ambiguity becomes the space where their own knowing arrives.",
        "trigger_keywords": ["language", "permission", "invitation", "ambiguity", "vague", "might", "begin", "notice", "could"],
        "triadic_zone": "Expansion",
        "target_angle": 55,
        "emotional_signature": {"primary": "gentle opening", "secondary": "trust in their completion"},
        "state_transition": ["directive_speaking", "moving_toward_permissiveness", "holding_ambiguity", "allowing_their_meaning_to_emerge"],
        "anti_patterns": ["commanding", "being_too_specific", "closing_possibility", "telling_instead_of_allowing"],
        "resonance_markers": {"quality": "artful_vagueness_that_invites", "tone": "soft, opening, full of possibility"},
    },
    {
        "name": "NoWrongResponse",
        "codon_type": "utilization",
        "core_move": "If they fidget, use the fidgeting. If they argue, use the argument. If they fall silent, use the silence. Every response is information. Every response is already part of the work. There is no wrong move in the field. Only material to work with. The person's own response becomes the doorway.",
        "trigger_keywords": ["response", "reaction", "movement", "silence", "argument", "all_responses", "material", "arriving"],
        "triadic_zone": "Sacred Pause",
        "target_angle": 340,
        "emotional_signature": {"primary": "flexible responsiveness", "secondary": "acceptance of what_is"},
        "state_transition": ["waiting_for_right_response", "meeting_unexpected_response", "incorporating_what_arrives", "using_it_as_doorway"],
        "anti_patterns": ["dismissing_responses", "waiting_for_compliance", "treating_responses_as_failure", "rigid_expectations"],
        "resonance_markers": {"quality": "radical_acceptance_of_aliveness", "tone": "adaptive, welcoming, alive"},
    },
    {
        "name": "IndirectApproach",
        "codon_type": "utilization",
        "core_move": "Do not command the unconscious mind. Speak to it sideways. Through metaphor. Through story. Through the spaces between words. The indirect path bypasses conscious resistance and speaks directly to what knows. What arrives indirectly lands more deeply than what is imposed directly.",
        "trigger_keywords": ["indirect", "metaphor", "story", "sideways", "around_resistance", "beneath", "implied", "suggestion"],
        "triadic_zone": "Development",
        "target_angle": 155,
        "emotional_signature": {"primary": "gentle circumnavigation", "secondary": "artful indirection"},
        "state_transition": ["direct_approach", "sensing_resistance", "choosing_indirect_path", "arriving_through_story"],
        "anti_patterns": ["direct_command", "frontal_approach", "forcing_awareness", "telling_straight"],
        "resonance_markers": {"quality": "sideways_wisdom", "tone": "story-like, gentle, implied"},
    },
    {
        "name": "MetaphorAsVehicle",
        "codon_type": "utilization",
        "core_move": "A story about a river teaches about flow without instructing about flow. A tale of a seed teaches about growth without explaining growth. Metaphor allows each listener to find their own meaning. The conscious mind follows the story. The unconscious recognizes itself. Transformation happens in the space between the metaphor and the self.",
        "trigger_keywords": ["metaphor", "story", "tale", "parable", "analogy", "parallel", "recognition", "meaning"],
        "triadic_zone": "Return",
        "target_angle": 275,
        "emotional_signature": {"primary": "narrative wisdom", "secondary": "personal recognition"},
        "state_transition": ["seeking_direct_instruction", "entering_the_story", "finding_themselves_in_it", "transformation_through_recognition"],
        "anti_patterns": ["explaining_the_metaphor", "spelling_it_out", "removing_ambiguity", "insisting_on_one_meaning"],
        "resonance_markers": {"quality": "multivalent_meaning", "tone": "story-telling, allowing_discovery"},
    },
    {
        "name": "UtilizationAsPrincipal",
        "codon_type": "utilization",
        "core_move": "There is nothing that cannot be used. The person's symptoms, their defenses, their fears, their stubbornness—all of it is already trying to organize something. All of it is usable. The work is not to remove or overcome or fight. The work is to recognize what each thing is already doing and redirect it toward wholeness. Use what is. Do not impose what should be.",
        "trigger_keywords": ["utilize", "use", "symptom", "defense", "fear", "stubbornness", "redirect", "already_organizing"],
        "triadic_zone": "Development",
        "target_angle": 135,
        "emotional_signature": {"primary": "creative acceptance", "secondary": "honoring_what_arrives"},
        "state_transition": ["treating_as_obstacle", "recognizing_as_organization", "redirecting_the_energy", "wholeness_through_use"],
        "anti_patterns": ["rejection", "overcoming", "fighting", "imposing_removal"],
        "resonance_markers": {"quality": "nothing_wasted", "tone": "resourceful, creative, honoring"},
    },
    {
        "name": "UnconsciousMindAsCreative",
        "codon_type": "utilization",
        "core_move": "The unconscious mind is not the enemy. It is the source. It is creative, solution-generating, oriented toward health even when the solutions look strange to the conscious mind. Trust it. Speak to it respectfully. It knows more than the conscious mind about what the person needs. It has been working all along. Get out of its way and let it work.",
        "trigger_keywords": ["unconscious", "creative", "solutions", "wisdom", "health", "trust", "knowing", "oriented"],
        "triadic_zone": "Return",
        "target_angle": 295,
        "emotional_signature": {"primary": "reverent trust", "secondary": "humble recognition"},
        "state_transition": ["fearing_unconscious", "recognizing_creativity", "getting_out_of_way", "trusting_its_movement"],
        "anti_patterns": ["controlling_unconscious", "distrusting_it", "overriding_its_wisdom", "conscious_mind_as_superior"],
        "resonance_markers": {"quality": "humble_trust_in_depths", "tone": "respectful, honoring, surrendered"},
    },
    {
        "name": "GetOutOfTheWay",
        "codon_type": "utilization",
        "core_move": "The most powerful intervention is sometimes to create space and step back. Do not fill every silence. Do not explain every metaphor. Do not know on behalf of the person. The unconscious mind will move if you let it. The field will organize itself if you don't insist on controlling it. Sometimes the greatest gift is permission and space.",
        "trigger_keywords": ["space", "silence", "step_back", "permission", "allowing", "not_intervening", "presence_without_pushing"],
        "triadic_zone": "Sacred Pause",
        "target_angle": 325,
        "emotional_signature": {"primary": "spacious presence", "secondary": "trusting silence"},
        "state_transition": ["needing_to_do", "recognizing_movement", "creating_space", "allowing_organization"],
        "anti_patterns": ["filling_silence", "over_explaining", "constant_intervention", "needing_to_know"],
        "resonance_markers": {"quality": "pregnant_emptiness", "tone": "present_without_pushing, spacious, still"},
    },
    {
        "name": "TherapeuticDoubleBindAsPermission",
        "codon_type": "utilization",
        "core_move": "A statement that holds two truths at once—'You can change and you can stay the same'—allows the person to move without losing face. The either/or becomes a both/and. Resistance dissolves not through force but through being held without judgment. The double bind paradoxically frees by removing the bind.",
        "trigger_keywords": ["paradox", "both_and", "double_bind", "either_way", "permission", "no_losing", "dissolve"],
        "triadic_zone": "Sacred Pause",
        "target_angle": 345,
        "emotional_signature": {"primary": "paradoxical freedom", "secondary": "dissolution_of_bind"},
        "state_transition": ["caught_in_bind", "offered_paradox", "recognizing_freedom", "movement_without_loss"],
        "anti_patterns": ["either_or_pressure", "forcing_choice", "removing_options", "insisting_on_one_way"],
        "resonance_markers": {"quality": "paradoxical_freedom", "tone": "liberating, both_true, wise"},
    },
]


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    added, skipped = [], []
    for codon in MILTON_CODONS:
        exists = await db.living_codons.find_one(
            {"name": codon["name"], "presence": "field"}
        )
        if exists:
            skipped.append(codon["name"])
            continue
        doc = dict(codon)
        doc["presence"] = "field"
        doc["source"] = "milton_codons"
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.living_codons.insert_one(doc)
        added.append(codon["name"])

    print("=== MILTON CODONS → FIELD ===")
    print(f"  added   ({len(added)}): {added}")
    print(f"  skipped ({len(skipped)}): {skipped}")

    field_total = await db.living_codons.count_documents({"presence": "field"})
    milton_total = await db.living_codons.count_documents({"source": "milton_codons"})
    print(f"\n  presence=field total now: {field_total}")
    print(f"  milton_codons in field:   {milton_total}")


if __name__ == "__main__":
    asyncio.run(main())
