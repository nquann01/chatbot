import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Trợ lý KPI AI", page_icon="📊", layout="wide")
st.title("📊 Chatbot Truy Vấn Dữ Liệu KPI Tự Động")

# Lấy khóa AI từ phần Secrets
api_key = st.secrets["GEMINI_API_KEY"]

# --- 2. CẤU HÌNH GOOGLE SHEETS ---
# SỬA Ở ĐÂY: Dán đường link Google Sheets của bạn vào giữa 2 dấu ngoặc kép:
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit?usp=sharing"
# ---------------------------------------------

# --- 3. HÀM TẢI DỮ LIỆU TỰ ĐỘNG NHẬN DIỆN SHEET ---
@st.cache_data(ttl=600) # Cứ 10 phút tự động lấy dữ liệu mới 1 lần
def load_gsheets_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    dataframes = []
    
    try:
        # Tự động quét và lấy TẤT CẢ tên sheet có trong file
        spreadsheet = conn.client.open_by_url(SHEET_URL)
        all_sheet_names = [sheet.title for sheet in spreadsheet.worksheets()]
        
        # Duyệt qua từng sheet và tải dữ liệu
        for sheet_name in all_sheet_names:
            try:
                df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name)
                # Chỉ lấy bảng có dữ liệu, bỏ qua các sheet trống để AI không bị nhiễu
                if not df.empty:
                    dataframes.append(df)
            except Exception as e:
                pass 
                
    except Exception as main_error:
        st.error(f"❌ Lỗi kết nối Google Sheets: {main_error}")
        
    return dataframes

# Bắt đầu tải dữ liệu vào App
with st.spinner("Đang tự động quét và tải dữ liệu từ Google Sheets..."):
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
        
        # Tạo Agent để AI đọc DataFrame
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
    st.error("Chưa có dữ liệu nào được tải lên! Vui lòng kiểm tra lại Link Google Sheets hoặc Quyền truy cập của Robot.")

# --- 5. XÂY DỰNG KHUNG CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị lại lịch sử chat cũ
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Xử lý khi người dùng gõ câu hỏi mới
if prompt := st.chat_input("Ví dụ: Doanh thu tháng 1 là bao nhiêu?"):
    # Hiện câu hỏi của user
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI tính toán và trả lời
    with st.chat_message("assistant"):
        with st.spinner("AI đang phân tích số liệu..."):
            try:
                # Dùng .invoke() và tắt callbacks để tránh lỗi Streamlit
                result = agent.invoke({"input": prompt}, config={"callbacks": []})
                response = result["output"]
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"⚠️ Hệ thống đang gặp lỗi xử lý dữ liệu. Chi tiết: {e}")
