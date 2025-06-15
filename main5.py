import streamlit as st
import json
from datetime import datetime
from scrape import scrape_website, extract_body_content, clean_body_content, split_dom_content
from qdrant_parse import parse_with_ollama, parse_with_ollama_rag, create_vector_store
from export_utils import export_to_html, export_to_pdf
from PIL import Image
from io import BytesIO
import base64

st.set_page_config(page_title="Web Sentinel", layout="wide")

# Light blue button + title styling
st.markdown("""
<style>
.title-box {
    background-color: white;
    padding: 10px;
    border: 1px solid #DDD;
    border-radius: 5px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}
.scroll-box {
    max-height: 400px;
    overflow-y: auto;
    padding: 12px;
    border: 1px solid #DDD;
    border-radius: 8px;
    background-color: #FAFAFA;
    margin-bottom: 16px;
}
.scroll-box::-webkit-scrollbar {
    width: 6px;
}
.scroll-box::-webkit-scrollbar-thumb {
    background-color: #ADD8E6;
    border-radius: 3px;
}
</style>
""", unsafe_allow_html=True)

# Session state
for key in ["scraped_data", "chat_history", "url_list", "vector_store"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key == "scraped_data" else [] if key.endswith("list") else None

def reset_session():
    st.session_state.scraped_data = {}
    st.session_state.chat_history = []
    st.session_state.url_list = []
    st.session_state.vector_store = None

def add_to_chat_history(role, content, sources=None):
    st.session_state.chat_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": sources or []
    })

def logo_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

logo = Image.open("logo3.png")

# Sidebar
with st.sidebar:
    st.markdown(
        f'''<div class="title-box" style="display: flex; align-items: center;">
            <img src="data:image/png;base64,{logo_to_base64(logo)}" width="60" style="margin-right: 15px;">
            <h1 style="margin: 0; font-size: 1.8rem;">Web Sentinel</h1>
        </div>''',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.header("🛠️ Settings")
    if st.button("🔄 Reset Session", type="secondary", use_container_width=True):
        reset_session()

    st.markdown("---")
    st.header("🔍 Search Settings")
    use_rag = st.checkbox("Use Advanced Search", value=True)

    st.markdown("---")
    st.header("📄 Export Options")
    export_type = st.selectbox("Export Format", ["HTML", "PDF"])
    export_content = st.selectbox("Export Content", ["Retrieved Data", "Chat History", "Both"])
    if st.button("📅 Export", use_container_width=True):
        if export_content in ["Retrieved Data", "Both"] and st.session_state.scraped_data:
            if export_type == "HTML":
                html = export_to_html(st.session_state.scraped_data, None)
                st.download_button("Download HTML", html, file_name="scraped.html", mime="text/html")
            else:
                pdf = export_to_pdf(st.session_state.scraped_data, None)
                st.download_button("Download PDF", pdf, file_name="scraped.pdf", mime="application/pdf")
        if export_content in ["Chat History", "Both"] and st.session_state.chat_history:
            if export_type == "HTML":
                html = export_to_html(None, st.session_state.chat_history)
                st.download_button("Download Chat (HTML)", html, file_name="chat.html", mime="text/html")
            else:
                pdf = export_to_pdf(None, st.session_state.chat_history)
                st.download_button("Download Chat (PDF)", pdf, file_name="chat.pdf", mime="application/pdf")

# Layout columns
left_col, right_col = st.columns([1.5, 2.5])

# --- Left: URL Management ---
with left_col:
    st.markdown("<h3>🌐 Website Management</h3>", unsafe_allow_html=True)
    st.caption("    ")
    with st.form("url_form", clear_on_submit=True):
        new_url = st.text_input("Enter Website", placeholder="https://example.com")
        col1, col2 = st.columns(2)
        add_button = col1.form_submit_button("➕ Add Website", type="primary", use_container_width=True)
        scrape_button = col2.form_submit_button("🔎 Analyze All", type="primary", use_container_width=True)

    if st.button("🗑️ Clear All Websites", use_container_width=True):
        st.session_state.url_list.clear()
        st.rerun()

    if add_button and new_url:
        if not new_url.startswith("http"):
            new_url = "https://" + new_url
        if new_url not in st.session_state.url_list:
            st.session_state.url_list.append(new_url)
            st.rerun()

    if scrape_button:
        urls_to_scrape = [u for u in st.session_state.url_list if u not in st.session_state.scraped_data]
        if urls_to_scrape:
            progress = st.progress(0)
            for i, url in enumerate(urls_to_scrape):
                try:
                    dom = scrape_website(url)
                    cleaned = clean_body_content(extract_body_content(dom))
                    st.session_state.scraped_data[url] = {
                        "content": cleaned,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                except Exception as e:
                    st.error(f"Error scraping {url}: {e}")
                progress.progress((i + 1) / len(urls_to_scrape))
            st.session_state.vector_store = create_vector_store(st.session_state.scraped_data)
            st.rerun()
    st.markdown("---")

    st.markdown("### 📋 Websites")

    url_container = st.container(height=601)

    with url_container:
        if st.session_state.url_list:
            for i, url in enumerate(st.session_state.url_list):
                col1, col2 = st.columns([10, 1])
                with col1:
                    status = "✅ Ready" if url in st.session_state.scraped_data else "⏳ Ready to be Analyzed"
                    status_color = "#28a745" if url in st.session_state.scraped_data else "#ffc107"
                    st.markdown(f'<div style="color: {status_color}; font-weight: 600;">{status}</div>', unsafe_allow_html=True)
                    # st.markdown(f'<div style="margin-top: 4px;">{url}</div>', unsafe_allow_html=True)
                    st.markdown(f'{url}')
                    # if url in st.session_state.scraped_data:
                    #     st.caption("📅 " + st.session_state.scraped_data[url]["scraped_at"])
                with col2:
                    if st.button("❌", key=f"remove_{i}", help=f"Remove {url}"):
                        st.session_state.url_list.pop(i)
                        st.session_state.scraped_data.pop(url, None)
                        st.rerun()
                
                # Add small spacer between URLs
                if i < len(st.session_state.url_list) - 1:
                    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div style="text-align: center; padding: 60px 20px; color: #666;">
                <h4 style="color: #666; margin-bottom: 16px;">No Websites Yet</h4>
                <p>Add some Websites above to get started!</p>
            </div>
            ''', unsafe_allow_html=True)






# --- Right: Chat Box ---
with right_col:
    if st.session_state.scraped_data:
        st.markdown("<h3>💬 Ask Your Data</h3>", unsafe_allow_html=True)
        # st.markdown('<div class="title-box" style="display: inline-block; vertical-alignment: center; white-space: nowrap; border: 1px solid #DDD; border-radius: 5px; ' \
        # 'box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);"><h4 style="margin: 0; display: inline-block;">💬 Chat with Your Data</h3></div>', unsafe_allow_html=True)
        st.markdown("""
        <style>
        .chat-container {
            height: 600px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
            margin-bottom: 20px;
        }
        .user-message {
            text-align: right;
            margin: 10px 0;
        }
        .user-bubble {
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 70%;
            text-align: left;
        }
        .assistant-message {
            margin: 10px 0;
            text-align: left;
        }
        .assistant-bubble {
            display: inline-block;
            background-color: #f1f1f1;
            color: #333;
            padding: 15px;
            border-radius: 15px;
            max-width: 70%;
            text-align: left;
        }
        </style>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=740)
        
        with chat_container:
            if "chat_history" not in st.session_state or st.session_state.chat_history is None:
                st.session_state.chat_history = []
            for i, message in enumerate(st.session_state.chat_history[-15:]):
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <div class="user-bubble">
                            {message["content"]}<br>
                            <small style="opacity: 0.8;">🕐 {message["timestamp"]}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="background-color: #f1f1f1; padding: 10px; border-radius: 15px; max-width: 70%; display: inline-block;">
                    """, unsafe_allow_html=True)
                    st.write(message["content"])
                    st.markdown(f"""
                            <small style="opacity: 0.7;">🕐 {message["timestamp"]}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

        if (
            st.session_state.chat_history and
            st.session_state.chat_history[-1]["role"] == "assistant" and
            st.session_state.chat_history[-1].get("sources")
        ):
            with st.expander("📖 Sources from last response", expanded=False):
                for src in st.session_state.chat_history[-1]["sources"]:
                    st.write(f"🔗 {src}")

        with st.form("chat_form", clear_on_submit=True):
            user_question = st.text_area("Ask a question...", placeholder="What's this site about?", height=80)
            send = st.form_submit_button("🚀 Get Insights", type="primary", use_container_width=True)

        if send and user_question:
            add_to_chat_history("user", user_question)
            with st.spinner("Thinking..."):
                try:
                    if use_rag and st.session_state.vector_store:
                        response, sources = parse_with_ollama_rag(st.session_state.vector_store, user_question)
                        method = "RAG"
                    else:
                        full_text = "\n\n".join([d["content"] for d in st.session_state.scraped_data.values()])
                        if not full_text.strip():
                            st.error("No content to search.")
                            st.stop()
                        chunks = split_dom_content(full_text)
                        response = parse_with_ollama(chunks, user_question)
                        sources = list(st.session_state.scraped_data.keys())
                        method = "Simple"

                    add_to_chat_history("assistant", response, sources)
                    st.success(f"Response generated with {method} search")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating response: {e}")
                    st.info("Try turning off RAG if issue persists.")
    else:
        st.markdown("<h3>💬 Chat with Your Data</h3>", unsafe_allow_html=True)
        # st.markdown('<div class="title-box" style="display: inline-block; vertical-alignment: center; white-space: nowrap; border: 1px solid #DDD; border-radius: 5px; ' \
        # 'box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);"><h4 style="margin: 0; display: inline-block;">💬 Chat with Your Data</h3></div>', unsafe_allow_html=True)
        st.markdown("""
        <style>
        .chat-container {
            height: 600px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
            margin-bottom: 20px;
        }
        .user-message {
            text-align: right;
            margin: 10px 0;
        }
        .user-bubble {
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 70%;
            text-align: left;
        }
        .assistant-message {
            margin: 10px 0;
            text-align: left;
        }
        .assistant-bubble {
            display: inline-block;
            background-color: #f1f1f1;
            color: #333;
            padding: 15px;
            border-radius: 15px;
            max-width: 70%;
            text-align: left;
        }
        </style>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=740)

        with chat_container:
            st.markdown('''
            <div style="text-align: center; padding: 60px 20px; color: #666;">
                <h3 style="color: #666; margin-bottom: 16px;">Ready to Chat!</h3>
                <p>Please analyze at least one Website to start chatting with your data.</p>
            </div>
            ''', unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            user_question = st.text_area("Ask a question...", placeholder="What's this site about?", height=80)
            send = st.form_submit_button("🚀 Get Insights", type="primary", use_container_width=True)

        if send and user_question:
            add_to_chat_history("user", user_question)
            add_to_chat_history("assistant", "Please analyze at least one Website to start chatting with your data.", "")
