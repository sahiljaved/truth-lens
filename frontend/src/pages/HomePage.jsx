import { Alert, Box, Container, Tab, Tabs, Typography } from "@mui/material";
import { useState } from "react";
import useVerification from "../hooks/useVerification";
import UploadZone from "../components/upload/UploadZone";
import TextInput from "../components/upload/TextInput";
import LoadingOverlay from "../components/shared/LoadingOverlay";
import ResultPanel from "../components/results/ResultPanel";

export default function HomePage() {
  const [tab, setTab] = useState(0);
  const { phase, error, result, submitFile, submitText, reset } = useVerification();
  const busy = ["uploading", "verifying", "polling"].includes(phase);

  return (
    <Container maxWidth="md" sx={{ py: 5 }}>
      <Typography variant="h3" fontWeight={700} gutterBottom>
        Verify news before you share it
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Upload an image, video, or paste text. TruthLens extracts the claim, searches trusted sources, and returns a confidence score.
      </Typography>

      {phase === "idle" || phase === "error" ? (
        <>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
            <Tab label="File upload" />
            <Tab label="Text" />
          </Tabs>
          {tab === 0 ? (
            <UploadZone onSubmit={submitFile} disabled={busy} />
          ) : (
            <TextInput onSubmit={submitText} disabled={busy} />
          )}
        </>
      ) : null}

      {busy && <LoadingOverlay phase={phase} />}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={reset}>
          {String(error)}
        </Alert>
      )}
      {phase === "done" && <ResultPanel result={result} onReset={reset} />}
    </Container>
  );
}
