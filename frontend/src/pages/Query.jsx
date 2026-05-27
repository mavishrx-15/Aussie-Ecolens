import { useState } from 'react'
import { Input, Button, Card, Typography, Tag, Row, Col, Empty, Spin } from 'antd'
import { SearchOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export default function Query() {
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [countInput, setCountInput] = useState(1)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  const addTag = () => {
    if (!tagInput.trim()) return
    setTags([...tags, { name: tagInput.toLowerCase(), count: countInput }])
    setTagInput('')
    setCountInput(1)
  }

  const removeTag = (index) => {
    setTags(tags.filter((_, i) => i !== index))
  }

  const handleSearch = async () => {
    if (tags.length === 0) return
    setLoading(true)
    // TODO: connect Hunyang's query API
    setTimeout(() => {
      setResults([
        { thumbnail_url: 'https://placehold.co/200x150?text=Koala', original_url: '#' },
        { thumbnail_url: 'https://placehold.co/200x150?text=Wombat', original_url: '#' },
      ])
      setLoading(false)
    }, 1000)
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)',
      padding: '40px 24px'
    }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>

        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32' }}>Search Wildlife</Title>
          <Text type="secondary">Search files by species and count</Text>
        </div>

        <div style={{
          background: 'white',
          borderRadius: 16,
          padding: 32,
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
          marginBottom: 24
        }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Input
              placeholder="Species (e.g. koala)"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onPressEnter={addTag}
              style={{ flex: 2 }}
              size="large"
            />
            <Input
              type="number"
              min={1}
              value={countInput}
              onChange={(e) => setCountInput(Number(e.target.value))}
              style={{ flex: 1 }}
              size="large"
              placeholder="Min count"
            />
            <Button
              icon={<PlusOutlined />}
              onClick={addTag}
              size="large"
              style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}
            >
              Add
            </Button>
          </div>

          <div style={{ marginBottom: 16, minHeight: 32 }}>
            {tags.map((tag, i) => (
              <Tag
                key={i}
                closable
                onClose={() => removeTag(i)}
                color="green"
                style={{ fontSize: 14, padding: '4px 10px', marginBottom: 4 }}
              >
                {tag.name} ≥ {tag.count}
              </Tag>
            ))}
          </div>

          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            size="large"
            block
            disabled={tags.length === 0}
            style={{ background: '#2e7d32', borderColor: '#2e7d32' }}
          >
            Search
          </Button>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        )}

        {!loading && results.length > 0 && (
          <Row gutter={[16, 16]}>
            {results.map((file, i) => (
              <Col key={i} xs={12} sm={8} md={6}>
                <Card
                  hoverable
                  cover={
                    <img
                      src={file.thumbnail_url}
                      alt="result"
                      style={{ height: 150, objectFit: 'cover' }}
                      onClick={() => window.open(file.original_url)}
                    />
                  }
                  bodyStyle={{ padding: 8 }}
                >
                  <Text type="secondary" style={{ fontSize: 12 }}>Click to view full image</Text>
                </Card>
              </Col>
            ))}
          </Row>
        )}

        {!loading && results.length === 0 && tags.length > 0 && (
          <Empty description="No results found" />
        )}
      </div>
    </div>
  )
}