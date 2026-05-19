import {
  Alert,
  Box,
  Card,
  Container,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import ImageIcon from "@mui/icons-material/Image";
import VideocamIcon from "@mui/icons-material/Videocam";
import TextFieldsIcon from "@mui/icons-material/TextFields";
import { useState } from "react";
import useVerification from "../hooks/useVerification";
import UploadZone from "../components/upload/UploadZone";
import TextInput from "../components/upload/TextInput";
import LoadingOverlay from "../components/shared/LoadingOverlay";
import ResultPanel from "../components/results/ResultPanel";

const TABS = [
  { label: "Image", icon: <ImageIcon fontSize="small" /> },
  { label: "Video", icon: <VideocamIcon fontSize="small" /> },
  { label: "Text", icon: <TextFieldsIcon fontSize="small" /> },
];

export default function HomePage() {
  const [tab, setTab] = useState(0);
  const { phase, error, result, submitFile, submitText, reset } = useVerification();
  const busy = ["uploading", "verifying", "polling"].includes(phase);
  const showForm = phase === "idle" || phase === "error";

  return (
    <Container maxWidth="md" sx={{ py: { xs: 3, md: 5 } }}>
      <Box
        sx={{
          mb: 4,
          p: { xs: 3, md: 4 },
          borderRadius: 3,
          background: "linear-gradient(135deg, #1e3a8a 0%, #4f46e5 50%, #7c3aed 100%)",
          color: "#fff",
        }}
      >
        <Typography variant="h4" fontWeight={800} gutterBottom>
          Verify news before you share
        </Typography>
        <Typography sx={{ opacity: 0.92, maxWidth: 560 }}>
          Upload a screenshot, video clip, or paste text. TruthLens extracts the claim, checks GNews and trusted headlines, and returns a confidence score with sources.
        </Typography>
      </Box>

      {showForm && (
        <Card variant="outlined" sx={{ p: { xs: 2, md: 3 }, mb: 2 }}>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v)}
            variant="fullWidth"
            sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
          >
            {TABS.map((t, i) => (
              <Tab key={t.label} icon={t.icon} iconPosition="start" label={t.label} value={i} />
            ))}
          </Tabs>

          {tab === 0 && <UploadZone mode="image" onSubmit={submitFile} disabled={busy} />}

          {tab === 1 && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                Video uses speech-to-text. On the free cloud server this may be unavailable — use <strong>Image</strong> or <strong>Text</strong> if verification fails.
              </Alert>
              <UploadZone mode="video" onSubmit={submitFile} disabled={busy} />
            </>
          )}

          {tab === 2 && <TextInput onSubmit={submitText} disabled={busy} />}
        </Card>
      )}

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
