import { Box, Chip, Tooltip, Typography } from "@mui/material";

const SEVERITY_COLOR = {
  LOW: "default",
  MEDIUM: "warning",
  HIGH: "error",
  CRITICAL: "error",
};

export default function FlagList({ flags = [] }) {
  if (!flags.length) return null;

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" gutterBottom>Flags</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
        {flags.map((flag, i) => (
          <Tooltip key={i} title={flag.detail || flag.type}>
            <Chip label={flag.type} color={SEVERITY_COLOR[flag.severity] || "default"} size="small" />
          </Tooltip>
        ))}
      </Box>
    </Box>
  );
}
