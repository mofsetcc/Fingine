import {
    Cancel as CancelIcon,
    Delete as DeleteIcon,
    Download as DownloadIcon,
    Edit as EditIcon,
    ExpandMore as ExpandMoreIcon,
    Login as LoginIcon,
    Notifications as NotificationsIcon,
    PhotoCamera as PhotoCameraIcon,
    Save as SaveIcon,
    Settings as SettingsIcon
} from '@mui/icons-material';
import {
    Accordion,
    AccordionDetails,
    AccordionSummary,
    Alert,
    Avatar,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControl,
    FormControlLabel,
    Grid,
    InputLabel,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    MenuItem,
    Select,
    Switch,
    Tab,
    Tabs,
    TextField,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { APIResponse } from '../types/base';
import { UserWithProfile } from '../types/user';

interface Timezone {
  id: string;
  name: string;
  offset: string;
}

interface NotificationTemplate {
  [key: string]: {
    type: string;
    default: boolean | string | number;
    description: string;
  };
}

interface ActivitySummary {
  recent_activities: Array<{
    type: string;
    timestamp: string;
    ip_address: string;
    metadata: Record<string, any>;
  }>;
  total_activities: number;
  login_count: number;
}

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
      id={`profile-tabpanel-${index}`}
      aria-labelledby={`profile-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const UserProfile: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [userProfile, setUserProfile] = useState<UserWithProfile | null>(null);
  const [timezones, setTimezones] = useState<Timezone[]>([]);
  const [notificationTemplate, setNotificationTemplate] = useState<NotificationTemplate>({});
  const [activitySummary, setActivitySummary] = useState<ActivitySummary | null>(null);
  
  // Edit states
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    display_name: '',
    timezone: ''
  });
  const [notificationPrefs, setNotificationPrefs] = useState<Record<string, any>>({});
  
  // UI states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [showExportDialog, setShowExportDialog] = useState(false);

  useEffect(() => {
    loadUserProfile();
    loadTimezones();
    loadNotificationTemplate();
  }, []);

  useEffect(() => {
    if (activeTab === 2) {
      loadActivitySummary();
    }
  }, [activeTab]);

  const loadUserProfile = async () => {
    try {
      const response = await fetch('/api/v1/profile/me', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load profile');
      }

      const data: APIResponse<UserWithProfile> = await response.json();
      setUserProfile(data.data);
      
      // Initialize edit form
      setEditForm({
        display_name: data.data.profile?.display_name || '',
        timezone: data.data.profile?.timezone || 'Asia/Tokyo'
      });
      
      // Initialize notification preferences
      setNotificationPrefs(data.data.profile?.notification_preferences || {});
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const loadTimezones = async () => {
    try {
      const response = await fetch('/api/v1/profile/timezones');
      if (response.ok) {
        const data: APIResponse<Timezone[]> = await response.json();
        setTimezones(data.data);
      }
    } catch (err) {
      console.error('Failed to load timezones:', err);
    }
  };

  const loadNotificationTemplate = async () => {
    try {
      const response = await fetch('/api/v1/profile/preferences/template');
      if (response.ok) {
        const data: APIResponse<NotificationTemplate> = await response.json();
        setNotificationTemplate(data.data);
      }
    } catch (err) {
      console.error('Failed to load notification template:', err);
    }
  };

  const loadActivitySummary = async () => {
    try {
      const response = await fetch('/api/v1/profile/me/activity', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data: APIResponse<ActivitySummary> = await response.json();
        setActivitySummary(data.data);
      }
    } catch (err) {
      console.error('Failed to load activity summary:', err);
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/v1/profile/me', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(editForm)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update profile');
      }

      setSuccess('Profile updated successfully');
      setIsEditing(false);
      await loadUserProfile();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/v1/profile/me/preferences', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(notificationPrefs)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update preferences');
      }

      setSuccess('Notification preferences updated successfully');
      await loadUserProfile();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (file: File) => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await fetch('/api/v1/profile/me/avatar', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload avatar');
      }

      setSuccess('Avatar uploaded successfully');
      await loadUserProfile();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload avatar');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAvatar = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/v1/profile/me/avatar', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete avatar');
      }

      setSuccess('Avatar deleted successfully');
      await loadUserProfile();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete avatar');
    } finally {
      setSaving(false);
    }
  };

  const handleExportData = async () => {
    try {
      const response = await fetch('/api/v1/profile/me/export', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to export data');
      }

      const data = await response.json();
      
      // Download as JSON file
      const blob = new Blob([JSON.stringify(data.data, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `user-data-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setShowExportDialog(false);
      setSuccess('Data exported successfully');
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export data');
    }
  };

  const formatActivityType = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!userProfile) {
    return (
      <Alert severity="error">
        Failed to load user profile. Please try refreshing the page.
      </Alert>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        User Profile
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label="Profile" icon={<EditIcon />} />
            <Tab label="Notifications" icon={<NotificationsIcon />} />
            <Tab label="Activity" icon={<LoginIcon />} />
            <Tab label="Settings" icon={<SettingsIcon />} />
          </Tabs>
        </Box>

        {/* Profile Tab */}
        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Box display="flex" flexDirection="column" alignItems="center">
                <Avatar
                  src={userProfile.profile?.avatar_url || undefined}
                  sx={{ width: 120, height: 120, mb: 2 }}
                >
                  {userProfile.profile?.display_name?.[0] || userProfile.email[0].toUpperCase()}
                </Avatar>
                
                <input
                  accept="image/*"
                  style={{ display: 'none' }}
                  id="avatar-upload"
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      handleAvatarUpload(file);
                    }
                  }}
                />
                <label htmlFor="avatar-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<PhotoCameraIcon />}
                    sx={{ mb: 1 }}
                    disabled={saving}
                  >
                    Upload Avatar
                  </Button>
                </label>
                
                {userProfile.profile?.avatar_url && (
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={handleDeleteAvatar}
                    disabled={saving}
                    size="small"
                  >
                    Remove Avatar
                  </Button>
                )}
              </Box>
            </Grid>

            <Grid item xs={12} md={8}>
              <Box display="flex" justifyContent="between" alignItems="center" mb={2}>
                <Typography variant="h6">Profile Information</Typography>
                {!isEditing ? (
                  <Button
                    startIcon={<EditIcon />}
                    onClick={() => setIsEditing(true)}
                  >
                    Edit Profile
                  </Button>
                ) : (
                  <Box>
                    <Button
                      startIcon={<SaveIcon />}
                      onClick={handleSaveProfile}
                      disabled={saving}
                      sx={{ mr: 1 }}
                    >
                      Save
                    </Button>
                    <Button
                      startIcon={<CancelIcon />}
                      onClick={() => {
                        setIsEditing(false);
                        setEditForm({
                          display_name: userProfile.profile?.display_name || '',
                          timezone: userProfile.profile?.timezone || 'Asia/Tokyo'
                        });
                      }}
                      disabled={saving}
                    >
                      Cancel
                    </Button>
                  </Box>
                )}
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Email"
                    value={userProfile.email}
                    disabled
                    helperText="Email cannot be changed"
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Display Name"
                    value={isEditing ? editForm.display_name : (userProfile.profile?.display_name || '')}
                    onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                    disabled={!isEditing}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <FormControl fullWidth disabled={!isEditing}>
                    <InputLabel>Timezone</InputLabel>
                    <Select
                      value={isEditing ? editForm.timezone : (userProfile.profile?.timezone || 'Asia/Tokyo')}
                      onChange={(e) => setEditForm({ ...editForm, timezone: e.target.value })}
                      label="Timezone"
                    >
                      {timezones.map((tz) => (
                        <MenuItem key={tz.id} value={tz.id}>
                          {tz.name} ({tz.offset})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Account Created"
                    value={formatTimestamp(userProfile.created_at)}
                    disabled
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Last Updated"
                    value={formatTimestamp(userProfile.updated_at)}
                    disabled
                  />
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Notifications Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box display="flex" justifyContent="between" alignItems="center" mb={3}>
            <Typography variant="h6">Notification Preferences</Typography>
            <Button
              startIcon={<SaveIcon />}
              onClick={handleSaveNotifications}
              disabled={saving}
              variant="contained"
            >
              Save Preferences
            </Button>
          </Box>

          <Grid container spacing={3}>
            {Object.entries(notificationTemplate).map(([key, template]) => (
              <Grid item xs={12} sm={6} md={4} key={key}>
                <Card variant="outlined">
                  <CardContent>
                    <FormControlLabel
                      control={
                        template.type === 'boolean' ? (
                          <Switch
                            checked={notificationPrefs[key] ?? template.default}
                            onChange={(e) => setNotificationPrefs({
                              ...notificationPrefs,
                              [key]: e.target.checked
                            })}
                          />
                        ) : (
                          <TextField
                            size="small"
                            value={notificationPrefs[key] ?? template.default}
                            onChange={(e) => setNotificationPrefs({
                              ...notificationPrefs,
                              [key]: template.type === 'integer' ? parseInt(e.target.value) || 0 : e.target.value
                            })}
                            type={template.type === 'integer' ? 'number' : 'text'}
                          />
                        )
                      }
                      label={
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {template.description}
                          </Typography>
                        </Box>
                      }
                      labelPlacement="top"
                    />
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        {/* Activity Tab */}
        <TabPanel value={activeTab} index={2}>
          <Typography variant="h6" gutterBottom>
            Account Activity
          </Typography>

          {activitySummary && (
            <>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h4" color="primary">
                        {activitySummary.total_activities}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Activities
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h4" color="success.main">
                        {activitySummary.login_count}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Successful Logins
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Typography variant="h6" gutterBottom>
                Recent Activities
              </Typography>
              
              <List>
                {activitySummary.recent_activities.map((activity, index) => (
                  <ListItem key={index} divider>
                    <ListItemIcon>
                      <LoginIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary={formatActivityType(activity.type)}
                      secondary={
                        <Box>
                          <Typography variant="caption" display="block">
                            {formatTimestamp(activity.timestamp)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            IP: {activity.ip_address}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </>
          )}
        </TabPanel>

        {/* Settings Tab */}
        <TabPanel value={activeTab} index={3}>
          <Typography variant="h6" gutterBottom>
            Account Settings
          </Typography>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Data Export</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary" paragraph>
                Export all your account data including profile information, activities, and preferences.
                This complies with GDPR data portability requirements.
              </Typography>
              <Button
                startIcon={<DownloadIcon />}
                onClick={() => setShowExportDialog(true)}
                variant="outlined"
              >
                Export My Data
              </Button>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Account Status</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box>
                <Chip
                  label={userProfile.email_verified_at ? "Email Verified" : "Email Not Verified"}
                  color={userProfile.email_verified_at ? "success" : "warning"}
                  sx={{ mr: 1, mb: 1 }}
                />
                <Typography variant="body2" color="text.secondary">
                  Account created: {formatTimestamp(userProfile.created_at)}
                </Typography>
              </Box>
            </AccordionDetails>
          </Accordion>
        </TabPanel>
      </Card>

      {/* Export Confirmation Dialog */}
      <Dialog open={showExportDialog} onClose={() => setShowExportDialog(false)}>
        <DialogTitle>Export User Data</DialogTitle>
        <DialogContent>
          <Typography>
            This will download all your account data as a JSON file. The export includes:
          </Typography>
          <List dense>
            <ListItem>
              <ListItemText primary="• Profile information" />
            </ListItem>
            <ListItem>
              <ListItemText primary="• Account activities" />
            </ListItem>
            <ListItem>
              <ListItemText primary="• Notification preferences" />
            </ListItem>
            <ListItem>
              <ListItemText primary="• OAuth connections" />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowExportDialog(false)}>
            Cancel
          </Button>
          <Button onClick={handleExportData} variant="contained">
            Export Data
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};