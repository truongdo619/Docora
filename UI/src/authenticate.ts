import axios from 'axios';

export const authenticate = async (username: string, password: string) => {
  try {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await axios.post(`${import.meta.env.VITE_BACKEND_URL}/login`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    if (response.status === 200 && response.data.access_token) {
      localStorage.setItem('username', username);
      localStorage.setItem('accessToken', response.data.access_token); // Store the token in localStorage
      localStorage.setItem('refreshToken', response.data.refresh_token); // Store the refresh token
      return true;
    } else {
      return false;
    }
  } catch (error) {
    console.error('Authentication failed:', error);
    return false;
  }
};

export const refreshAccessToken = async () => {
  try {
    const refreshToken = localStorage.getItem('refreshToken');

    // Send the refresh token as a query parameter
    const response = await axios.post(`${import.meta.env.VITE_BACKEND_URL}/refresh-token?refresh_token=${refreshToken || ''}`, null, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 200 && response.data.access_token) {
      localStorage.setItem('accessToken', response.data.access_token); // Update the access token
      return true;
    } else {
      return false;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
};


// New function to register a new user
export const register = async (username: string, email: string, password: string) => {
  try {
    const requestBody = {
      username,
      email,
      password
    };

    const response = await axios.post(`${import.meta.env.VITE_BACKEND_URL}/register`, requestBody, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 200) {
      console.log('Registration successful:', response.data);
      return { success: true };
    } else {
      console.error('Registration failed with status:', response);
      return { success: false, message: 'Registration failed. Please try again.' };
    }
  } catch (error: any) {
    // Assuming the error response contains an error message in response.data.message
    const errorMessage = error.response?.data?.detail || 'An unexpected error occurred. Please try again.';
    console.error('Registration failed:', errorMessage);
    return { success: false, message: "Registration failed. " + errorMessage };
  }
};



export const logout = () => {
  // Clear any authentication-related data
  localStorage.removeItem('accessToken'); // Remove the token from localStorage
  localStorage.removeItem('refreshToken'); // Remove the refresh token
  localStorage.removeItem('username'); // Remove the username
  console.log("User logged out");

  // Optionally, you can clear other data like user profile or preferences
};