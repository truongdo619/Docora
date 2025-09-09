import React from 'react';
import DocumentList from './DocumentList'; // Assuming DocumentList is in the same directory
// import ResponsiveAppBar from './ResponsiveAppBar'; // Assuming ResponsiveAppBar is in the same directory
import AppAppBar from '../HomePage/components/AppAppBar';

const DocumentListPage: React.FC = () => {
  return (
    <div
      style={{
        width: '100%',
        height: '100vh',
        backgroundImage: 'linear-gradient(180deg, #CEE5FD, #FFF)',
        WebkitBackgroundSize: '100% 20%',
        backgroundSize: '100% 20%',
        backgroundRepeat: 'no-repeat',
      }}
    >
      {/* <ResponsiveAppBar /> */}
      <AppAppBar mode="light" toggleColorMode={() => {}} />
      <DocumentList />
    </div>
  );
};

export default DocumentListPage;
