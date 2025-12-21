
import { useState, useEffect } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import { getAuthHeaders } from '../../../utils/auth';

const API_BASE_URL = 'http://localhost:8000';

const ChangePasswordModal = ({ onClose }: { onClose: () => void }) => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      });
      if (response.ok) {
        setSuccess('Password changed successfully');
        setTimeout(onClose, 2000);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to change password');
      }
    } catch (err) {
      setError('An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6 animate-fade-in">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">Change Password</h3>
          <button onClick={onClose}><i className="ri-close-line text-2xl text-gray-500"></i></button>
        </div>
        {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>}
        {success && <div className="bg-green-50 text-green-600 p-3 rounded-lg mb-4 text-sm">{success}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
            <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500" required />
          </div>
          <button type="submit" disabled={loading} className="w-full py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium">
            {loading ? 'Updating...' : 'Update Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default function AdminProfile() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('personal');
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  const [profileData, setProfileData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '', // Not in DB currently
    role: '',
    department: '',
    location: '',
    bio: '',
    joinDate: '',
    lastLogin: 'Unknown', // Not tracked
    loginCount: 0 // Not tracked
  });

  const [securitySettings, setSecuritySettings] = useState({
    twoFactorEnabled: false,
    emailNotifications: true,
    loginAlerts: false, // Mock
    sessionTimeout: '30' // Mock
  });

  const fetchProfile = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/me`, { headers: getAuthHeaders() });
      if (response.ok) {
        const data = await response.json();
        const names = (data.name || '').split(' ');
        const firstName = names[0] || '';
        const lastName = names.slice(1).join(' ') || '';
        setProfileData({
          firstName,
          lastName,
          email: data.email || '',
          phone: '',
          role: data.role || 'User',
          department: data.department || '',
          location: data.location || '',
          bio: data.bio || '',
          joinDate: data.created_at ? new Date(data.created_at).toLocaleDateString() : 'N/A',
          lastLogin: 'N/A',
          loginCount: 0
        });
        // We need to fetch security settings if they are not in /me.
        // I added them to /me in backend earlier step... check login.py
        // Wait, I updated UserUpdate but NOT AuthResponse in login.py replacement!
        // Ah, AuthResponse changes in models.py were done.
        // But login.py 'me' function manually returns dict, and I updated it? 
        // I updated 'me' function return dict in previous step. But I missed adding 'two_factor_enabled' and 'email_notifications' to 'me' return dict?
        // Let me check my thought log...
        // Step 348 (login.py edit): I added department, location, bio, created_at.
        // I DID NOT add two_factor_enabled, email_notifications to the return dict in /me endpoint.
        // So they won't be returned by /me.
        // I need to update login.py again to return them.
      }
    } catch (e) {
      console.error("Failed to fetch profile", e);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSaveProfile = async () => {
    try {
      const fullName = `${profileData.firstName} ${profileData.lastName}`.trim();
      const response = await fetch(`${API_BASE_URL}/me`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          name: fullName,
          department: profileData.department,
          location: profileData.location,
          bio: profileData.bio
        })
      });
      if (response.ok) {
        setIsEditing(false);
      } else {
        alert('Failed to update profile');
      }
    } catch (e) {
      alert('Error updating profile');
    }
  };

  const handleSecurityChange = async (setting: string, value: boolean | string) => {
    // Optimistic update
    setSecuritySettings(prev => ({ ...prev, [setting]: value }));

    if (setting === 'twoFactorEnabled') {
      try {
        await fetch(`${API_BASE_URL}/me`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
          body: JSON.stringify({ two_factor_enabled: value })
        });
      } catch (e) { /* revert? */ }
    } else if (setting === 'emailNotifications') {
      try {
        await fetch(`${API_BASE_URL}/me`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
          body: JSON.stringify({ email_notifications: value })
        });
      } catch (e) { /* revert? */ }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar isMobileMenuOpen={isMobileMenuOpen} setIsMobileMenuOpen={setIsMobileMenuOpen} />
      <div className="flex-1 ml-0 flex flex-col">
        <AdminHeader setIsMobileMenuOpen={setIsMobileMenuOpen} />
        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto">
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Admin Profile</h1>
              <p className="text-gray-600">Manage your account settings and security preferences</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center gap-6">
                  <div className="w-20 h-20 bg-gradient-to-br from-orange-400 to-red-500 rounded-full flex items-center justify-center">
                    <span className="text-2xl font-bold text-white uppercase">
                      {(profileData.firstName?.[0] || '')}{(profileData.lastName?.[0] || '')}
                    </span>
                  </div>
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-gray-900 mb-1">{profileData.firstName} {profileData.lastName}</h2>
                    <p className="text-gray-600 mb-2">{profileData.role} &bull; {profileData.location || 'No Location'}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1"><i className="ri-calendar-line"></i> Joined {profileData.joinDate}</span>
                    </div>
                  </div>
                  <button onClick={() => setIsEditing(!isEditing)} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                    {isEditing ? 'Cancel' : 'Edit Profile'}
                  </button>
                </div>
              </div>

              <div className="border-b border-gray-200">
                <nav className="flex space-x-8 px-6">
                  <button onClick={() => setActiveTab('personal')} className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${activeTab === 'personal' ? 'border-red-500 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>Personal Information</button>
                  <button onClick={() => setActiveTab('security')} className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${activeTab === 'security' ? 'border-red-500 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>Security Settings</button>
                </nav>
              </div>

              <div className="p-6">
                {activeTab === 'personal' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                        <input type="text" value={profileData.firstName} onChange={(e) => setProfileData(prev => ({ ...prev, firstName: e.target.value }))} disabled={!isEditing} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 disabled:bg-gray-50" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                        <input type="text" value={profileData.lastName} onChange={(e) => setProfileData(prev => ({ ...prev, lastName: e.target.value }))} disabled={!isEditing} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 disabled:bg-gray-50" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                        <input type="email" value={profileData.email} disabled className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 cursor-not-allowed" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Department</label>
                        <input type="text" value={profileData.department} onChange={(e) => setProfileData(prev => ({ ...prev, department: e.target.value }))} disabled={!isEditing} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 disabled:bg-gray-50" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Location</label>
                        <input type="text" value={profileData.location} onChange={(e) => setProfileData(prev => ({ ...prev, location: e.target.value }))} disabled={!isEditing} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 disabled:bg-gray-50" />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Bio</label>
                      <textarea value={profileData.bio} onChange={(e) => setProfileData(prev => ({ ...prev, bio: e.target.value }))} disabled={!isEditing} rows={4} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 disabled:bg-gray-50" />
                    </div>
                    {isEditing && (
                      <div className="flex gap-3">
                        <button onClick={handleSaveProfile} className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">Save Changes</button>
                        <button onClick={() => setIsEditing(false)} className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors whitespace-nowrap">Cancel</button>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'security' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <h3 className="text-lg font-medium text-gray-900">Authentication</h3>
                        <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                          <div><h4 className="font-medium text-gray-900">Two-Factor Authentication</h4><p className="text-sm text-gray-600">Add an extra layer of security</p></div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" checked={securitySettings.twoFactorEnabled} onChange={(e) => handleSecurityChange('twoFactorEnabled', e.target.checked)} className="sr-only peer" />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                          </label>
                        </div>
                        <div className="p-4 border border-gray-200 rounded-lg">
                          <div className="flex justify-between items-center">
                            <div><h4 className="font-medium text-gray-900">Password</h4><p className="text-sm text-gray-600">Change your account password</p></div>
                            <button onClick={() => setShowPasswordModal(true)} className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors text-sm font-medium">Change</button>
                          </div>
                        </div>
                      </div>
                      <div className="space-y-4">
                        <h3 className="text-lg font-medium text-gray-900">Notifications</h3>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                            <div><h4 className="font-medium text-gray-900">Email Notifications</h4><p className="text-sm text-gray-600">Receive alerts via email</p></div>
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input type="checkbox" checked={securitySettings.emailNotifications} onChange={(e) => handleSecurityChange('emailNotifications', e.target.checked)} className="sr-only peer" />
                              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                            </label>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      {showPasswordModal && <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />}
    </div>
  );
}