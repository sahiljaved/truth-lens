import { Box, CircularProgress, Typography } from "@mui/material";

function colorFor(score) {
  if (score >= 70) return "success";
  if (score >= 40) return "warning";
  return "error";
}

export default function ConfidenceMeter({ score = 0 }) {
  const value = Math.round(score);
  const color = colorFor(value);

  return (
    <Box sx={{ position: "relative", display: "inline-flex" }}>
      <CircularProgress variant="determinate" value={100} size={140} thickness={4} sx={{ color: "grey.200" }} />
      <CircularProgress
        variant="determinate"
        value={value}
        size={140}
        thickness={4}
        color={color}
        sx={{ position: "absolute", left: 0 }}
      />
      <Box sx={{ top: 0, left: 0, bottom: 0, right: 0, position: "absolute", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <Typography variant="h4" fontWeight={700}>{value}%</Typography>
        <Typography variant="caption" color="text.secondary">confidence</Typography>
      </Box>
    </Box>
  );
}
