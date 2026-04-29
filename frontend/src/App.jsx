import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { COOKIE_SESSION_TOKEN } from './api/http';
import { logout as logoutRequest } from './api/auth';
import { getMe, getStoredViewMode, setStoredViewMode } from './api/users';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import './i18n/i18n';
import './styles/Admin.css';
import './styles/Dashboard.css';
import './styles/Games.css';
import './styles/Layout.css';
import Admin from './pages/Admin';
import CreateGame from './pages/CreateGame';
import GameDetails from './pages/GameDetails';
import Games from './pages/Games';
import Home from './pages/Home';
import Leaderboard from './pages/Leaderboard';
import LegalDocument from './pages/LegalDocument';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import PartnerAnalytics from './pages/PartnerAnalytics';
import Profile from './pages/Profile';
import Register from './pages/Register';
import VenueCalendar from './pages/VenueCalendar';
import VenueManage from './pages/VenueManage';
import Wallet from './pages/Wallet';
import Welcome from './pages/Welcome';

export default function App() {
 const [token, setToken] = useState(null);
 const [user, setUser] = useState(null);
 const [authResolved, setAuthResolved] = useState(false);
 const [authCheckVersion, setAuthCheckVersion] = useState(0);
 const [viewMode, setViewMode] = useState(getStoredViewMode());

 useEffect(() => {
  setAuthResolved(false);
  getMe()
   .then((nextUser) => {
    setToken(COOKIE_SESSION_TOKEN);
    setUser(nextUser);
    setAuthResolved(true);
   })
   .catch(() => {
    setAuthResolved(true);
    setToken(null);
    setUser(null);
   });
 }, [authCheckVersion]);

 useEffect(() => {
  if (!user?.is_admin && viewMode === 'admin') {
   setStoredViewMode('default');
   setViewMode('default');
  }
 }, [user, viewMode]);

 const onAuth = () => {
  setAuthCheckVersion((current) => current + 1);
 };

 const onLogout = async () => {
  try {
   await logoutRequest();
  } catch {
   // Clear local auth state even if the cookie is already invalid server-side.
  }
  setStoredViewMode('default');
  setToken(null);
  setUser(null);
  setViewMode('default');
  setAuthResolved(true);
 };

 const onUserUpdate = (nextUser) => {
  setUser(nextUser);
 };

 const effectiveRole = user?.is_admin && viewMode === 'admin' ? 'admin' : (user?.role || 'player');

 const onViewModeChange = (mode) => {
  const userRole = user?.role || 'default';
  const normalized = mode === 'admin' && user?.is_admin ? 'admin' : userRole;
  setStoredViewMode(normalized === userRole ? 'default' : normalized);
  setViewMode(normalized === userRole ? 'default' : normalized);
 };

 const WithLayout = ({ children, title, subtitle }) => (
  <Layout user={user} token={token} onLogout={onLogout} title={title} subtitle={subtitle} effectiveRole={effectiveRole}>
   {children}
  </Layout>
 );

 return (
  <Routes>
   <Route path="/" element={!authResolved ? null : (token ? <Navigate to="/dashboard" replace /> : <Welcome />)} />
   <Route path="/login" element={!authResolved ? null : (token ? <Navigate to="/dashboard" replace /> : <Login onAuth={onAuth} />)} />
   <Route path="/register" element={!authResolved ? null : (token ? <Navigate to="/dashboard" replace /> : <Register onAuth={onAuth} />)} />
   <Route path="/legal/terms" element={<LegalDocument type="terms" />} />
   <Route path="/legal/privacy" element={<LegalDocument type="privacy" />} />
   <Route
    path="/onboarding"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <Onboarding user={user} token={token} />
     </ProtectedRoute>
    }
   />
   <Route
    path="/dashboard"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <WithLayout title="Dashboard" subtitle="Welcome back!">
       <Home user={user} token={token} effectiveRole={effectiveRole} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/games"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <WithLayout title="All Games" subtitle="Find and join games near you">
       <Games token={token} effectiveRole={effectiveRole} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
   path="/games/:id"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <WithLayout title="Game Details" subtitle="View game information">
       <GameDetails token={token} user={user} effectiveRole={effectiveRole} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/games/create"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole} allowedRoles={['player']}>
      <WithLayout title="Create Game" subtitle="Schedule a new game">
       <CreateGame token={token} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/partner/analytics"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole} allowedRoles={['partner']}>
      <WithLayout title="Analytics" subtitle="Revenue analytics and partner performance">
       <PartnerAnalytics token={token} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/partner/calendar"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole} allowedRoles={['partner']}>
      <WithLayout title="Calendar" subtitle="Manage your venue availability">
       <VenueCalendar token={token} user={user} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/partner/venues"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole} allowedRoles={['partner']}>
      <WithLayout title="My Venues" subtitle="Manage your venues">
       <VenueManage token={token} user={user} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/wallet"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <WithLayout title="Wallet" subtitle="Manage your credits">
       <Wallet token={token} user={user} effectiveRole={effectiveRole} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/admin"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole} allowedRoles={['admin']}>
      <WithLayout title="Admin Panel" subtitle="System administration">
       <Admin token={token} user={user} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/admin/users"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole} allowedRoles={['admin']}>
      <WithLayout title="Users" subtitle="Manage users">
       <Admin token={token} user={user} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/profile"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <WithLayout title="Profile" subtitle="Your profile">
       <Profile token={token} user={user} onUserUpdate={onUserUpdate} effectiveRole={effectiveRole} onViewModeChange={onViewModeChange} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route
    path="/leaderboard"
    element={
     <ProtectedRoute token={authResolved ? token : null} user={user} effectiveRole={effectiveRole}>
      <WithLayout title="Leaderboard" subtitle="Top players">
       <Leaderboard token={token} />
      </WithLayout>
     </ProtectedRoute>
    }
   />
   <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
 );
}
