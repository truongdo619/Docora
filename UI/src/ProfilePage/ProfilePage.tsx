import React, { useState, useContext, useEffect, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../axiosSetup';
import { AuthContext } from '../AuthContext';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  TextField,
  Button,
  Snackbar,
  Alert,
} from '@mui/material';

import PersonIcon from '@mui/icons-material/Person';
import LockIcon from '@mui/icons-material/Lock';
import LoadingOverlay from 'react-loading-overlay-ts';
import AppAppBar from '../HomePage/components/AppAppBar';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`vertical-tabpanel-${index}`}
      aria-labelledby={`vertical-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `vertical-tab-${index}`,
    'aria-controls': `vertical-tabpanel-${index}`,
  };
}

function ProfilePage() {
  const { isAuthenticated } = useContext(AuthContext);
  const navigate = useNavigate();

  if (!isAuthenticated) {
    navigate('/signin');
    return null;
  }

  const [tabValue, setTabValue] = useState(0);

  // Profile states (initially empty; will be populated from API)
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [workplace, setWorkplace] = useState('');
  const [phone, setPhone] = useState('');
  const [isActive, setIsActive] = useState(false);

  // Password states
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');

  // Snackbar (notification) states
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [notification, setNotification] = useState('');
  const [notificationSeverity, setNotificationSeverity] = useState<'success' | 'error'>('success');

  const handleCloseSnackbar = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') return;
    setOpenSnackbar(false);
  };

  // Fetch profile info using GET /get-user-infor
  useEffect(() => {
    async function fetchProfile() {
      setIsActive(true);
      const token = localStorage.getItem('accessToken');
      try {
        const response = await axiosInstance.get(`${import.meta.env.VITE_BACKEND_URL}/get-user-infor`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          onUnauthorized: () => navigate('/signin'),
        });
        console.log(response);
        const data = response.data;
        setUsername(data.username);
        setFullName(data.fullname); // API returns "fullname"
        setEmail(data.email);
        setAddress(data.address || '');
        setWorkplace(data.workplace || '');
        setPhone(data.phone || '');
      } catch (error) {
        console.error('Error fetching profile:', error);
      } finally {
        setIsActive(false);
      }
    }
    fetchProfile();
  }, [navigate]);

  // Handle tab change
  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Save personal info using POST /update-user-infor
  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    setIsActive(true);
    const token = localStorage.getItem('accessToken');
    const payload = {
      phone,
      address,
      workplace,
      fullname: fullName,
    };

    try {
      const response = await axiosInstance.post(`${import.meta.env.VITE_BACKEND_URL}/update-user-infor`, payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        onUnauthorized: () => navigate('/signin')
      });

      const updatedData = response.data;
      // Update local state with returned data
      setUsername(updatedData.username);
      setFullName(updatedData.fullname);
      setEmail(updatedData.email);
      setAddress(updatedData.address);
      setWorkplace(updatedData.workplace);
      setPhone(updatedData.phone);
      // Show success notification
      setNotification('Profile updated successfully!');
      setNotificationSeverity('success');
      setOpenSnackbar(true);
    } catch (error) {
      console.error('Error updating profile:', error);
      setNotification('An error occurred while updating your profile.');
      setNotificationSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setIsActive(false);
    }
  };

  // Change password using POST /change-password
  const handlePasswordChange = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmNewPassword) {
      setNotification('New passwords do not match!');
      setNotificationSeverity('error');
      setOpenSnackbar(true);
      return;
    }
    const token = localStorage.getItem('accessToken');
    const payload = { old_password: currentPassword, new_password: newPassword };

    setIsActive(true);
    try {
      const response = await axiosInstance.post(`${import.meta.env.VITE_BACKEND_URL}/change-password`, payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        onUnauthorized: () => navigate('/signin'),
      });

      const result = response.data;
      if (result.msg === 'done') {
        setNotification('Password changed successfully!');
        setNotificationSeverity('success');
        setOpenSnackbar(true);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmNewPassword('');
      } else if (result.msg === 'wrong password') {
        setNotification('Wrong password');
        setNotificationSeverity('error');
        setOpenSnackbar(true);
      } else {
        setNotification('Failed to change password.');
        setNotificationSeverity('error');
        setOpenSnackbar(true);
      }
    } catch (error) {
      console.error('Error changing password:', error);
      setNotification('An error occurred while changing your password.');
      setNotificationSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setIsActive(false);
    }
  };

  return (
    <>
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
        <>
          <AppAppBar mode="light" toggleColorMode={() => {}} />
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 12, mb: 4 }}>
            <Box
              sx={{
                display: 'flex',
                width: { xs: '95%', sm: '80%', md: '900px' },
                backgroundColor: 'background.paper',
                borderRadius: 2,
                boxShadow: 3,
                p: 2,
              }}
            >
              {/* Left side: Vertical Tabs */}
              <Box
                sx={{
                  width: 250,
                  backgroundColor: '#f5f5f5',
                  borderRight: '1px solid #ddd',
                }}
              >
                <Tabs
                  orientation="vertical"
                  variant="scrollable"
                  value={tabValue}
                  onChange={handleChange}
                  aria-label="Profile Tabs"
                  sx={{
                    height: '100%',
                    '.MuiTabs-indicator': {
                      left: 0,
                    },
                  }}
                >
                  <Tab
                    icon={<PersonIcon />}
                    label="Personal Information"
                    {...a11yProps(0)}
                    sx={{
                      '& .MuiTab-wrapper': {
                        flexDirection: 'row',
                        gap: 1,
                        justifyContent: 'flex-start',
                        alignItems: 'center',
                      },
                      textAlign: 'left',
                      alignItems: 'flex-start',
                    }}
                  />
                  <Tab
                    icon={<LockIcon />}
                    label="Password"
                    {...a11yProps(1)}
                    sx={{
                      '& .MuiTab-wrapper': {
                        flexDirection: 'row',
                        gap: 1,
                        justifyContent: 'flex-start',
                        alignItems: 'center',
                      },
                      textAlign: 'left',
                      alignItems: 'flex-start',
                    }}
                  />
                </Tabs>
              </Box>

              {/* Right side: Tab Panels */}
              <Box sx={{ flexGrow: 1 }}>
                {/* Personal Information */}
                <TabPanel value={tabValue} index={0}>
                  <Typography
                    variant="h6"
                    sx={{ mb: 3, display: 'flex', alignItems: 'center' }}
                  >
                    <PersonIcon sx={{ mr: 1 }} />
                    Personal Information
                  </Typography>
                  <Box
                    component="form"
                    onSubmit={handleSave}
                    display="flex"
                    flexDirection="column"
                    maxWidth={500}
                  >
                    <TextField
                      label="Username"
                      value={username}
                      margin="normal"
                      required
                      disabled
                    />
                    <TextField
                      label="Full Name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      margin="normal"
                      required
                    />
                    <TextField
                      label="Email"
                      type="email"
                      value={email}
                      margin="normal"
                      required
                      disabled
                    />
                    <TextField
                      label="Address"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      margin="normal"
                    />
                    <TextField
                      label="Workplace"
                      value={workplace}
                      onChange={(e) => setWorkplace(e.target.value)}
                      margin="normal"
                    />
                    <TextField
                      label="Phone"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      margin="normal"
                    />

                    <Box display="flex" justifyContent="flex-end" mt={2}>
                      <Button variant="contained" color="primary" type="submit">
                        Save
                      </Button>
                    </Box>
                  </Box>
                </TabPanel>

                {/* Password */}
                <TabPanel value={tabValue} index={1}>
                  <Typography
                    variant="h6"
                    sx={{ mb: 2, display: 'flex', alignItems: 'center' }}
                  >
                    <LockIcon sx={{ mr: 1 }} />
                    Change Password
                  </Typography>
                  <Box
                    component="form"
                    onSubmit={handlePasswordChange}
                    display="flex"
                    flexDirection="column"
                    maxWidth={400}
                  >
                    <TextField
                      label="Current Password"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      margin="normal"
                      required
                    />
                    <TextField
                      label="New Password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      margin="normal"
                      required
                    />
                    <TextField
                      label="Confirm New Password"
                      type="password"
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                      margin="normal"
                      required
                    />
                    <Box display="flex" justifyContent="flex-end" mt={2}>
                      <Button variant="contained" color="primary" type="submit">
                        Update Password
                      </Button>
                    </Box>
                  </Box>
                </TabPanel>
              </Box>
            </Box>
          </Box>
        </>
      </LoadingOverlay>

      {/* Snackbar Notification */}
      <Snackbar
        open={openSnackbar}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={notificationSeverity} sx={{ width: '100%' }}>
          {notification}
        </Alert>
      </Snackbar>
    </>
  );
}

export default ProfilePage;
