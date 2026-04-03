import streamlit as st
import pandas as pd
import os
import io
from PIL import Image
from streamlit_gsheets import GSheetsConnection
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. ĐỊNH NGHĨA PHONG CÁCH CHUYÊN NGHIỆP (CSS CUSTOM) ---
st.set_page_config(page_title="KPI Intelligence Hub", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    /* Tổng thể nền và font */
    .main { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    /* Tùy chỉnh Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        color: white !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p {
        color: #94A3B8 !important;
    }
    
    /* Card cho Metric */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #E2E8F0;
    }
    
    /* Tùy chỉnh khung Chat */
    .stChatMessage {
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
    }
    
    /* Header chuyên nghiệp */
    .main-header {
        font-size: 32px;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 20px;
        letter-spacing: -0.025em;
    }
    
    /* Nút bấm tinh tế */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC TẢI DỮ LIỆU ---
api_key = st.secrets["GEMINI_API_KEY"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit"
SHEET_NAMES = ["Cửa hàng 2025", "Cửa hàng 2026", "Dự Án Online 2025", "Dự Án Online 2026", "Các nguồn 2025", "Các nguồn 2026"] 

@st.cache_data(ttl=600)
def load_gsheets_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    dataframes = []
    for sheet in SHEET_NAMES:
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet)
            df = df.dropna(how='all').dropna(axis=1, how='all')
            if not df.empty:
                dataframes.append({"name": sheet, "data": df})
        except Exception as e:
            st.error(f"Lỗi đọc sheet {sheet}: {e}")
    return dataframes

with st.spinner("💎 Đang kết nối hệ thống dữ liệu..."):
    sheet_data_list = load_gsheets_data()
    all_dfs = [item["data"] for item in sheet_data_list]

# --- 3. THANH SIDEBAR (SIDEBAR UX) ---
with st.sidebar:
    st.markdown("<h2 style='color: white;'>💎 Intelligence Hub</h2>", unsafe_allow_html=True)
    st.caption("Phiên bản Doanh nghiệp v2.0")
    
    st.divider()
    
    st.subheader("📁 Quản lý nguồn")
    uploaded_file = st.file_uploader("Bổ sung dữ liệu tạm thời", type=["csv", "xlsx"])
    
    if st.button("🔄 Đồng bộ dữ liệu mới nhất", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    
    st.subheader("📥 Báo cáo nhanh")
    if "messages" in st.session_state and st.session_state.messages:
        chat_log = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
        st.download_button("📩 Tải lịch sử phân tích", chat_log, "KPI_Analysis.txt", use_container_width=True)

# --- 4. KHỞI TẠO AI AGENT ---
if all_dfs:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.1)
        agent = create_pandas_dataframe_agent(
            llm, all_dfs, verbose=True, allow_dangerous_code=True, handle_parsing_errors=True,
            prefix="Bạn là chuyên gia phân tích dữ liệu cao cấp. Luôn trả lời bằng Tiếng Việt, sử dụng các thuật ngữ kinh doanh chuyên nghiệp. Ưu tiên trình bày kết quả dưới dạng danh sách hoặc bảng nếu có thể."
        )
    except Exception as e:
        st.error(f"Lỗi AI: {e}")

# --- 5. GIAO DIỆN CHÍNH (TABS UX) ---
st.markdown("<div class='main-header'>📊 Hệ Thống Quản Trị KPI</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["💬 Trợ Lý Chiến Lược", "🚀 Dashboard Điều Hành"])

# TAB 1: CHATBOT AI
with tab1:
    # Gợi ý câu hỏi tinh tế dưới dạng Cards
    st.markdown("#### Bạn muốn phân tích điều gì hôm nay?")
    c1, c2, c3 = st.columns(3)
    q = None
    with c1: 
        if st.button("📉 Tìm xu hướng tăng trưởng", use_container_width=True): q = "Phân tích xu hướng tăng trưởng của các chỉ số chính."
    with c2: 
        if st.button("🎯 Kiểm tra mục tiêu KPI", use_container_width=True): q = "Hạng mục nào đã đạt KPI, hạng mục nào chưa?"
    with c3: 
        if st.button("🎨 Biểu đồ tổng quan", use_container_width=True): q = "Vẽ biểu đồ cột so sánh các chỉ số quan trọng."

    st.divider()
    
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # Hiển thị lịch sử chat
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "image" in m: st.image(m["image"])

    # Khung input chat
    if user_input := st.chat_input("Nhập câu hỏi phân tích..."):
        prompt = q or user_input
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("AI đang xử lý dữ liệu chuyên sâu..."):
                try:
                    res = agent.invoke({"input": prompt})
                    ans = res["output"]
                    st.markdown(ans)
                    msg = {"role": "assistant", "content": ans}
                    if os.path.exists("bieudo.png"):
                        img = Image.open("bieudo.png")
                        st.image(img)
                        msg["image"] = img
                        os.remove("bieudo.png")
                    st.session_state.messages.append(msg)
                except Exception as e:
                    st.error("⚠️ Hệ thống đang quá tải. Vui lòng thử lại sau 30 giây.")

# TAB 2: DASHBOARD ĐIỀU HÀNH
with tab2:
    if sheet_data_list:
        selected_name = st.selectbox("📂 Chọn bộ dữ liệu hiển thị:", [item["name"] for item in sheet_data_list])
        df_final = next(item["data"] for item in sheet_data_list if item["name"] == selected_name)
        
        # Dashboard Header
        st.markdown(f"### ⚡ Snapshot: {selected_name}")
        
        # Metrics Row
        num_cols = df_final.select_dtypes(include=['number']).columns
        if len(num_cols) > 0:
            m_cols = st.columns(len(num_cols[:4]))
            for i, col in enumerate(num_cols[:4]):
                with m_cols[i]:
                    st.metric(label=col, value=f"{df_final[col].sum():,.0f}")
            
            st.divider()
            
            # Charts Row
            g1, g2 = st.columns([2, 1])
            with g1:
                st.markdown("**📉 Biểu đồ biến động thực tế**")
                st.area_chart(df_final[num_cols[0]])
            with g2:
                st.markdown("**📋 Top 10 bản ghi mới nhất**")
                st.dataframe(df_final.head(10), hide_index=True)
        else:
            st.dataframe(df_final)
