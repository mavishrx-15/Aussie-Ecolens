import { Menu, Typography } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import logo from '../assets/icon.png'

const { Text } = Typography

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()

  const items = [
    { key: '/upload', label: 'Upload' },
    { key: '/query', label: 'Search' },
    { key: '/manage', label: 'Manage' },
  ]

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      background: 'white',
      padding: '0 24px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 32 }}>
        <img src={logo} alt="logo" style={{ height: 36 }} />
        <Text strong style={{ color: '#2e7d32', fontSize: 16 }}>Aussie EcoLens</Text>
      </div>

      <Menu
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={items}
        onClick={({ key }) => navigate(key)}
        style={{ flex: 1, border: 'none' }}
      />

      <Text
        style={{ cursor: 'pointer', color: '#888' }}
        onClick={() => navigate('/')}
      >
        Sign out
      </Text>
    </div>
  )
}