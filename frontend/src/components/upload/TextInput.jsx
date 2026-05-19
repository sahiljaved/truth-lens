import { useState } from "react";
import { Box, Button, LinearProgress, Paper, TextField, Typography } from "@mui/material";

const MAX = 50000;

export default function TextInput({ onSubmit, disabled }) {
  const [text, setText] = useState("");

  return (
    <Paper sx={{ p: 3 }}>
      <TextField
        fullWidth
        multiline
        minRows={8}
        placeholder="Paste a claim or news snippet to verify…"
        value={text}
        disabled={disabled}
        onChange={(e) => setText(e.target.value.slice(0, MAX))}
      />
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          {text.length.toLocaleString()} / {MAX.toLocaleString()}
        </Typography>
        <LinearProgress variant="determinate" value={(text.length / MAX) * 100} sx={{ flex: 1, height: 6, borderRadius: 3 }} />
        <Button variant="contained" disabled={!text.trim() || disabled} onClick={() => onSubmit(text.trim())}>
          Verify text
        </Button>
      </Box>
    </Paper>
  );
}
