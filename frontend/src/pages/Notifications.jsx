import { useState } from 'react'
import { Input, Button, Typography, Tag, Card, message, Space } from 'antd'
import { BellOutlined, PlusOutlined } from '@ant-design/icons'
import axios from 'axios'
import { API_BASE_URL } from '../config'

const { Title, Text } = Typography

const COMMON_SPECIES = [
  'cattle', 'dingo', 'australian magpie', 'laughing kookaburra',
  'common wombat', 'eastern gray kangaroo', 'australian echidna',
  'swamp wallaby', 'common brushtail', 'australian brushturkey',
  'southern cassowary', 'wild boar', 'red fox', 'domestic cat',
  'human'
]

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

  // Reset all state after successful subscription
  const resetForm = () => {
    setEmail('')
    setTags([])
    setTagInput('')
    setSubscribed(false)
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
      resetForm()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)', padding: '40px 24px' }}>
      <div style={{ maxWidth: 600, margin: '0 auto' }}>

        <Space direction="vertical" align="center" style={{ width: '100%', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32', marginBottom: 0 }}>
            <BellOutlined /> Notifications
          </Title>
          <Text type="secondary">Get notified when new wildlife is detected</Text>
        </Space>

        <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">

            {/* Email input */}
            <div>
              <Title level={5}>Your Email</Title>
              <Input
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                size="large"
              />
            </div>

            {/* Quick select species via CheckableTag */}
            <div>
              <Title level={5}>Quick Select Species</Title>
              <Space size={[6, 8]} wrap>
                {COMMON_SPECIES.map(species => (
                  <Tag.CheckableTag
                    key={species}
                    checked={tags.includes(species)}
                    onChange={(checked) => checked ? addTag(species) : removeTag(species)}
                    style={{ fontSize: 13, padding: '3px 10px', borderRadius: 20 }}
                  >
                    {species}
                  </Tag.CheckableTag>
                ))}
              </Space>
            </div>

            {/* Custom species input */}
            <div>
              <Title level={5}>Custom Species</Title>
              <Space.Compact style={{ width: '100%' }}>
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
                  type="primary"
                  style={{ background: '#2e7d32', borderColor: '#2e7d32' }}
                >
                  Add
                </Button>
              </Space.Compact>
            </div>

            {/* Selected tags — only shows custom ones not in COMMON_SPECIES */}
            {tags.filter(t => !COMMON_SPECIES.includes(t)).length > 0 && (
              <Space size={[6, 4]} wrap>
                <Text type="secondary">Custom:</Text>
                {tags.filter(t => !COMMON_SPECIES.includes(t)).map(tag => (
                  <Tag key={tag} closable onClose={() => removeTag(tag)} color="green">
                    {tag}
                  </Tag>
                ))}
              </Space>
            )}

            {/* Subscribe / reset actions */}
            {subscribed ? (
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Button type="primary" icon={<BellOutlined />} size="large" block disabled style={{ background: '#2e7d32', borderColor: '#2e7d32' }}>
                  Check your email to confirm
                </Button>
                <Button size="large" block onClick={resetForm}>
                  Subscribe again
                </Button>
              </Space>
            ) : (
              <Button
                type="primary"
                icon={<BellOutlined />}
                onClick={handleSubscribe}
                size="large"
                block
                loading={loading}
                style={{ background: '#2e7d32', borderColor: '#2e7d32' }}
              >
                Subscribe
              </Button>
            )}

          </Space>
        </Card>
      </div>
    </div>
  )
}