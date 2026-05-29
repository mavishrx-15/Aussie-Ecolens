import { useState } from 'react'
import { Input, Button, Card, Typography, Tag, Row, Col, Empty, Spin, Tabs, message } from 'antd'
import { SearchOutlined, PlusOutlined } from '@ant-design/icons'
import axios from 'axios'
import { QUERY_API_BASE_URL } from '../config'
import { getToken } from '../auth'

const { Title, Text } = Typography

export default function Query() {
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [countInput, setCountInput] = useState(1)
  const [species, setSpecies] = useState([])
  const [speciesInput, setSpeciesInput] = useState('')
  const [thumbnailUrl, setThumbnailUrl] = useState('')
  const [results, setResults] = useState([])
  const [fullImageUrl, setFullImageUrl] = useState('')
  const [loading, setLoading] = useState(false)

  const addTag = () => {
    if (!tagInput.trim()) return
    setTags([...tags, { name: tagInput.toLowerCase(), count: countInput }])
    setTagInput('')
    setCountInput(1)
  }

  const removeTag = (index) => setTags(tags.filter((_, i) => i !== index))

  const addSpecies = () => {
    if (!speciesInput.trim()) return
    setSpecies([...species, speciesInput.toLowerCase()])
    setSpeciesInput('')
  }

  const removeSpecies = (index) => setSpecies(species.filter((_, i) => i !== index))

  const handleTagSearch = async () => {
    if (tags.length === 0) return
    setLoading(true)
    try {
      const token = await getToken()
      const query = {}
      tags.forEach(t => query[t.name] = t.count)
      const res = await axios.post(`${QUERY_API_BASE_URL}/query/tags`, query, {
        headers: { Authorization: token }
      })
      setResults(res.data.results || [])
      if (res.data.results?.length === 0) message.info('No results found')
    } catch (err) {
      message.error('Query failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSpeciesSearch = async () => {
    if (species.length === 0) return
    setLoading(true)
    try {
      const token = await getToken()
      const res = await axios.post(`${QUERY_API_BASE_URL}/query/species`, { species }, {
        headers: { Authorization: token }
      })
      setResults(res.data.results || [])
      if (res.data.results?.length === 0) message.info('No results found')
    } catch (err) {
      message.error('Query failed')
    } finally {
      setLoading(false)
    }
  }

  const handleThumbnailSearch = async () => {
    if (!thumbnailUrl.trim()) return
    setLoading(true)
    try {
      const token = await getToken()
      const res = await axios.post(`${QUERY_API_BASE_URL}/query/thumbnail`, { thumbnail_url: thumbnailUrl }, {
        headers: { Authorization: token }
      })
      setFullImageUrl(res.data.original_url || '')
    } catch (err) {
      message.error('Query failed')
    } finally {
      setLoading(false)
    }
  }

  const cardStyle = {
    background: 'white',
    borderRadius: 16,
    padding: 32,
    boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
    marginBottom: 24
  }

  const items = [
    {
      key: '1',
      label: 'Search by Tags',
      children: (
        <div>
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
          <div style={{ marginBottom: 16 }}>
            {tags.map((tag, i) => (
              <Tag key={i} closable onClose={() => removeTag(i)} color="green" style={{ fontSize: 14, padding: '4px 10px', marginBottom: 4 }}>
                {tag.name} ≥ {tag.count}
              </Tag>
            ))}
          </div>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleTagSearch} size="large" block disabled={tags.length === 0} style={{ background: '#2e7d32', borderColor: '#2e7d32' }}>
            Search
          </Button>
        </div>
      )
    },
    {
      key: '2',
      label: 'Search by Species',
      children: (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Input
              placeholder="Species (e.g. dingo)"
              value={speciesInput}
              onChange={(e) => setSpeciesInput(e.target.value)}
              onPressEnter={addSpecies}
              size="large"
              style={{ flex: 1 }}
            />
            <Button icon={<PlusOutlined />} onClick={addSpecies} size="large" style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}>
              Add
            </Button>
          </div>
          <div style={{ marginBottom: 16 }}>
            {species.map((s, i) => (
              <Tag key={i} closable onClose={() => removeSpecies(i)} color="green" style={{ fontSize: 14, padding: '4px 10px', marginBottom: 4 }}>
                {s}
              </Tag>
            ))}
          </div>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSpeciesSearch} size="large" block disabled={species.length === 0} style={{ background: '#2e7d32', borderColor: '#2e7d32' }}>
            Search
          </Button>
        </div>
      )
    },
    {
      key: '3',
      label: 'Search by Thumbnail URL',
      children: (
        <div>
          <Input
            placeholder="Paste thumbnail URL here"
            value={thumbnailUrl}
            onChange={(e) => setThumbnailUrl(e.target.value)}
            size="large"
            style={{ marginBottom: 16 }}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleThumbnailSearch} size="large" block disabled={!thumbnailUrl} style={{ background: '#2e7d32', borderColor: '#2e7d32' }}>
            Find Original
          </Button>
          {fullImageUrl && (
            <div style={{ marginTop: 16 }}>
              <Text strong>Original image URL: </Text>
              <a href={fullImageUrl} target="_blank" rel="noreferrer">{fullImageUrl}</a>
            </div>
          )}
        </div>
      )
    }
  ]

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)', padding: '40px 24px' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32' }}>Search Wildlife</Title>
          <Text type="secondary">Search files by species, tags, or thumbnail URL</Text>
        </div>

        <div style={cardStyle}>
          <Tabs items={items} />
        </div>

        {loading && <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>}

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

        {!loading && results.length === 0 && (tags.length > 0 || species.length > 0) && (
          <Empty description="No results found" />
        )}
      </div>
    </div>
  )
}