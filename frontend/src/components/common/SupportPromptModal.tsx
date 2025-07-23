import React, { useState } from 'react';
import { FaHeart, FaTimes } from 'react-icons/fa';

interface SupportPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSupport: () => void;
  onNoSupport: () => void;
}

export const SupportPromptModal: React.FC<SupportPromptModalProps> = ({
  isOpen,
  onClose,
  onSupport,
  onNoSupport
}) => {
  const [showNoMessage, setShowNoMessage] = useState(false);

  const handleNoSupport = () => {
    setShowNoMessage(true);
    onNoSupport();
    
    // Hide the message and close modal after 2 seconds
    setTimeout(() => {
      setShowNoMessage(false);
      onClose();
    }, 2000);
  };

  const handleSupport = () => {
    onSupport();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[110] bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4 relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <FaTimes size={16} />
        </button>

        {!showNoMessage ? (
          <>
            {/* Main content */}
            <div className="text-center mb-6">
              <div className="text-4xl mb-3">🎨</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Support Clouvel?
              </h3>
              <p className="text-gray-600 text-sm">
                Help us keep creating amazing AI art for everyone!
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleSupport}
                className="flex-1 bg-gradient-to-r from-purple-600 to-purple-500 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-purple-600 transition-all duration-200 font-medium flex items-center justify-center gap-2"
              >
                <FaHeart size={14} />
                Yes, Support!
              </button>
              <button
                onClick={handleNoSupport}
                className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                No thanks
              </button>
            </div>
          </>
        ) : (
          // "No support" message
          <div className="text-center py-4">
            <div className="text-3xl mb-3">🐕</div>
            <p className="text-gray-700 font-medium">
              Woof, maybe another time commando
            </p>
          </div>
        )}
      </div>
    </div>
  );
};