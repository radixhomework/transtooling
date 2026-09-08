import { useTranslation } from "react-i18next";
import Waveform from "./Waveform.jsx";

export default function StatusBadge({ status, progress }) {
  const { t } = useTranslation();
  let label = t(`status.${status}`, { defaultValue: status });
  if (status === "processing" && Number.isFinite(progress)) {
    label = t("status.processingProgress", { percent: Math.round(progress) });
  }
  return (
    <span className={`badge badge-${status}`}>
      {status === "processing" && <Waveform size="sm" />}
      {label}
    </span>
  );
}
