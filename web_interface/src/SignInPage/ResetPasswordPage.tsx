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
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import LoadingOverlay from 'react-loading-overlay-ts';
import background from '../assets/images/scott-webb-hDyO6rr3kqk-unsplash.jpg';

const defaultTheme = createTheme();

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [newPassword, setNewPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [message, setMessage] = React.useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);
  const [isActive, setIsActive] = React.useState(false); // State to control overlay

  // Extract the token from the query parameters
  const token = new URLSearchParams(location.search).get('token');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (newPassword !== confirmPassword) {
      setMessage({
        type: 'error',
        text: "Passwords don't match. Please try again.",
      });
      return;
    }
    console.log('IsActive:', isActive);
    setIsActive(true); // Show overlay spinner
    console.log('IsActive:', isActive);
    try {
      await axios.post(`${import.meta.env.VITE_BACKEND_URL}/reset-password/`, {
        token, // Use the token from the query parameters
        new_password: newPassword,
      });

      setMessage({
        type: 'success',
        text: 'Your password has been reset successfully. Redirecting to the sign-in page...',
      });

      // Redirect to the sign-in page after showing success message
      setTimeout(() => {
        navigate('/signin');
      }, 2000);
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Failed to reset the password. Please try again.',
      });
    } finally {
      setIsActive(false); // Hide overlay spinner
    }
  };

  return (
    <LoadingOverlay
      active={isActive}
      spinner
      text="Processing ..."
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

          {/* Background image on the left side */}
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

          {/* Form on the right side */}
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
                Reset Password
              </Typography>
              <Typography
                variant="body2"
                sx={{ mb: 4, textAlign: 'center' }}
              >
                Enter your new password below to reset it.
              </Typography>

              <Box
                component="form"
                noValidate
                onSubmit={handleSubmit}
                sx={{ mt: 1, width: '100%' }}
              >
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="new-password"
                  label="New Password"
                  name="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="confirm-password"
                  label="Confirm Password"
                  name="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />

                {message && (
                  <Typography
                    variant="h6"
                    color={
                      message.type === 'success' ? 'success.main' : 'error'
                    }
                    sx={{ mt: 2, textAlign: 'center' }}
                  >
                    {message.text}
                  </Typography>
                )}

                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  sx={{ mt: 3, mb: 2 }}
                >
                  Reset Password
                </Button>

                <Button
                  variant="text"
                  fullWidth
                  onClick={() => navigate('/signin')}
                >
                  Back to Sign In
                </Button>
              </Box>
            </Box>
          </Grid>
        </Grid>
    </ThemeProvider>
  </LoadingOverlay>
  );
};

export default ResetPasswordPage;
