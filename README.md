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
- (Optional) Tesseract OCR for image processing

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
   AZURE_OPENAI_API_KEY=your_openai_api_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002
   AZURE_OPENAI_RESPONSE_MODEL_ID=gpt-4o
   
   AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
   AZURE_SEARCH_KEY=your_search_key
   
   MEM0_API_KEY=your_mem0_api_key
   ```

   **basic-agent-memory/.env** and **basic-chat-agent/.env**:
   ```env
   AZURE_OPENAI_API_KEY=your_openai_api_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
   ```

## 🎯 Usage

### Agent with Search - Streamlit UI

```bash
cd agent-with-search
streamlit run app.py
```

**Features:**
- Upload documents (PDF, DOCX, TXT, CSV, Excel, Images)
- Set document privacy (private/shared/public)
- Chat with AI using document context
- Switch between users
- View and manage memories
- Delete documents

### Agent with Search - CLI

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

### Document Access Control

The `agent-with-search` project implements multi-level access control:

1. **Private Documents** - Only accessible by the owner
2. **Shared with Specific Users** - Accessible by owner + specified users
3. **Public Documents** - Accessible by all users

### Memory Isolation

- User memories are stored separately in Mem0
- Each user has their own conversation history
- Switching users creates a new context

### Best Practices

- Never commit `.env` files (already in `.gitignore`)
- Rotate API keys if exposed
- Use Azure CLI authentication in production when possible
- Implement proper user authentication in production deployments

## 🏗️ Architecture

### Agent with Search

```
┌─────────────┐
│  Streamlit  │
│     UI      │
└──────┬──────┘
       │
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
