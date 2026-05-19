import { Box, Container, Typography } from "@mui/material";
import { APP_VERSION } from "../../config";

export default function Footer() {
  return (
    <Box component="footer" sx={{ py: 3, mt: 6, borderTop: 1, borderColor: "divider" }}>
      <Container maxWidth="md">
        <Typography variant="caption" color="text.secondary" align="center" display="block">
          TruthLens · Misinformation verification · Build {APP_VERSION}
        </Typography>
        <Typography variant="caption" color="text.disabled" align="center" display="block" sx={{ mt: 0.5 }}>
          If you see &quot;Show history&quot; or a different layout, the wrong site is deployed — redeploy from the <code>frontend</code> folder.
        </Typography>
      </Container>
    </Box>
  );
}
