import { Form, Input, Button, Typography } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import logo from '../assets/icon.png'

const { Title, Text } = Typography

export default function Login() {
  const navigate = useNavigate()

  const handleLogin = (values) => {
    // TODO: connect Cognito
    navigate('/upload')
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{
        background: 'white',
        borderRadius: 16,
        padding: 40,
        width: 400,
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <img src={logo} alt="Aussie EcoLens" style={{ height: 75, marginBottom: 8 }} />
          <Title level={3} style={{ color: '#2e7d32', margin: '8px 0 4px' }}>
            Aussie EcoLens
          </Title>
          <Text type="secondary">Wildlife Observation Platform</Text>
        </div>

        <Form layout="vertical" onFinish={handleLogin}>
          <Form.Item
            label="Email"
            name="email"
            rules={[{ required: true, type: 'email', message: 'Please enter a valid email' }]}
          >
            <Input placeholder="you@example.com" size="large" />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[{ required: true, message: 'Please enter your password' }]}
          >
            <Input.Password placeholder="••••••••" size="large" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              style={{ background: '#2e7d32', borderColor: '#2e7d32' }}
            >
              Sign in
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">Don't have an account? </Text>
          <Link to="/register" style={{ color: '#2e7d32', fontWeight: 500 }}>
            Sign up
          </Link>
        </div>
      </div>
    </div>
  )
}