import HomePage from './HomePage.js';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';

function App() {
    
  return (
      <div className="app">
        <Routes>
          <Route exact path="/" element={<HomePage />} />
        </Routes>
      </div>
  );
}

export default App;
