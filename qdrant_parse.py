# from langchain_ollama import OllamaLLM
# from langchain_core.prompts import ChatPromptTemplate
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_core.documents import Document
# import re
# import uuid
# from typing import List, Dict, Tuple, Optional
# import numpy as np

# # Qdrant imports
# from qdrant_client import QdrantClient
# from qdrant_client.http import models
# from sentence_transformers import SentenceTransformer

# # Initialize embedding model for Qdrant
# embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# # Initialize Qdrant client (in-memory for development, change to persistent for production)
# qdrant_client = QdrantClient(":memory:")
# COLLECTION_NAME = "web_owl_content"

# # Original template for non-RAG queries
# template = (
#     "You are tasked with extracting specific information from the following text content: {dom_content}. "
#     "Please follow these instructions carefully: \n\n"
#     "1. **Extract Information:** Only extract the information that directly matches the provided description: {parse_description}. "
#     "2. **No Extra Content:** Do not include any additional text, comments, or explanations in your response. "
#     "3. **Empty Response:** If no information matches the description, return an empty string ('')."
#     "4. **Direct Data Only:** Your output should contain only the data that is explicitly requested, with no other text."
# )

# # RAG template for chat-based queries
# rag_template = (
#     "You are an AI assistant that answers questions based on scraped web content. "
#     "Use the following context to answer the user's question. Be comprehensive and helpful.\n\n"
#     "Context from scraped websites:\n{context}\n\n"
#     "Question: {question}\n\n"
#     "Answer based on the provided context. If the context doesn't contain relevant information, "
#     "say so clearly. Provide specific details and examples when available."
# )

# model = OllamaLLM(model="llama3.1:8b")

# class QdrantVectorStore:
#     """Wrapper class to make Qdrant work like the original vector store interface"""
    
#     def __init__(self, client: QdrantClient, collection_name: str):
#         self.client = client
#         self.collection_name = collection_name
#         self.documents = []  # Store original documents for compatibility
    
#     def similarity_search(self, query: str, k: int = 5) -> List[Document]:
#         """Perform similarity search and return Document objects"""
#         try:
#             # Generate embedding for the query
#             query_embedding = embedding_model.encode(query).tolist()
            
#             # Search in Qdrant
#             search_results = self.client.search(
#                 collection_name=self.collection_name,
#                 query_vector=query_embedding,
#                 limit=k
#             )
            
#             # Convert results back to Document format
#             documents = []
#             for result in search_results:
#                 doc = Document(
#                     page_content=result.payload['content'],
#                     metadata={
#                         'source': result.payload['source'],
#                         'chunk_id': result.payload['chunk_id'],
#                         'scraped_at': result.payload['scraped_at'],
#                         'section': result.payload.get('section', 'unknown')
#                     }
#                 )
#                 documents.append(doc)
            
#             return documents
            
#         except Exception as e:
#             print(f"Error in similarity search: {e}")
#             return []

# def create_vector_store(scraped_data):
#     """Create a Qdrant vector store from scraped data with section tagging for better RAG performance."""
#     try:
#         if not scraped_data:
#             return None
        
#         # Delete existing collection if it exists
#         try:
#             qdrant_client.delete_collection(collection_name=COLLECTION_NAME)
#         except:
#             pass  # Collection might not exist
        
#         # Create new collection
#         qdrant_client.create_collection(
#             collection_name=COLLECTION_NAME,
#             vectors_config=models.VectorParams(
#                 size=384,  # Dimension for all-MiniLM-L6-v2
#                 distance=models.Distance.COSINE
#             )
#         )
        
#         documents = []
#         text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000,
#             chunk_overlap=200,
#             length_function=len,
#         )
        
#         points = []
#         point_id = 0
        
#         for url, data in scraped_data.items():
#             full_text = data["content"]

#             # Heuristic section splitting (same as original)
#             sections = {
#                 "hero": "",
#                 "listing": "",
#                 "footer": ""
#             }

#             lines = full_text.splitlines()
#             current_section = "hero"
#             for line in lines:
#                 stripped = line.strip()

#                 # Switch sections based on basic keywords
#                 if any(word in stripped.lower() for word in ["stock", "vin", "view details", "leasing", "great value"]):
#                     current_section = "listing"
#                 elif any(word in stripped.lower() for word in ["contact us", "book an appointment", "privacy", "careers"]):
#                     current_section = "footer"

#                 sections[current_section] += stripped + "\n"

#             # Chunk and process each section
#             for section_name, section_text in sections.items():
#                 if not section_text.strip():
#                     continue
                    
#                 chunks = text_splitter.split_text(section_text)
#                 for i, chunk in enumerate(chunks):
#                     if not chunk.strip():
#                         continue
                    
#                     # Create embedding
#                     embedding = embedding_model.encode(chunk).tolist()
                    
#                     # Create point for Qdrant
#                     point = models.PointStruct(
#                         id=point_id,
#                         vector=embedding,
#                         payload={
#                             "content": chunk,
#                             "source": url,
#                             "chunk_id": f"{section_name}_{i}",
#                             "scraped_at": data["scraped_at"],
#                             "section": section_name
#                         }
#                     )
#                     points.append(point)
                    
#                     # Also create Document for compatibility
#                     doc = Document(
#                         page_content=chunk,
#                         metadata={
#                             "source": url,
#                             "chunk_id": f"{section_name}_{i}",
#                             "scraped_at": data["scraped_at"],
#                             "section": section_name
#                         }
#                     )
#                     documents.append(doc)
                    
#                     point_id += 1
        
#         if points:
#             # Insert all points into Qdrant
#             qdrant_client.upsert(
#                 collection_name=COLLECTION_NAME,
#                 points=points
#             )
            
#             # Return wrapper that behaves like original vector store
#             vector_store = QdrantVectorStore(qdrant_client, COLLECTION_NAME)
#             vector_store.documents = documents  # Store for compatibility
#             return vector_store
        
#         return None
        
#     except Exception as e:
#         print(f"Error creating vector store: {e}")
#         return None

# def parse_with_ollama_rag(vector_store, question, k=10):
#     """Parse using RAG with section-aware ranking to improve answer accuracy."""
#     if not vector_store:
#         return "No data available for search.", []

#     # Perform similarity search using Qdrant
#     retrieved_docs = vector_store.similarity_search(question, k=k)

#     # Filter out irrelevant sections (like footer/contact form)
#     filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("section") != "footer"]

#     # Sort to prioritize 'hero' chunks
#     ranked_docs = sorted(
#         filtered_docs,
#         key=lambda doc: doc.metadata.get("section") == "hero",
#         reverse=True
#     )

#     if not ranked_docs:
#         return "No relevant information found in the scraped data.", []

#     # Build context string
#     context_parts = []
#     sources = set()

#     for doc in ranked_docs:
#         context_parts.append(f"From {doc.metadata['source']}:\n{doc.page_content}")
#         sources.add(doc.metadata["source"])

#     context = "\n\n".join(context_parts)

#     # Prompt the model
#     prompt = ChatPromptTemplate.from_template(rag_template)
#     chain = prompt | model

#     response = chain.invoke({
#         "context": context,
#         "question": question
#     })

#     return response, list(sources)

# def parse_with_ollama(dom_chunks, parse_description):
#     """Original parsing function for backward compatibility"""
#     prompt = ChatPromptTemplate.from_template(template)
#     chain = prompt | model

#     parsed_results = []

#     for i, chunk in enumerate(dom_chunks, start=1):
#         response = chain.invoke(
#             {"dom_content": chunk, "parse_description": parse_description}
#         )
#         print(f"Parsed batch: {i} of {len(dom_chunks)}")
#         parsed_results.append(response)

#     return "\n".join(parsed_results)

# def search_scraped_data(scraped_data, query, max_results=3):
#     """Simple text search in scraped data (fallback method)"""
#     results = []
#     query_lower = query.lower()
    
#     for url, data in scraped_data.items():
#         content_lower = data['content'].lower()
        
#         # Simple relevance scoring based on query term frequency
#         score = 0
#         query_terms = re.findall(r'\w+', query_lower)
        
#         for term in query_terms:
#             score += content_lower.count(term)
        
#         if score > 0:
#             # Extract relevant snippets
#             snippets = []
#             lines = data['content'].split('\n')
            
#             for line in lines:
#                 if any(term in line.lower() for term in query_terms):
#                     snippets.append(line.strip())
#                     if len(snippets) >= 3:  # Limit snippets per source
#                         break
            
#             results.append({
#                 'url': url,
#                 'score': score,
#                 'snippets': snippets,
#                 'scraped_at': data['scraped_at']
#             })
    
#     # Sort by relevance score and return top results
#     results.sort(key=lambda x: x['score'], reverse=True)
#     return results[:max_results]

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import re
import uuid
from typing import List, Dict, Tuple, Optional
import numpy as np

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# Initialize embedding model for Qdrant
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Qdrant client (in-memory for development, change to persistent for production)
qdrant_client = QdrantClient(":memory:")
COLLECTION_NAME = "web_owl_content"

# Original template for non-RAG queries
template = (
    "You are tasked with extracting specific information from the following text content: {dom_content}. "
    "Please follow these instructions carefully: \n\n"
    "1. **Extract Information:** Only extract the information that directly matches the provided description: {parse_description}. "
    "2. **No Extra Content:** Do not include any additional text, comments, or explanations in your response. "
    "3. **Empty Response:** If no information matches the description, return an empty string ('')."
    "4. **Direct Data Only:** Your output should contain only the data that is explicitly requested, with no other text."
)

# RAG template for chat-based queries
rag_template = (
    "You are an AI assistant that answers questions based on scraped web content. "
    "Use the following context to answer the user's question. Be comprehensive and helpful.\n\n"
    "Context from scraped websites:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer based on the provided context. If the context doesn't contain relevant information, "
    "say so clearly. Provide specific details and examples when available."
)

model = OllamaLLM(model="llama3.1:8b")

class QdrantVectorStore:
    """Wrapper class to make Qdrant work like the original vector store interface"""
    
    def __init__(self, client: QdrantClient, collection_name: str):
        self.client = client
        self.collection_name = collection_name
        self.documents = []  # Store original documents for compatibility
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform similarity search and return Document objects"""
        try:
            # Generate embedding for the query
            query_embedding = embedding_model.encode(query).tolist()
            
            # Search in Qdrant
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k
            )
            
            # Convert results back to Document format
            documents = []
            for result in search_results:
                doc = Document(
                    page_content=result.payload['content'],
                    metadata={
                        'source': result.payload['source'],
                        'chunk_id': result.payload['chunk_id'],
                        'scraped_at': result.payload['scraped_at'],
                        'section': result.payload.get('section', 'unknown')
                    }
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []

def create_vector_store(scraped_data):
    """Create a Qdrant vector store from scraped data with section tagging for better RAG performance."""
    try:
        if not scraped_data:
            return None
        
        # Delete existing collection if it exists
        try:
            qdrant_client.delete_collection(collection_name=COLLECTION_NAME)
        except:
            pass  # Collection might not exist
        
        # Create new collection
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=384,  # Dimension for all-MiniLM-L6-v2
                distance=models.Distance.COSINE
            )
        )
        
        documents = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        points = []
        point_id = 0
        
        for url, data in scraped_data.items():
            full_text = data["content"]

            # Heuristic section splitting (same as original)
            sections = {
                "hero": "",
                "listing": "",
                "footer": ""
            }

            lines = full_text.splitlines()
            current_section = "hero"
            for line in lines:
                stripped = line.strip()

                # Switch sections based on basic keywords
                if any(word in stripped.lower() for word in ["stock", "vin", "view details", "leasing", "great value"]):
                    current_section = "listing"
                elif any(word in stripped.lower() for word in ["contact us", "book an appointment", "privacy", "careers"]):
                    current_section = "footer"

                sections[current_section] += stripped + "\n"

            # Chunk and process each section
            for section_name, section_text in sections.items():
                if not section_text.strip():
                    continue
                    
                chunks = text_splitter.split_text(section_text)
                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    
                    # Create embedding
                    embedding = embedding_model.encode(chunk).tolist()
                    
                    # Create point for Qdrant
                    point = models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "content": chunk,
                            "source": url,
                            "chunk_id": f"{section_name}_{i}",
                            "scraped_at": data["scraped_at"],
                            "section": section_name
                        }
                    )
                    points.append(point)
                    
                    # Also create Document for compatibility
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "source": url,
                            "chunk_id": f"{section_name}_{i}",
                            "scraped_at": data["scraped_at"],
                            "section": section_name
                        }
                    )
                    documents.append(doc)
                    
                    point_id += 1
        
        if points:
            # Insert all points into Qdrant
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            
            # Return wrapper that behaves like original vector store
            vector_store = QdrantVectorStore(qdrant_client, COLLECTION_NAME)
            vector_store.documents = documents  # Store for compatibility
            return vector_store
        
        return None
        
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None

def parse_with_ollama_rag(vector_store, question, k=10):
    """Parse using RAG with section-aware ranking to improve answer accuracy."""
    if not vector_store:
        return "No data available for search.", []

    # Perform similarity search using Qdrant
    retrieved_docs = vector_store.similarity_search(question, k=k)

    if not retrieved_docs:
        return "No relevant information found in the scraped data.", []

    # Filter out irrelevant sections (like footer/contact form)
    filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("section") != "footer"]

    # Sort to prioritize 'hero' chunks - this is the key ranking logic from parse.py
    ranked_docs = sorted(
        filtered_docs,
        key=lambda doc: (
            doc.metadata.get("section") == "hero",     # Hero sections first
            doc.metadata.get("section") == "listing"   # Then listing sections
        ),
        reverse=True
    )

    if not ranked_docs:
        return "No relevant information found in the scraped data.", []

    # Build context string
    context_parts = []
    sources = set()

    for doc in ranked_docs:
        context_parts.append(f"From {doc.metadata['source']}:\n{doc.page_content}")
        sources.add(doc.metadata["source"])

    context = "\n\n".join(context_parts)

    # Prompt the model
    prompt = ChatPromptTemplate.from_template(rag_template)
    chain = prompt | model

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return response, list(sources)

def parse_with_ollama(dom_chunks, parse_description):
    """Original parsing function for backward compatibility"""
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model

    parsed_results = []

    for i, chunk in enumerate(dom_chunks, start=1):
        response = chain.invoke(
            {"dom_content": chunk, "parse_description": parse_description}
        )
        print(f"Parsed batch: {i} of {len(dom_chunks)}")
        parsed_results.append(response)

    return "\n".join(parsed_results)

def search_scraped_data(scraped_data, query, max_results=3):
    """Simple text search in scraped data (fallback method)"""
    results = []
    query_lower = query.lower()
    
    for url, data in scraped_data.items():
        content_lower = data['content'].lower()
        
        # Simple relevance scoring based on query term frequency
        score = 0
        query_terms = re.findall(r'\w+', query_lower)
        
        for term in query_terms:
            score += content_lower.count(term)
        
        if score > 0:
            # Extract relevant snippets
            snippets = []
            lines = data['content'].split('\n')
            
            for line in lines:
                if any(term in line.lower() for term in query_terms):
                    snippets.append(line.strip())
                    if len(snippets) >= 3:  # Limit snippets per source
                        break
            
            results.append({
                'url': url,
                'score': score,
                'snippets': snippets,
                'scraped_at': data['scraped_at']
            })
    
    # Sort by relevance score and return top results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:max_results]