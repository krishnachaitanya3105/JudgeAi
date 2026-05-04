import { createContext } from 'react';

export const AuthContext = createContext(null);

export const ROLE_CREDENTIALS = {
  officer: {
    email: 'officer@judgeai.local',
    password: 'officer123',
    name: 'Officer',
    defaultRoute: '/officer-dashboard',
  },
  admin: {
    email: 'admin@judgeai.local',
    password: 'admin123',
    name: 'Admin',
    defaultRoute: '/admin-dashboard',
  },
};
