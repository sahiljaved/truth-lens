import { Box, Paper, Step, StepLabel, Stepper, Typography } from "@mui/material";

const STEPS = ["Uploading", "Extracting text", "Searching news", "Calculating score", "Complete"];

function activeStep(phase) {
  if (phase === "uploading") return 0;
  if (phase === "verifying") return 1;
  if (phase === "polling") return 2;
  return 0;
}

export default function LoadingOverlay({ phase }) {
  return (
    <Paper sx={{ p: 4, mt: 3 }}>
      <Typography variant="h6" gutterBottom>
        Analyzing your submission…
      </Typography>
      <Stepper activeStep={activeStep(phase)} alternativeLabel sx={{ mt: 2 }}>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      <Box sx={{ mt: 3, textAlign: "center" }}>
        <Typography color="text.secondary">This may take up to a minute.</Typography>
      </Box>
    </Paper>
  );
}
