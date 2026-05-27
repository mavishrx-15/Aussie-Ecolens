import { useState } from 'react'
import { Input, Button, Typography, Tag, Space, Divider, message, Card } from 'antd'
import { PlusOutlined, DeleteOutlined, TagOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export default function Manage() {
  const [urlInput, setUrlInput] = useState('')
  const [urls, setUrls] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState([])

  const addUrl = () => {
    if (!urlInput.trim()) return
    setUrls([...urls, urlInput.trim()])
    setUrlInput('')
  }

  const removeUrl = (index) => {
    setUrls(urls.filter((_, i) => i !== index))
  }

  const addTag = () => {
    if (!tagInput.trim()) return
    setTags([...tags, tagInput.toLowerCase().trim()])
    setTagInput('')
  }

  const removeTag = (index) => {
    setTags(tags.filter((_, i) => i !== index))
  }

  const handleTagOperation = async (operation) => {
    if (urls.length === 0 || tags.length === 0) {
      message.warning('Please add at least one URL and one tag')
      return
    }
    // TODO: connect Hunyang's tag API
    message.success(operation === 1 ? 'Tags added successfully' : 'Tags removed successfully')
  }

  const handleDelete = async () => {
    if (urls.length === 0) {
      message.warning('Please add at least one URL')
      return
    }
    // TODO: connect Hunyang's delete API
    message.success('Files deleted successfully')
    setUrls([])
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)',
      padding: '40px 24px'
    }}>
      <div style={{ maxWidth: 700, margin: '0 auto' }}>

        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32' }}>Manage Files</Title>
          <Text type="secondary">Add or remove tags, delete files</Text>
        </div>

        <Card style={{ borderRadius: 16, marginBottom: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>

          {/* URL input */}
          <Title level={5}>File URLs</Title>
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <Input
              placeholder="Paste file URL here"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onPressEnter={addUrl}
              size="large"
            />
            <Button
              onClick={addUrl}
              size="large"
              style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}
            >
              Add
            </Button>
          </Space.Compact>

          <div style={{ marginBottom: 16, minHeight: 32 }}>
            {urls.map((url, i) => (
              <Tag
                key={i}
                closable
                onClose={() => removeUrl(i)}
                style={{ marginBottom: 4, maxWidth: '100%' }}
              >
                {url.length > 60 ? url.substring(0, 60) + '...' : url}
              </Tag>
            ))}
          </div>

          <Divider />

          {/* Tag input */}
          <Title level={5}>Tags</Title>
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <Input
              placeholder="Species name (e.g. koala)"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onPressEnter={addTag}
              size="large"
            />
            <Button
              onClick={addTag}
              size="large"
              style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}
            >
              Add
            </Button>
          </Space.Compact>

          <div style={{ marginBottom: 24, minHeight: 32 }}>
            {tags.map((tag, i) => (
              <Tag
                key={i}
                closable
                onClose={() => removeTag(i)}
                color="green"
                style={{ marginBottom: 4 }}
              >
                {tag}
              </Tag>
            ))}
          </div>

          <Divider />

          {/* Actions */}
          <Space style={{ width: '100%', justifyContent: 'center' }} size="middle">
            <Button
              icon={<PlusOutlined />}
              size="large"
              style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}
              onClick={() => handleTagOperation(1)}
            >
              Add Tags
            </Button>
            <Button
              icon={<TagOutlined />}
              size="large"
              onClick={() => handleTagOperation(0)}
            >
              Remove Tags
            </Button>
            <Button
              icon={<DeleteOutlined />}
              size="large"
              danger
              onClick={handleDelete}
            >
              Delete Files
            </Button>
          </Space>
        </Card>
      </div>
    </div>
  )
}