import type { ReactNode } from 'react';
import logo from '../../assets/logo.png';

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="py-6 px-4 bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 shadow-lg">
        <div className="max-w-6xl mx-auto flex items-center justify-center">
          <div className="flex items-center space-x-4">
            <img 
              src={logo} 
              alt="Logo" 
              className="h-16 w-16 rounded-full shadow-lg border-4 border-white/20 hover:scale-105 transition-transform duration-300"
            />
            <div className="text-center">
              <h1 className="text-3xl font-bold text-white tracking-wide drop-shadow-lg">
                Product Generator
              </h1>
              <p className="text-blue-200 text-sm mt-1 font-medium">
                AI-Powered Design Creation
              </p>
            </div>
          </div>
        </div>
      </header>
      <main className="p-4 max-w-6xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}; 