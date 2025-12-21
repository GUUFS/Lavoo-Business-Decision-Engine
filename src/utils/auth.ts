export const getAuthToken = (): string | null => {
    return localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('authToken');
};

export const getAuthHeaders = (): Record<string, string> => {
    const token = getAuthToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
};
