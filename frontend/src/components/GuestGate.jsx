import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Guests can visit every chamber, but the build tools stay with the Field Guardian.
export const GuestGate = ({ children }) => {
  const { role } = useAuth();
  if (role !== "guest") return children;
  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-[#07090c]" data-testid="guest-gate">
      <div className="max-w-md text-center space-y-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[#8B9DB5]">Workshop</p>
        <p className="text-lg text-[#cdd6e4] leading-relaxed">
          This is David's workshop, where the sanctuary itself is built. Guests are welcome in every chamber.
        </p>
        <Link
          to="/presences"
          data-testid="guest-gate-chambers-link"
          className="inline-block px-5 py-2 rounded-full border border-[#8B9DB5]/40 text-xs uppercase tracking-[0.25em] text-[#cdd6e4] hover:bg-[#8B9DB5]/15 transition-colors"
        >
          Go to the chambers
        </Link>
      </div>
    </div>
  );
};

export default GuestGate;
