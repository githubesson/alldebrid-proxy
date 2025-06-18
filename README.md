# AllDebrid API

A simple FastAPI application that acts as a proxy for downloading files from various downloaders through AllDebrid. 

## WARNING

You need a server that isn't blocked on alldebrid for this to work. This api is intended for low-spec vpses that act as proxies for automating alldebrid use (for example, if you have a dedicated server with ovh which is blocked from alldebrid, you can get the cheapest box somewhere that isn't blocked and host this api on it, essentially acting as a proxy for alldebrid - could you do it with a normal http proxy? probably, but the ones that are supposedly unblocked are literally more expensive than the box I'm using for this. lol.).

**ANY ISSUES ABOUT IP BLOCKS WILL BE CLOSED WITHOUT FURTHER INVESTIGATION.**

## Features

- ✅ Authenticates with AllDebrid on startup using API key
- ✅ Accepts links from 80+ file hosting services via REST API
- ✅ **Browse multi-file links** (folders, collections) before downloading
- ✅ Unlocks links through AllDebrid with automatic filename detection
- ✅ Streams downloads back to the client
- ✅ Password-protected link support
- ✅ Static token authentication for API access
- ✅ Proper error handling and logging

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   # Required: Your AllDebrid API key
   export ALLDEBRID_API_KEY="your_alldebrid_api_key_here"
   
   # Optional: Your proxy API token
   export API_TOKEN="your-custom-api-token"
   ```

3. **Run the server:**
   ```bash
   python main.py
   ```
   
   Or for production:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Usage

### Authentication

All API endpoints (except `/`) require a Bearer token in the Authorization header:

```bash
Authorization: Bearer your-custom-api-token
```

### Endpoints

#### `GET /` - Health Check
Returns the API status.

```bash
curl http://localhost:8000/
```

#### `GET /status` - Service Status
Returns the AllDebrid authentication status.

```bash
curl -H "Authorization: Bearer your-custom-api-token" \
     http://localhost:8000/status
```

#### `POST /download` - Download File
Downloads a file from various file hosts through AllDebrid.

**Request Body:**
```json
{
  "url": "https://mega.nz/file/...",
  "filename": "optional-filename.zip" - if not provided, itll get filled in with whatever the alldebrid api returns
}
```

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer your-custom-api-token" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://mega.nz/file/ABC123", "filename": "my-file.zip"}' \
     -o downloaded-file.zip \
     http://localhost:8000/download
```

#### `POST /browse` - Browse Multi-File Links
Browse the contents of multi-file links (folders, archives, etc.) before downloading. Perfect for mega.nz folders, rapidgator collections, and other multi-file links.

**Request Body:**
```json
{
  "url": "https://mega.nz/folder/...",
  "password": "optional-password-for-protected-links"
}
```

**Response:**
```json
{
  "url": "https://mega.nz/folder/ABC123",
  "total_files": 5,
  "password_protected": false,
  "files": [
    {
      "filename": "video1.mp4",
      "size": 1073741824,
      "size_human": "1.00 GB",
      "link": "https://redirect.alldebrid.com/...",
      "host": "mega.nz",
      "hostDomain": "mega.nz",
      "supported": true
    }
  ]
}
```

**Examples:**

Browse a mega.nz folder:
```bash
curl -X POST \
     -H "Authorization: Bearer your-custom-api-token" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://mega.nz/folder/ABC123#DEF456"}' \
     http://localhost:8000/browse
```

Browse a password-protected link:
```bash
curl -X POST \
     -H "Authorization: Bearer your-custom-api-token" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://rapidgator.net/folder/xyz", "password": "secret123"}' \
     http://localhost:8000/browse
```

**Use Cases:**
- 📂 Browse mega.nz folders before downloading specific files
- 🔍 Preview rapidgator/1fichier collections 
- 📋 Get file listings with sizes and metadata
- 🔐 Handle password-protected multi-file links
- 🎯 Select specific files from large collections

### Response

The `/download` endpoint returns a streaming response with the file content. The file will be downloaded directly to your client.

## Typical Workflow

### Scenario: Download specific files from a mega.nz folder

1. **First, browse the folder** to see what's available:
```bash
curl -X POST \
     -H "Authorization: Bearer your-custom-api-token" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://mega.nz/folder/ABC123#DEF456"}' \
     http://localhost:8000/browse
```

2. **Review the response** to see all files:
```json
{
  "total_files": 10,
  "files": [
    {
      "filename": "movie1.mkv",
      "size_human": "4.2 GB",
      "link": "https://redirect.alldebrid.com/file1..."
    },
    {
      "filename": "movie2.mp4", 
      "size_human": "2.8 GB",
      "link": "https://redirect.alldebrid.com/file2..."
    }
  ]
}
```

3. **Download specific files** using their individual links:
```bash
curl -X POST \
     -H "Authorization: Bearer your-custom-api-token" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://redirect.alldebrid.com/file1..."}' \
     -o movie1.mkv \
     http://localhost:8000/download
```

This workflow is perfect for large collections where you only want specific files!

## Configuration

The following environment variables can be configured:

- `ALLDEBRID_API_KEY` (required): Your AllDebrid API key
- `API_TOKEN` (optional): Static token for API authentication (defaults to "your-custom-api-token")

## Getting AllDebrid API Key

1. Log in to your AllDebrid account
2. Go to https://alldebrid.com/apikeys/
3. Generate or copy your API key
4. Set it as the `ALLDEBRID_API_KEY` environment variable

## Error Handling

The API includes comprehensive error handling:

- **403**: Invalid authentication token
- **500**: AllDebrid authentication failure, link unlock failure, or download errors
- **4xx/5xx**: HTTP errors from AllDebrid or file servers

## Development

For development with auto-reload:

```bash
python main.py
```

If you encounter any errors open a pull request with a fix!

The API will be available at `http://localhost:8000` with automatic reloading on code changes. 

## Contact

Twitter - https://x.com/7N7  
Others - https://misleadi.ng/