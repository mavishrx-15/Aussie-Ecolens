import { useState } from 'react'
import { Form, Input, Button, Typography, message, Modal } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { signUp, confirmSignUp } from '../auth'
import logo from '../assets/icon.png'

const { Title, Text } = Typography

export default function Register() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [confirmModal, setConfirmModal] = useState(false)
  const [confirmEmail, setConfirmEmail] = useState('')
  const [confirmCode, setConfirmCode] = useState('')

  const handleRegister = async (values) => {
    setLoading(true)
    try {
      await signUp(values.email, values.password, values.firstName, values.lastName)
      setConfirmEmail(values.email)
      setConfirmModal(true)
      message.success('Account created! Please check your email for confirmation code.')
    } catch (err) {
      message.error(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    try {
      await confirmSignUp(confirmEmail, confirmCode)
      message.success('Email confirmed! Please log in.')
      setConfirmModal(false)
      navigate('/')
    } catch (err) {
      message.error(err.message || 'Confirmation failed')
    }
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
          <img src={logo} alt="Aussie EcoLens" style={{ height: 100, marginBottom: 8 }} />
          <Title level={3} style={{ color: '#2e7d32', margin: '8px 0 4px' }}>
            Create Account
          </Title>
          <Text type="secondary">Join Aussie EcoLens</Text>
        </div>

        <Form layout="vertical" onFinish={handleRegister}>
          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item
              label="First Name"
              name="firstName"
              rules={[{ required: true, message: 'Required' }]}
              style={{ flex: 1 }}
            >
              <Input placeholder="John" size="large" />
            </Form.Item>
            <Form.Item
              label="Last Name"
              name="lastName"
              rules={[{ required: true, message: 'Required' }]}
              style={{ flex: 1 }}
            >
              <Input placeholder="Smith" size="large" />
            </Form.Item>
          </div>

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
            rules={[{ required: true, min: 8, message: 'Password must be at least 8 characters' }]}
          >
            <Input.Password placeholder="••••••••" size="large" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={loading}
              style={{ background: '#2e7d32', borderColor: '#2e7d32' }}
            >
              Create Account
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">Already have an account? </Text>
          <Link to="/" style={{ color: '#2e7d32', fontWeight: 500 }}>
            Sign in
          </Link>
        </div>
      </div>

      {/* Email confirmation modal */}
      <Modal
        title="Confirm your email"
        open={confirmModal}
        onOk={handleConfirm}
        onCancel={() => setConfirmModal(false)}
        okText="Confirm"
        okButtonProps={{ style: { background: '#2e7d32', borderColor: '#2e7d32' } }}
      >
        <Text type="secondary">Enter the confirmation code sent to your email:</Text>
        <Input
          placeholder="Confirmation code"
          value={confirmCode}
          onChange={(e) => setConfirmCode(e.target.value)}
          size="large"
          style={{ marginTop: 12 }}
        />
      </Modal>
    </div>
  )
}