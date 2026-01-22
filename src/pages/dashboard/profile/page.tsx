
import { useState, useEffect } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import { useCurrentUser, updateProfile } from "../../../api/user";
import { calculateUserLevel } from '../earnings/levelcalculator';


interface ToastState {
  show: boolean;
  message: string;
  type: 'success' | 'error';
}

export default function ProfilePage() {
  const { data: user, refetch } = useCurrentUser();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    department: '',
    location: '',
    bio: ''
  });

  const [toast, setToast] = useState<ToastState>({
    show: false,
    message: '',
    type: 'success'
  });

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name || '',
        email: user.email || '',
        department: user.department || '',
        location: user.location || '',
        bio: user.bio || ''
      });
    }
  }, [user]);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast({ show: false, message: '', type: 'success' }), 5000);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    try {
      await updateProfile(formData);
      showToast('Profile updated successfully!');
      setIsEditing(false);
      refetch();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to update profile. Please try again.';
      showToast(errorMsg, 'error');
    }
  };

  const levelInfo = user?.total_chops !== undefined ? calculateUserLevel(user.total_chops) : null;
  const joinDate = user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric'
  }) : 'March 2024';

  return (
    <div className="min-h-screen bg-gray-50 flex bg-gradient-to-br from-orange-50 to-white">
      <DashboardSidebar />
      <div className="flex-1 p-4 md:p-6 lg:p-8 overflow-y-auto">
        <div className="max-w-4xl mx-auto">
          {/* Toast Notification */}
          {toast.show && (
            <div className="fixed top-6 right-6 z-50 animate-slide-in">
              <div className={`flex items-center gap-4 px-8 py-4 rounded-xl shadow-2xl text-white font-semibold text-lg min-w-[300px] border-l-8 ${toast.type === 'success' ? 'bg-green-600 border-green-800' : 'bg-red-600 border-red-800'
                }`}>
                <i className={`ri-${toast.type === 'success' ? 'check' : 'close'}-fill text-3xl`}></i>
                <div className="flex-1">
                  <div className="text-xl capitalize mb-0.5 font-bold">{toast.type}</div>
                  <p className="text-sm font-medium opacity-90">{toast.message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Header */}
          <div className="mb-6 md:mb-8 flex justify-between items-end">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Profile Settings</h1>
              <p className="text-gray-600 border-l-4 border-orange-500 pl-4 py-1">Manage your personal branding and account visibility</p>
            </div>
          </div>

          {/* Profile Form */}
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            {/* Profile Header */}
            <div className="bg-gradient-to-r from-orange-500 to-red-600 px-6 py-10 md:px-10 md:py-14 relative">
              <div className="flex flex-col md:flex-row items-center gap-8 relative z-10">
                {/* <div className="w-24 h-24 md:w-32 md:h-32 bg-white rounded-3xl flex items-center justify-center shadow-2xl transform rotate-3 hover:rotate-0 transition-transform duration-300">
                  <span className="text-6xl md:text-7xl">{levelInfo?.currentLevel.badge || '🏗️'}</span>
                </div> */}
                <div className="text-center md:text-left">
                  <div className="flex items-center gap-3 mb-2 justify-center md:justify-start">
                    <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight">{user?.name}</h2>
                    <span className={`px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-xs font-bold text-white border border-white/30 uppercase tracking-widest`}>
                      {user?.subscription_status?.toLowerCase() === 'active' ? 'PRO' : 'FREE'}
                    </span>
                  </div>
                  <p className="text-orange-100 text-lg opacity-90">Joined Lavoo since <span className="font-bold border-b border-orange-200/50 pb-0.5">{joinDate}</span></p>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-32 -mt-32 blur-3xl"></div>
            </div>

            {/* Form Content */}
            <div className="p-6 md:p-10">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Personal Information */}
                <div className="md:col-span-2 flex items-center justify-between border-b border-gray-100 pb-4 mb-2">
                  <h3 className="text-xl font-bold text-gray-900">Personal Information</h3>
                  {!isEditing && (
                    <button
                      onClick={() => setIsEditing(true)}
                      className="text-orange-600 hover:text-orange-700 font-bold flex items-center gap-2 group transition-all"
                    >
                      <i className="ri-edit-box-line text-xl group-hover:scale-110 transition-transform"></i>
                      <span>Edit Profile</span>
                    </button>
                  )}
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wider">Full Name</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    className={`w-full px-5 py-4 border-2 rounded-xl transition-all font-medium ${isEditing
                      ? 'border-orange-500 focus:ring-4 focus:ring-orange-100 bg-white'
                      : 'border-gray-100 bg-gray-50 text-gray-500'
                      }`}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wider">Email Address</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    className={`w-full px-5 py-4 border-2 rounded-xl transition-all font-medium ${isEditing
                      ? 'border-orange-500 focus:ring-4 focus:ring-orange-100 bg-white'
                      : 'border-gray-100 bg-gray-50 text-gray-500'
                      }`}
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wider">Subscription Status</label>
                  <div className="w-full px-5 py-4 border-2 border-gray-100 rounded-xl bg-gray-50 text-gray-500 font-bold flex items-center justify-between">
                    <span>{user?.subscription_status || 'Free'}</span>
                    <i className="ri-lock-line"></i>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wider">Subscription Plan</label>
                  <div className="w-full px-5 py-4 border-2 border-gray-100 rounded-xl bg-gray-50 text-gray-500 font-bold flex items-center justify-between">
                    <span>{user?.subscription_plan || 'N/A'}</span>
                    <i className="ri-lock-line"></i>
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wider">Bio</label>
                  <textarea
                    rows={4}
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    className={`w-full px-5 py-4 border-2 rounded-xl transition-all font-medium resize-none ${isEditing
                      ? 'border-orange-500 focus:ring-4 focus:ring-orange-100 bg-white'
                      : 'border-gray-100 bg-gray-50 text-gray-500'
                      }`}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              {isEditing && (
                <div className="flex flex-col sm:flex-row gap-4 mt-12 pt-8 border-t border-gray-100 animate-slide-up">
                  <button
                    onClick={handleSave}
                    className="flex-1 bg-gradient-to-r from-orange-500 to-orange-600 text-white px-8 py-4 rounded-xl font-bold hover:shadow-lg hover:shadow-orange-200 transition-all flex items-center justify-center gap-2"
                  >
                    <i className="ri-save-line text-xl"></i>
                    Update Records
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="flex-1 border-2 border-gray-200 text-gray-600 px-8 py-4 rounded-xl font-bold hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
                  >
                    <i className="ri-close-line text-xl"></i>
                    Discard Changes
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
