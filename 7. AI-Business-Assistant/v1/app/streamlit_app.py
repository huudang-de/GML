import streamlit as st
import requests

st.set_page_config(page_title="GML AI Assistant", page_icon="🪵", layout="wide")
st.title("🪵 Gỗ Minh Long — AI Business Assistant")

# Sidebar: Suggested questions
with st.sidebar:
    st.header("💡 Câu hỏi gợi ý")
    suggestions = [
        "Lợi nhuận tháng này so với tháng trước?",
        "Top 5 khách hàng có dư nợ lớn nhất?",
        "Tồn kho hiện tại của ván ép?",
        "Cash Runway còn bao nhiêu tháng?",
        "Vòng quay hàng tồn kho Q3 là bao nhiêu?",
    ]
    for q in suggestions:
        if st.button(q, use_container_width=True):
            st.session_state['query'] = q

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Hỏi bất kỳ điều gì về doanh nghiệp..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call FastAPI
    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích dữ liệu..."):
            try:
                response = requests.post(
                    "http://localhost:8000/chat",
                    json={"query": prompt, "session_id": st.session_state.get("session_id", "default")}
                )
                response.raise_for_status()
                result = response.json()
                
                # Display answer
                st.markdown(result["answer"])

                # Display supporting data table if available
                if result.get("data"):
                    st.dataframe(result["data"])

                # Display SQL query used (expandable, for transparency)
                if result.get("sql_query"):
                    with st.expander("🔍 SQL đã thực thi"):
                        st.code(result["sql_query"], language="sql")

                # Display sources (RAG)
                if result.get("sources"):
                    with st.expander("📄 Nguồn tham khảo"):
                        for src in result["sources"]:
                            st.caption(f"• {src}")
                            
                st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
            except Exception as e:
                st.error(f"Lỗi khi kết nối với API: {str(e)}")
