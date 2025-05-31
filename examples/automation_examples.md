# Data Processing Pipeline System - Automation Examples

## 1. API Data Ingestion Examples

### Example 1: Weather Data Collection
```bash
# Create an API source that polls weather data every 5 minutes
curl -X POST "http://localhost:5000/api/v1/api-sources" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weather Data Collector",
    "url": "https://api.openweathermap.org/data/2.5/weather",
    "method": "GET",
    "params": {
      "q": "New York",
      "appid": "YOUR_API_KEY"
    },
    "poll_interval": 300,
    "enabled": true,
    "pipeline_id": "your-weather-pipeline-id",
    "data_format": "json"
  }'
```

### Example 2: Stock Price Monitoring
```bash
# Monitor stock prices with authentication
curl -X POST "http://localhost:5000/api/v1/api-sources" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stock Price Monitor",
    "url": "https://api.example-finance.com/stocks/AAPL",
    "method": "GET",
    "headers": {
      "Authorization": "Bearer YOUR_TOKEN"
    },
    "poll_interval": 60,
    "enabled": true,
    "pipeline_id": "stock-analysis-pipeline"
  }'
```

## 2. Webhook Setup Examples

### Example 1: GitHub Webhook for Code Analysis
```bash
# Create webhook for GitHub events
curl -X POST "http://localhost:5000/api/v1/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub Code Analysis",
    "endpoint_path": "github-events",
    "pipeline_id": "code-analysis-pipeline",
    "secret_token": "your-webhook-secret",
    "data_mapping": {
      "repository": "repository.name",
      "commit_id": "head_commit.id",
      "author": "head_commit.author.name"
    }
  }'
```

### Example 2: E-commerce Order Processing
```bash
# Create webhook for order notifications
curl -X POST "http://localhost:5000/api/v1/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order Processing",
    "endpoint_path": "orders",
    "pipeline_id": "order-fulfillment-pipeline",
    "enabled": true
  }'
```

## 3. File Upload Triggers

### Example 1: CSV File Processing
```bash
# Create trigger for CSV files
curl -X POST "http://localhost:5000/api/v1/file-triggers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CSV Data Processor",
    "watch_path": "uploads",
    "pipeline_id": "csv-processing-pipeline",
    "file_patterns": ["*.csv", "*.CSV"],
    "enabled": true
  }'

# Start file watching
curl -X POST "http://localhost:5000/api/v1/file-triggers/start-watching"
```

### Example 2: Image Analysis Trigger
```bash
# Create trigger for image files
curl -X POST "http://localhost:5000/api/v1/file-triggers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Image Analyzer",
    "watch_path": "uploads/images",
    "pipeline_id": "image-analysis-pipeline",
    "file_patterns": ["*.jpg", "*.png", "*.jpeg"],
    "enabled": true
  }'
```

## 4. Complete Automation Workflow

### Step 1: Create a Data Processing Pipeline
```bash
curl -X POST "http://localhost:5000/api/v1/pipelines" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Data Analysis",
    "description": "Automated sales data processing and analysis",
    "steps": [
      {
        "name": "Load Sales Data",
        "type": "load",
        "source_path": "api_data.json",
        "format": "json"
      },
      {
        "name": "Clean Data",
        "type": "transform",
        "operations": [
          {"type": "dropna"},
          {"type": "convert_types", "columns": {"amount": "float", "date": "datetime"}}
        ]
      },
      {
        "name": "Calculate Monthly Totals",
        "type": "aggregate",
        "group_by": ["month"],
        "aggregations": {"amount": "sum", "transactions": "count"}
      },
      {
        "name": "Save Results",
        "type": "save",
        "output_path": "outputs/monthly_sales.csv",
        "format": "csv"
      }
    ]
  }'
```

## 5. Testing Your Setup

### Test API Connection
```bash
curl -X POST "http://localhost:5000/api/v1/api-sources/{source-id}/test"
```

### Send Test Webhook Data
```bash
curl -X POST "http://localhost:5000/api/v1/webhook/your-endpoint" \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "timestamp": "2024-01-01T00:00:00Z"}'
```

### Upload Test File (triggers file processing)
```bash
curl -X POST "http://localhost:5000/api/v1/files/upload" \
  -F "file=@test_data.csv"
```