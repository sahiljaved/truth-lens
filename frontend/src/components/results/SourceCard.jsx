import { Box, Card, CardContent, Chip, LinearProgress, Link, Typography } from "@mui/material";

export default function SourceCard({ source }) {
  const weight = Math.round((source.credibility_weight || 0) * 100);

  return (
    <Card variant="outlined" sx={{ mb: 1 }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography fontWeight={600}>{source.name}</Typography>
          <Box sx={{ display: "flex", gap: 0.5 }}>
            {source.source_type && (
              <Chip label={source.source_type.replace(/_/g, " ")} size="small" variant="outlined" />
            )}
            {source.is_trusted && <Chip label="Trusted" size="small" color="success" />}
          </Box>
        </Box>
        {source.url && (
          <Link href={source.url} target="_blank" rel="noopener" variant="body2">
            {source.url}
          </Link>
        )}
        {source.snippet && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {source.snippet}
          </Typography>
        )}
        <Box sx={{ mt: 1 }}>
          <Typography variant="caption">Credibility</Typography>
          <LinearProgress variant="determinate" value={weight} sx={{ mt: 0.5, height: 6, borderRadius: 3 }} />
        </Box>
      </CardContent>
    </Card>
  );
}
