import { useEffect } from 'react';

interface ToastProps {
    message: string;
    type?: 'success' | 'error' | 'info';
    onClose: () => void;
    duration?: number;
}

export default function Toast({ message, type = 'success', onClose, duration = 3000 }: ToastProps) {
    useEffect(() => {
        const timer = setTimeout(() => {
            onClose();
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const bgColors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500'
    };

    const icons = {
        success: 'ri-checkbox-circle-line',
        error: 'ri-error-warning-line',
        info: 'ri-information-line'
    };

    return (
        <div className={`fixed top-4 right-4 z-50 flex items-center shadow-lg rounded-lg px-4 py-3 text-white transition-all transform translate-y-0 ${bgColors[type]}`}>
            <i className={`${icons[type]} text-xl mr-3`}></i>
            <span className="font-medium pr-2">{message}</span>
            <button onClick={onClose} className="ml-2 hover:bg-white/20 rounded-full p-1">
                <i className="ri-close-line"></i>
            </button>
        </div>
    );
}
