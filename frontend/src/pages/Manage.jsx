import { useState } from 'react'
import { Input, Button, Typography, Tag, Space, Divider, message, Card, Upload } from 'antd'
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

  // File tag query
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

  const handleTagOperation = async (operation) => {
    if (urls.length === 0 || tags.length === 0) {
      message.warning('Please add at least one URL and one tag')
      return
    }
    setLoading(true)
    try {
      const token = await getToken()
      await axios.post(`${QUERY_API_BASE_URL}/tags/bulk`, {
        urls,
        tags,
        operation
      }, {
        headers: { Authorization: token }
      })
      message.success(operation === 1 ? 'Tags added successfully' : 'Tags removed successfully')
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
      setUrls([])
    } catch (err) {
      message.error('Delete failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFileQuery = async (file) => {
    setFileLoading(true)
    try {
      const token = await getToken()
      const formData = new FormData()
      formData.append('file', file)
      const res = await axios.post(`${QUERY_API_BASE_URL}/query/file-tags`,
        { detected_tags: [file.name.split('.')[0]] },
        { headers: { Authorization: token } }
      )
      setFileResults(res.data.results || [])
      if (res.data.results?.length === 0) message.info('No matching files found')
    } catch (err) {
      message.error('Query failed')
    } finally {
      setFileLoading(false)
    }
    return false
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

        {/* Tag management */}
        <Card style={{ borderRadius: 16, marginBottom: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
          <Title level={5}>File URLs</Title>
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <Input
              placeholder="Paste file URL here"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onPressEnter={addUrl}
              size="large"
            />
            <Button onClick={addUrl} size="large" style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}>
              Add
            </Button>
          </Space.Compact>

          <div style={{ marginBottom: 16, minHeight: 32 }}>
            {urls.map((url, i) => (
              <Tag key={i} closable onClose={() => removeUrl(i)} style={{ marginBottom: 4 }}>
                {url.length > 60 ? url.substring(0, 60) + '...' : url}
              </Tag>
            ))}
          </div>

          <Divider />

          <Title level={5}>Tags</Title>
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <Input
              placeholder="Species name (e.g. koala)"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onPressEnter={addTag}
              size="large"
            />
            <Button onClick={addTag} size="large" style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}>
              Add
            </Button>
          </Space.Compact>

          <div style={{ marginBottom: 24, minHeight: 32 }}>
            {tags.map((tag, i) => (
              <Tag key={i} closable onClose={() => removeTag(i)} color="green" style={{ marginBottom: 4 }}>
                {tag}
              </Tag>
            ))}
          </div>

          <Divider />

          <Space style={{ width: '100%', justifyContent: 'center' }} size="middle">
            <Button icon={<PlusOutlined />} size="large" loading={loading} style={{ background: '#2e7d32', borderColor: '#2e7d32', color: 'white' }} onClick={() => handleTagOperation(1)}>
              Add Tags
            </Button>
            <Button icon={<TagOutlined />} size="large" loading={loading} onClick={() => handleTagOperation(0)}>
              Remove Tags
            </Button>
            <Button icon={<DeleteOutlined />} size="large" danger loading={loading} onClick={handleDelete}>
              Delete Files
            </Button>
          </Space>
        </Card>

        {/* Query by file */}
        <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
          <Title level={5}>Search by File</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            Upload a file to find all matching files in the database
          </Text>
          <Dragger beforeUpload={handleFileQuery} showUploadList={false} accept="image/*,video/*">
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ color: '#2e7d32', fontSize: 40 }} />
            </p>
            <p className="ant-upload-text">Click or drag file to search</p>
          </Dragger>

          {fileLoading && <div style={{ textAlign: 'center', padding: 24 }}>Searching...</div>}

          {fileResults.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Title level={5}>Matching Files</Title>
              {fileResults.map((file, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <a href={file.original_url} target="_blank" rel="noreferrer">{file.original_url}</a>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}