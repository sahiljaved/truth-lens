import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  palette: {
    mode: "light",
    primary: { main: "#2563eb" },
    secondary: { main: "#7c3aed" },
    background: { default: "#f1f5f9", paper: "#ffffff" },
  },
  shape: { borderRadius: 12 },
});

export default theme;
