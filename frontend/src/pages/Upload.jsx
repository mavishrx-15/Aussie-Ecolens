import { useState } from 'react'
import { Upload, Button, Typography, message, Progress } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import axios from 'axios'
import { API_BASE_URL } from '../config'

const { Title, Text } = Typography
const { Dragger } = Upload

export default function UploadPage() {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const handleUpload = async (file) => {
    setUploading(true)
    setProgress(0)
    try {
      // Step 1: Get presigned URL
      const res = await axios.post(`${API_BASE_URL}/upload-url`, {
        filename: file.name
      })
      const { uploadUrl } = res.data

      // Step 2: Upload to S3
      await axios.put(uploadUrl, file, {
        headers: { 'Content-Type': file.type },
        onUploadProgress: (e) => {
          setProgress(Math.round((e.loaded / e.total) * 100))
        }
      })

      message.success(`${file.name} uploaded successfully!`)
    } catch (err) {
      message.error('Upload failed, please try again.')
    } finally {
      setUploading(false)
    }
    return false
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)',
      padding: '40px 24px'
    }}>
      <div style={{ maxWidth: 600, margin: '0 auto' }}>

        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32' }}>Upload Media</Title>
          <Text type="secondary">Upload images or videos for wildlife detection</Text>
        </div>

        <div style={{
          background: 'white',
          borderRadius: 16,
          padding: 32,
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)'
        }}>
          <Dragger
            beforeUpload={handleUpload}
            accept="image/*,video/*"
            showUploadList={false}
            disabled={uploading}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ color: '#2e7d32', fontSize: 48 }} />
            </p>
            <p className="ant-upload-text">Click or drag file to upload</p>
            <p className="ant-upload-hint">
              Supports JPG, PNG, MP4. Wildlife species will be auto-detected.
            </p>
          </Dragger>

          {uploading && (
            <div style={{ marginTop: 24 }}>
              <Progress percent={progress} strokeColor="#2e7d32" />
              <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginTop: 8 }}>
                Uploading...
              </Text>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}