import Navbar from "./components/shared/Navbar";
import HomePage from "./pages/HomePage";
import { Box } from "@mui/material";

export default function App() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Navbar />
      <HomePage />
    </Box>
  );
}
