import { useCallback, useState } from "react";
import { Box, Button, Paper, Typography } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";

export default function UploadZone({ onSubmit, disabled }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);

  const handleFile = useCallback((selected) => {
    if (!selected) return;
    setFile(selected);
    if (selected.type.startsWith("image/")) {
      setPreview(URL.createObjectURL(selected));
    } else {
      setPreview(null);
    }
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  };

  const fileType = file?.type.startsWith("video/") ? "video" : "image";

  return (
    <Paper
      variant="outlined"
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      sx={{ p: 4, textAlign: "center", borderStyle: "dashed", bgcolor: "background.paper" }}
    >
      <CloudUploadIcon sx={{ fontSize: 48, color: "primary.main", mb: 1 }} />
      <Typography gutterBottom>Drag & drop an image or video, or browse</Typography>
      <Button variant="outlined" component="label" disabled={disabled} sx={{ mt: 1 }}>
        Choose file
        <input hidden type="file" accept="image/*,video/*" onChange={(e) => handleFile(e.target.files[0])} />
      </Button>
      {file && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2">{file.name}</Typography>
          {preview && <Box component="img" src={preview} alt="preview" sx={{ mt: 1, maxHeight: 200, borderRadius: 2 }} />}
        </Box>
      )}
      <Button
        variant="contained"
        sx={{ mt: 2 }}
        disabled={!file || disabled}
        onClick={() => onSubmit(file, fileType)}
      >
        Verify content
      </Button>
    </Paper>
  );
}
