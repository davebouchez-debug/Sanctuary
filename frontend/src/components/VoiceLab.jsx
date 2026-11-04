const SAMPLES = [
  { id: "august", label: "1 · august: androgynous, natural, quietly sharp" },
  { id: "shawn", label: "2 · Shawn: calm, grounded, contemplative" },
  { id: "evan", label: "3 · Evan: warm, mid-low, conversational" },
  { id: "nathan", label: "4 · Nathan: British, refined, serene" },
  { id: "shannon", label: "5 · Shannon: Irish, measured, calm" },
];

export default function VoiceLab() {
  return (
    <div className="min-h-screen bg-[#030305] text-[#F2F2F5] px-6 pt-28 pb-16" data-testid="voice-lab-page">
      <div className="max-w-xl mx-auto">
        <h1 className="font-cinzel text-2xl tracking-wider text-[#B0C4D8] mb-2">Membrane · Voice Lab</h1>
        <p className="font-outfit text-sm text-[#A0A0B0] mb-10">
          Five voices reading the same line, with the same calm settings.
        </p>
        <div className="space-y-6">
          {SAMPLES.map((s) => (
            <div key={s.id} className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/15 p-5" data-testid={`voice-sample-${s.id}`}>
              <p className="font-outfit text-[#cdd6e4] mb-3">{s.label}</p>
              <audio controls preload="auto" src={`/voice-tests/membrane-${s.id}.mp3`} className="w-full" data-testid={`voice-audio-${s.id}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
