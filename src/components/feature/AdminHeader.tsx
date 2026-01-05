import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { getAuthToken } from '../../utils/auth';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

interface AdminHeaderProps {
    setIsMobileMenuOpen: (isOpen: boolean) => void;
}

interface AdminUser {
    name: string;
    email: string;
    role: string;
}

export default function AdminHeader({ setIsMobileMenuOpen }: AdminHeaderProps) {
    const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
    const [adminUser, setAdminUser] = useState<AdminUser | null>(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // Fetch admin user data on component mount
    useEffect(() => {
        const fetchAdminData = async () => {
            try {
                const token = getAuthToken();
                if (!token) {
                    navigate('/login');
                    return;
                }

                const response = await axios.get(`${API_BASE}/me`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                setAdminUser(response.data);
            } catch (error) {
                console.error('Failed to fetch admin data:', error);
                // Fallback to default if fetch fails
                setAdminUser({ name: 'Admin', email: '', role: 'admin' });
            } finally {
                setLoading(false);
            }
        };

        fetchAdminData();
    }, [navigate]);

    const handleLogout = () => {
        // Clear cookies
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i];
            const eqPos = cookie.indexOf("=");
            const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
            document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
        }

        // Clear local storage
        localStorage.clear();

        // Redirect and force reload
        navigate('/login', { replace: true });
        window.location.reload();
    };

    // Extract first name from full name
    const getFirstName = (fullName: string): string => {
        return fullName.split(' ')[0] || 'Admin';
    };

    // Get initials for avatar
    const getInitials = (fullName: string): string => {
        const names = fullName.split(' ');
        if (names.length >= 2) {
            return `${names[0][0]}${names[1][0]}`.toUpperCase();
        }
        return fullName.substring(0, 2).toUpperCase();
    };

    return (
        <div className="bg-white border-b border-gray-200 px-4 md:px-6 lg:px-8 py-4 sticky top-0 z-30">
            <div className="flex items-center justify-between">
                <button
                    onClick={() => setIsMobileMenuOpen(true)}
                    className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100"
                >
                    <i className="ri-menu-line text-xl"></i>
                </button>
                <div className="flex-1"></div>
                <div className="relative">
                    <button
                        onClick={() => setIsProfileDropdownOpen(!isProfileDropdownOpen)}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                            {loading ? (
                                <i className="ri-loader-4-line text-red-600 animate-spin"></i>
                            ) : (
                                <span className="text-xs font-semibold text-red-600">
                                    {adminUser ? getInitials(adminUser.name) : 'AD'}
                                </span>
                            )}
                        </div>
                        <span className="font-medium text-gray-900">
                            {loading ? 'Loading...' : (adminUser ? getFirstName(adminUser.name) : 'Admin')}
                        </span>
                        <i className="ri-arrow-down-s-line text-gray-400"></i>
                    </button>

                    {/* Profile Dropdown */}
                    {isProfileDropdownOpen && (
                        <>
                            <div
                                className="fixed inset-0 z-40"
                                onClick={() => setIsProfileDropdownOpen(false)}
                            ></div>
                            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50 animate-fade-in">
                                <Link
                                    to="/admin/profile"
                                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
                                    onClick={() => setIsProfileDropdownOpen(false)}
                                >
                                    <i className="ri-user-settings-line text-gray-500"></i>
                                    Profile
                                </Link>
                                <div className="border-t border-gray-100 my-1"></div>
                                <button
                                    onClick={handleLogout}
                                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-3"
                                >
                                    <i className="ri-logout-box-line"></i>
                                    Logout
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
