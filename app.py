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
# 1. CẤU HÌNH GIAO DIỆN CHUYÊN NGHIỆP (CSS)
# =========================================================
st.set_page_config(page_title="Hệ Thống KPI AI v4.0", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    div[data-testid="stMetric"] { 
        background-color: white; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        border-left: 5px solid #3B82F6;
    }
    .main-header { font-size: 28px; font-weight: 800; color: #1E293B; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 2. HÀM XỬ LÝ DỮ LIỆU THÔNG MINH (FIX LỖI)
# =========================================================
def split_sheet_to_blocks(df):
    """Tự động tách các khối dữ liệu nếu cách nhau bởi dòng trống"""
    mask = df.notnull().any(axis=1)
    groups = (mask != mask.shift()).cumsum()
    blocks = []
    for _, g in df[mask].groupby(groups):
        if len(g) > 1:
            block = g.copy()
            # Ép kiểu tiêu đề về String để tránh lỗi TypeError: label must be string
            block.columns = [str(c) for c in block.iloc[0]]
            block = block[1:].reset_index(drop=True)
            block = block.dropna(axis=1, how='all')
            blocks.append(block)
    return blocks

@st.cache_data(ttl=600)
def load_data_from_gsheets(url, sheets):
    conn = st.connection("gsheets", type=GSheetsConnection)
    all_segments = []
    for name in sheets:
        try:
            # Fix lỗi 'open_by_url' bằng cách dùng read mặc định của connection
            raw = conn.read(spreadsheet=url, worksheet=name)
            blocks = split_sheet_to_blocks(raw)
            for b in blocks:
                all_segments.append({"source": name, "df": b})
        except Exception as e:
            st.sidebar.error(f"Lỗi đọc Sheet {name}: {e}")
    return all_segments

# --- CẤU HÌNH (BẮT BUỘC SỬA TẠI ĐÂY) ---
API_KEY = st.secrets["GEMINI_API_KEY"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit"
SHEET_LIST = ["Cửa hàng 2025", "Cửa hàng 2026", "Dự Án Online 2025", "Dự Án Online 2026", "Các nguồn 2025", "Các nguồn 2026"] # Ghi đúng tên các sheet của bạn
# ---------------------------------------

with st.spinner("💎 Đang đồng bộ hóa dữ liệu thông minh..."):
    data_bundles = load_data_from_gsheets(SHEET_URL, SHEET_LIST)
    list_of_dfs = [item["df"] for item in data_bundles]

# =========================================================
# 3. SIDEBAR - ĐIỀU KHIỂN
# =========================================================
with st.sidebar:
    st.markdown("## 💎 AI Intelligence")
    st.caption("Bản quyền hệ thống KPI v4.0")
    
    if st.button("🔄 Làm mới dữ liệu Cloud", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.subheader("📁 Dữ liệu bổ sung")
    extra = st.file_uploader("Kéo thả file Excel/CSV", type=["csv", "xlsx"])
    if extra:
        try:
            e_df = pd.read_csv(extra) if extra.name.endswith('.csv') else pd.read_excel(extra)
            e_df.columns = [str(c) for c in e_df.columns]
            list_of_dfs.append(e_df)
            st.success("✅ Đã tích hợp file.")
        except: st.error("Lỗi định dạng file.")

# =========================================================
# 4. KHỞI TẠO AI (GEMINI AGENT)
# =========================================================
if list_of_dfs:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=API_KEY, temperature=0)
        
        RULES = """
        Bạn là Chuyên gia Phân tích Dữ liệu. Trả lời Tiếng Việt.
        - Dữ liệu có nhiều bảng (Doanh thu, Chi phí...). Hãy quét hết các bảng để tìm số liệu.
        - Vẽ biểu đồ bằng matplotlib, lưu: plt.savefig('bieudo.png').
        - Định dạng tiền tệ VNĐ rõ ràng.
        """
        
        agent = create_pandas_dataframe_agent(
            llm, list_of_dfs, verbose=True, allow_dangerous_code=True, 
            handle_parsing_errors=True, prefix=RULES
        )
    except Exception as e:
        st.error(f"Lỗi AI: {e}")

# =========================================================
# 5. GIAO DIỆN CHÍNH (TABS)
# =========================================================
st.markdown("<div class='main-header'>📊 Hệ Thống Quản Trị Dữ Liệu</div>", unsafe_allow_html=True)
tab1, tab2 = st.tabs(["💬 Trợ Lý Phân Tích", "📈 Dashboard Snapshot"])

# --- TAB 1: CHATBOT AI ---
with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # Gợi ý nhanh
    col_a, col_b, col_c = st.columns(3)
    q = None
    if col_a.button("📊 Tổng doanh thu", use_container_width=True): q = "Tổng doanh thu là bao nhiêu?"
    if col_b.button("🎨 Vẽ biểu đồ", use_container_width=True): q = "Hãy vẽ biểu đồ cột so sánh các số liệu."
    if col_c.button("🔥 Điểm bất thường", use_container_width=True): q = "Có hạng mục nào sụt giảm không?"

    st.divider()
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "image" in m: st.image(m["image"])

    u_input = st.chat_input("Hỏi AI điều gì đó...")
    prompt = q or u_input

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("AI đang tính toán..."):
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
                    st.error("AI bận, thử lại sau 30 giây!")

# --- TAB 2: DASHBOARD SNAPSHOT ---
with tab2:
    if not data_bundles:
        st.info("Chưa có dữ liệu để hiển thị.")
    else:
        names = [f"Khối {i+1} (Sheet: {item['source']})" for i, item in enumerate(data_bundles)]
        choice = st.selectbox("🎯 Chọn dữ liệu cần xem nhanh:", names)
        idx = names.index(choice)
        df_target = data_bundles[idx]["df"]

        # Metrics hàng đầu
        num_cols = df_target.select_dtypes(include=[np.number]).columns
        if len(num_cols) > 0:
            m_cols = st.columns(min(len(num_cols), 4))
            for i, col in enumerate(num_cols[:4]):
                # Ép kiểu str(col) để fix lỗi TypeError của Streamlit
                m_cols[i].metric(str(col), f"{df_target[col].sum():,.0f}")
            
            st.divider()
            c_left, c_right = st.columns([2, 1])
            with c_left:
                st.markdown(f"**📈 Xu hướng: {num_cols[0]}**")
                st.line_chart(df_target[num_cols[0]])
            with c_right:
                st.markdown("**📋 Xem nhanh dữ liệu**")
                st.dataframe(df_target.head(10), hide_index=True)
        else:
            st.dataframe(df_target)
