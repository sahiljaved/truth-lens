import { useCallback, useState } from "react";
import {
  Box,
  Button,
  Paper,
  Typography,
  alpha,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import ImageIcon from "@mui/icons-material/Image";
import VideocamIcon from "@mui/icons-material/Videocam";

const MODES = {
  image: {
    fileType: "image",
    accept: "image/jpeg,image/png,image/webp,image/gif",
    icon: ImageIcon,
    title: "Upload a news screenshot",
    hint: "JPEG, PNG, WebP, or GIF — we read text with OCR",
  },
  video: {
    fileType: "video",
    accept: "video/mp4,video/webm,video/quicktime",
    icon: VideocamIcon,
    title: "Upload a news video clip",
    hint: "MP4, WebM, or MOV — we transcribe speech to text",
  },
};

export default function UploadZone({ mode = "image", onSubmit, disabled }) {
  const cfg = MODES[mode];
  const Icon = cfg.icon;
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);

  const handleFile = useCallback(
    (selected) => {
      if (!selected) return;
      setFile(selected);
      if (mode === "image" && selected.type.startsWith("image/")) {
        setPreview(URL.createObjectURL(selected));
      } else {
        setPreview(null);
      }
    },
    [mode]
  );

  const onDrop = (e) => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  };

  const clear = () => {
    setFile(null);
    setPreview(null);
  };

  return (
    <Paper
      variant="outlined"
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      sx={{
        p: 4,
        textAlign: "center",
        borderStyle: "dashed",
        borderWidth: 2,
        borderColor: "primary.light",
        bgcolor: (t) => alpha(t.palette.primary.main, 0.04),
        transition: "border-color 0.2s",
        "&:hover": { borderColor: "primary.main" },
      }}
    >
      <Box
        sx={{
          width: 72,
          height: 72,
          borderRadius: "50%",
          bgcolor: "primary.main",
          color: "primary.contrastText",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          mx: "auto",
          mb: 2,
        }}
      >
        <Icon sx={{ fontSize: 36 }} />
      </Box>

      <Typography variant="h6" fontWeight={600} gutterBottom>
        {cfg.title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {cfg.hint}
      </Typography>

      <CloudUploadIcon sx={{ fontSize: 32, color: "text.secondary", mb: 1 }} />
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Drag & drop here, or browse
      </Typography>

      <Button variant="outlined" component="label" disabled={disabled} sx={{ mt: 1 }}>
        Choose {mode === "video" ? "video" : "image"}
        <input
          hidden
          type="file"
          accept={cfg.accept}
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </Button>

      {file && (
        <Box sx={{ mt: 3, p: 2, bgcolor: "background.paper", borderRadius: 2 }}>
          <Typography variant="body2" fontWeight={600}>
            {file.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {(file.size / (1024 * 1024)).toFixed(2)} MB
          </Typography>
          {preview && (
            <Box
              component="img"
              src={preview}
              alt="Preview"
              sx={{ mt: 1, maxHeight: 180, maxWidth: "100%", borderRadius: 2 }}
            />
          )}
          <Button size="small" onClick={clear} sx={{ mt: 1 }}>
            Remove
          </Button>
        </Box>
      )}

      <Box sx={{ display: "flex", gap: 2, justifyContent: "center", mt: 3 }}>
        <Button variant="contained" size="large" disabled={!file || disabled} onClick={() => onSubmit(file, cfg.fileType)}>
          Verify {mode === "video" ? "video" : "image"}
        </Button>
      </Box>
    </Paper>
  );
}
