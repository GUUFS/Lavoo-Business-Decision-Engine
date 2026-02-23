import { useState, useEffect } from 'react';
import { useBetaStatus } from '../../api/user';
import { useNavigate } from 'react-router-dom';

function Countdown({ endsAt }: { endsAt: string }) {
    const [timeLeft, setTimeLeft] = useState<{ h: number, m: number, s: number } | null>(null);

    useEffect(() => {
        const timer = setInterval(() => {
            const diff = new Date(endsAt).getTime() - new Date().getTime();
            if (diff <= 0) {
                setTimeLeft({ h: 0, m: 0, s: 0 });
                clearInterval(timer);
                return;
            }
            setTimeLeft({
                h: Math.floor(diff / (1000 * 60 * 60)),
                m: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
                s: Math.floor((diff % (1000 * 60)) / 1000)
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [endsAt]);

    if (!timeLeft) return <span>--:--:--</span>;
    return (
        <span className="font-mono font-bold">
            {timeLeft.h.toString().padStart(2, '0')}:{timeLeft.m.toString().padStart(2, '0')}:{timeLeft.s.toString().padStart(2, '0')}
        </span>
    );
}

export default function BetaStatusBanner() {
    const { data: betaStatus } = useBetaStatus();
    const navigate = useNavigate();

    if (!betaStatus || !betaStatus.status) return null;

    const handleAction = () => {
        navigate('/dashboard/upgrade');
    };

    return (
        <div className="w-full px-4 sm:px-6 lg:px-8 py-2">
            {betaStatus.status === 'beta_no_card' && (
                <div className="bg-gradient-to-r from-orange-400 to-orange-500 rounded-lg p-3 text-white shadow-md animate-pulse">
                    <div className="max-w-7xl mx-auto flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="font-bold text-sm sm:text-base">{betaStatus.message}</span>
                        </div>
                        <button onClick={handleAction} className="bg-white text-orange-600 px-4 py-1 rounded-full font-bold text-xs sm:text-sm hover:bg-orange-50 transition-colors">
                            Save Card
                        </button>
                    </div>
                </div>
            )}

            {betaStatus.status === 'beta_with_card' && (
                <div className="bg-white border border-green-200 rounded-lg p-3 text-green-700 shadow-sm relative overflow-hidden">
                    <div className="max-w-7xl mx-auto flex items-center gap-3 relative z-10">
                        <span className="text-xl">✅</span>
                        <span className="font-bold text-sm sm:text-base">{betaStatus.message}</span>
                    </div>
                    <div className="absolute top-0 right-0 w-24 h-24 bg-green-50 rounded-full -mr-12 -mt-12 z-0 opacity-50"></div>
                </div>
            )}

            {betaStatus.status === 'grace_with_card' && (
                <div className="bg-gradient-to-r from-purple-500 via-pink-500 to-red-500 rounded-lg p-3 text-white shadow-md">
                    <div className="max-w-7xl mx-auto flex items-center gap-3">
                        <span className="text-xl">🎉</span>
                        <span className="font-bold text-sm sm:text-base">{betaStatus.message}</span>
                    </div>
                </div>
            )}

            {betaStatus.status === 'grace_no_card' && (
                <div className="bg-red-600 rounded-lg p-3 text-white shadow-lg animate-pulse ring-2 ring-red-300">
                    <div className="max-w-7xl mx-auto flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-xl">⚠️</span>
                            <div>
                                <span className="font-black text-sm sm:text-base block leading-none">{betaStatus.message}</span>
                                <span className="text-xs opacity-90">Payment Method Required</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="hidden sm:block text-right">
                                <p className="text-[10px] uppercase font-bold opacity-80">Expires in</p>
                                {betaStatus.countdown_ends_at && <Countdown endsAt={betaStatus.countdown_ends_at} />}
                            </div>
                            <button onClick={handleAction} className="bg-white text-red-600 px-4 py-1 rounded-full font-bold text-xs sm:text-sm hover:bg-red-50 transition-colors">
                                Fix Now
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
