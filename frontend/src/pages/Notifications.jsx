import { useState } from 'react'
import { Input, Button, Typography, Tag, Card, message, Switch, Space } from 'antd'
import { BellOutlined, PlusOutlined } from '@ant-design/icons'
import axios from 'axios'
import { API_BASE_URL } from '../config'

const { Title, Text } = Typography

const COMMON_SPECIES = ['koala', 'wombat', 'kangaroo', 'dingo', 'echidna', 'platypus', 'magpie', 'kookaburra']

export default function Notifications() {
  const [email, setEmail] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(false)
  const [subscribed, setSubscribed] = useState(false)

  const addTag = (tag) => {
    const t = tag.toLowerCase().trim()
    if (!t || tags.includes(t)) return
    setTags([...tags, t])
    setTagInput('')
  }

  const removeTag = (tag) => {
    setTags(tags.filter(t => t !== tag))
  }

  const handleSubscribe = async () => {
    if (!email || tags.length === 0) {
      message.warning('Please enter email and select at least one species')
      return
    }
    setLoading(true)
    try {
      await axios.post(`${API_BASE_URL}/subscribe`, {
        action: 'subscribe',
        email,
        tags
      })
      message.success('Confirmation email sent! Please check your inbox.')
      setSubscribed(true)
    } catch (err) {
      message.error('Subscription failed, please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)',
      padding: '40px 24px'
    }}>
      <div style={{ maxWidth: 600, margin: '0 auto' }}>

        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32' }}>
            <BellOutlined /> Notifications
          </Title>
          <Text type="secondary">Get notified when new wildlife is detected</Text>
        </div>

        <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>

          {/* Email */}
          <Title level={5}>Your Email</Title>
          <Input
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            size="large"
            style={{ marginBottom: 24 }}
          />

          {/* Common species quick select */}
          <Title level={5}>Quick Select Species</Title>
          <div style={{ marginBottom: 16 }}>
            {COMMON_SPECIES.map(species => (
              <Tag
                key={species}
                style={{ cursor: 'pointer', marginBottom: 8, padding: '4px 10px' }}
                color={tags.includes(species) ? 'green' : 'default'}
                onClick={() => tags.includes(species) ? removeTag(species) : addTag(species)}
              >
                {species}
              </Tag>
            ))}
          </div>

          {/* Custom tag input */}
          <Title level={5}>Custom Species</Title>
          <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
            <Input
              placeholder="Enter species name"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onPressEnter={() => addTag(tagInput)}
              size="large"
            />
            <Button
              icon={<PlusOutlined />}
              onClick={() => addTag(tagInput)}
              size="large"
              style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}
            >
              Add
            </Button>
          </Space.Compact>

          {/* Selected tags */}
          {tags.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <Text type="secondary">Subscribed to: </Text>
              {tags.map(tag => (
                <Tag
                  key={tag}
                  closable
                  onClose={() => removeTag(tag)}
                  color="green"
                  style={{ marginBottom: 4 }}
                >
                  {tag}
                </Tag>
              ))}
            </div>
          )}

          <Button
            type="primary"
            icon={<BellOutlined />}
            onClick={handleSubscribe}
            size="large"
            block
            loading={loading}
            disabled={subscribed}
            style={{ background: '#2e7d32', borderColor: '#2e7d32' }}
          >
            {subscribed ? 'Check your email to confirm' : 'Subscribe'}
          </Button>
        </Card>
      </div>
    </div>
  )
}