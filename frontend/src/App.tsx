import { lazy } from 'react';
import { Provider } from 'react-redux';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import './App.css';
import { store } from './store';

// Lazy-loaded components for code splitting
import Layout from './components/Layout';
import LazyRoute from './components/LazyRoute';

// Lazy load page components
const Dashboard = lazy(() => import('./pages/Dashboard'));
const StockAnalysis = lazy(() => import('./pages/StockAnalysis'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));

function App() {
  return (
    <Provider store={store}>
      <Router>
        <div className="App">
          <Routes>
            <Route 
              path="/login" 
              element={
                <LazyRoute>
                  <Login />
                </LazyRoute>
              } 
            />
            <Route 
              path="/register" 
              element={
                <LazyRoute>
                  <Register />
                </LazyRoute>
              } 
            />
            <Route path="/" element={<Layout />}>
              <Route 
                index 
                element={
                  <LazyRoute>
                    <Dashboard />
                  </LazyRoute>
                } 
              />
              <Route 
                path="stock/:ticker" 
                element={
                  <LazyRoute>
                    <StockAnalysis />
                  </LazyRoute>
                } 
              />
            </Route>
          </Routes>
        </div>
      </Router>
    </Provider>
  );
}

export default App;