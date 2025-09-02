import React, { useState } from 'react';
import Avatar from '@mui/material/Avatar';
import Button from '@mui/material/Button';
import CssBaseline from '@mui/material/CssBaseline';
import TextField from '@mui/material/TextField';
import Link from '@mui/material/Link';
import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import Typography from '@mui/material/Typography';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import background from '../assets/images/scott-webb-hDyO6rr3kqk-unsplash.jpg';
import { register } from '../authenticate'; // Import the register function

function Copyright(props: any) {
  return (
    <Typography variant="body2" color="text.secondary" align="center" {...props}>
      {'Copyright © '}
      <Link color="inherit" href="/">
        Docora
      </Link>{' '}
      {new Date().getFullYear()}
      {'.'}
    </Typography>
  );
}

const defaultTheme = createTheme();

export default function SignUpPage() {
  const [signUpSuccess, setSignUpSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<{ username?: string; email?: string; password?: string; serverError?: string }>({});

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const username = data.get('username') as string;
    const email = data.get('email') as string;
    const password = data.get('password') as string;
    const confirmPassword = data.get('confirmPassword') as string;

    let errors: { username?: string; email?: string; password?: string } = {};

    // Simple Username validation (optional)
    if (!username || username.trim().length === 0) {
      errors.username = 'Username is required.';
    }

    // Email validation
    if (!validateEmail(email)) {
      errors.email = 'Invalid email address.';
    }

    // Password confirmation validation
    if (password !== confirmPassword) {
      errors.password = 'Passwords do not match.';
    }

    if (Object.keys(errors).length > 0) {
      setErrorMessage(errors);
      return;
    }

    // Call the register function and handle the response
    const registrationResponse  = await register(username, email, password);

  if (registrationResponse.success) {
    setSignUpSuccess(true);
    setErrorMessage({}); // Clear errors
    // Redirect to sign-in page after 1.5 seconds
    setTimeout(() => {
      window.location.href = '#/signin';
    }, 1000);
  } else {
    setErrorMessage({ serverError: registrationResponse.message || 'Registration failed. Please try again.' });
  }
  };

  return (
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
            backgroundColor: (t) =>
              t.palette.mode === 'light' ? t.palette.grey[50] : t.palette.grey[900],
            backgroundSize: 'cover',
            backgroundPosition: 'left',
          }}
        />
        <Grid item xs={12} sm={8} md={5} component={Paper} elevation={6} square>
          <Box
            sx={{
              my: 8,
              mx: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Avatar sx={{ m: 1, bgcolor: 'secondary.main' }}>
              <LockOutlinedIcon />
            </Avatar>
            <Typography component="h1" variant="h5">
              Sign Up
            </Typography>
            <Box component="form" noValidate onSubmit={handleSubmit} sx={{ mt: 1 }}>
              {signUpSuccess ? (
                <Typography variant="h6" color="success.main" align="center" sx={{ mb: 2 }}>
                  Sign-Up Successful! Redirecting to sign-in page...
                </Typography>
              ) : (
                <>
                  <TextField
                    margin="normal"
                    required
                    fullWidth
                    id="username"
                    label="Username"
                    name="username"
                    autoComplete="username"
                    autoFocus
                    error={!!errorMessage.username}
                    helperText={errorMessage.username || ''}
                  />
                  <TextField
                    margin="normal"
                    required
                    fullWidth
                    id="email"
                    label="Email Address"
                    name="email"
                    autoComplete="email"
                    error={!!errorMessage.email}
                    helperText={errorMessage.email || ''}
                  />
                  <TextField
                    margin="normal"
                    required
                    fullWidth
                    name="password"
                    label="Password"
                    type="password"
                    id="password"
                    autoComplete="new-password"
                    error={!!errorMessage.password}
                    helperText={errorMessage.password || ''}
                  />
                  <TextField
                    margin="normal"
                    required
                    fullWidth
                    name="confirmPassword"
                    label="Confirm Password"
                    type="password"
                    id="confirmPassword"
                    autoComplete="new-password"
                    error={!!errorMessage.password}
                    helperText={errorMessage.password || ''}
                  />
                  {errorMessage.serverError && (
                    <Typography variant="body2" color="error" align="center" sx={{ mt: 2 }}>
                      {errorMessage.serverError}
                    </Typography>
                  )}
                  <Button type="submit" fullWidth variant="contained" sx={{ mt: 3, mb: 2 }}>
                    Sign Up
                  </Button>
                  <Grid container>
                    <Grid item>
                      <Link href="#/signin" variant="body2">
                        {"Already have an account? Sign in"}
                      </Link>
                    </Grid>
                  </Grid>
                </>
              )}
              <Copyright sx={{ mt: 5 }} />
            </Box>
          </Box>
        </Grid>
      </Grid>
    </ThemeProvider>
  );
}
