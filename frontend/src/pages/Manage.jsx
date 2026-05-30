import { useState } from 'react'
import { Input, Button, Typography, Tag, Space, Divider, message, Card, Upload, Row, Col, Spin } from 'antd'
import { PlusOutlined, DeleteOutlined, TagOutlined, InboxOutlined } from '@ant-design/icons'
import axios from 'axios'
import { QUERY_API_BASE_URL } from '../config'
import { getToken } from '../auth'

const { Title, Text } = Typography
const { Dragger } = Upload

export default function Manage() {
  const [urlInput, setUrlInput] = useState('')
  const [urls, setUrls] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(false)

  // File tag query state
  const [fileResults, setFileResults] = useState([])
  const [fileLoading, setFileLoading] = useState(false)

  const addUrl = () => {
    if (!urlInput.trim()) return
    setUrls([...urls, urlInput.trim()])
    setUrlInput('')
  }

  const removeUrl = (index) => setUrls(urls.filter((_, i) => i !== index))

  const addTag = () => {
    if (!tagInput.trim()) return
    setTags([...tags, tagInput.toLowerCase().trim()])
    setTagInput('')
  }

  const removeTag = (index) => setTags(tags.filter((_, i) => i !== index))

  // Clear URL and tag inputs after any successful operation
  const clearInputs = () => {
    setUrls([])
    setTags([])
    setUrlInput('')
    setTagInput('')
  }

  const handleTagOperation = async (operation) => {
    if (urls.length === 0 || tags.length === 0) {
      message.warning('Please add at least one URL and one tag')
      return
    }
    setLoading(true)
    try {
      const token = await getToken()
      await axios.post(`${QUERY_API_BASE_URL}/tags/bulk`, { urls, tags, operation }, {
        headers: { Authorization: token }
      })
      message.success(operation === 1 ? 'Tags added successfully' : 'Tags removed successfully')
      clearInputs()
    } catch (err) {
      message.error('Operation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (urls.length === 0) {
      message.warning('Please add at least one URL')
      return
    }
    setLoading(true)
    try {
      const token = await getToken()
      await axios.delete(`${QUERY_API_BASE_URL}/files`, {
        headers: { Authorization: token },
        data: { urls }
      })
      message.success('Files deleted successfully')
      clearInputs()
    } catch (err) {
      message.error('Delete failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFileQuery = async (file) => {
    setFileLoading(true)
    setFileResults([])  
    try {
      const token = await getToken()

      // Step 1: Get temp upload URL
      const urlRes = await axios.post(`${QUERY_API_BASE_URL}/query/upload-url`, {
        fileName: file.name
      }, {
        headers: { Authorization: token }
      })

      const { uploadUrl, bucket, key, contentType } = urlRes.data

      // Step 2: Upload file to temp S3 location
      await axios.put(uploadUrl, file, {
        headers: { 'Content-Type': contentType }
      })

      // Step 3: Query by file tags
      const res = await axios.post(`${QUERY_API_BASE_URL}/query/file-tags`, { bucket, key }, {
        headers: { Authorization: token }
      })

      setFileResults(res.data.results || [])
      if (res.data.results?.length === 0) message.info('No matching files found')
    } catch (err) {
      console.error('Error details:', err.response?.data)
      message.error('Query failed')
    } finally {
      setFileLoading(false)
    }
    return false
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)', padding: '40px 24px' }}>
      <div style={{ maxWidth: 700, margin: '0 auto' }}>

        <Space direction="vertical" align="center" style={{ width: '100%', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32', marginBottom: 0 }}>Manage Files</Title>
          <Text type="secondary">Add or remove tags, delete files</Text>
        </Space>

        {/* Tag management card */}
        <Card style={{ borderRadius: 16, marginBottom: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Title level={5} style={{ marginBottom: 0 }}>File URLs</Title>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="Paste file URL here"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onPressEnter={addUrl}
                size="large"
              />
              <Button onClick={addUrl} size="large" type="primary" style={{ background: '#2e7d32', borderColor: '#2e7d32' }}>
                Add
              </Button>
            </Space.Compact>
            <Space size={[8, 4]} wrap style={{ minHeight: 32 }}>
              {urls.map((url, i) => (
                <Tag key={i} closable onClose={() => removeUrl(i)}>
                  {url.length > 60 ? url.substring(0, 60) + '...' : url}
                </Tag>
              ))}
            </Space>

            <Divider style={{ margin: 0 }} />

            <Title level={5} style={{ marginBottom: 0 }}>Tags</Title>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="Species name (e.g. koala)"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onPressEnter={addTag}
                size="large"
              />
              <Button onClick={addTag} size="large" type="primary" style={{ background: '#2e7d32', borderColor: '#2e7d32' }}>
                Add
              </Button>
            </Space.Compact>
            <Space size={[8, 4]} wrap style={{ minHeight: 32 }}>
              {tags.map((tag, i) => (
                <Tag key={i} closable onClose={() => removeTag(i)} color="green">
                  {tag}
                </Tag>
              ))}
            </Space>

            <Divider style={{ margin: 0 }} />

            <Space style={{ width: '100%', justifyContent: 'center' }} size="middle">
              <Button icon={<PlusOutlined />} size="large" loading={loading} type="primary" style={{ background: '#2e7d32', borderColor: '#2e7d32' }} onClick={() => handleTagOperation(1)}>
                Add Tags
              </Button>
              <Button icon={<TagOutlined />} size="large" loading={loading} onClick={() => handleTagOperation(0)}>
                Remove Tags
              </Button>
              <Button icon={<DeleteOutlined />} size="large" danger loading={loading} onClick={handleDelete}>
                Delete Files
              </Button>
            </Space>
          </Space>
        </Card>

        {/* Search by file upload card */}
        <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Title level={5} style={{ marginBottom: 4 }}>Search by File</Title>
              <Text type="secondary">Upload a file to find all matching files in the database</Text>
            </div>
            <Dragger beforeUpload={handleFileQuery} showUploadList={false} accept="image/*,video/*">
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ color: '#2e7d32', fontSize: 40 }} />
              </p>
              <p className="ant-upload-text">Click or drag file to search</p>
            </Dragger>

            {fileLoading && (
              <Space style={{ width: '100%', justifyContent: 'center' }}>
                <Spin size="large" />
              </Space>
            )}

            {fileResults.length > 0 && (
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Title level={5}>Matching Files</Title>
                <Row gutter={[16, 16]}>
                  {fileResults.map((file, i) => (
                    <Col key={i} xs={12} sm={8} md={6}>
                      <Card
                        hoverable
                        cover={
                          <img
                            src={file.preview_url || file.thumbnail_url}
                            alt="result"
                            style={{ height: 150, objectFit: 'cover', cursor: 'pointer' }}
                            onClick={() => window.open(file.full_url)}
                          />
                        }
                        styles={{ body: { padding: 8 } }}
                      >
                        <Space size={[4, 4]} wrap style={{ marginBottom: 4 }}>
                          {file.tag_names?.map(tag => (
                            <Tag key={tag} color="green" style={{ fontSize: 11 }}>{tag}</Tag>
                          ))}
                        </Space>
                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                          Click image to view full
                        </Text>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Space>
            )}
          </Space>
        </Card>
      </div>
    </div>
  )
}