import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import './App.css';

// Components (will be created in later tasks)
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import StockAnalysis from './pages/StockAnalysis';
import Login from './pages/Login';
import Register from './pages/Register';

function App() {
  return (
    <Provider store={store}>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="stock/:ticker" element={<StockAnalysis />} />
            </Route>
          </Routes>
        </div>
      </Router>
    </Provider>
  );
}

export default App;