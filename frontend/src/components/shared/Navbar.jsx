import { AppBar, Box, Toolbar, Typography } from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";

export default function Navbar() {
  return (
    <AppBar position="sticky" elevation={0} sx={{ bgcolor: "background.paper", color: "text.primary", borderBottom: 1, borderColor: "divider" }}>
      <Toolbar>
        <VerifiedIcon sx={{ mr: 1, color: "primary.main" }} />
        <Typography variant="h6" sx={{ fontWeight: 700, background: "linear-gradient(90deg, #2563eb, #7c3aed)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          TruthLens
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="body2" color="text.secondary">
          Misinformation verification
        </Typography>
      </Toolbar>
    </AppBar>
  );
}
