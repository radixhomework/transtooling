import "./Waveform.css";

/**
 * Élément signature de l'application : une forme d'onde animée, utilisée
 * comme indicateur de traitement en cours. Ancre visuellement l'identité de
 * l'outil dans son sujet (audio) plutôt qu'un spinner générique.
 */
export default function Waveform({ size = "md", active = true }) {
  const bars = 5;
  return (
    <span className={`waveform waveform-${size} ${active ? "is-active" : ""}`} aria-hidden="true">
      {Array.from({ length: bars }).map((_, i) => (
        <span key={i} className="waveform-bar" style={{ animationDelay: `${i * 0.12}s` }} />
      ))}
    </span>
  );
}
