import { useEffect, useState } from 'react'
import { Card, Typography, Statistic, Row, Col, Spin } from 'antd'
import axios from 'axios'
import { GCP_STATS_URL } from '../config'

const { Title, Text } = Typography

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get(GCP_STATS_URL).then(res => {
      setStats(res.data)
    }).finally(() => setLoading(false))
  }, [])

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)',
      padding: '40px 24px'
    }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#2e7d32' }}>Wildlife Statistics</Title>
          <Text type="secondary">Powered by GCP Cloud Run</Text>
        </div>

        {loading && <div style={{ textAlign: 'center' }}><Spin size="large" /></div>}

        {stats && (
          <>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col span={12}>
                <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)', textAlign: 'center' }}>
                  <Statistic
                    title="Total Files"
                    value={stats.total_files}
                    valueStyle={{ color: '#2e7d32' }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)', textAlign: 'center' }}>
                  <Statistic
                    title="Most Common Species"
                    value={stats.most_common_species}
                    valueStyle={{ color: '#2e7d32', fontSize: 20 }}
                  />
                </Card>
              </Col>
            </Row>

            <Card style={{ borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
              <Title level={5}>Species Breakdown</Title>
              {Object.entries(stats.species_count)
                .sort((a, b) => b[1] - a[1])
                .map(([species, count]) => (
                  <div key={species} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text style={{ textTransform: 'capitalize' }}>{species}</Text>
                      <Text strong>{count} files</Text>
                    </div>
                    <div style={{ background: '#e8f5e9', borderRadius: 4, height: 8 }}>
                      <div style={{
                        background: '#2e7d32',
                        borderRadius: 4,
                        height: 8,
                        width: `${(count / stats.total_files) * 100}%`
                      }} />
                    </div>
                  </div>
                ))}
            </Card>
          </>
        )}
      </div>
    </div>
  )
}