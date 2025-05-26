from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import re

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
embeddings = OllamaEmbeddings(model="llama3.1:8b")


def create_vector_store(scraped_data):
    """Create a vector store from scraped data for RAG"""
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    for url, data in scraped_data.items():
        # Split the content into smaller chunks
        chunks = text_splitter.split_text(data['content'])
        
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": url,
                    "chunk_id": i,
                    "scraped_at": data['scraped_at']
                }
            )
            documents.append(doc)
    
    if documents:
        # Create FAISS vector store
        vector_store = FAISS.from_documents(documents, embeddings)
        return vector_store
    
    return None


def parse_with_ollama_rag(vector_store, question, k=5):
    """Parse using RAG approach with vector similarity search"""
    if not vector_store:
        return "No data available for search.", []
    
    # Perform similarity search
    relevant_docs = vector_store.similarity_search(question, k=k)
    
    if not relevant_docs:
        return "No relevant information found in the scraped data.", []
    
    # Prepare context from relevant documents
    context_parts = []
    sources = set()
    
    for doc in relevant_docs:
        context_parts.append(f"From {doc.metadata['source']}:\n{doc.page_content}")
        sources.add(doc.metadata['source'])
    
    context = "\n\n".join(context_parts)
    
    # Create prompt and get response
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