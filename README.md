# AllDebrid API

A simple FastAPI application that acts as a proxy for downloading files from various downloaders through AllDebrid. 

## WARNING

You need a server that isn't blocked on alldebrid for this to work. This api is intended for low-spec vpses that act as proxies for automating alldebrid use (for example, if you have a dedicated server with ovh which is blocked from alldebrid, you can get the cheapest box somewhere that isn't blocked and host this api on it, essentially acting as a proxy for alldebrid - could you do it with a normal http proxy? probably, but the ones that are supposedly unblocked are literally more expensive than the box I'm using for this. lol.).

**ANY ISSUES ABOUT IP BLOCKS WILL BE CLOSED WITHOUT FURTHER INVESTIGATION.**

## Features

- ✅ Authenticates with AllDebrid on startup using API key
- ✅ Accepts links via REST API
- ✅ Unlocks links through AllDebrid
- ✅ Streams downloads back to the client
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
Downloads a file from mega.nz through AllDebrid.

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

### Response

The `/download` endpoint returns a streaming response with the file content. The file will be downloaded directly to your client.

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