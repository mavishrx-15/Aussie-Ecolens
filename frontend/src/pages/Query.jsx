import { useState } from "react";
import {
  Input,
  Button,
  Card,
  Typography,
  Tag,
  Row,
  Col,
  Empty,
  Spin,
  Tabs,
  Space,
  message,
} from "antd";
import { SearchOutlined, PlusOutlined } from "@ant-design/icons";
import axios from "axios";
import { QUERY_API_BASE_URL } from "../config";
import { getToken } from "../auth";

const { Title, Text } = Typography;

const COMMON_SPECIES = [
  "cattle",
  "dingo",
  "australian magpie",
  "laughing kookaburra",
  "common wombat",
  "eastern gray kangaroo",
  "australian echidna",
  "swamp wallaby",
  "common brushtail",
  "australian brushturkey",
  "southern cassowary",
  "wild boar",
  "red fox",
  "domestic cat",
  "human",
];

export default function Query() {
  // Tag search state
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState("");
  const [countInput, setCountInput] = useState(1);

  // Species search state
  const [species, setSpecies] = useState([]);
  const [speciesInput, setSpeciesInput] = useState("");

  // Thumbnail search state
  const [thumbnailUrl, setThumbnailUrl] = useState("");
  const [fullImageUrl, setFullImageUrl] = useState("");

  // Shared state
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  // Controls Empty display — only for tag/species searches
  const [hasSearched, setHasSearched] = useState(false);

  const addTag = () => {
    if (!tagInput.trim()) return;
    setTags([...tags, { name: tagInput.toLowerCase(), count: countInput }]);
    setTagInput("");
    setCountInput(1);
  };

  const removeTag = (index) => {
    setTags(tags.filter((_, i) => i !== index));
    setResults([]);
    setHasSearched(false);
  };

  const addSpecies = (name) => {
    const val = (name || speciesInput).toLowerCase().trim();
    if (!val || species.includes(val)) return;
    setSpecies([...species, val]);
    if (!name) setSpeciesInput("");
  };

  const removeSpecies = (index) => {
    setSpecies(species.filter((_, i) => i !== index));
    setResults([]);
    setHasSearched(false);
  };

  // Reset all state on tab switch
  const handleTabChange = () => {
    setTags([]);
    setTagInput("");
    setCountInput(1);
    setSpecies([]);
    setSpeciesInput("");
    setThumbnailUrl("");
    setResults([]);
    setFullImageUrl("");
    setHasSearched(false);
  };

  const handleTagSearch = async () => {
    if (tags.length === 0) {
      message.warning("Please add at least one tag");
      return;
    }
    setLoading(true);
    setHasSearched(true);
    try {
      const token = await getToken();
      const query = {};
      tags.forEach((t) => (query[t.name] = t.count));
      const res = await axios.post(`${QUERY_API_BASE_URL}/query/tags`, query, {
        headers: { Authorization: token },
      });
      setResults(res.data.results || []);
      if (res.data.results?.length === 0) message.info("No results found");
    } catch (err) {
      message.error("Query failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSpeciesSearch = async () => {
    if (species.length === 0) {
      message.warning("Please add at least one species");
      return;
    }
    setLoading(true);
    setHasSearched(true);
    try {
      const token = await getToken();
      const res = await axios.post(
        `${QUERY_API_BASE_URL}/query/species`,
        { species },
        {
          headers: { Authorization: token },
        },
      );
      setResults(res.data.results || []);
      if (res.data.results?.length === 0) message.info("No results found");
    } catch (err) {
      message.error("Query failed");
    } finally {
      setLoading(false);
    }
  };

  const [thumbnailResult, setThumbnailResult] = useState(null);

  const handleThumbnailSearch = async () => {
    if (!thumbnailUrl.trim()) {
      message.warning("Please enter a thumbnail URL");
      return;
    }
    setLoading(true);
    setFullImageUrl("");
    setThumbnailResult(null);
    try {
      const token = await getToken();
      const res = await axios.post(
        `${QUERY_API_BASE_URL}/query/thumbnail`,
        { thumbnail_url: thumbnailUrl },
        { headers: { Authorization: token } },
      );
      setFullImageUrl(res.data.full_url || res.data.original_url || "");
      setThumbnailResult(res.data);
      if (!res.data.full_url && !res.data.original_url)
        message.info("No original image found");
    } catch (err) {
      message.error("Query failed");
    } finally {
      setLoading(false);
    }
  };

  const items = [
    {
      key: "1",
      label: "Search by Tags",
      children: (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space.Compact style={{ width: "100%" }}>
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
              type="primary"
              style={{ background: "#2e7d32", borderColor: "#2e7d32" }}
            >
              Add
            </Button>
          </Space.Compact>
          <Space size={[8, 4]} wrap>
            {tags.map((tag, i) => (
              <Tag
                key={i}
                closable
                onClose={() => removeTag(i)}
                color="green"
                style={{ fontSize: 14, padding: "4px 10px" }}
              >
                {tag.name} ≥ {tag.count}
              </Tag>
            ))}
          </Space>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleTagSearch}
            size="large"
            block
            style={{ background: "#2e7d32", borderColor: "#2e7d32" }}
          >
            Search
          </Button>
        </Space>
      ),
    },
    {
      key: "2",
      label: "Search by Species",
      children: (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="Species (e.g. dingo)"
              value={speciesInput}
              onChange={(e) => setSpeciesInput(e.target.value)}
              onPressEnter={() => addSpecies()}
              size="large"
            />
            <Button
              icon={<PlusOutlined />}
              onClick={() => addSpecies()}
              size="large"
              type="primary"
              style={{ background: "#2e7d32", borderColor: "#2e7d32" }}
            >
              Add
            </Button>
          </Space.Compact>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Quick select:
            </Text>
            <Space size={[6, 6]} wrap style={{ marginTop: 6 }}>
              {COMMON_SPECIES.map((s) => (
                <Tag.CheckableTag
                  key={s}
                  checked={species.includes(s)}
                  onChange={(checked) =>
                    checked ? addSpecies(s) : removeSpecies(species.indexOf(s))
                  }
                  style={{
                    fontSize: 12,
                    padding: "3px 10px",
                    borderRadius: 20,
                  }}
                >
                  {s}
                </Tag.CheckableTag>
              ))}
            </Space>
          </div>
          <Space size={[8, 4]} wrap>
            {species.map((s, i) => (
              <Tag
                key={i}
                closable
                onClose={() => removeSpecies(i)}
                color="green"
                style={{ fontSize: 14, padding: "4px 10px" }}
              >
                {s}
              </Tag>
            ))}
          </Space>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSpeciesSearch}
            size="large"
            block
            style={{ background: "#2e7d32", borderColor: "#2e7d32" }}
          >
            Search
          </Button>
        </Space>
      ),
    },
    {
      key: "3",
      label: "Search by Thumbnail URL",
      children: (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Input
            placeholder="Paste thumbnail URL here"
            value={thumbnailUrl}
            onChange={(e) => setThumbnailUrl(e.target.value)}
            size="large"
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleThumbnailSearch}
            size="large"
            block
            style={{ background: "#2e7d32", borderColor: "#2e7d32" }}
          >
            Find Original
          </Button>
          {thumbnailResult && (
            <Space direction="vertical" style={{ width: "100%" }} size="small">
              <Text strong>Original file found:</Text>
              <div
                style={{ position: "relative", cursor: "pointer" }}
                onClick={() => window.open(thumbnailResult.full_url)}
              >
                <img
                  src={thumbnailResult.thumbnail_url}
                  alt="thumbnail"
                  style={{ width: "100%", borderRadius: 8 }}
                />
                {thumbnailResult.full_url?.includes(".mp4") ||
                thumbnailResult.full_url?.includes("/videos/") ? (
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "50%",
                      transform: "translate(-50%, -50%)",
                      background: "rgba(0,0,0,0.5)",
                      borderRadius: "50%",
                      width: 50,
                      height: 50,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <span style={{ color: "white", fontSize: 20 }}>▶</span>
                  </div>
                ) : null}
              </div>
              <Button
                size="small"
                block
                onClick={() => {
                  navigator.clipboard.writeText(thumbnailResult.full_url);
                  message.success("URL copied!");
                }}
              >
                Copy full URL
              </Button>
            </Space>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #e6f4ea 0%, #c8e6c9 100%)",
        padding: "40px 24px",
      }}
    >
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <Space
          direction="vertical"
          align="center"
          style={{ width: "100%", marginBottom: 32 }}
        >
          <Title level={2} style={{ color: "#2e7d32", marginBottom: 0 }}>
            Search Wildlife
          </Title>
          <Text type="secondary">
            Search files by species, tags, or thumbnail URL
          </Text>
        </Space>

        <Card
          style={{ borderRadius: 16, marginBottom: 24 }}
          styles={{ body: { padding: 32 } }}
        >
          <Tabs items={items} onChange={handleTabChange} />
        </Card>

        {loading && (
          <Space
            style={{
              width: "100%",
              justifyContent: "center",
              padding: "40px 0",
            }}
          >
            <Spin size="large" />
          </Space>
        )}

        {/* Tag/species search results grid */}
        {!loading && results.length > 0 && (
          <Row gutter={[16, 16]}>
            {results.map((file, i) => (
              <Col key={i} xs={12} sm={8} md={6}>
                <Card
                  hoverable
                  cover={
                    <img
                      src={file.thumbnail_url || file.preview_url}
                      alt="result"
                      style={{
                        height: 150,
                        objectFit: "cover",
                        cursor: "pointer",
                      }}
                      onClick={() => window.open(file.full_url)}
                    />
                  }
                  styles={{ body: { padding: 8 } }}
                >
                  <Space size={[4, 4]} wrap style={{ marginBottom: 4 }}>
                    {file.tag_names?.map((tag) => (
                      <Tag key={tag} color="green" style={{ fontSize: 12 }}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                  <Button
                    size="small"
                    block
                    onClick={() => {
                      navigator.clipboard.writeText(
                        file.thumbnail_url || file.preview_url,
                      );
                      message.success("Thumbnail URL copied!");
                    }}
                  >
                    Copy thumbnail URL
                  </Button>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    Click image to view full
                  </Text>
                </Card>
              </Col>
            ))}
          </Row>
        )}

        {/* Only show after tag/species search, not thumbnail */}
        {!loading && hasSearched && results.length === 0 && (
          <Empty description="No results found" />
        )}
      </div>
    </div>
  );
}
