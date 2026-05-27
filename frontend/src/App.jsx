import Navbar from './components/Navbar'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Upload from './pages/Upload'
import Query from './pages/Query'
import Manage from './pages/Manage'

function Layout({ children }) {
  const location = useLocation()
  const hideNav = ['/', '/register'].includes(location.pathname)
  return (
    <>
      {!hideNav && <Navbar />}
      {children}
    </>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/query" element={<Query />} />
          <Route path="/manage" element={<Manage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App