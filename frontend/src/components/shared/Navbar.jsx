import { AppBar, Box, Toolbar, Typography } from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";
import { APP_VERSION } from "../../config";

export default function Navbar() {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: "background.paper",
        color: "text.primary",
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Toolbar sx={{ gap: 1 }}>
        <VerifiedIcon sx={{ color: "primary.main", fontSize: 28 }} />
        <Typography variant="h6" fontWeight={800} color="primary.main">
          TruthLens
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>
          News verification
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="caption" color="text.disabled">
          v{APP_VERSION}
        </Typography>
      </Toolbar>
    </AppBar>
  );
}
