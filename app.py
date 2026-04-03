import streamlit as st
import pandas as pd
import os
import io
import numpy as np
from PIL import Image
from streamlit_gsheets import GSheetsConnection
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# =========================================================
# 1. CẤU HÌNH GIAO DIỆN CHUYÊN NGHIỆP (UX/UI)
# =========================================================
st.set_page_config(page_title="Hệ Thống Phân Tích KPI AI", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #F1F5F9; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    .stMetric { 
        background-color: white; 
        padding: 20px; 
        border-radius: 15px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        border-left: 5px solid #3B82F6;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #E2E8F0;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 2. HÀM XỬ LÝ DỮ LIỆU ĐA TẦNG (FIX LỖI ĐỌC SAI)
# =========================================================
def split_dataframe_by_empty_rows(df):
    """Tự động tách một Sheet thành nhiều bảng nhỏ nếu có dòng trống giữa chúng"""
    # Tìm các dòng không hoàn toàn trống
    mask = df.notnull().any(axis=1)
    # Gom nhóm các dòng liên tục có dữ liệu
    groups = (mask != mask.shift()).cumsum()
    dfs = []
    for _, g in df[mask].groupby(groups):
        if len(g) > 1:
            # Lấy dòng đầu của nhóm làm Header
            new_df = g.copy()
            new_df.columns = new_df.iloc[0]
            new_df = new_df[1:].reset_index(drop=True)
            # Xóa các cột hoàn toàn trống trong bảng nhỏ
            new_df = new_df.dropna(axis=1, how='all')
            dfs.append(new_df)
    return dfs

@st.cache_data(ttl=600)
def load_full_data(sheet_url, sheet_names):
    conn = st.connection("gsheets", type=GSheetsConnection)
    all_data_segments = []
    for name in sheet_names:
        try:
            raw_df = conn.read(spreadsheet=sheet_url, worksheet=name)
            # Tách các khối dữ liệu trong cùng 1 sheet
            segments = split_dataframe_by_empty_rows(raw_df)
            for s in segments:
                all_data_segments.append({"sheet": name, "df": s})
        except Exception as e:
            st.sidebar.error(f"Lỗi đọc Sheet {name}: {e}")
    return all_data_segments

# --- CẤU HÌNH NGUỒN (SỬA TẠI ĐÂY) ---
API_KEY = st.secrets["GEMINI_API_KEY"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit"
# Liệt kê tất cả sheet bạn muốn App quét qua:
SHEET_LIST = ["Cửa hàng 2025", "Cửa hàng 2026", "Dự Án Online 2025", "Dự Án Online 2026", "Các nguồn 2025", "Các nguồn 2026"] 

with st.spinner("💎 Hệ thống đang phân tích cấu trúc dữ liệu..."):
    data_bundles = load_full_data(SHEET_URL, SHEET_LIST)
    list_of_dfs = [item["df"] for item in data_bundles]

# =========================================================
# 3. SIDEBAR - ĐIỀU KHIỂN & HYBRID DATA
# =========================================================
with st.sidebar:
    st.markdown("## 💎 Intelligence Hub")
    st.caption("Quản trị dữ liệu đa nguồn v3.0")
    
    if st.button("🔄 Làm mới dữ liệu Cloud", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.subheader("📁 Nạp thêm dữ liệu")
    extra_file = st.file_uploader("Upload file Excel/CSV tạm thời", type=["csv", "xlsx"])
    if extra_file:
        try:
            edf = pd.read_csv(extra_file) if extra_file.name.endswith('.csv') else pd.read_excel(extra_file)
            list_of_dfs.append(edf)
            st.success("✅ Đã gộp file mới vào bộ não AI!")
        except: st.error("Lỗi định dạng file.")

    st.divider()
    if "messages" in st.session_state and st.session_state.messages:
        full_log = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
        st.download_button("📥 Xuất báo cáo Chat", full_log, "Report_KPI.txt", use_container_width=True)

# =========================================================
# 4. KHỞI TẠO BỘ NÃO AI (GEMINI)
# =========================================================
if list_of_dfs:
    try:
        # Sử dụng model 1.5-flash để cân bằng giữa tốc độ và độ thông minh
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=API_KEY, temperature=0)
        
        SYTEM_PROMPT = """
        Bạn là Giám đốc Phân tích Dữ liệu chuyên nghiệp. 
        - Bạn được cung cấp DANH SÁCH NHIỀU BẢNG dữ liệu từ Google Sheets.
        - Một sheet có thể chứa nhiều bảng khác nhau (Doanh thu, Chi phí, KPI...). Hãy kiểm tra kỹ từng bảng.
        - Trả lời bằng Tiếng Việt, lịch sự. Định dạng số tiền kiểu 1.000.000 VNĐ.
        - Khi vẽ biểu đồ: dùng matplotlib, lưu bằng plt.savefig('bieudo.png').
        - Nếu dữ liệu không rõ ràng, hãy hỏi lại người dùng thay vì đoán sai.
        """
        
        agent = create_pandas_dataframe_agent(
            llm, list_of_dfs, verbose=True, allow_dangerous_code=True, 
            handle_parsing_errors=True, prefix=SYTEM_PROMPT
        )
    except Exception as e:
        st.error(f"Lỗi AI: {e}")

# =========================================================
# 5. GIAO DIỆN TABS CHÍNH
# =========================================================
tab1, tab2 = st.tabs(["💬 Trợ Lý Chiến Lược", "📊 Trung Tâm Điều Hành"])

# --- TAB 1: AI CHATBOT ---
with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    
    st.markdown("#### Bạn cần phân tích chỉ số nào?")
    c1, c2, c3 = st.columns(3)
    q = None
    if c1.button("📊 Tổng hợp Doanh thu"): q = "Tính tổng doanh thu và liệt kê theo từng hạng mục chính."
    if c2.button("📉 Tìm điểm bất thường"): q = "Dữ liệu có điểm nào bất thường hoặc sụt giảm nghiêm trọng không?"
    if c3.button("🎨 Vẽ biểu đồ xu hướng"): q = "Vẽ biểu đồ đường thể hiện biến động dữ liệu quan trọng nhất."

    st.divider()
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "image" in m: st.image(m["image"])

    u_input = st.chat_input("Hỏi AI về bất kỳ dữ liệu nào trong Sheets...")
    prompt = q or u_input

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("AI đang truy vấn đa bảng..."):
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
                    st.error("Gặp lỗi hoặc hết hạn mức. Vui lòng thử lại sau 1 phút.")

# --- TAB 2: DASHBOARD TỔNG LỰC ---
with tab2:
    if not data_bundles:
        st.info("Chưa có dữ liệu.")
    else:
        # Chọn bảng để xem chi tiết
        names = [f"Bảng {i+1} (từ {item['sheet']})" for i, item in enumerate(data_bundles)]
        choice = st.selectbox("🎯 Chọn khối dữ liệu muốn xem nhanh:", names)
        idx = names.index(choice)
        df_target = data_bundles[idx]["df"]

        # Metrics hàng đầu
        num_cols = df_target.select_dtypes(include=[np.number]).columns
        if len(num_cols) > 0:
            m_cols = st.columns(min(len(num_cols), 4))
            for i, col in enumerate(num_cols[:4]):
                m_cols[i].metric(col, f"{df_target[col].sum():,.0f}")
            
            st.divider()
            
            # Biểu đồ tự động
            g1, g2 = st.columns([2, 1])
            with g1:
                st.markdown(f"**📈 Biểu đồ đường: {num_cols[0]}**")
                st.line_chart(df_target[num_cols[0]])
            with g2:
                st.markdown("**📋 Dữ liệu thô**")
                st.dataframe(df_target.head(10), hide_index=True)
        else:
            st.dataframe(df_target)
