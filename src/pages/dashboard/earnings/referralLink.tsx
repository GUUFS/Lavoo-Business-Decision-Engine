import { useState } from 'react';

interface ReferralLinkModalProps {
  referralLink: string;
  onClose: () => void;
}

export default function ReferralLinkModal({ referralLink, onClose }: ReferralLinkModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-900">Your Referral Link</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <i className="ri-close-line text-2xl"></i>
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Share this link with friends to earn rewards when they sign up!
        </p>

        <div className="bg-gray-50 rounded-lg p-3 mb-4 border border-gray-200">
          <p className="text-sm text-gray-900 break-all font-mono">
            {referralLink}
          </p>
        </div>

        <button
          onClick={handleCopy}
          className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
            copied
              ? 'bg-green-500 text-white'
              : 'bg-orange-500 text-white hover:bg-orange-600'
          }`}
        >
          {copied ? (
            <span className="flex items-center justify-center gap-2">
              <i className="ri-check-line"></i>
              Copied!
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <i className="ri-file-copy-line"></i>
              Copy Link
            </span>
          )}
        </button>
      </div>
    </div>
  );
}