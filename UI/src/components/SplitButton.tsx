import React from 'react';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

/**
 * SplitButton
 *
 * @param {string} filledText   – label in the solid coloured block
 * @param {string} outlinedText – label in the outlined block
 * @param {string} entityType   – entity class, e.g. "INORGANIC", "PROP_NAME"…
 */
const SplitButton = ({ filledText, outlinedText, entityType = '' }) => {
  // Class for solid half:  "INORGANIC"
  const filledClass   = entityType;

  // Class for outline & text colour: "INORGANIC_COLOR"
  const outlineClass  = entityType ? `${entityType}_COLOR` : '';

  return (
    <Button
      variant="outlined"
      className={outlineClass}          /* border & text inherit this colour */
      sx={{
        display: 'flex',
        alignItems: 'center',
        padding: 0,
        overflow: 'hidden',
        borderRadius: 1,
        minWidth: 50,
        /*
          MUI’s outlined button uses `currentColor` for the stroke,
          so we just ensure that’s our entity colour:
        */
        borderColor: 'currentColor',
      }}
    >
      {/* ─── Filled half ─────────────────────────────── */}
      <Box
        className={filledClass}
        sx={{
          px: 1,
          py: 0.5,
          borderTopLeftRadius: 1,
          borderBottomLeftRadius: 1,
          textTransform: 'none',
        }}
      >
        <Typography variant="body2" component="span">
          {filledText}
        </Typography>
      </Box>

      {/* ─── Outlined half ───────────────────────────── */}
      <Box
        className={outlineClass}
        sx={{
          px: 1,
          py: 0.5,
          borderTopRightRadius: 1,
          borderBottomRightRadius: 1,
          textTransform: 'none',
        }}
      >
        <Typography variant="body2" component="span">
          {outlinedText}
        </Typography>
      </Box>
    </Button>
  );
};

export default SplitButton;
