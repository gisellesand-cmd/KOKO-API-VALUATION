import React from 'react';
import { createRoot } from 'react-dom/client';
import { LandingPage } from './components/LandingPage';
import './styles/index.css';

const API_URL = import.meta.env.VITE_API_URL || window.location.origin;

const container = document.getElementById('app');
if (container) {
  container.setAttribute('data-koko-widget', '');
  createRoot(container).render(
    <React.StrictMode>
      <LandingPage apiUrl={API_URL} locale="es" />
    </React.StrictMode>,
  );
}
