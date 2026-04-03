import streamlit as st
import pandas as pd
import os
import io
from PIL import Image
from streamlit_gsheets import GSheetsConnection
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Siêu Trợ Lý KPI AI", page_icon="🚀", layout="wide")
st.title("🚀 Siêu Trợ Lý Phân Tích KPI & Dữ Liệu Đa Nguồn")

api_key = st.secrets["GEMINI_API_KEY"]

# --- 2. CẤU HÌNH GOOGLE SHEETS (NHỚ SỬA Ở ĐÂY) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit"
SHEET_NAMES = ["Cửa hàng 2025", "Cửa hàng 2026", "Dự Án Online 2025", "Dự Án Online 2026", "Các nguồn 2025", "Các nguồn 2026"] 

# --- 3. HÀM TẢI DỮ LIỆU ---
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
            st.warning(f"⚠️ Lỗi sheet '{sheet}': {e}")
    return dataframes

# --- SIDEBAR: CÔNG CỤ BỔ SUNG ---
with st.sidebar:
    st.header("🛠️ Công cụ bổ sung")
    
    # TÍNH NĂNG 1: TẢI FILE BỔ SUNG
    st.subheader("📁 Tải file dữ liệu mới")
    uploaded_file = st.file_uploader("Kết hợp thêm file Excel/CSV", type=["csv", "xlsx"])
    
    st.divider()
    if st.button("🔄 Làm mới dữ liệu Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    # Xuất báo cáo nhanh
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        st.download_button("📥 Tải báo cáo Chat", chat_text, "Bao_Cao.txt", use_container_width=True)

# --- XỬ LÝ DỮ LIỆU TỔNG HỢP ---
with st.spinner("Đang chuẩn bị dữ liệu..."):
    # Lấy dữ liệu từ Sheets
    sheet_data_list = load_gsheets_data()
    all_dfs_for_ai = [item["data"] for item in sheet_data_list]
    
    # Nếu có file upload thêm, gộp vào danh sách cho AI đọc
    if uploaded_file:
        try:
            extra_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            all_dfs_for_ai.append(extra_df)
            st.sidebar.success(f"✅ Đã nhận file: {uploaded_file.name}")
        except:
            st.sidebar.error("❌ File tải lên không đúng định dạng.")

# --- 4. KHỞI TẠO AI ---
if all_dfs_for_ai:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
        # AI sẽ đọc TẤT CẢ các DataFrame bao gồm từ Sheets và file Upload
        agent = create_pandas_dataframe_agent(
            llm, all_dfs_for_ai, verbose=True, allow_dangerous_code=True, handle_parsing_errors=True,
            prefix="Bạn là chuyên gia phân tích dữ liệu đa nguồn. Hãy trả lời Tiếng Việt chuyên nghiệp."
        )
    except Exception as e:
        st.error(f"Lỗi AI: {e}")

# --- 5. GIAO DIỆN TAB ---
tab1, tab2 = st.tabs(["💬 Chatbot Phân Tích", "📊 Dashboard Cố Định"])

with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # Hiển thị lịch sử
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "image" in m: st.image(m["image"])

    # Khung nhập liệu
    if prompt := st.chat_input("Hỏi tôi về dữ liệu Sheets hoặc File vừa tải lên..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Đang suy luận..."):
                try:
                    result = agent.invoke({"input": prompt})
                    response = result["output"]
                    st.markdown(response)
                    
                    msg_data = {"role": "assistant", "content": response}
                    if os.path.exists("bieudo.png"):
                        img = Image.open("bieudo.png")
                        st.image(img)
                        msg_data["image"] = img
                        os.remove("bieudo.png")
                    st.session_state.messages.append(msg_data)
                except Exception as e:
                    st.error(f"Lỗi: {e}")

with tab2:
    st.subheader("📈 Chỉ số quan trọng (Key Metrics)")
    if sheet_data_list:
        # Lấy dữ liệu từ sheet đầu tiên để làm Dashboard mẫu
        main_df = sheet_data_list[0]["data"]
        num_cols = main_df.select_dtypes(include=['number']).columns
        
        if len(num_cols) >= 2:
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Tổng {num_cols[0]}", f"{main_df[num_cols[0]].sum():,.0f}")
            c2.metric(f"Trung bình {num_cols[1]}", f"{main_df[num_cols[1]].mean():,.2f}")
            c3.metric("Số dòng dữ liệu", len(main_df))
            
            st.divider()
            st.markdown(f"**Biểu đồ xu hướng: {num_cols[0]}**")
            st.line_chart(main_df[num_cols[0]])
        else:
            st.write("Cần ít nhất 2 cột số để hiển thị Dashboard đẹp hơn.")
            st.dataframe(main_df.head(10))
