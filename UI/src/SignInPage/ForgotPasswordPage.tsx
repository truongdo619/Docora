import * as React from 'react';
import {
  Box,
  Button,
  CssBaseline,
  Grid,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useNavigate } from 'react-router-dom';
import LoadingOverlay from 'react-loading-overlay-ts';
import background from '../assets/images/scott-webb-hDyO6rr3kqk-unsplash.jpg';
import axios from 'axios';

const defaultTheme = createTheme();

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = React.useState('');
  const [message, setMessage] = React.useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isActive, setIsActive] = React.useState(false); // State to control the overlay spinner

  const handleSubmit = async () => {
    setIsActive(true); // Show the loading spinner
    try {
      const response = await axios.post(
        `${import.meta.env.VITE_BACKEND_URL}/forget-password/`,
        { email }
      );
      setMessage({
        type: 'success',
        text: 'An email with password reset instructions has been sent! Redirecting to sign-in page...',
      });

      setTimeout(() => {
        navigate('/signin');
      }, 2000);
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Failed to send password reset instructions. Please try again.',
      });
    } finally {
      setIsActive(false); // Hide the loading spinner
    }
  };

  return (
    <LoadingOverlay
      active={isActive}
      spinner
      text="Processing..."
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
      <ThemeProvider theme={defaultTheme}>
        <Grid container component="main" sx={{ height: '100vh' }}>
          <CssBaseline />

          <Grid
            item
            xs={false}
            sm={4}
            md={7}
            sx={{
              backgroundImage: `url(${background})`,
              backgroundRepeat: 'no-repeat',
              backgroundColor: (t) =>
                t.palette.mode === 'light'
                  ? t.palette.grey[50]
                  : t.palette.grey[900],
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          />

          <Grid
            item
            xs={12}
            sm={8}
            md={5}
            component={Paper}
            elevation={6}
            square
          >
            <Box
              sx={{
                my: 8,
                mx: 4,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <Typography component="h1" variant="h5" sx={{ mb: 2 }}>
                Forgot Password
              </Typography>
              <Typography variant="body2" sx={{ mb: 4 }}>
                Enter the email associated with your account, and we'll send a
                link to reset your password.
              </Typography>

              <Box
                component="form"
                noValidate
                sx={{ mt: 1, width: '22rem', maxWidth: '100%' }}
              >
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="email"
                  label="Email Address"
                  name="email"
                  autoComplete="email"
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Box>

              <Button
                onClick={handleSubmit}
                variant="contained"
                sx={{ mt: 3, mb: 2, display: 'flex', justifyContent: 'center' }}
              >
                Send Reset Instructions
              </Button>

              {message && (
                <Typography
                  variant="h6"
                  color={
                    message.type === 'success' ? 'success.main' : 'error'
                  }
                  sx={{ mt: 2 }}
                >
                  {message.text}
                </Typography>
              )}

              <Button variant="text" onClick={() => navigate('/signin')}>
                Back to Sign In
              </Button>
            </Box>
          </Grid>
        </Grid>
      </ThemeProvider>
    </LoadingOverlay>
  );
};

export default ForgotPasswordPage;
