import Waveform from "./Waveform.jsx";

const LABELS = {
  pending: "En attente",
  processing: "En cours",
  cancelling: "Annulation…",
  done: "Terminée",
  error: "Erreur",
  cancelled: "Annulée",
};

export default function StatusBadge({ status, progress }) {
  let label = LABELS[status] || status;
  if (status === "processing" && Number.isFinite(progress)) {
    label = `En cours · ${Math.round(progress)}%`;
  }
  return (
    <span className={`badge badge-${status}`}>
      {status === "processing" && <Waveform size="sm" />}
      {label}
    </span>
  );
}
