import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="py-6 px-4 bg-white shadow">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">Zazzle Product Generator</h1>
      </header>
      <main className="p-4 max-w-6xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}; 