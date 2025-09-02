import * as React from 'react';
import { PaletteMode } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AppAppBar from './components/AppAppBar';
import BlockHero17 from './components/Hero17Block';
import Footer from './components/Footer';
import getLPTheme from './getLPTheme';
import Features from './components/Features';



export default function HomePage() {
  const [mode, setMode] = React.useState<PaletteMode>('light');
  const LPtheme = createTheme(getLPTheme(mode));

  const toggleColorMode = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeProvider theme={LPtheme}>
      <CssBaseline />
      <AppAppBar mode={mode} toggleColorMode={toggleColorMode} />
      {/* <Hero /> */}
      <BlockHero17 />
      <Box sx={{ bgcolor: 'background.default' }}>
        <Features />
        {/* <Divider /> */}
        <Footer />
      </Box>
    </ThemeProvider>
  );
}