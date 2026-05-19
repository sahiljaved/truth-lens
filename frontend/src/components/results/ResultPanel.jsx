import { Accordion, AccordionDetails, AccordionSummary, Box, Button, Paper, Typography } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ConfidenceMeter from "./ConfidenceMeter";
import VerdictBadge from "./VerdictBadge";
import SourceCard from "./SourceCard";
import FlagList from "./FlagList";

export default function ResultPanel({ result, onReset }) {
  if (!result) return null;

  return (
    <Paper sx={{ p: 4, mt: 3 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 3, alignItems: "center", mb: 3 }}>
        <ConfidenceMeter score={result.score_percent ?? result.confidence_score * 100} />
        <Box>
          <VerdictBadge verdict={result.verdict} />
          <Typography variant="body1" sx={{ mt: 2, maxWidth: 560 }}>
            {result.summary}
          </Typography>
        </Box>
      </Box>
      <FlagList flags={result.flags} />
      {result.sources?.length > 0 && (
        <Accordion sx={{ mt: 2 }} defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight={600}>Sources ({result.sources.length})</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {result.sources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </AccordionDetails>
        </Accordion>
      )}
      <Button variant="outlined" sx={{ mt: 3 }} onClick={onReset}>
        Verify another
      </Button>
    </Paper>
  );
}
