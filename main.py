import streamlit as st
import json
from datetime import datetime
from scrape import (
    scrape_website,
    extract_body_content,
    clean_body_content,
    split_dom_content,
)
from parse import parse_with_ollama, parse_with_ollama_rag, create_vector_store
from export_utils import export_to_html, export_to_pdf

# Initialize session state
def initialize_session_state():
    if "scraped_data" not in st.session_state:
        st.session_state.scraped_data = {}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "url_list" not in st.session_state:
        st.session_state.url_list = []
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None

def reset_session():
    """Reset all session data"""
    st.session_state.scraped_data = {}
    st.session_state.chat_history = []
    st.session_state.url_list = []
    st.session_state.vector_store = None
    st.success("Session reset successfully!")

def add_to_chat_history(role, content, sources=None):
    """Add message to chat history"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = {
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "sources": sources or []
    }
    st.session_state.chat_history.append(message)

# Streamlit UI
st.title("🕷️ Enhanced AI Web Scraper")
st.markdown("---")

# Initialize session state
initialize_session_state()

# Sidebar for controls
with st.sidebar:
    st.header("🛠️ Controls")
    
    # Reset Session Button
    if st.button("🔄 Reset Session", type="secondary"):
        reset_session()
    
    st.markdown("---")
    
    # RAG Settings
    st.header("🧠 Search Settings")
    use_rag = st.checkbox("Use Advanced RAG Search", value=True, 
                         help="Uses semantic similarity search for better results")
    
    st.markdown("---")
    
    # Export Options
    st.header("📤 Export Options")
    export_type = st.selectbox("Export Format", ["HTML", "PDF"])
    export_content = st.selectbox("Export Content", ["Scraped Data", "Chat History", "Both"])
    
    if st.button("📥 Export"):
        if export_content == "Scraped Data" or export_content == "Both":
            if st.session_state.scraped_data:
                if export_type == "HTML":
                    html_content = export_to_html(st.session_state.scraped_data, None)
                    st.download_button(
                        "Download Scraped Data (HTML)",
                        html_content,
                        file_name=f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                        mime="text/html"
                    )
                else:
                    pdf_content = export_to_pdf(st.session_state.scraped_data, None)
                    st.download_button(
                        "Download Scraped Data (PDF)",
                        pdf_content,
                        file_name=f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
        
        if export_content == "Chat History" or export_content == "Both":
            if st.session_state.chat_history:
                if export_type == "HTML":
                    html_content = export_to_html(None, st.session_state.chat_history)
                    st.download_button(
                        "Download Chat History (HTML)",
                        html_content,
                        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                        mime="text/html"
                    )
                else:
                    pdf_content = export_to_pdf(None, st.session_state.chat_history)
                    st.download_button(
                        "Download Chat History (PDF)",
                        pdf_content,
                        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🌐 URL Management")
    
    # URL input
    new_url = st.text_input("Enter Website URL", placeholder="https://example.com")
    
    col_add, col_clear = st.columns([1, 1])
    with col_add:
        if st.button("➕ Add URL"):
            if new_url and new_url not in st.session_state.url_list:
                st.session_state.url_list.append(new_url)
                st.success(f"Added: {new_url}")
            elif new_url in st.session_state.url_list:
                st.warning("URL already in list!")
    
    with col_clear:
        if st.button("🗑️ Clear All URLs"):
            st.session_state.url_list = []
            st.success("URL list cleared!")
    
    # Display current URLs
    if st.session_state.url_list:
        st.subheader("📋 URLs to Scrape")
        for i, url in enumerate(st.session_state.url_list):
            col_url, col_remove = st.columns([4, 1])
            with col_url:
                st.text(f"{i+1}. {url}")
            with col_remove:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.url_list.pop(i)
                    st.rerun()

with col2:
    st.header("🔍 Scraping Status")
    
    # Display scraped URLs
    if st.session_state.scraped_data:
        st.subheader("✅ Scraped URLs")
        for url in st.session_state.scraped_data.keys():
            st.success(f"✓ {url}")
    
    # Scrape button
    if st.button("🕷️ Scrape Websites", type="primary"):
        if st.session_state.url_list:
            # Determine which URLs need to be scraped
            urls_to_scrape = [url for url in st.session_state.url_list 
                            if url not in st.session_state.scraped_data]
            
            if urls_to_scrape:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, url in enumerate(urls_to_scrape):
                    status_text.text(f"Scraping {i+1}/{len(urls_to_scrape)}: {url}")
                    
                    try:
                        # Scrape the website
                        dom_content = scrape_website(url)
                        body_content = extract_body_content(dom_content)
                        cleaned_content = clean_body_content(body_content)
                        
                        # Store the scraped data
                        st.session_state.scraped_data[url] = {
                            "content": cleaned_content,
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        progress_bar.progress((i + 1) / len(urls_to_scrape))
                        
                    except Exception as e:
                        st.error(f"Error scraping {url}: {str(e)}")
                
                # Create vector store for RAG
                if st.session_state.scraped_data and use_rag:
                    status_text.text("Creating vector store for RAG...")
                    try:
                        st.session_state.vector_store = create_vector_store(st.session_state.scraped_data)
                        if st.session_state.vector_store:
                            st.success("✅ RAG vector store created successfully!")
                        else:
                            st.warning("⚠️ Failed to create vector store, will use simple search")
                    except Exception as e:
                        st.error(f"Error creating vector store: {str(e)}")
                        st.session_state.vector_store = None
                
                status_text.text("✅ Scraping completed!")
                st.success(f"Successfully scraped {len(urls_to_scrape)} new URLs!")
            else:
                st.info("All URLs have already been scraped!")
        else:
            st.warning("Please add URLs to scrape first!")

# Chat Interface
st.markdown("---")
st.header("💬 Chat with Your Data")

if st.session_state.scraped_data:
    # Display chat history
    if st.session_state.chat_history:
        st.subheader("📜 Chat History")
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(f"**{message['timestamp']}**")
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(f"**{message['timestamp']}**")
                    st.write(message["content"])
                    if message.get("sources"):
                        with st.expander("📖 Sources"):
                            for source in message["sources"]:
                                st.write(f"- {source}")
    
    # Chat input
    user_question = st.chat_input("Ask a question about the scraped data...")
    
    if user_question:
        # Add user message to chat history
        add_to_chat_history("user", user_question)
        
        # Display user message
        with st.chat_message("user"):
            st.write(f"**{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
            st.write(user_question)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    if use_rag and st.session_state.vector_store:
                        # Use RAG approach
                        response, sources = parse_with_ollama_rag(
                            st.session_state.vector_store, 
                            user_question
                        )
                        st.info("🧠 Using RAG semantic search")
                    else:
                        # Fallback to original method
                        all_content = "\n\n".join([
                            f"Content from {url}:\n{data['content']}" 
                            for url, data in st.session_state.scraped_data.items()
                        ])
                        dom_chunks = split_dom_content(all_content)
                        response = parse_with_ollama(dom_chunks, user_question)
                        sources = list(st.session_state.scraped_data.keys())
                        st.info("🔍 Using simple text search")
                    
                    # Display response
                    st.write(f"**{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
                    st.write(response)
                    
                    if sources:
                        with st.expander("📖 Sources"):
                            for source in sources:
                                st.write(f"- {source}")
                    
                    # Add assistant message to chat history
                    add_to_chat_history("assistant", response, sources)
                    
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                    st.info("💡 Try toggling the RAG setting in the sidebar if you're having issues")

else:
    st.info("👆 Please scrape some websites first to start chatting with the data!")

# Display scraped content (expandable)
if st.session_state.scraped_data:
    st.markdown("---")
    st.header("📄 Scraped Content")
    
    for url, data in st.session_state.scraped_data.items():
        with st.expander(f"📖 {url} (scraped at {data['scraped_at']})"):
            st.text_area(
                "Content", 
                data["content"], 
                height=300, 
                key=f"content_{hash(url)}"
            )

