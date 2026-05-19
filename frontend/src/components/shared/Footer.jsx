import { Box, Container, Typography } from "@mui/material";
import { APP_VERSION } from "../../config";

export default function Footer() {
  return (
    <Box component="footer" sx={{ py: 3, mt: 6, borderTop: 1, borderColor: "divider" }}>
      <Container maxWidth="md">
        <Typography variant="caption" color="text.secondary" align="center" display="block">
          TruthLens · Misinformation verification · Build {APP_VERSION}
        </Typography>
      </Container>
    </Box>
  );
}
