import streamlit as st
from dotenv import load_dotenv
from src.task10_generation import generate_with_citation

load_dotenv()

st.set_page_config(
    page_title="UET Chatbot - RAG",
    page_icon="🎓",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🎓 UET Assistant")
    st.caption("Trợ lý hỏi đáp quy chế & dịch vụ sinh viên UET")
    top_k = st.slider("Số lượng chunks tham khảo (top_k)", 3, 10, 5)
    if st.button("🗑️ Xóa hội thoại"):
        st.session_state.messages = []
        st.rerun()

st.title("🎓 UET Chatbot")
st.caption("Hệ thống giải đáp thắc mắc về học phí, học bổng và quy định đào tạo")

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander(f"📚 Nguồn tham khảo ({message.get('retrieval_source', 'hybrid')})"):
                for idx, src in enumerate(message["sources"], 1):
                    meta = src.get("metadata", {})
                    st.markdown(
                        f"**[{idx}] {meta.get('title', meta.get('source', 'Tài liệu'))}**  \n"
                        f"*Phương thức: `{src.get('retrieval_method', 'N/A')}` | Score: `{src.get('score', 0):.4f}`*  \n"
                        f"> {src.get('content', '')}"
                    )

query = st.chat_input("Nhập câu hỏi của bạn (ví dụ: điều kiện xét học bổng xuất sắc)...")

if query:
    # 1. Lưu và hiển thị câu hỏi user
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # 2. Gọi RAG Pipeline sinh câu trả lời
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
            answer_text = result["answer"]
            sources = result.get("sources", [])
            method = result.get("retrieval_source", "hybrid")

            st.markdown(answer_text)

            if sources:
                with st.expander(f"📚 Nguồn tham khảo ({method})"):
                    for idx, src in enumerate(sources, 1):
                        meta = src.get("metadata", {})
                        st.markdown(
                            f"**[{idx}] {meta.get('title', meta.get('source', 'Tài liệu'))}**  \n"
                            f"*Phương thức: `{src.get('retrieval_method', 'N/A')}` | Score: `{src.get('score', 0):.4f}`*  \n"
                            f"> {src.get('content', '')}"
                        )

    # 3. Lưu câu trả lời assistant vào session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer_text,
        "sources": sources,
        "retrieval_source": method,
    })
