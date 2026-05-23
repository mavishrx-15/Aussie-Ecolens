import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Upload from './pages/Upload'
import Query from './pages/Query'
import Manage from './pages/Manage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/query" element={<Query />} />
        <Route path="/manage" element={<Manage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App