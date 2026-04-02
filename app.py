import streamlit as st
import pandas as pd
import os
import glob
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# Cấu hình giao diện trang web
st.set_page_config(page_title="Trợ lý KPI AI", page_icon="📊")
st.title("📊 Chatbot Truy Vấn Dữ Liệu KPI 2025")

# Lấy khóa bảo mật AI từ hệ thống
api_key = st.secrets["GEMINI_API_KEY"]

# Hàm tự động đọc tất cả file CSV
# Hàm tự động đọc tất cả các file Excel (.xlsx) và từng Sheet bên trong
@st.cache_data
def load_excel_files():
    excel_files = glob.glob("*.xlsx")
    dataframes = []
    
    for file in excel_files:
        try:
            # sheet_name=None giúp đọc TOÀN BỘ các sheet trong file
            excel_data = pd.read_excel(file, sheet_name=None) 
            
            # Tách từng sheet ra thành từng bảng dữ liệu riêng cho AI đọc
            for sheet_name, df in excel_data.items():
                dataframes.append(df)
        except Exception as e:
            pass
            
    return dataframes

dfs = load_excel_files()

# Khởi tạo "Bộ não" AI
if dfs:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0)
    agent = create_pandas_dataframe_agent(llm, dfs, verbose=True, allow_dangerous_code=True, handle_parsing_errors=True)
else:
    st.error("Không tìm thấy file dữ liệu nào!")

# Xây dựng giao diện Chatbot
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Khung nhập câu hỏi
if prompt := st.chat_input("Ví dụ: Doanh thu cửa hàng Đỗ Quang tháng 1 là bao nhiêu?"):
    # Hiển thị câu hỏi của user
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI xử lý và trả lời
    with st.chat_message("assistant"):
        with st.spinner("AI đang tính toán số liệu..."):
            try:
                # Cú pháp chuẩn của LangChain bản mới nhất: {"input": prompt}
                result = agent.invoke({"input": prompt})
                response = result["output"]
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                # In thẳng nguyên nhân lỗi ra màn hình để bắt bệnh ngay lập tức
                st.error(f"Hệ thống đang gặp lỗi kỹ thuật. Mã lỗi chi tiết: {e}")
