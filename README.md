# AI Agent Framework Demo Projects

A collection of AI agent implementations using Azure OpenAI, Azure AI Search, and Mem0 for building intelligent, memory-enabled chatbots with document search capabilities.

## 🚀 Projects

### 1. Agent with Search (`agent-with-search/`)

Advanced AI agent with vector search, document processing, and user memory capabilities.

**Features:**
- 🔍 **Hybrid Vector Search** - Semantic search using Azure AI Search with embeddings
- 📄 **Multi-format Document Support** - PDF, DOCX, TXT, CSV, Excel, Images (OCR)
- 🔒 **Document Privacy & Sharing** - User-based access control with sharing capabilities
- 🧠 **Persistent Memory** - User-specific memory using Mem0
- 🎨 **Streamlit UI** - Beautiful web interface for chat and document management
- 📊 **Document Analytics** - Track document ownership, access levels, and search relevance scores

**Tech Stack:**
- Azure OpenAI (GPT-4o + text-embedding-ada-002)
- Azure AI Search (Vector + Semantic search)
- Mem0 (User memory)
- Streamlit (Web UI)
- **Microsoft Entra ID** (OAuth 2.0 authentication)
- Python 3.13+

### 2. Basic Agent Memory (`basic-agent-memory/`)

Simple implementations showcasing different memory patterns for AI agents.

**Includes:**
- `agent-interactive.py` - Interactive chat with memory
- `agent-longmemory.py` - Long-term memory management
- `agent-simplemem.py` - Simple memory implementation
- `main_withapikey.py` - Basic agent with API key authentication

### 3. Basic Chat Agent (`basic-chat-agent/`)

Minimal AI agent implementation demonstrating core chat functionality.

**Features:**
- Simple chat interface
- Azure CLI authentication support
- API key authentication option

## 📋 Prerequisites

- Python 3.13+
- Azure OpenAI resource with deployments:
  - GPT-4o (or similar chat model)
  - text-embedding-ada-002 (for vector search)
- Azure AI Search resource
- Mem0 account and API key
- **Microsoft Entra ID App Registration** (for authentication)
- (Optional) Tesseract OCR for image processing

## 🔐 Entra ID Setup (Required for Authentication)

To enable Microsoft Entra ID authentication, follow these steps:

### Step 1: Create App Registration

1. Go to [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations**
2. Click **+ New registration**
3. Configure:
   - **Name**: `AI Agent Demo` (or your preferred name)
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: Select `Single-page application` and add:
     - `http://localhost:8501` (for Streamlit local dev)
4. Click **Register**

### Step 2: Save Important Values

After registration, note these values from the **Overview** page:
- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Step 3: Configure Authentication

1. Go to **Authentication** in your app registration
2. Under **Single-page application**, ensure redirect URIs include:
   - `http://localhost:8501` (Streamlit)
   - `http://localhost:8501/` (with trailing slash)
3. Enable **Access tokens** and **ID tokens** under Implicit grant

### Step 4: API Permissions (Optional)

For basic profile access, default permissions are sufficient. For custom API access:

1. Go to **Expose an API** → Set Application ID URI (e.g., `api://your-client-id`)
2. Add a scope (e.g., `user_impersonation`)
3. Go to **API permissions** → Add permission → My APIs → Select your scope

### Step 5: Update Environment Variables

Add to your `agent-with-search/.env`:
```env
# Entra ID Authentication
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-client-id
ENTRA_REDIRECT_URI=http://localhost:8501
# Optional: Custom API scope
ENTRA_API_SCOPE=api://your-client-id/user_impersonation
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   cd /path/to/demo1
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies** (for each project)
   ```bash
   # Agent with Search
   pip install -r agent-with-search/requirements.txt
   
   # Basic Agent Memory
   pip install -r basic-agent-memory/requirements.txt
   
   # Basic Chat Agent
   pip install -r basic-chat-agent/requirements.txt
   ```

4. **Set up environment variables**

   Create `.env` files in each project folder:

   **agent-with-search/.env**:
   ```env
   # Azure OpenAI
   AZURE_OPENAI_API_KEY=your_openai_api_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002
   AZURE_OPENAI_RESPONSE_MODEL_ID=gpt-4o
   
   # Azure AI Search
   AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
   AZURE_SEARCH_KEY=your_search_key
   
   # Mem0
   MEM0_API_KEY=your_mem0_api_key
   
   # Entra ID Authentication
   ENTRA_TENANT_ID=your-tenant-id
   ENTRA_CLIENT_ID=your-client-id
   ENTRA_REDIRECT_URI=http://localhost:8501
   # ENTRA_API_SCOPE=api://your-client-id/user_impersonation  # Optional
   ```

   **basic-agent-memory/.env** and **basic-chat-agent/.env**:
   ```env
   AZURE_OPENAI_API_KEY=your_openai_api_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
   ```

## 🎯 Usage

### Agent with Search - Streamlit UI (with Entra ID Auth)

```bash
cd agent-with-search
streamlit run app_with_auth.py
```

This version requires Microsoft sign-in. Users authenticate with their organizational account before accessing the chat.

**Features:**
- 🔐 Microsoft Entra ID sign-in
- Upload documents (PDF, DOCX, TXT, CSV, Excel, Images)
- Set document privacy (private/shared/public)
- Chat with AI using document context
- User identity from Azure AD (email-based)
- View and manage memories
- Delete documents

### Agent with Search - Streamlit UI (without Auth)

```bash
cd agent-with-search
streamlit run app.py
```

Manual user ID input (for testing/development).

### Agent with Search - CLI (with Entra ID Auth)

```bash
cd agent-with-search
python documentai_with_auth.py
```

Uses device code flow - you'll see a code to enter at https://microsoft.com/devicelogin.

**Commands:**
- `/upload <file_path>` - Upload a document
- `/uploadblob <url>` - Upload from Azure Blob Storage
- `/share <doc_name> <emails>` - Share document with users (comma-separated emails)
- `/docs` - List accessible documents
- `/delete <doc_name>` - Delete a document
- `/memories` - View your memories
- `/whoami` - Show current user info
- `/quit` - Exit

### Agent with Search - CLI (without Auth)

```bash
cd agent-with-search
python documentai.py
```

**Commands:**
- `/upload <file_path>` - Upload a document
- `/uploadblob <url>` - Upload from Azure Blob Storage
- `/share <doc_name> <users>` - Share document with users
- `/docs` - List accessible documents
- `/delete <doc_name>` - Delete a document
- `/memories` - View your memories
- `/switch <user_id>` - Switch user context
- `/quit` - Exit

### Basic Chat Agent

```bash
cd basic-chat-agent
python main.py
```

## 🔐 Security & Privacy

### Entra ID Authentication

The `agent-with-search` project now supports Microsoft Entra ID authentication:

- **OAuth 2.0 + PKCE** - Industry-standard secure authentication for SPAs
- **Device Code Flow** - For CLI applications without browser access
- **User Identity** - Email/UPN used as user_id for document access control
- **No Client Secret** - Public client authentication (safe for SPAs)

### Document Access Control

The `agent-with-search` project implements multi-level access control:

1. **Private Documents** - Only accessible by the owner
2. **Shared with Specific Users** - Accessible by owner + specified users (by email)
3. **Public Documents** - Accessible by all users

### Memory Isolation

- User memories are stored separately in Mem0
- Each user has their own conversation history
- Switching users creates a new context

### Best Practices

- Never commit `.env` files (already in `.gitignore`)
- Rotate API keys if exposed
- Use Entra ID authentication in production
- Share documents using email addresses (matches Entra ID identity)
- Enable MFA in your Entra ID tenant for enhanced security

## 🏗️ Architecture

### Agent with Search

```
┌─────────────┐      ┌──────────────────┐
│  Streamlit  │─────>│  Microsoft       │
│     UI      │<─────│  Entra ID        │
└──────┬──────┘      │  (OAuth 2.0)     │
       │             └──────────────────┘
       v
┌─────────────────────┐      ┌──────────────┐
│  Agent Framework    │─────>│ Azure OpenAI │
│  (Chat + Memory)    │      │   (GPT-4o)   │
└──────┬──────────────┘      └──────────────┘
       │
       v
┌─────────────────────┐      ┌──────────────┐
│ Document Processing │─────>│ Azure OpenAI │
│   + Embeddings      │      │  (Embeddings)│
└──────┬──────────────┘      └──────────────┘
       │
       v
┌─────────────────────┐      ┌──────────────┐
│  Azure AI Search    │<─────│     Mem0     │
│  (Vector + Hybrid)  │      │   (Memory)   │
└─────────────────────┘      └──────────────┘
```

### Key Components

1. **Document Processing**
   - Text extraction (PDF, DOCX, TXT, CSV, Excel)
   - OCR for images (Tesseract)
   - Chunking with overlap (1000 words, 200 overlap)

2. **Vector Search**
   - Text embeddings via Azure OpenAI
   - HNSW vector index
   - Hybrid search (keyword + vector + semantic)

3. **Access Control**
   - Entra ID user authentication
   - Email-based user identity
   - Owner-based filtering
   - Shared document lists
   - User-specific search results

4. **Memory Management**
   - Conversation history
   - User preferences
   - Context-aware responses

## 📊 Document Search Flow

1. User uploads document
2. Document is chunked into segments
3. Each chunk gets an embedding (vector)
4. Chunks stored in Azure AI Search with metadata
5. User query is converted to embedding
6. Hybrid search finds relevant chunks
7. Semantic reranking improves relevance
8. Top results sent to AI as context

## 🧪 Testing

Test different user scenarios:

```python
# Terminal 1: User Alice
streamlit run app.py
# Set user_id: alice
# Upload private document

# Terminal 2: User Bob
streamlit run app.py
# Set user_id: bob
# Try to access Alice's document (should fail)
# Upload public document (Alice can see it)
```

## 🤝 Contributing

Feel free to extend these implementations with:
- Additional document formats
- More authentication methods
- Advanced search features
- Multi-modal capabilities (vision, audio)
- Analytics and monitoring

## 📝 License

This is a demo project for learning purposes.

## 🆘 Troubleshooting

### Common Issues

**"Unsupported data type" error when generating embeddings**
- Check that `AZURE_OPENAI_ENDPOINT` is the base URL only
- Should be: `https://your-resource.openai.azure.com/`
- Not: `https://your-resource.openai.azure.com/openai/deployments/...`

**Token expiration (AADSTS70043)**
- Run `az account clear && az login`
- Use API key authentication instead
- Check Conditional Access policies with your Azure admin

**No documents found in search**
- Verify index exists in Azure AI Search
- Check user_id matches between upload and search
- Ensure embeddings were generated successfully

**OCR not working**
- Install Tesseract: `brew install tesseract` (Mac) or `sudo apt-get install tesseract-ocr` (Linux)
- Verify installation: `tesseract --version`

## 🎓 Learning Resources

- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search Vector Search](https://learn.microsoft.com/azure/search/vector-search-overview)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [Agent Framework Documentation](https://github.com/microsoft/agent-framework)

## 🔄 Version History

- **v1.0** - Initial implementation with basic chat
- **v2.0** - Added vector search and document processing
- **v3.0** - Implemented privacy controls and document sharing
- **v4.0** - Enhanced UI and multi-format support

---

Built with ❤️ using Azure AI Services
