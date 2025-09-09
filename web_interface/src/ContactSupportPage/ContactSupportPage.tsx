import React, { useState } from 'react';
import { PaletteMode } from '@mui/material';
import {
  ThemeProvider,
  createTheme,
} from '@mui/material/styles';
import {
  CssBaseline,
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Snackbar,
  Alert,
} from '@mui/material';
import axios from 'axios';
import LoadingOverlay from 'react-loading-overlay-ts';

import getLPTheme from '../HomePage/getLPTheme';
import AppAppBar from '../HomePage/components/AppAppBar';

export default function ContactSupportPage() {
  const [mode, setMode] = useState<PaletteMode>('light');
  const [showCustomTheme, setShowCustomTheme] = useState(true);

  const LPtheme = createTheme(getLPTheme(mode));
  const defaultTheme = createTheme({ palette: { mode } });

  const toggleColorMode = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isActive, setIsActive] = useState(false);

  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [notification, setNotification] = useState('');
  const [notificationSeverity, setNotificationSeverity] = useState<'success' | 'error'>('success');

  const handleCloseSnackbar = (
    event?: React.SyntheticEvent | Event,
    reason?: string
  ) => {
    if (reason === 'clickaway') return;
    setOpenSnackbar(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsActive(true);
    try {
      const response = await axios.post(`${import.meta.env.VITE_PDF_BACKEND_URL}/contact-support`, {
        name,
        email,
        content: message,
      });
      
      if (response.data.msg === 'done') {
        setNotification('Thank you! Your message has been sent.');
        setNotificationSeverity('success');
        setName('');
        setEmail('');
        setMessage('');
      } else {
        throw new Error('Email sending failed');
      }
    } catch (error) {
      console.error('Error sending support message:', error);
      setNotification('Oops! Something went wrong. Please try again.');
      setNotificationSeverity('error');
    }
    setIsActive(false);
    setOpenSnackbar(true);
  };

  return (
    <LoadingOverlay
      active={isActive}
      spinner
      text='Processing ...'
      styles={{
        overlay: (base) => ({
          ...base,
          position: 'fixed',
          width: '100vw',
          height: '100vh',
          top: 0,
          left: 0,
          zIndex: 9999,
        }),
      }}
    >
      <ThemeProvider theme={showCustomTheme ? LPtheme : defaultTheme}>
        <CssBaseline />
        <AppAppBar mode={mode} toggleColorMode={toggleColorMode} />

          <Box
            sx={{
              bgcolor: 'background.default',
              color: 'text.primary',
              minHeight: '100vh',
              py: 4,
              mt: 12,
            }}
          >
            <Container maxWidth="sm">
              <Typography variant="h4" gutterBottom>
                How can we help?
              </Typography>

              <Box component="form" onSubmit={handleSubmit}>
                <TextField
                  label="Your Name"
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />

                <TextField
                  label="Your Email Address"
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />

                <TextField
                  label="How can we help?"
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  multiline
                  rows={6}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                />

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                  <Button type="submit" variant="contained">
                    Send Message
                  </Button>
                </Box>
              </Box>
            </Container>
          </Box>

        <Snackbar
          open={openSnackbar}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert
            onClose={handleCloseSnackbar}
            severity={notificationSeverity}
            sx={{ width: '100%' }}
          >
            {notification}
          </Alert>
        </Snackbar>
      </ThemeProvider>
    </LoadingOverlay>
  );
}
