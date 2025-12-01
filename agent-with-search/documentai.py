from dotenv import load_dotenv
import os
import asyncio
from pathlib import Path

load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential
from mem0 import MemoryClient

# Azure AI Search imports
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

# For document processing
import pypdf
import docx
import json

# Create Azure OpenAI client
client = AzureOpenAIChatClient(
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
)

# Create Mem0 client
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# Create agent
agent = client.create_agent(
    instructions="You are a helpful assistant that can answer questions based on uploaded documents and remember user information.",
    name="DocumentBot"
)

# Create OpenAI client for embeddings
embedding_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")

class AzureAISearchKnowledgeBase:
    """Knowledge base using Azure AI Search"""
    
    def __init__(self, search_endpoint: str, search_key: str, index_name: str = "documents-index"):
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_name = index_name
        
        # Create index client
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=AzureKeyCredential(search_key)
        )
        
        # Create search client
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key)
        )
        
        # Create index if it doesn't exist
        self._create_index_if_not_exists()
        
        self.uploaded_docs = []
    
    def _create_index_if_not_exists(self):
        """Create the search index with vector search and access control if it doesn't exist"""
        try:
            # Check if index exists
            self.index_client.get_index(self.index_name)
            print(f"✅ Using existing index: {self.index_name}")
        except:
            # Create new index with vector field AND access control
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="document_name", type=SearchFieldDataType.String),
                SimpleField(name="chunk_id", type=SearchFieldDataType.Int32),
                
                # ACCESS CONTROL FIELDS
                SimpleField(name="owner_user_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="is_shared", type=SearchFieldDataType.Boolean, filterable=True),
                SimpleField(
                    name="allowed_users",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True
                ),
                SimpleField(name="uploaded_at", type=SearchFieldDataType.String),
                
                # Keep your existing user_id for backward compatibility
                SimpleField(name="user_id", type=SearchFieldDataType.String, filterable=True),
                
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=1536,
                    vector_search_profile_name="my-vector-profile"
                ),
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="my-hnsw-config")
                ],
                profiles=[
                    VectorSearchProfile(
                        name="my-vector-profile",
                        algorithm_configuration_name="my-hnsw-config"
                    )
                ]
            )
            
            # Configure semantic search
            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")]
                )
            )
            
            semantic_search = SemanticSearch(configurations=[semantic_config])
            
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            self.index_client.create_index(index)
            print(f"✅ Created new index with vector search and access control: {self.index_name}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        with open(file_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    def _extract_txt(self, file_path: str) -> str:
        """Extract text from TXT"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _extract_csv(self, file_path: str) -> str:
        """Extract text from CSV"""
        import pandas as pd
        try:
            df = pd.read_csv(file_path)
            # Convert dataframe to readable text
            text = f"CSV File Content:\n\n"
            text += f"Columns: {', '.join(df.columns)}\n\n"
            text += df.to_string(index=False)
            return text
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return ""

    def _extract_excel(self, file_path: str) -> str:
        """Extract text from Excel (XLSX/XLS)"""
        import pandas as pd
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            text = f"Excel File Content:\n\n"
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                text += f"\n--- Sheet: {sheet_name} ---\n"
                text += f"Columns: {', '.join(df.columns)}\n\n"
                text += df.to_string(index=False)
                text += "\n\n"
            
            return text
        except Exception as e:
            print(f"Error reading Excel: {e}")
            return ""
    
    def _extract_image_ocr(self, file_path: str) -> str:
        """Extract text from image using OCR (Tesseract)"""
        try:
            from PIL import Image
            import pytesseract
            
            # Open image
            image = Image.open(file_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            return f"Image OCR Content:\n\n{text}"
        except Exception as e:
            print(f"Error performing OCR: {e}")
            print("Make sure Tesseract is installed:")
            print("  Mac: brew install tesseract")
            print("  Ubuntu: sudo apt-get install tesseract-ocr")
            return ""

    def upload_document(self, file_path: str, user_id: str = "default_user", 
                   is_shared: bool = False, allowed_users: list = None):
        """Upload and index a document with access control
        
        Args:
            file_path: Path to the document file
            user_id: User ID who owns this document
            is_shared: If True, document is visible to all users
            allowed_users: List of specific user IDs who can access (optional)
        """
        try:
            from datetime import datetime
            
            doc_name = Path(file_path).name
            ext = Path(file_path).suffix.lower()
            
            # Extract text based on file type
            if ext == '.pdf':
                text = self._extract_pdf(file_path)
            elif ext == '.docx':
                text = self._extract_docx(file_path)
            elif ext == '.txt':
                text = self._extract_txt(file_path)
            elif ext == '.csv':
                text = self._extract_csv(file_path)
            elif ext in ['.xlsx', '.xls']:
                text = self._extract_excel(file_path)
            elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                text = self._extract_image_ocr(file_path)
            else:
                print(f"❌ Unsupported file type: {ext}")
                print(f"   Supported: PDF, DOCX, TXT, CSV, XLSX, XLS, PNG, JPG, JPEG, TIFF, BMP")
                return False
            
            if not text or not text.strip():
                print(f"❌ No text extracted from {doc_name}")
                return False
            
            # Chunk the document
            chunks = self._create_chunks(text)
            
            # Create a safe document ID
            safe_doc_name = doc_name.replace('.', '_').replace(' ', '_')
            safe_doc_name = ''.join(c for c in safe_doc_name if c.isalnum() or c in ['_', '-', '='])
            
            # Prepare allowed_users list
            if allowed_users is None:
                allowed_users = []
            
            # Always include the owner in allowed_users
            if user_id not in allowed_users:
                allowed_users.append(user_id)
            
            # Create documents for indexing with embeddings and access control
            documents = []
            upload_time = datetime.now().isoformat()
            
            print(f"📊 Generating embeddings for {len(chunks)} chunks...")
            for idx, chunk in enumerate(chunks):
                embedding = self._generate_embedding(chunk)
                if embedding is None:
                    print(f"⚠️  Skipping chunk {idx} due to embedding error")
                    continue
                    
                doc = {
                    "id": f"{safe_doc_name}_{idx}",
                    "content": chunk,
                    "document_name": doc_name,
                    "chunk_id": idx,
                    "user_id": user_id,  # Keep for backward compatibility
                    # NEW ACCESS CONTROL FIELDS
                    "owner_user_id": user_id,
                    "is_shared": is_shared,
                    "allowed_users": allowed_users,
                    "uploaded_at": upload_time,
                    "content_vector": embedding
                }
                documents.append(doc)
                if (idx + 1) % 10 == 0:
                    print(f"  ✔ Generated {idx + 1}/{len(chunks)} embeddings")
            
            # Upload to Azure AI Search
            result = self.search_client.upload_documents(documents=documents)
            
            self.uploaded_docs.append(doc_name)
            
            # Show access info
            access_info = "shared with all" if is_shared else f"private"
            if allowed_users and len(allowed_users) > 1 and not is_shared:
                access_info = f"shared with {len(allowed_users)} users"
            
            print(f"✅ Uploaded and indexed: {doc_name} ({len(chunks)} chunks, {access_info})")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading document: {e}")
            import traceback
            traceback.print_exc()
            return False
    

    def _create_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200):
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def _generate_embedding(self, text: str):
        """Generate embedding for text using Azure OpenAI"""
        try:
            response = embedding_client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return None
    
    def search(self, query: str, top_k: int = 3, user_id: str = "default_user"):
        """Hybrid search with access control
        
        Args:
            query: Search query
            top_k: Number of results to return
            user_id: Current user's ID (filters results by access)
        """
        try:
            # Build filter for access control
            # User can see:
            # 1. Documents they own (owner_user_id)
            # 2. Shared documents (is_shared = true)
            # 3. Documents where they're in allowed_users list
            
            filter_expression = (
                f"owner_user_id eq '{user_id}' or "
                f"is_shared eq true or "
                f"allowed_users/any(u: u eq '{user_id}')"
            )
            
            # Generate embedding for the query
            query_vector = self._generate_embedding(query)
            
            if query_vector is None:
                print("⚠️  Falling back to keyword search only")
                # Fallback to keyword search
                results = self.search_client.search(
                    search_text=query,
                    top=top_k,
                    filter=filter_expression,
                    select=["content", "document_name", "owner_user_id", "is_shared"]
                )
            else:
                # Hybrid search: vector + keyword
                vector_query = VectorizedQuery(
                    vector=query_vector,
                    k_nearest_neighbors=top_k,
                    fields="content_vector"
                )
                
                results = self.search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    top=top_k,
                    filter=filter_expression,
                    select=["content", "document_name", "owner_user_id", "is_shared"],
                    query_type="semantic",
                    semantic_configuration_name="my-semantic-config"
                )
            
            retrieved_chunks = []
            for result in results:
                retrieved_chunks.append({
                    "content": result["content"],
                    "document_name": result["document_name"],
                    "owner": result.get("owner_user_id", "unknown"),
                    "is_shared": result.get("is_shared", False),
                    "score": result.get("@search.score", 0),
                    "reranker_score": result.get("@search.reranker_score", 0)
                })
            
            return retrieved_chunks
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_documents(self, user_id: str = "default_user", include_shared: bool = True):
        """Get list of documents accessible by user with ownership info
        
        Args:
            user_id: Current user's ID
            include_shared: If True, include shared documents
        """
        try:
            # Build filter
            if include_shared:
                filter_expression = (
                    f"owner_user_id eq '{user_id}' or "
                    f"is_shared eq true or "
                    f"allowed_users/any(u: u eq '{user_id}')"
                )
            else:
                filter_expression = f"owner_user_id eq '{user_id}'"
            
            results = self.search_client.search(
                search_text="*",
                filter=filter_expression,
                select=["document_name", "owner_user_id", "is_shared"],
                top=1000
            )
            
            # Group by document name with ownership info
            docs = {}
            for result in results:
                doc_name = result["document_name"]
                if doc_name not in docs:
                    docs[doc_name] = {
                        "name": doc_name,
                        "owner": result.get("owner_user_id", "unknown"),
                        "is_shared": result.get("is_shared", False),
                        "chunks": 0
                    }
                docs[doc_name]["chunks"] += 1
            
            return list(docs.values())
            
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []
    
    def delete_document(self, doc_name: str, user_id: str = "default_user", is_admin: bool = False):
        """Delete a document (only if user owns it or is admin)
        
        Args:
            doc_name: Name of the document to delete
            user_id: User ID (must own the document)
            is_admin: If True, can delete any document
        """
        try:
            # Check ownership first (unless admin)
            if not is_admin:
                check_results = self.search_client.search(
                    search_text="*",
                    filter=f"document_name eq '{doc_name}' and owner_user_id eq '{user_id}'",
                    top=1
                )
                
                if not any(check_results):
                    print(f"❌ Permission denied: You don't own '{doc_name}'")
                    return False
            
            # Find all chunks for this document
            results = self.search_client.search(
                search_text="*",
                filter=f"document_name eq '{doc_name}'"
            )
            
            # Delete each chunk
            doc_ids = [{"id": result["id"]} for result in results]
            if doc_ids:
                self.search_client.delete_documents(documents=doc_ids)
                if doc_name in self.uploaded_docs:
                    self.uploaded_docs.remove(doc_name)
                print(f"✅ Deleted document: {doc_name}")
                return True
            else:
                print(f"❌ Document not found: {doc_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False

    def share_document(self, doc_name: str, owner_user_id: str, target_user_ids: list):
        """Share a document with specific users
        
        Args:
            doc_name: Name of the document to share
            owner_user_id: Owner of the document
            target_user_ids: List of user IDs to share with
        """
        try:
            # Get all chunks of this document
            results = self.search_client.search(
                search_text="*",
                filter=f"document_name eq '{doc_name}' and owner_user_id eq '{owner_user_id}'"
            )
            
            # Update each chunk with new allowed_users
            updated_docs = []
            for result in results:
                current_allowed = result.get("allowed_users", [])
                
                # Merge with new users
                updated_allowed = list(set(current_allowed + target_user_ids))
                
                updated_doc = {
                    "id": result["id"],
                    "allowed_users": updated_allowed
                }
                updated_docs.append(updated_doc)
            
            if updated_docs:
                self.search_client.merge_documents(documents=updated_docs)
                print(f"✅ Shared '{doc_name}' with {len(target_user_ids)} users")
                return True
            else:
                print(f"❌ Document not found or you don't own it")
                return False
                
        except Exception as e:
            print(f"❌ Error sharing document: {e}")
            return False

    def upload_from_blob(self, blob_url: str, doc_name: str = None, user_id: str = "default_user"):
        """Upload document directly from Azure Blob Storage URL
        
        Args:
            blob_url: URL to the blob storage file
            doc_name: Optional document name (extracted from URL if not provided)
            user_id: User ID who owns this document
        """
        try:
            import requests
            
            # Extract document name from URL if not provided
            if not doc_name:
                doc_name = blob_url.split('/')[-1]
            
            print(f"📥 Downloading from Azure Blob: {doc_name}...")
            
            # Download from blob
            response = requests.get(blob_url)
            response.raise_for_status()
            
            # Save temporarily
            temp_path = f"/tmp/{doc_name}"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            print(f"📤 Uploading to Azure AI Search...")
            
            # Upload using existing method
            result = self.upload_document(temp_path, user_id=user_id)
            
            # Clean up
            os.remove(temp_path)
            
            return result
            
        except Exception as e:
            print(f"❌ Error uploading from blob: {e}")
            import traceback
            traceback.print_exc()
            return False

# Initialize Azure AI Search
knowledge_base = AzureAISearchKnowledgeBase(
    search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    search_key=os.getenv("AZURE_SEARCH_KEY"),
    index_name="documents-index"
)

async def chat_with_azure_search_and_memory(user_id: str = "default_user"):
    """Interactive chat with Azure AI Search and Mem0 memory"""
    
    print("=" * 70)
    print("   🤖 AZURE AI SEARCH + MEMORY CHAT SYSTEM 🤖")
    print("=" * 70)
    print("\n📝 Commands:")
    print("  /upload <file_path>        - Upload a local document")
    print("  /uploadblob <blob_url>     - Upload from Azure Blob Storage")
    print("  /share <doc_name> <users>  - Share document with users (comma-separated)")
    print("  /docs                      - List all uploaded documents")
    print("  /index                     - Show detailed index information")
    print("  /delete <doc_name>         - Delete a document from the index")
    print("  /memories                  - Show your memories")
    print("  /switch <user_id>          - Switch to a different user")
    print("  /quit                      - Exit")
    print("=" * 70 + "\n")
    
    thread = agent.get_new_thread()
    current_user_id = user_id
    
    while True:
        user_input = input(f"[{current_user_id}]> ").strip()
        
        if not user_input:
            continue
        
        # Handle /upload command (LOCAL FILES)
        if user_input.startswith("/upload ") and not user_input.startswith("/uploadblob"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                file_path = parts[1].strip()
                
                if not os.path.exists(file_path):
                    print(f"❌ File not found: {file_path}\n")
                    continue
                
                knowledge_base.upload_document(file_path, user_id=current_user_id)
                print()
            else:
                print("❌ Usage: /upload <file_path>\n")
            continue
        
        # Handle /uploadblob command (AZURE BLOB FILES) - NEW!
        if user_input.startswith("/uploadblob"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                blob_url = parts[1].strip()
                knowledge_base.upload_from_blob(blob_url, user_id=current_user_id)
                print()
            else:
                print("❌ Usage: /uploadblob <blob_url>\n")
                print("   Example: /uploadblob https://mystorageaccount.blob.core.windows.net/documents/file.pdf\n")
            continue
        
        # Handle /docs command
        if user_input == "/docs":
            docs = knowledge_base.get_all_documents(user_id=current_user_id, include_shared=True)
            print(f"\n{'='*70}")
            print(f"📚 Accessible Documents ({len(docs)} total)")
            print(f"{'='*70}")
            if docs:
                for idx, doc in enumerate(docs, 1):
                    access = "🌐 Public" if doc["is_shared"] else "🔒 Private"
                    owner_indicator = "👤 You" if doc["owner"] == current_user_id else f"👥 {doc['owner']}"
                    print(f"{idx}. {doc['name']} | {access} | Owner: {owner_indicator}")
            else:
                print("No documents available.")
            print(f"{'='*70}\n")
            continue
        
        # Handle /delete command
        if user_input.startswith("/delete"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                doc_name = parts[1].strip()
                knowledge_base.delete_document(doc_name, user_id=current_user_id)
                print()
            else:
                print("❌ Usage: /delete <doc_name>\n")
            continue
        
        # Handle /share command
        if user_input.startswith("/share"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3:
                doc_name = parts[1].strip()
                users_str = parts[2].strip()
                target_users = [u.strip() for u in users_str.split(",") if u.strip()]
                
                if target_users:
                    knowledge_base.share_document(doc_name, current_user_id, target_users)
                    print()
                else:
                    print("❌ No valid users provided\n")
            else:
                print("❌ Usage: /share <doc_name> <user1,user2,user3>\n")
                print("   Example: /share report.pdf alice,bob\n")
            continue
        
        # Handle /memories command
        if user_input == "/memories":
            try:
                memories = mem0_client.search(
                    query="user information preferences facts",
                    filters={"user_id": current_user_id},
                    limit=50
                )
                print(f"\n{'='*70}")
                print(f"🧠 Memories for '{current_user_id}'")
                print(f"{'='*70}")
                if memories and 'results' in memories and memories['results']:
                    for idx, mem in enumerate(memories['results'], 1):
                        print(f"{idx}. {mem.get('memory', 'N/A')}")
                else:
                    print("📭 No memories found.")
                print(f"{'='*70}\n")
            except Exception as e:
                print(f"❌ Error retrieving memories: {e}\n")
            continue
        
        # Handle /switch command
        if user_input.startswith("/switch"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                current_user_id = parts[1].strip()
                print(f"\n✅ Switched to: {current_user_id}\n")
            else:
                print("❌ Usage: /switch <user_id>\n")
            continue

        # Handle /index command to show indexed documents
        if user_input == "/index":
            try:
                # Get ALL documents from the index
                results = knowledge_base.search_client.search(
                    search_text="*",
                    top=1000,
                    select=["id", "document_name", "chunk_id"]
                )
                
                # Group by document name
                docs = {}
                for result in results:
                    doc_name = result["document_name"]
                    if doc_name not in docs:
                        docs[doc_name] = 0
                    docs[doc_name] += 1
                
                print(f"\n{'='*70}")
                print(f"📊 Documents in Azure AI Search Index")
                print(f"{'='*70}")
                if docs:
                    for doc_name, chunk_count in docs.items():
                        print(f"📄 {doc_name} ({chunk_count} chunks)")
                else:
                    print("No documents found in the index.")
                print(f"{'='*70}\n")
            except Exception as e:
                print(f"❌ Error querying index: {e}\n")
            continue

        # Handle /quit command
        if user_input == "/quit":
            print("\n👋 Goodbye!")
            break
        
        # Regular chat message - search Azure AI Search and memories
        if user_input:
            # Search Azure AI Search for relevant context
            doc_context = ""
            relevant_docs = knowledge_base.search(user_input, top_k=5, user_id=current_user_id)
            if relevant_docs:
                doc_context = "📄 Relevant information from documents:\n\n"
                print(f"[Debug] Found {len(relevant_docs)} relevant chunks")
                for idx, doc in enumerate(relevant_docs, 1):
                    print(f"[Debug] Chunk {idx}: {doc['document_name']} (score: {doc.get('score', 'N/A')})")
                    doc_context += f"[From {doc['document_name']}]:\n{doc['content'][:1500]}\n\n"
            
            # Search Mem0 for memories
            memory_context = ""
            try:
                relevant_memories = mem0_client.search(
                    query=user_input,
                    filters={"user_id": current_user_id},
                    limit=5
                )
                
                if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                    memory_context = "🧠 What I remember about you:\n"
                    for mem in relevant_memories['results']:
                        memory_context += f"- {mem.get('memory', '')}\n"
                    memory_context += "\n"
            except Exception as e:
                print(f"[Debug] Memory search failed: {e}")
            
            # Combine contexts
            full_context = f"{memory_context}{doc_context}\nUser question: {user_input}"
            
            print("🤖 Agent: ", end="", flush=True)
            
            full_response = ""
            try:
                async for chunk in agent.run_stream(full_context, thread=thread):
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        full_response += chunk.text
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
            
            print("\n")
            
            # Save to Mem0
            try:
                messages = [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": full_response}
                ]
                mem0_client.add(messages, user_id=current_user_id)
            except Exception as e:
                print(f"[Debug] Failed to save memory: {e}")

# Run the chat
#asyncio.run(chat_with_azure_search_and_memory())

# Only run if executed directly (not when imported)
if __name__ == "__main__":
    asyncio.run(chat_with_azure_search_and_memory())