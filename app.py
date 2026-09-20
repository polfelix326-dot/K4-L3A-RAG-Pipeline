import os
import time
from dotenv import load_dotenv
import streamlit as st

from src.task10_generation import generate_with_citation

load_dotenv()

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="RAG Pipeline Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (CSS) cho giao diện hiện đại, chuyên nghiệp
st.markdown(
    """
    <style>
    /* Font & General Layout */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Header styling */
    .main-header {
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    }
    .header-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 9999px;
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        color: white;
        margin-bottom: 0.4rem;
    }
    
    /* Method badges */
    .badge-method {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.2rem 0.65rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-hybrid {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }
    .badge-dense {
        background-color: #dbeafe;
        color: #1e40af;
        border: 1px solid #bfdbfe;
    }
    .badge-bm25 {
        background-color: #ede9fe;
        color: #5b21b6;
        border: 1px solid #ddd6fe;
    }
    .badge-pageindex {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-none {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
    }
    
    /* Source item card */
    .source-card {
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
        background-color: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        transition: transform 0.15s ease;
    }
    .source-card:hover {
        transform: translateY(-1px);
        border-color: rgba(59, 130, 246, 0.4);
    }
    .source-meta {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.6rem;
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 0.35rem;
    }
    .source-title {
        font-weight: 600;
        color: #0f172a;
        font-size: 0.9rem;
    }
    .source-snippet {
        font-size: 0.84rem;
        line-height: 1.45;
        color: #334155;
        background: rgba(255, 255, 255, 0.5);
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        border-left: 3px solid #3b82f6;
    }
    /* Làm nổi bật khung chat ở cạnh dưới màn hình */
    [data-testid="stChatInput"] {
        border-radius: 12px !important;
        border: 2px solid #3b82f6 !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.15) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Khởi tạo Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "enable_memory" not in st.session_state:
    st.session_state.enable_memory = True

# Helper: format badge method
def get_method_badge(method: str) -> str:
    m = (method or "none").lower()
    icons = {
        "hybrid": "⚡",
        "dense": "🧠",
        "bm25": "🔍",
        "pageindex": "📄",
        "none": "⚠️",
    }
    icon = icons.get(m, "📌")
    return f'<span class="badge-method badge-{m}">{icon} {m.upper()}</span>'


# ==========================================
# SIDEBAR: CẤU HÌNH PIPELINE & THÔNG TIN
# ==========================================
with st.sidebar:
    st.title("🎓 RAG Assistant")
    st.caption("Chatbot RAG hỗ trợ tra cứu thông tin chính sách & quy định")
    
    st.markdown("---")
    st.subheader("⚙️ Cấu hình Retrieval")
    top_k = st.slider(
        "Số lượng tài liệu (Top-K)",
        min_value=3,
        max_value=10,
        value=5,
        step=1,
        help="Số lượng chunks trích xuất tối đa cung cấp cho bộ sinh câu trả lời.",
    )
    
    score_threshold = st.slider(
        "Ngưỡng Fallback (Threshold)",
        min_value=0.0,
        max_value=1.0,
        value=0.35,
        step=0.05,
        help="Nếu cosine score của Dense search < threshold, pipeline sẽ kích hoạt Fallback.",
    )
    
    st.markdown("---")
    st.subheader("🧠 Conversation Memory (Bonus)")
    st.session_state.enable_memory = st.checkbox(
        "Bật bộ nhớ ngữ cảnh",
        value=st.session_state.enable_memory,
        help="Lưu giữ các câu hỏi - trả lời gần nhất để LLM hiểu câu hỏi nối tiếp (follow-up).",
    )
    
    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("ℹ️ Trạng thái Hệ thống")
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    st.markdown(f"**Provider:** `{llm_provider}`")
    st.markdown(f"**Model:** `{llm_model}`")
    st.caption("Pipeline Contract: Schema v1.0 tuân thủ `MODULE_CONTRACTS.md`")


# ==========================================
# GIAO DIỆN CHÍNH (MAIN AREA)
# ==========================================
st.markdown(
    """
    <div class="main-header">
        <span class="header-badge">Vin RAG Pipeline v1.0</span>
        <h1 style="margin: 0; padding: 0; font-size: 2rem;">Trợ Lý Tra Cứu Thông Tin Thông Minh</h1>
        <p style="color: #64748b; margin-top: 0.3rem;">
            Hệ thống hỏi đáp ứng dụng Hybrid Retrieval (Dense + BM25 + RRF) kết hợp Citation & Source Verification.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Hướng dẫn vị trí ô chat & Gợi ý câu hỏi mẫu khi chưa có tin nhắn
if not st.session_state.messages:
    st.markdown(
        """
        <div style="padding: 12px 16px; background: rgba(59, 130, 246, 0.08); border-left: 4px solid #3b82f6; border-radius: 8px; margin-bottom: 1.2rem;">
            <b style="color: #1e40af;">💬 Bạn muốn đặt câu hỏi?</b><br/>
            Ô nhập câu hỏi được <b>ghim cố định ở cạnh dưới cùng của màn hình</b> (thanh chat bar ở đáy trang). Bạn có thể gõ câu hỏi vào ô <i>"💬 Nhập câu hỏi của bạn tại đây..."</i> rồi nhấn <b>Enter</b>, hoặc bấm chọn nhanh một trong các câu hỏi mẫu bên dưới:
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("### 💡 Gợi ý câu hỏi thử nghiệm")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Điều kiện xét cấp học bổng khuyến khích học tập?", use_container_width=True):
            st.session_state.prefill_query = "Điều kiện xét cấp học bổng khuyến khích học tập?"
            st.rerun()
        if st.button("💳 Quy định mức thu học phí và thời hạn đóng?", use_container_width=True):
            st.session_state.prefill_query = "Quy định mức thu học phí và thời hạn đóng?"
            st.rerun()
    with col2:
        if st.button("🏛️ Thủ tục đăng ký ký túc xá và đối tượng ưu tiên?", use_container_width=True):
            st.session_state.prefill_query = "Thủ tục đăng ký ký túc xá và đối tượng ưu tiên?"
            st.rerun()
        if st.button("🌦️ Dự báo thời tiết ngày mai thế nào? (Out-of-domain test)", use_container_width=True):
            st.session_state.prefill_query = "Dự báo thời tiết ngày mai thế nào?"
            st.rerun()

# Render các tin nhắn trong lịch sử chat
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Nếu là assistant và có nguồn trích dẫn
        sources = message.get("sources", [])
        retrieval_source = message.get("retrieval_source", "none")
        latency = message.get("latency", None)
        
        if message["role"] == "assistant" and (sources or retrieval_source != "none"):
            # Header info về retrieval
            cols = st.columns([2, 1])
            with cols[0]:
                badge_html = get_method_badge(retrieval_source)
                count_str = f"({len(sources)} trích đoạn)" if sources else "(Không tìm thấy nguồn phù hợp)"
                st.markdown(f"**Phương thức:** {badge_html} &nbsp; <small style='color:#64748b'>{count_str}</small>", unsafe_allow_html=True)
            with cols[1]:
                if latency:
                    st.caption(f"⏱️ Phản hồi: {latency:.2f}s")
            
            # Hiển thị chi tiết từng nguồn tài liệu đã dùng (Citation & Source Highlighting)
            if sources:
                with st.expander(f"📚 Xem chi tiết {len(sources)} nguồn tài liệu trích dẫn", expanded=False):
                    for s_idx, src in enumerate(sources, 1):
                        meta = src.get("metadata", {})
                        title = meta.get("title", f"Tài liệu #{s_idx}")
                        source_file = meta.get("source", "Không rõ")
                        doc_type = meta.get("doc_type", "legal")
                        url = meta.get("url")
                        score = src.get("score", 0.0)
                        method = src.get("retrieval_method", retrieval_source)
                        content = src.get("content", "").strip()
                        
                        st.markdown(
                            f"""
                            <div class="source-card">
                                <div class="source-meta">
                                    <span class="source-title">#{s_idx}. {title}</span>
                                    <span>• Nguồn: <code>{source_file}</code></span>
                                    <span>• Loại: <b>{doc_type.upper()}</b></span>
                                    <span>• Score: <b>{score:.4f}</b></span>
                                    {get_method_badge(method)}
                                </div>
                                <div class="source-snippet">
                                    {content}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if url:
                            st.caption(f"🔗 [Mở liên kết gốc]({url})")


# ==========================================
# NHẬN CÂU HỎI VÀ XỬ LÝ GENERATION
# ==========================================
# Luôn luôn hiển thị thanh st.chat_input ở dưới đáy màn hình
user_typed_query = st.chat_input("💬 Nhập câu hỏi của bạn tại đây (ấn Enter để gửi)...")

# Xác định query: từ nút bấm gợi ý hoặc từ người dùng gõ vào ô chat
query = None
if getattr(st.session_state, "prefill_query", None):
    query = st.session_state.prefill_query
    del st.session_state.prefill_query
elif user_typed_query:
    query = user_typed_query

if query:
    # 1. Hiển thị câu hỏi của User
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # 2. Xử lý câu trả lời của Assistant
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            start_time = time.time()
            
            # Tích hợp Conversation Memory nếu được bật
            enriched_query = query
            if st.session_state.enable_memory and len(st.session_state.messages) > 1:
                # Lấy 2 lượt trao đổi gần nhất làm ngữ cảnh
                recent_history = [
                    f"{m['role'].capitalize()}: {m['content']}"
                    for m in st.session_state.messages[-3:-1]
                ]
                if recent_history:
                    history_context = " | ".join(recent_history)
                    enriched_query = f"{query} (Ngữ cảnh hội thoại trước: {history_context})"

            try:
                # Gọi hàm tạo câu trả lời chuẩn theo hợp đồng Task 10
                result = generate_with_citation(query, top_k=top_k)
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                retrieval_source = result.get("retrieval_source", "hybrid")
            except NotImplementedError:
                answer = (
                    "Hệ thống đang trong quá trình tích hợp module Retrieval Pipeline. "
                    "Giao diện đã sẵn sàng nhận kết quả theo đúng chuẩn Schema `GenerationResult`."
                )
                sources = []
                retrieval_source = "none"
            except Exception as e:
                answer = f"⚠️ Đã xảy ra lỗi khi xử lý câu hỏi: {e}"
                sources = []
                retrieval_source = "none"

            elapsed = time.time() - start_time

            # Render câu trả lời
            st.markdown(answer)

            # Render badge và nguồn
            badge_html = get_method_badge(retrieval_source)
            count_str = f"({len(sources)} trích đoạn)" if sources else ""
            st.markdown(f"**Phương thức:** {badge_html} &nbsp; <small style='color:#64748b'>{count_str}</small>", unsafe_allow_html=True)

            if sources:
                with st.expander(f"📚 Xem chi tiết {len(sources)} nguồn tài liệu trích dẫn", expanded=True):
                    for s_idx, src in enumerate(sources, 1):
                        meta = src.get("metadata", {})
                        title = meta.get("title", f"Tài liệu #{s_idx}")
                        source_file = meta.get("source", "Không rõ")
                        doc_type = meta.get("doc_type", "legal")
                        url = meta.get("url")
                        score = src.get("score", 0.0)
                        method = src.get("retrieval_method", retrieval_source)
                        content = src.get("content", "").strip()

                        st.markdown(
                            f"""
                            <div class="source-card">
                                <div class="source-meta">
                                    <span class="source-title">#{s_idx}. {title}</span>
                                    <span>• Nguồn: <code>{source_file}</code></span>
                                    <span>• Loại: <b>{doc_type.upper()}</b></span>
                                    <span>• Score: <b>{score:.4f}</b></span>
                                    {get_method_badge(method)}
                                </div>
                                <div class="source-snippet">
                                    {content}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if url:
                            st.caption(f"🔗 [Mở liên kết gốc]({url})")

    # 3. Lưu vào session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
        "latency": elapsed,
    })
