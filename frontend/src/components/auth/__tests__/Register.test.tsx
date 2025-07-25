import { ThemeProvider, createTheme } from '@mui/material/styles';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../../hooks/useAuth';
import { Register } from '../Register';

// Mock the useAuth hook
const mockLogin = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    logout: jest.fn(),
    updateUser: jest.fn()
  })
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  Link: ({ children, to, ...props }: any) => <a href={to} {...props}>{children}</a>
}));

// Mock fetch
global.fetch = jest.fn();

const theme = createTheme();

const renderRegister = () => {
  return render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <AuthProvider>
          <Register />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
};

describe('Register Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockClear();
  });

  it('renders register form correctly', () => {
    renderRegister();
    
    expect(screen.getByText('Create Account')).toBeInTheDocument();
    expect(screen.getByText('Join Kessan Analysis Platform today')).toBeInTheDocument();
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByLabelText('Display Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create Account' })).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    renderRegister();
    
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument();
      expect(screen.getByText('Display name is required')).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
      expect(screen.getByText('Please confirm your password')).toBeInTheDocument();
      expect(screen.getByText('You must accept the terms and conditions')).toBeInTheDocument();
    });
  });

  it('validates email format', async () => {
    renderRegister();
    
    const emailInput = screen.getByLabelText('Email Address');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
    });
  });

  it('validates display name length', async () => {
    renderRegister();
    
    const displayNameInput = screen.getByLabelText('Display Name');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    // Test minimum length
    fireEvent.change(displayNameInput, { target: { value: 'a' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Display name must be at least 2 characters')).toBeInTheDocument();
    });
    
    // Test maximum length
    fireEvent.change(displayNameInput, { target: { value: 'a'.repeat(51) } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Display name must be less than 50 characters')).toBeInTheDocument();
    });
  });

  it('validates password strength', async () => {
    renderRegister();
    
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    // Test weak password
    fireEvent.change(passwordInput, { target: { value: 'weak' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Password is too weak. Use a mix of letters, numbers, and symbols')).toBeInTheDocument();
    });
  });

  it('validates password confirmation', async () => {
    renderRegister();
    
    const passwordInput = screen.getByLabelText('Password');
    const confirmPasswordInput = screen.getByLabelText('Confirm Password');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'DifferentPass123!' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    });
  });

  it('shows password strength indicator', () => {
    renderRegister();
    
    const passwordInput = screen.getByLabelText('Password');
    
    // Test weak password
    fireEvent.change(passwordInput, { target: { value: 'weak' } });
    expect(screen.getByText('Very Weak')).toBeInTheDocument();
    
    // Test strong password
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } });
    expect(screen.getByText('Strong')).toBeInTheDocument();
  });

  it('requires terms acceptance', async () => {
    renderRegister();
    
    const emailInput = screen.getByLabelText('Email Address');
    const displayNameInput = screen.getByLabelText('Display Name');
    const passwordInput = screen.getByLabelText('Password');
    const confirmPasswordInput = screen.getByLabelText('Confirm Password');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    // Fill all fields except terms
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(displayNameInput, { target: { value: 'Test User' } });
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('You must accept the terms and conditions')).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    const mockResponse = {
      data: {
        access_token: 'test-token',
        token_type: 'bearer',
        user: {
          id: '1',
          email: 'test@example.com',
          email_verified_at: null
        }
      }
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    renderRegister();
    
    const emailInput = screen.getByLabelText('Email Address');
    const displayNameInput = screen.getByLabelText('Display Name');
    const passwordInput = screen.getByLabelText('Password');
    const confirmPasswordInput = screen.getByLabelText('Confirm Password');
    const termsCheckbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(displayNameInput, { target: { value: 'Test User' } });
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.click(termsCheckbox);
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'StrongPass123!',
          display_name: 'Test User'
        })
      });
    });

    expect(screen.getByText('Registration successful! Please check your email to verify your account.')).toBeInTheDocument();
    expect(mockLogin).toHaveBeenCalledWith(mockResponse.data.user, mockResponse.data.access_token);
    
    // Check that navigation happens after delay
    setTimeout(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    }, 2000);
  });

  it('handles registration error', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Email already exists' })
    });

    renderRegister();
    
    const emailInput = screen.getByLabelText('Email Address');
    const displayNameInput = screen.getByLabelText('Display Name');
    const passwordInput = screen.getByLabelText('Password');
    const confirmPasswordInput = screen.getByLabelText('Confirm Password');
    const termsCheckbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(displayNameInput, { target: { value: 'Test User' } });
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'StrongPass123!' } });
    fireEvent.click(termsCheckbox);
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Email already exists')).toBeInTheDocument();
    });
  });

  it('toggles password visibility', () => {
    renderRegister();
    
    const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;
    const confirmPasswordInput = screen.getByLabelText('Confirm Password') as HTMLInputElement;
    const toggleButtons = screen.getAllByRole('button', { name: '' }); // Visibility toggle buttons
    
    expect(passwordInput.type).toBe('password');
    expect(confirmPasswordInput.type).toBe('password');
    
    // Toggle password visibility
    fireEvent.click(toggleButtons[0]);
    expect(passwordInput.type).toBe('text');
    
    // Toggle confirm password visibility
    fireEvent.click(toggleButtons[1]);
    expect(confirmPasswordInput.type).toBe('text');
  });

  it('redirects to OAuth providers', () => {
    // Mock window.location.href
    delete (window as any).location;
    window.location = { href: '' } as any;

    renderRegister();
    
    const googleButton = screen.getByText('Google');
    const lineButton = screen.getByText('LINE');
    
    fireEvent.click(googleButton);
    expect(window.location.href).toBe('/api/v1/oauth/google/login');
    
    fireEvent.click(lineButton);
    expect(window.location.href).toBe('/api/v1/oauth/line/login');
  });

  it('clears errors when user starts typing', async () => {
    renderRegister();
    
    const emailInput = screen.getByLabelText('Email Address');
    const submitButton = screen.getByRole('button', { name: 'Create Account' });
    
    // Trigger validation error
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument();
    });
    
    // Start typing to clear error
    fireEvent.change(emailInput, { target: { value: 'test' } });
    
    await waitFor(() => {
      expect(screen.queryByText('Email is required')).not.toBeInTheDocument();
    });
  });

  it('has link to login page', () => {
    renderRegister();
    
    expect(screen.getByText('Sign in')).toBeInTheDocument();
  });
});