import { Chip } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HelpIcon from "@mui/icons-material/Help";
import CancelIcon from "@mui/icons-material/Cancel";
import BlockIcon from "@mui/icons-material/Block";

const CONFIG = {
  likely_true: { label: "Likely True", color: "success", icon: <CheckCircleIcon /> },
  uncertain: { label: "Uncertain", color: "warning", icon: <HelpIcon /> },
  likely_false: { label: "Likely False", color: "error", icon: <CancelIcon /> },
  unverifiable: { label: "Unverifiable", color: "default", icon: <BlockIcon /> },
};

export default function VerdictBadge({ verdict }) {
  const cfg = CONFIG[verdict] || CONFIG.uncertain;
  return <Chip icon={cfg.icon} label={cfg.label} color={cfg.color} size="medium" sx={{ fontWeight: 600 }} />;
}
