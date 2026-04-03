import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Trợ lý KPI AI", page_icon="📊", layout="wide")
st.title("📊 Chatbot Truy Vấn Dữ Liệu KPI")

# Lấy khóa AI từ phần Secrets
api_key = st.secrets["GEMINI_API_KEY"]

# --- 2. CẤU HÌNH GOOGLE SHEETS (SỬA Ở ĐÂY) ---
# 1. Dán đường link Google Sheets của bạn vào đây:
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit"

# 2. Ghi chính xác tên các Sheet bạn muốn đọc (Ví dụ: "Tháng 1", "Tháng 2"):
SHEET_NAMES = ["Cửa hàng 2025", "Cửa hàng 2026", "Dự Án Online 2025", "Dự Án Online 2026", "Các nguồn 2025", "Các nguồn 2026"] 
# ---------------------------------------------

# --- 3. HÀM TẢI DỮ LIỆU TỪ GOOGLE SHEETS ---
@st.cache_data(ttl=600) # Cứ 10 phút tự động lấy dữ liệu mới 1 lần
def load_gsheets_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    dataframes = []
    
    for sheet in SHEET_NAMES:
        try:
            # Đọc trực tiếp từng sheet được chỉ định
            df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet)
            if not df.empty:
                dataframes.append(df)
        except Exception as e:
            st.warning(f"⚠️ Bỏ qua sheet '{sheet}' vì lỗi: {e}")
            
    return dataframes

# Bắt đầu tải dữ liệu vào App
with st.spinner("Đang tải dữ liệu từ Google Sheets..."):
    dfs = load_gsheets_data()

# --- 4. KHỞI TẠO BỘ NÃO AI ---
QUY_TAC = """
Bạn là một Giám đốc Phân tích Dữ liệu (Data Analyst) chuyên nghiệp.
Nhiệm vụ của bạn là dựa vào các bảng dữ liệu được cung cấp để trả lời câu hỏi.

Quy tắc BẮT BUỘC:
1. Luôn suy luận cẩn thận các cột và dòng trước khi tính toán.
2. Trả lời hoàn toàn bằng Tiếng Việt một cách tự nhiên, chuyên nghiệp và súc tích.
3. Nếu dữ liệu không có trong bảng, hãy nói rõ là "Tôi không tìm thấy dữ liệu này", TUYỆT ĐỐI KHÔNG TỰ BỊA RA CON SỐ.
4. Với các số tiền lớn, hãy định dạng rõ ràng (Ví dụ: 15.500.000 VNĐ hoặc 15,5 triệu).
"""

if dfs:
    try:
        # Dùng model Gemini 2.5 Flash cực kỳ thông minh và nhanh
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
        
        agent = create_pandas_dataframe_agent(
            llm, 
            dfs, 
            verbose=True, 
            allow_dangerous_code=True, 
            handle_parsing_errors=True, 
            prefix=QUY_TAC
        )
    except Exception as e:
         st.error(f"❌ Lỗi khởi tạo AI: {e}")
else:
    st.error("Chưa có dữ liệu nào được tải lên! Vui lòng kiểm tra lại Link, Tên Sheet hoặc Quyền truy cập.")

# --- 5. XÂY DỰNG KHUNG CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ví dụ: Doanh thu tháng 1 là bao nhiêu?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("AI đang phân tích số liệu..."):
            try:
                result = agent.invoke({"input": prompt}, config={"callbacks": []})
                response = result["output"]
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"⚠️ Hệ thống đang gặp lỗi xử lý. Chi tiết: {e}")
