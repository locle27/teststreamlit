"""
🏨 HOTEL ROOM MANAGEMENT SYSTEM
=====================================
Hệ thống quản lý phòng khách sạn hiện đại với giao diện thân thiện và chức năng tải lên Google Sheets

INSTALLATION REQUIREMENTS:
pip install streamlit pandas numpy plotly openpyxl xlrd pypdf2 beautifulsoup4 gspread google-auth google-auth-oauthlib

Author: Optimized Version (Reviewed and Enhanced by Gemini)
Version: 3.1.4 (Fixed expander css_class error, using open_by_key)
"""

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import plotly.express as px
import io
import calendar
from datetime import timedelta
import re
import xlrd # Cần thiết cho file .xls cũ
import openpyxl # Cần thiết cho file .xlsx hiện đại
import csv
from typing import Dict, List, Optional, Tuple, Any
import json # Để đọc service account key

# Kiểm tra và nhập các thư viện tùy chọn, thông báo nếu thiếu
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    st.warning("⚠️ Thư viện PyPDF2 không có sẵn. Chức năng xử lý file PDF sẽ bị vô hiệu hóa. Vui lòng cài đặt: pip install pypdf2")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    st.warning("⚠️ Thư viện BeautifulSoup4 không có sẵn. Chức năng xử lý file HTML sẽ bị vô hiệu hóa. Vui lòng cài đặt: pip install beautifulsoup4")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    # Sẽ hiển thị cảnh báo trong sidebar sau


# Hằng số toàn cục xác định số lượng đơn vị phòng cho mỗi loại phòng
ROOM_UNIT_PER_ROOM_TYPE = 4 # <<<< THAY ĐỔI Ở ĐÂY
# Hằng số toàn cục xác định tổng số phòng vật lý của khách sạn
TOTAL_HOTEL_CAPACITY = 4 # (Giữ nguyên là 4 theo yêu cầu)

# Định nghĩa các cột cơ sở và cột dẫn xuất
REQUIRED_APP_COLS_BASE = [
    'Tên chỗ nghỉ', 'Vị trí', 'Tên người đặt', 'Thành viên Genius',
    'Ngày đến', 'Ngày đi', 'Được đặt vào',
    'Tình trạng', 'Tổng thanh toán', 'Hoa hồng', 'Tiền tệ', 'Số đặt phòng',
    'Check-in Date', 'Check-out Date', 'Booking Date', 'Stay Duration'
]
REQUIRED_APP_COLS_DERIVED = ['Giá mỗi đêm']
ALL_REQUIRED_COLS = REQUIRED_APP_COLS_BASE + REQUIRED_APP_COLS_DERIVED


# Cấu hình trang Streamlit nâng cao
st.set_page_config(
    page_title="🏨 Hotel Management Pro",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bugs",
        'About': "# Hotel Management System v3.1.4\nĐã sửa lỗi css_class của expander, sử dụng open_by_key."
    }
)

# CSS tùy chỉnh
st.markdown("""
<style>
    :root {
        --primary-color: #1f77b4; --secondary-color: #ff7f0e; --success-color: #2ca02c;
        --warning-color: #ffbb00; --danger-color: #d62728; --info-color: #17a2b8;
        --light-bg: #f8f9fa; --dark-bg: #343a40;
    }
    .css-1d391kg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .metric-card { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 5px solid var(--primary-color); margin-bottom: 1rem; transition: transform 0.2s ease, box-shadow 0.2s ease; }
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 4px 20px rgba(0,0,0,0.15); }
    .stButton > button { border-radius: 20px; border: none; padding: 0.6rem 1.2rem; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    .status-available { color: var(--success-color); font-weight: bold; }
    .status-occupied { color: var(--danger-color); font-weight: bold; }
    .status-partial { color: var(--warning-color); font-weight: bold; }
    .dataframe { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .loading-spinner { border: 4px solid #f3f3f3; border-top: 4px solid var(--primary-color); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; text-align: center; font-family: 'Segoe UI', sans-serif; } .day-header { font-weight: bold; padding: 8px 0; background-color: #e9ecef; color: #495057; border-radius: 5px; font-size: 0.9em; } .day-cell { border: 1px solid #dee2e6; padding: 8px 2px; min-height: 75px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; border-radius: 5px; cursor: pointer; transition: background-color 0.2s, box-shadow 0.2s; position: relative; background-color: #fff; } .day-cell:hover { background-color: #f8f9fa; box-shadow: 0 0 5px rgba(0,0,0,0.1); } .day-button-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; z-index: 10; cursor: pointer; } .day-number { font-size: 1.1em; font-weight: bold; margin-bottom: 3px; color: #343a40; } .day-status { font-size: 0.75em; color: #6c757d; padding: 0 2px; word-break: break-word; } .dot-indicator { font-size: 1.8em; line-height: 0.5; margin-top: -2px; margin-bottom: 2px; } .dot-green { color: var(--success-color); } .dot-orange { color: var(--warning-color); } .dot-red { color: var(--danger-color); } .day-disabled { color: #adb5bd; background-color: #f1f3f5; cursor: not-allowed; } .day-today { border: 2px solid var(--primary-color); background-color: #e7f3ff; } .day-selected { background-color: #cfe2ff; border: 2px solid #0a58ca; box-shadow: 0 0 8px rgba(10, 88, 202, 0.3); } .guest-separator { border-bottom: 1px dashed #ced4da; margin: 4px 0; width: 90%; align-self: center; } 
    /* .calendar-details-expander .streamlit-expanderHeader { font-size: 1.1em; font-weight: bold; } */ /* Bỏ hoặc sửa nếu cần */
    /* .calendar-details-expander p { margin-bottom: 0.3rem; } */ /* Bỏ hoặc sửa nếu cần */
</style>
""", unsafe_allow_html=True)

# --- MẪU TIN NHẮN VÀ HÀM XỬ LÝ ---
DEFAULT_MESSAGE_TEMPLATE_CONTENT = """
HET PHONG : We sincerely apologize for this inconvenience. Due to an unforeseen issue, the room you booked is no longer available
Thank you for your understanding.
We hope to have the pleasure of welcoming you on your next visit.
Have a pleasant evening

DON PHONG : You're welcome! Please feel free to relax and get some breakfast.
We'll get your room ready and clean for you, and I'll let you know as soon as possible when it's all set

WELCOME :
1. Welcome!
2. Chào mừng bạn đến với chỗ nghỉ của chúng tôi!
3. We hope you have a pleasant stay.

CHECK OUT :
1. Check-out time is 12:00 noon. Please leave the key in the room and close the door when you leave. Thank you!
2. If you need to check out earlier or later, please let us know in advance.

WIFI INFO :
1. Wi-Fi name: OldQuarterHome
Password: 12345678
2. Wi-Fi name: HomeInOldQuarter
Password: 87654321

HDSD :
1. Please turn off the lights, air conditioner, and electrical devices when you go out.
2. Vui lòng giữ gìn vệ sinh chung và không hút thuốc trong phòng.

LATE CHECK OUT :
If you need to check out later than 12:00, please inform us in advance. Additional charges may apply.

EARLY CHECK IN : Hello, I'm so sorry, but the room isn't available right now.
You're welcome to leave your luggage here and use the Wi-Fi.
I'll check again around 12:00 AM and let you know as soon as possible

CHECK IN : When you arrive at 118 Hang Bac Street, you will see a souvenir shop at the front.
Please walk into the shop about 10 meters, and you will find a staircase on your right-hand side.
Go up the stairs, then look for your room number.
The door will be unlocked, and the key will be inside the room.
FEED BACK : We hope you had a wonderful stay!
We'd love to hear about your experience – feel free to leave us a review on Booking.com

PARK : Please park your motorbike across the street, but make sure not to block their right-side door.
"""

def parse_message_templates(text_content: str) -> Dict[str, List[Tuple[str, str]]]:
    templates: Dict[str, List[Tuple[str, str]]] = {}
    current_category: Optional[str] = None
    current_label: Optional[str] = None
    current_message_lines: List[str] = []
    cleaned_content = re.sub(r"'", "", text_content)

    def finalize_and_store_message():
        nonlocal current_category, current_label, current_message_lines, templates
        if current_category and current_label and current_message_lines:
            message = "\n".join(current_message_lines).strip()
            if message:
                if current_category not in templates:
                    templates[current_category] = []
                existing_label_index = -1
                for i, (lbl, _) in enumerate(templates[current_category]):
                    if lbl == current_label:
                        existing_label_index = i
                        break
                if existing_label_index != -1:
                    templates[current_category][existing_label_index] = (current_label, message)
                else:
                    templates[current_category].append((current_label, message))
            current_message_lines = []

    for line in cleaned_content.splitlines():
        stripped_line = line.strip()
        main_cat_match = re.match(r'^([A-Z][A-Z\s]*[A-Z]|[A-Z]+)\s*:\s*(.*)', line)
        sub_label_numbered_match = re.match(r'^\s*(\d+\.)\s*(.*)', stripped_line)
        sub_label_named_match = None
        if current_category:
             potential_sub_label_named_match = re.match(r'^\s*([\w\s()]+?)\s*:\s*(.*)', stripped_line)
             if potential_sub_label_named_match:
                 if potential_sub_label_named_match.group(1).strip() != current_category and potential_sub_label_named_match.group(1).strip().isupper() is False:
                     sub_label_named_match = potential_sub_label_named_match
        if main_cat_match:
            potential_cat_name = main_cat_match.group(1).strip()
            if potential_cat_name.isupper():
                finalize_and_store_message()
                current_category = potential_cat_name
                current_label = "DEFAULT"
                message_on_same_line = main_cat_match.group(2).strip()
                if message_on_same_line:
                    current_message_lines.append(message_on_same_line)
            elif current_category and sub_label_named_match is None:
                sub_label_named_match = main_cat_match
        if current_category:
            is_new_sub_label = False
            if sub_label_numbered_match:
                finalize_and_store_message()
                current_label = sub_label_numbered_match.group(1).strip()
                message_on_same_line = sub_label_numbered_match.group(2).strip()
                if message_on_same_line:
                    current_message_lines.append(message_on_same_line)
                is_new_sub_label = True
            elif sub_label_named_match:
                if not (main_cat_match and main_cat_match.group(1).strip().isupper() and main_cat_match.group(1).strip() == sub_label_named_match.group(1).strip()):
                    finalize_and_store_message()
                    current_label = sub_label_named_match.group(1).strip()
                    message_on_same_line = sub_label_named_match.group(2).strip()
                    if message_on_same_line:
                        current_message_lines.append(message_on_same_line)
                    is_new_sub_label = True
            if not is_new_sub_label and main_cat_match is None:
                if stripped_line or current_message_lines:
                    if not current_label and stripped_line:
                        current_label = "DEFAULT"
                    current_message_lines.append(line)
    finalize_and_store_message()
    return templates

def format_templates_to_text(templates_dict: Dict[str, List[Tuple[str, str]]]) -> str:
    output_lines = []
    for category_name in sorted(templates_dict.keys()):
        labeled_messages = templates_dict[category_name]
        default_message_written_on_cat_line = False
        if labeled_messages and labeled_messages[0][0] == "DEFAULT":
            default_msg_text = labeled_messages[0][1]
            msg_lines = default_msg_text.split('\n')
            output_lines.append(f"{category_name} : {msg_lines[0] if msg_lines else ''}")
            if len(msg_lines) > 1:
                output_lines.extend(msg_lines[1:])
            default_message_written_on_cat_line = True
        else:
            output_lines.append(f"{category_name} :")

        for i, (label, msg_text) in enumerate(labeled_messages):
            if label == "DEFAULT" and default_message_written_on_cat_line and i == 0:
                continue
            msg_lines = msg_text.split('\n')
            if not (label == "DEFAULT" and i==0) :
                 if not (default_message_written_on_cat_line and i==0 and label=="DEFAULT"):
                      if not (not default_message_written_on_cat_line and i==0 and label=="DEFAULT" and output_lines and not output_lines[-1].endswith(":")):
                        output_lines.append("")
            if label == "DEFAULT":
                output_lines.extend(msg_lines)
            elif label.endswith('.'):
                output_lines.append(f"{label} {msg_lines[0] if msg_lines else ''}")
                if len(msg_lines) > 1:
                    output_lines.extend(msg_lines[1:])
            else:
                output_lines.append(f"{label} : {msg_lines[0] if msg_lines else ''}")
                if len(msg_lines) > 1:
                    output_lines.extend(msg_lines[1:])
        output_lines.append("")
    return "\n".join(output_lines) if output_lines else ""

def parse_app_standard_date(date_input: Any) -> Optional[datetime.date]:
    if pd.isna(date_input):
        return None
    if isinstance(date_input, datetime.datetime):
        return date_input.date()
    if isinstance(date_input, datetime.date):
        return date_input
    if isinstance(date_input, pd.Timestamp):
        return date_input.date()
    date_str = str(date_input).strip().lower()
    try:
        if re.match(r"ngày\s*\d{1,2}\s*tháng\s*\d{1,2}\s*năm\s*\d{4}", date_str):
            m = re.search(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", date_str)
            if m:
                return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        parsed_date = pd.to_datetime(date_str, errors='coerce', dayfirst=True).date()
        if parsed_date:
            return parsed_date
        parsed_date = pd.to_datetime(date_str, errors='coerce', dayfirst=False).date()
        if parsed_date:
            return parsed_date
    except Exception:
        pass
    st.warning(f"Không thể phân tích ngày: '{date_input}'.")
    return None

def create_demo_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    st.info("Đang tạo dữ liệu demo...")
    demo_data = {
        'Tên chỗ nghỉ': [
            'Home in Old Quarter - Night market',
            'Old Quarter Home- Kitchen & Balcony',
            'Home in Old Quarter - Night market',
            'Old Quarter Home- Kitchen & Balcony',
            'Riverside Boutique Apartment'
        ],
        'Vị trí': [
            'Phố Cổ Hà Nội, Hoàn Kiếm, Vietnam',
            '118 Phố Hàng Bạc, Hoàn Kiếm, Vietnam',
            'Phố Cổ Hà Nội, Hoàn Kiếm, Vietnam',
            '118 Phố Hàng Bạc, Hoàn Kiếm, Vietnam',
            'Quận 2, TP. Hồ Chí Minh, Vietnam'
        ],
        'Tên người đặt': [
            'Demo User Alpha',
            'Demo User Beta',
            'Demo User Alpha',
            'Demo User Gamma',
            'Demo User Delta'
        ],
        'Thành viên Genius': ['Không', 'Có', 'Không', 'Có', 'Không'],
        'Ngày đến': [
            'ngày 22 tháng 5 năm 2025',
            'ngày 23 tháng 5 năm 2025',
            'ngày 25 tháng 5 năm 2025',
            'ngày 26 tháng 5 năm 2025',
            'ngày 1 tháng 6 năm 2025'
        ],
        'Ngày đi': [
            'ngày 23 tháng 5 năm 2025',
            'ngày 24 tháng 5 năm 2025',
            'ngày 26 tháng 5 năm 2025',
            'ngày 28 tháng 5 năm 2025',
            'ngày 5 tháng 6 năm 2025'
        ],
        'Được đặt vào': [
            'ngày 20 tháng 5 năm 2025',
            'ngày 21 tháng 5 năm 2025',
            'ngày 22 tháng 5 năm 2025',
            'ngày 23 tháng 5 năm 2025',
            'ngày 25 tháng 5 năm 2025'
        ],
        'Tình trạng': ['OK', 'OK', 'Đã hủy', 'OK', 'OK'],
        'Tổng thanh toán': [300000, 450000, 200000, 600000, 1200000],
        'Hoa hồng': [60000, 90000, 40000, 120000, 240000],
        'Tiền tệ': ['VND', 'VND', 'VND', 'VND', 'VND'],
        'Số đặt phòng': [f'DEMO{i+1:09d}' for i in range(5)]
    }
    df_demo = pd.DataFrame(demo_data)
    df_demo['Check-in Date'] = df_demo['Ngày đến'].apply(parse_app_standard_date)
    df_demo['Check-out Date'] = df_demo['Ngày đi'].apply(parse_app_standard_date)
    df_demo['Booking Date'] = df_demo['Được đặt vào'].apply(parse_app_standard_date)
    df_demo['Check-in Date'] = pd.to_datetime(df_demo['Check-in Date'], errors='coerce')
    df_demo['Check-out Date'] = pd.to_datetime(df_demo['Check-out Date'], errors='coerce')
    df_demo['Booking Date'] = pd.to_datetime(df_demo['Booking Date'], errors='coerce')
    df_demo.dropna(subset=['Check-in Date', 'Check-out Date'], inplace=True)
    if not df_demo.empty:
        df_demo['Stay Duration'] = (df_demo['Check-out Date'] - df_demo['Check-in Date']).dt.days
        df_demo['Stay Duration'] = df_demo['Stay Duration'].apply(lambda x: max(0, x) if pd.notna(x) else 0)
    else:
        df_demo['Stay Duration'] = 0

    if 'Tổng thanh toán' in df_demo.columns and 'Stay Duration' in df_demo.columns:
        df_demo['Giá mỗi đêm'] = np.where(
            (df_demo['Stay Duration'].notna()) & (df_demo['Stay Duration'] > 0) & (df_demo['Tổng thanh toán'].notna()),
            df_demo['Tổng thanh toán'] / df_demo['Stay Duration'],
            0.0
        ).round(0)
    else:
        df_demo['Giá mỗi đêm'] = 0.0

    active_bookings_demo = df_demo[df_demo['Tình trạng'] != 'Đã hủy'].copy()
    return df_demo, active_bookings_demo

# --- KHỞI TẠO SESSION STATE ---
# ... (Giữ nguyên)
if 'df' not in st.session_state: st.session_state.df = None
if 'active_bookings' not in st.session_state: st.session_state.active_bookings = None
if 'room_types' not in st.session_state: st.session_state.room_types = []
if 'data_source' not in st.session_state: st.session_state.data_source = None
if 'uploaded_file_name' not in st.session_state: st.session_state.uploaded_file_name = None
if 'last_action_message' not in st.session_state: st.session_state.last_action_message = None
if 'current_date_calendar' not in st.session_state: st.session_state.current_date_calendar = datetime.date.today()
if 'selected_calendar_date' not in st.session_state: st.session_state.selected_calendar_date = None
if 'booking_sort_column' not in st.session_state:
    st.session_state.booking_sort_column = 'Booking Date'
if 'booking_sort_ascending' not in st.session_state:
    st.session_state.booking_sort_ascending = False

if 'message_templates_dict' not in st.session_state:
    st.session_state.message_templates_dict = parse_message_templates(DEFAULT_MESSAGE_TEMPLATE_CONTENT)

if 'raw_template_content_for_download' not in st.session_state:
    if 'message_templates_dict' in st.session_state and st.session_state.message_templates_dict is not None:
        st.session_state.raw_template_content_for_download = format_templates_to_text(st.session_state.message_templates_dict)
    else:
        st.session_state.raw_template_content_for_download = ""

if 'editing_booking_id_for_dialog' not in st.session_state:
    st.session_state.editing_booking_id_for_dialog = None

if "add_form_check_in_final" not in st.session_state:
    st.session_state.add_form_check_in_final = datetime.date.today()
if "add_form_check_out_final" not in st.session_state:
    st.session_state.add_form_check_out_final = datetime.date.today() + timedelta(days=1)

if 'google_service_account_json_content' not in st.session_state:
    st.session_state.google_service_account_json_content = None
if 'google_sheet_id_input_val' not in st.session_state: 
    st.session_state.google_sheet_id_input_val = ""
if 'google_worksheet_name_input_val' not in st.session_state: # Thêm key cho Worksheet name
    st.session_state.google_worksheet_name_input_val = "Bookings"

def get_cleaned_room_types(df: pd.DataFrame) -> list:
    """
    Trả về danh sách các loại phòng duy nhất, đã loại bỏ giá trị rỗng và sắp xếp.
    """
    if df is None or 'Tên chỗ nghỉ' not in df.columns:
        return []
    room_types = df['Tên chỗ nghỉ'].dropna().astype(str).str.strip()
    room_types = room_types[room_types != '']
    return sorted(room_types.unique())

# --- GIAO DIỆN NGƯỜI DÙNG (UI) & LOGIC TẢI DỮ LIỆU ---
# ... (Giữ nguyên)
st.sidebar.title("🏨 Quản lý phòng")
if not PYPDF2_AVAILABLE: st.sidebar.warning("Xử lý PDF hạn chế. Cài đặt: `pip install pypdf2`")
if not BS4_AVAILABLE: st.sidebar.warning("Xử lý HTML hạn chế. Cài đặt: `pip install beautifulsoup4`")
if not GSPREAD_AVAILABLE: st.sidebar.error("Google Sheets bị vô hiệu hóa. Cài đặt: `pip install gspread google-auth google-auth-oauthlib`")


uploaded_file = st.sidebar.file_uploader("Tải lên file đặt phòng (Excel, PDF, HTML)", type=['xls', 'xlsx', 'pdf', 'html'], key="file_uploader_key", help="Hỗ trợ file Excel, PDF, HTML từ Booking.com.")
if uploaded_file is not None:
    if st.session_state.uploaded_file_name != uploaded_file.name or st.session_state.df is None:
        with st.spinner(f"Đang xử lý file: {uploaded_file.name}..."):
            df_from_file, active_bookings_from_file = load_data_from_file(uploaded_file)
        if df_from_file is not None and not df_from_file.empty:
            st.session_state.df = df_from_file
            st.session_state.active_bookings = active_bookings_from_file
            st.session_state.room_types = get_cleaned_room_types(df_from_file)
            st.session_state.data_source = 'file'
            st.session_state.uploaded_file_name = uploaded_file.name
            st.sidebar.success(f"Đã tải và xử lý thành công file: {uploaded_file.name}")
            st.session_state.selected_calendar_date = None
            st.rerun()
        else:
            st.sidebar.error(f"Không thể xử lý file {uploaded_file.name} hoặc file không chứa dữ liệu hợp lệ.")
            st.session_state.data_source = 'error_loading_file'
            st.session_state.uploaded_file_name = uploaded_file.name
elif st.session_state.df is None and st.session_state.data_source != 'error_loading_file':
    st.sidebar.info("Hiện đang sử dụng dữ liệu demo. Tải file của bạn lên để bắt đầu.")
    st.session_state.df, st.session_state.active_bookings = create_demo_data()
    if st.session_state.df is not None and not st.session_state.df.empty:
        st.session_state.room_types = get_cleaned_room_types(st.session_state.df)
    else:
        st.session_state.room_types = []
    st.session_state.data_source = 'demo'
    st.session_state.selected_calendar_date = None


df = st.session_state.get('df')
active_bookings = st.session_state.get('active_bookings')
room_types = st.session_state.get('room_types', []) 
default_min_date = datetime.date.today() - timedelta(days=365)
default_max_date = datetime.date.today() + timedelta(days=365)

if df is not None and not df.empty:
    # Kiểm tra xem cột có tồn tại và có dữ liệu không trước khi lấy min/max
    if 'Check-in Date' in df.columns:
        min_date_series = df['Check-in Date'].dropna()
        min_date_val = min_date_series.min().date() if not min_date_series.empty and pd.api.types.is_datetime64_any_dtype(min_date_series) else default_min_date
    else:
        min_date_val = default_min_date

    if 'Check-out Date' in df.columns:
        max_date_series = df['Check-out Date'].dropna()
        max_date_val = max_date_series.max().date() if not max_date_series.empty and pd.api.types.is_datetime64_any_dtype(max_date_series) else default_max_date
    else:
        max_date_val = default_max_date
else:
    min_date_val = default_min_date
    max_date_val = default_max_date

# --- CÁC TAB CHỨC NĂNG ---
tab_titles = ["📊 Dashboard", "📅 Lịch phòng", "📋 Quản lý đặt phòng", "📈 Phân tích", "➕ Thêm đặt phòng", "💌 Mẫu tin nhắn"]
tab_dashboard, tab_calendar, tab_booking_mgmt, tab_analytics, tab_add_booking, tab_message_templates = st.tabs(tab_titles)

# --- TAB DASHBOARD ---
with tab_dashboard:
    st.header("📊 Tổng quan Dashboard")
    if df is not None and not df.empty and active_bookings is not None and not active_bookings.empty: # Thêm kiểm tra active_bookings not empty
        st.markdown("#### Số liệu chính")
        col1, col2, col3, col4 = st.columns(4)
        today_dt = datetime.date.today()

        total_bookings_count = len(df)
        active_bookings_count = len(active_bookings) if active_bookings is not None else 0
        with col1:
            st.markdown(f"""<div class="metric-card" style="border-left-color: var(--primary-color);"><p style="font-size: 0.9rem; color: #666;">Tổng số đặt phòng</p><h3 style="color: var(--primary-color); margin-top: 0.5rem;">{total_bookings_count}</h3><p style="font-size: 0.8rem; color: var(--success-color);">{active_bookings_count} đang hoạt động</p></div>""", unsafe_allow_html=True)

        total_checked_in_revenue_dashboard = 0
        if 'Tổng thanh toán' in active_bookings.columns: # Đã kiểm tra active_bookings not empty
            active_bookings_copy = active_bookings.copy()
            active_bookings_copy['Check-in Date'] = pd.to_datetime(active_bookings_copy['Check-in Date'], errors='coerce')
            
            checked_in_df_dashboard = active_bookings_copy[
                (active_bookings_copy['Check-in Date'].dt.date <= today_dt) & (active_bookings_copy['Tình trạng'] != 'Đã hủy')
            ]
            total_checked_in_revenue_dashboard = checked_in_df_dashboard['Tổng thanh toán'].sum()


        with col2:
            st.markdown(f"""<div class="metric-card" style="border-left-color: var(--success-color);"><p style="font-size: 0.9rem; color: #666;">Tổng TT đã Check-in (VND)</p><h3 style="color: var(--success-color); margin-top: 0.5rem;">{total_checked_in_revenue_dashboard:,.0f}</h3><p style="font-size: 0.8rem; color: #666;">Tính đến hôm nay</p></div>""", unsafe_allow_html=True)

        total_expected_revenue_all_active_dashboard = active_bookings['Tổng thanh toán'].sum() if 'Tổng thanh toán' in active_bookings.columns else 0
        with col3:
            st.markdown(f"""<div class="metric-card" style="border-left-color: var(--secondary-color);"><p style="font-size: 0.9rem; color: #666;">Tổng TT dự kiến (Tất cả HĐ, VND)</p><h3 style="color: var(--secondary-color); margin-top: 0.5rem;">{total_expected_revenue_all_active_dashboard:,.0f}</h3><p style="font-size: 0.8rem; color: #666;">Từ các đặt phòng hoạt động</p></div>""", unsafe_allow_html=True)

        
        active_bookings_copy_dash = active_bookings.copy() # Đã kiểm tra active_bookings not empty
        active_bookings_copy_dash['Check-in Date'] = pd.to_datetime(active_bookings_copy_dash['Check-in Date'], errors='coerce')
        active_bookings_copy_dash['Check-out Date'] = pd.to_datetime(active_bookings_copy_dash['Check-out Date'], errors='coerce')

        active_on_today_dashboard = active_bookings_copy_dash[
            (active_bookings_copy_dash['Check-in Date'].dt.date <= today_dt) & 
            (active_bookings_copy_dash['Check-out Date'].dt.date > today_dt) & 
            (active_bookings_copy_dash['Tình trạng'] != 'Đã hủy')
        ]
        occupied_today_count_dashboard_actual = len(active_on_today_dashboard)

        occupancy_rate_today_dashboard = (occupied_today_count_dashboard_actual / TOTAL_HOTEL_CAPACITY) * 100 if TOTAL_HOTEL_CAPACITY > 0 else 0
        denominator_display_dashboard = TOTAL_HOTEL_CAPACITY
        with col4:
            st.markdown(f"""<div class="metric-card" style="border-left-color: var(--info-color);"><p style="font-size: 0.9rem; color: #666;">Tỷ lệ lấp đầy (Tổng)</p><h3 style="color: var(--info-color); margin-top: 0.5rem;">{occupancy_rate_today_dashboard:.1f}%</h3><p style="font-size: 0.8rem; color: #666;">{occupied_today_count_dashboard_actual}/{denominator_display_dashboard} phòng</p></div>""", unsafe_allow_html=True)

        st.markdown("---"); st.markdown("#### Biểu đồ tổng quan")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader("📈 Xu hướng lấp đầy (7 ngày qua)")
            weekly_data_list = []
            if TOTAL_HOTEL_CAPACITY > 0: # Đã kiểm tra active_bookings not empty
                active_bookings_copy_chart = active_bookings.copy()
                active_bookings_copy_chart['Check-in Date'] = pd.to_datetime(active_bookings_copy_chart['Check-in Date'], errors='coerce')
                active_bookings_copy_chart['Check-out Date'] = pd.to_datetime(active_bookings_copy_chart['Check-out Date'], errors='coerce')

                for i in range(7):
                    date_iter_chart = today_dt - datetime.timedelta(days=6-i)
                    active_on_date_iter_chart = active_bookings_copy_chart[
                        (active_bookings_copy_chart['Check-in Date'].dt.date <= date_iter_chart) & 
                        (active_bookings_copy_chart['Check-out Date'].dt.date > date_iter_chart) & 
                        (active_bookings_copy_chart['Tình trạng'] != 'Đã hủy')
                    ]
                    occupied_chart_actual = len(active_on_date_iter_chart)
                    occupancy_chart = (occupied_chart_actual / TOTAL_HOTEL_CAPACITY) * 100 if TOTAL_HOTEL_CAPACITY > 0 else 0
                    weekly_data_list.append({'Ngày': date_iter_chart.strftime('%a, %d/%m'), 'Tỷ lệ lấp đầy %': occupancy_chart})
            if weekly_data_list:
                weekly_df_chart = pd.DataFrame(weekly_data_list)
                fig_weekly = px.line(weekly_df_chart, x='Ngày', y='Tỷ lệ lấp đầy %', markers=True, line_shape='spline', hover_data={'Tỷ lệ lấp đầy %': ':.1f'})
                fig_weekly.update_layout(height=300, showlegend=False, yaxis_title="Tỷ lệ lấp đầy (%)", xaxis_title="Ngày", yaxis_range=[0, 105])
                st.plotly_chart(fig_weekly, use_container_width=True)
            else: st.info("Không đủ dữ liệu cho biểu đồ xu hướng lấp đầy 7 ngày qua.")
        with col_chart2:
            st.subheader("🏠 Hiệu suất loại phòng (theo Tổng thanh toán)")
            if 'Tổng thanh toán' in active_bookings.columns and 'Tên chỗ nghỉ' in active_bookings.columns: # Đã kiểm tra active_bookings not empty
                room_revenue_df = active_bookings.groupby('Tên chỗ nghỉ')['Tổng thanh toán'].sum().reset_index()
                room_revenue_df = room_revenue_df[room_revenue_df['Tổng thanh toán'] > 0]
                room_revenue_df.columns = ['Loại phòng', 'Tổng thanh toán']
                room_revenue_df['Loại phòng Display'] = room_revenue_df['Loại phòng'].apply(lambda x: x[:25] + "..." if len(x) > 25 else x)
                if not room_revenue_df.empty:
                    fig_pie_revenue = px.pie(room_revenue_df, values='Tổng thanh toán', names='Loại phòng Display', hole=0.4, title="Phân bổ Tổng thanh toán theo Loại phòng")
                    fig_pie_revenue.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie_revenue.update_layout(height=350, showlegend=True, legend_title_text='Loại phòng', margin=dict(t=50, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie_revenue, use_container_width=True)
                else: st.info("Không có dữ liệu doanh thu theo loại phòng để hiển thị.")
            else: st.info("Không đủ dữ liệu ('Tổng thanh toán', 'Tên chỗ nghỉ') cho biểu đồ.")
    else:
        st.info(" Dữ liệu không đủ hoặc chưa được tải. Vui lòng tải file đặt phòng hợp lệ.")
        if st.button("🔄 Tải lại dữ liệu demo", key="reload_demo_dashboard"):
            st.session_state.df, st.session_state.active_bookings = create_demo_data()
            st.session_state.room_types = get_cleaned_room_types(st.session_state.df)
            st.session_state.data_source = 'demo'; st.session_state.uploaded_file_name = None; st.session_state.selected_calendar_date = None
            if "add_form_check_in_final" in st.session_state: del st.session_state.add_form_check_in_final
            if "add_form_check_out_final" in st.session_state: del st.session_state.add_form_check_out_final
            st.rerun()


# --- TAB LỊCH PHÒNG ---
with tab_calendar:
    st.header("📅 Lịch phòng tổng quan")
    st.subheader("Tổng quan phòng trống")
    if active_bookings is not None and not active_bookings.empty: # Thêm kiểm tra not empty
        today_date = datetime.date.today(); tomorrow_date = today_date + timedelta(days=1)
        today_overall_info = get_overall_calendar_day_info(today_date, active_bookings, TOTAL_HOTEL_CAPACITY)
        total_available_today = today_overall_info['available_units']
        tomorrow_overall_info = get_overall_calendar_day_info(tomorrow_date, active_bookings, TOTAL_HOTEL_CAPACITY)
        total_available_tomorrow = tomorrow_overall_info['available_units']
        col_today_avail, col_tomorrow_avail = st.columns(2)
        with col_today_avail:
            st.markdown(f"##### Hôm nay ({today_date.strftime('%d/%m')})")
            if total_available_today > 0: st.info(f"**{total_available_today}** phòng trống / {TOTAL_HOTEL_CAPACITY} tổng số")
            else: st.warning(f"Hết phòng hôm nay ({TOTAL_HOTEL_CAPACITY - total_available_today}/{TOTAL_HOTEL_CAPACITY} đã bị chiếm).")
        with col_tomorrow_avail:
            st.markdown(f"##### Ngày mai ({tomorrow_date.strftime('%d/%m')})")
            if total_available_tomorrow > 0: st.info(f"**{total_available_tomorrow}** phòng trống / {TOTAL_HOTEL_CAPACITY} tổng số")
            else: st.warning(f"Hết phòng ngày mai ({TOTAL_HOTEL_CAPACITY- total_available_tomorrow}/{TOTAL_HOTEL_CAPACITY} đã bị chiếm).") 
    else: st.info("Không có dữ liệu đặt phòng để tính phòng trống.")
    st.markdown("---")
    col_nav1, col_nav_title, col_nav2 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("◀️ Tháng trước", key="prev_month_calendar", use_container_width=True):
            current_date_cal = st.session_state.current_date_calendar; first_day_current_month = current_date_cal.replace(day=1); last_day_prev_month = first_day_current_month - timedelta(days=1)
            st.session_state.current_date_calendar = last_day_prev_month.replace(day=1); st.session_state.selected_calendar_date = None; st.rerun()
    with col_nav_title: st.subheader(f"Tháng {st.session_state.current_date_calendar.month} năm {st.session_state.current_date_calendar.year}")
    with col_nav2:
        if st.button("Tháng sau ▶️", key="next_month_calendar", use_container_width=True):
            current_date_cal = st.session_state.current_date_calendar; 
            current_month_days = calendar.monthrange(current_date_cal.year, current_date_cal.month)[1]
            first_day_of_current_month = current_date_cal.replace(day=1)
            first_day_next_month = first_day_of_current_month + timedelta(days=current_month_days) 
            st.session_state.current_date_calendar = first_day_next_month.replace(day=1); st.session_state.selected_calendar_date = None; st.rerun()
    if st.button("📅 Về tháng hiện tại", key="today_month_calendar"):
        st.session_state.current_date_calendar = datetime.date.today(); st.session_state.selected_calendar_date = None; st.rerun()

    day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    cols_header = st.columns(7)
    for i, day_name_header in enumerate(day_names): cols_header[i].markdown(f"<div class='day-header'>{day_name_header}</div>", unsafe_allow_html=True)

    if df is not None and not df.empty:
        current_year = st.session_state.current_date_calendar.year; current_month = st.session_state.current_date_calendar.month
        cal_obj = calendar.Calendar(); month_days_matrix = cal_obj.monthdayscalendar(current_year, current_month)
        for week_data in month_days_matrix:
            cols_week = st.columns(7)
            for i, day_num_cal in enumerate(week_data):
                with cols_week[i]:
                    if day_num_cal == 0: st.markdown(f"<div class='day-cell day-disabled'></div>", unsafe_allow_html=True)
                    else:
                        current_day_date_cal = datetime.date(current_year, current_month, day_num_cal)
                        day_info_cal = get_overall_calendar_day_info(current_day_date_cal, active_bookings, TOTAL_HOTEL_CAPACITY)
                        status_indicator_html = ""
                        if day_info_cal['status_indicator_type'] == "green_dot": status_indicator_html = "<div class='dot-indicator dot-green'>•</div>"
                        elif day_info_cal['status_indicator_type'] == "orange_dash": status_indicator_html = "<div class='dot-indicator dot-orange'>—</div>"
                        elif day_info_cal['status_indicator_type'] == "red_x": status_indicator_html = "<div class='dot-indicator dot-red'>✕</div>"
                        day_class = "day-cell"
                        if current_day_date_cal == datetime.date.today(): day_class += " day-today"
                        if st.session_state.selected_calendar_date == current_day_date_cal: day_class += " day-selected"
                        
                        button_html_id = f"day-cell-btn-{current_day_date_cal.strftime('%Y%m%d')}"
                        st.markdown(f"""
                        <div class='{day_class}' id='{button_html_id}'>
                            <div class='day-number'>{day_num_cal}</div>
                            {status_indicator_html}
                            <div class='day-status'>{day_info_cal['status_text']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("", key=f"day_button_overlay_{current_day_date_cal.strftime('%Y%m%d')}", help=f"Xem chi tiết ngày {current_day_date_cal.strftime('%d/%m/%Y')}", use_container_width=True):
                             st.session_state.selected_calendar_date = None if st.session_state.selected_calendar_date == current_day_date_cal else current_day_date_cal
                             st.rerun()
    else: st.info("Không có dữ liệu đặt phòng để hiển thị lịch.")

    if st.session_state.selected_calendar_date is not None:
        selected_date_cal = st.session_state.selected_calendar_date
        st.markdown("---")
        # Loại bỏ css_class khỏi st.expander
        with st.expander(f"🗓️ Chi tiết hoạt động ngày: {selected_date_cal.strftime('%A, %d/%m/%Y')}", expanded=True):
            daily_activity_cal = get_daily_activity(selected_date_cal, active_bookings)
            col_checkin_cal, col_checkout_cal, col_occupied_cal = st.columns(3)
            with col_checkin_cal:
                st.markdown("##### 🛬 Khách Check-in")
                if daily_activity_cal['check_in']:
                    st.success(f"**{len(daily_activity_cal['check_in'])}** lượt check-in:")
                    for guest in daily_activity_cal['check_in']: st.markdown(f"- **{guest.get('name','N/A')}** ({guest.get('room_type','N/A')})"); st.caption(f"  Mã ĐP: {guest.get('booking_id','N/A')}")
                else: st.info("Không có khách check-in.")
            with col_checkout_cal:
                st.markdown("##### 🛫 Khách Check-out")
                if daily_activity_cal['check_out']:
                    st.warning(f"**{len(daily_activity_cal['check_out'])}** lượt check-out:")
                    for guest in daily_activity_cal['check_out']: st.markdown(f"- **{guest.get('name','N/A')}** ({guest.get('room_type','N/A')})"); st.caption(f"  Mã ĐP: {guest.get('booking_id','N/A')}")
                else: st.info("Không có khách check-out.")
            with col_occupied_cal:
                st.markdown("##### 🏨 Khách đang ở")
                if daily_activity_cal['occupied']:
                    st.info(f"**{len(daily_activity_cal['occupied'])}** lượt khách ở:")
                    for guest in daily_activity_cal['occupied']:
                        check_in_str = guest['check_in'].strftime('%d/%m') if guest['check_in'] else 'N/A'
                        check_out_str = guest['check_out'].strftime('%d/%m') if guest['check_out'] else 'N/A'
                        total_payment_val = guest.get('total_payment', 0.0)
                        total_payment_str = f"{total_payment_val:,.0f}" if pd.notna(total_payment_val) and total_payment_val != 0.0 else "0"
                        st.markdown(f"- **{guest.get('name','N/A')}** ({guest.get('room_type','N/A')})")
                        st.caption(f"  Từ {check_in_str} đến {check_out_str} (Mã ĐP: {guest.get('booking_id','N/A')}) - Tổng tiền: {total_payment_str}")
                        st.markdown("<div class='guest-separator'></div>", unsafe_allow_html=True)
                else: st.info("Không có khách đang ở.")
            if st.button("Ẩn chi tiết ngày", key="hide_day_details_calendar", type="primary"):
                st.session_state.selected_calendar_date = None; st.rerun()

# --- TAB QUẢN LÝ ĐẶT PHÒNG ---
with tab_booking_mgmt:
    st.header("📋 Quản lý tất cả đặt phòng")
    if df is not None and not df.empty:
        st.subheader("Danh sách đặt phòng")
        base_display_columns_map_mgmt = {
            'Số đặt phòng': 'Mã ĐP', 'Tên người đặt': 'Khách',
            'Tên chỗ nghỉ': 'Loại phòng', 'Check-in Date': 'Check-in',
            'Check-out Date': 'Check-out', 'Stay Duration': 'Số đêm',
            'Tình trạng': 'Trạng thái', 'Tổng thanh toán': 'Tổng tiền (VND)',
            'Giá mỗi đêm': 'Giá/đêm (VND)',
            'Booking Date': 'Ngày đặt'
        }
        display_columns_original_names_mgmt = [
            'Số đặt phòng', 'Tên người đặt', 'Tên chỗ nghỉ',
            'Check-in Date', 'Check-out Date', 'Stay Duration',
            'Tình trạng', 'Tổng thanh toán', 'Giá mỗi đêm', 'Booking Date'
        ]
        display_columns_original_names_mgmt = [
            col for col in display_columns_original_names_mgmt
            if col in df.columns and col in base_display_columns_map_mgmt
        ]

        st.markdown("##### Bộ lọc đặt phòng")
        filter_cols_main = st.columns([2,2,3])
        with filter_cols_main[0]:
            unique_statuses_mgmt_list = []
            if 'Tình trạng' in df.columns:
                try:
                    unique_statuses_mgmt_list = sorted(df['Tình trạng'].dropna().astype(str).unique().tolist())
                except Exception: 
                    unique_statuses_mgmt_list = df['Tình trạng'].dropna().astype(str).unique().tolist()
            status_filter_manage = st.multiselect("Trạng thái:", options=unique_statuses_mgmt_list, default=unique_statuses_mgmt_list, key="status_filter_manage_tab3")
        with filter_cols_main[1]:
            unique_room_types_manage = st.session_state.get('room_types', []) 
            room_filter_manage = st.multiselect("Loại phòng:", options=unique_room_types_manage, default=unique_room_types_manage, key="room_filter_manage_tab3")
        with filter_cols_main[2]:
            temp_max_date_filter = max_date_val if min_date_val <= max_date_val else min_date_val + timedelta(days=1) 
            date_range_manage = st.date_input(
                "Khoảng ngày check-in:", 
                value=(min_date_val, temp_max_date_filter), 
                min_value=min_date_val, 
                max_value=max_date_val if max_date_val >= min_date_val else temp_max_date_filter, 
                key="date_range_filter_manage_tab3"
            )

        df_after_main_filters = df.copy()
        if status_filter_manage and 'Tình trạng' in df_after_main_filters.columns: df_after_main_filters = df_after_main_filters[df_after_main_filters['Tình trạng'].isin(status_filter_manage)]
        if room_filter_manage and 'Tên chỗ nghỉ' in df_after_main_filters.columns: df_after_main_filters = df_after_main_filters[df_after_main_filters['Tên chỗ nghỉ'].isin(room_filter_manage)]
        if date_range_manage and len(date_range_manage) == 2 and 'Check-in Date' in df_after_main_filters.columns:
            start_date_filter_mgmt, end_date_filter_mgmt = date_range_manage
            df_after_main_filters['Check-in Date'] = pd.to_datetime(df_after_main_filters['Check-in Date'], errors='coerce') 
            df_after_main_filters = df_after_main_filters[
                (df_after_main_filters['Check-in Date'].dt.date >= start_date_filter_mgmt) & 
                (df_after_main_filters['Check-in Date'].dt.date <= end_date_filter_mgmt)
            ]

        st.markdown("##### Lọc bổ sung")
        additional_filter_options_map = {
            "Không có": None, "Thành viên Genius": "Thành viên Genius", "Số đêm": "Stay Duration",
            "Giá mỗi đêm": "Giá mỗi đêm", "Tiền tệ": "Tiền tệ"
        }
        selected_additional_filter_display = st.selectbox(
            "Chọn cột để lọc bổ sung:", options=list(additional_filter_options_map.keys()), key="additional_filter_column_select"
        )
        additional_filter_column_actual = additional_filter_options_map[selected_additional_filter_display]

        df_filtered_for_table = df_after_main_filters.copy()

        if additional_filter_column_actual and additional_filter_column_actual in df_filtered_for_table.columns:
            if additional_filter_column_actual == "Thành viên Genius":
                unique_genius_values_list = []
                if "Thành viên Genius" in df_filtered_for_table.columns:
                    try:
                        unique_genius_values_list = sorted(df_filtered_for_table["Thành viên Genius"].dropna().astype(str).unique())
                    except Exception:
                        unique_genius_values_list = df_filtered_for_table["Thành viên Genius"].dropna().astype(str).unique().tolist()
                selected_genius_values = st.multiselect(
                    "Lọc theo Thành viên Genius:", options=unique_genius_values_list, default=unique_genius_values_list, key="additional_genius_filter_multiselect"
                )
                if selected_genius_values: df_filtered_for_table = df_filtered_for_table[df_filtered_for_table["Thành viên Genius"].isin(selected_genius_values)]
            elif additional_filter_column_actual == "Tiền tệ":
                unique_currency_values_list = []
                if "Tiền tệ" in df_filtered_for_table.columns:
                    try:
                        unique_currency_values_list = sorted(df_filtered_for_table["Tiền tệ"].dropna().astype(str).unique())
                    except Exception:
                         unique_currency_values_list = df_filtered_for_table["Tiền tệ"].dropna().astype(str).unique().tolist()
                selected_currency_values = st.multiselect(
                    "Lọc theo Tiền tệ:", options=unique_currency_values_list, default=unique_currency_values_list, key="additional_currency_filter_multiselect"
                )
                if selected_currency_values: df_filtered_for_table = df_filtered_for_table[df_filtered_for_table["Tiền tệ"].isin(selected_currency_values)]
            elif additional_filter_column_actual == "Stay Duration":
                min_sd = int(df_filtered_for_table["Stay Duration"].min()) if not df_filtered_for_table["Stay Duration"].empty else 0
                max_sd = int(df_filtered_for_table["Stay Duration"].max()) if not df_filtered_for_table["Stay Duration"].empty else 1
                if min_sd >= max_sd : max_sd = min_sd + 1 
                
                selected_stay_duration = st.slider(
                    "Lọc theo Số đêm:", min_value=min_sd, max_value=max_sd, value=(min_sd, max_sd), key="additional_stay_duration_slider"
                )
                df_filtered_for_table = df_filtered_for_table[
                    (df_filtered_for_table["Stay Duration"] >= selected_stay_duration[0]) &
                    (df_filtered_for_table["Stay Duration"] <= selected_stay_duration[1])
                ]
            elif additional_filter_column_actual == "Giá mỗi đêm":
                min_price_night = float(df_filtered_for_table["Giá mỗi đêm"].min()) if not df_filtered_for_table["Giá mỗi đêm"].empty else 0.0
                max_price_night = float(df_filtered_for_table["Giá mỗi đêm"].max()) if not df_filtered_for_table["Giá mỗi đêm"].empty else 1000000.0
                if min_price_night >= max_price_night : max_price_night = min_price_night + 10000 
                
                price_range_cols = st.columns(2)
                with price_range_cols[0]: min_price_input = st.number_input("Giá mỗi đêm tối thiểu:", min_value=0.0, value=min_price_night, step=10000.0, key="additional_min_price_input")
                with price_range_cols[1]: max_price_input = st.number_input("Giá mỗi đêm tối đa:", min_value=min_price_input, value=max_price_night, step=10000.0, key="additional_max_price_input")
                if max_price_input >= min_price_input:
                    df_filtered_for_table = df_filtered_for_table[
                        (df_filtered_for_table["Giá mỗi đêm"] >= min_price_input) &
                        (df_filtered_for_table["Giá mỗi đêm"] <= max_price_input)
                    ]
        st.markdown("---")
        search_term_mgmt = st.text_input("Tìm theo tên khách hoặc mã đặt phòng:", key="search_booking_tab3", placeholder="Nhập từ khóa...")
        if search_term_mgmt:
            df_filtered_for_table = df_filtered_for_table[(df_filtered_for_table['Tên người đặt'].astype(str).str.contains(search_term_mgmt, case=False, na=False)) | (df_filtered_for_table['Số đặt phòng'].astype(str).str.contains(search_term_mgmt, case=False, na=False))]

        current_sort_col = st.session_state.get('booking_sort_column', 'Booking Date')
        current_sort_asc = st.session_state.get('booking_sort_ascending', False)

        if current_sort_col in df_filtered_for_table.columns and not df_filtered_for_table.empty:
            try:
                if current_sort_col in ['Tổng thanh toán', 'Stay Duration', 'Giá mỗi đêm']:
                     df_filtered_for_table[current_sort_col] = pd.to_numeric(df_filtered_for_table[current_sort_col], errors='coerce')
                df_filtered_for_table = df_filtered_for_table.sort_values(by=current_sort_col, ascending=current_sort_asc, na_position='last')
            except Exception as e_sort: st.warning(f"Lỗi khi sắp xếp cột '{base_display_columns_map_mgmt.get(current_sort_col, current_sort_col)}': {e_sort}")

        if df_filtered_for_table.empty:
            st.info("Không có đặt phòng nào phù hợp với bộ lọc hoặc từ khóa tìm kiếm.")
        else:
            st.write(f"Tìm thấy {len(df_filtered_for_table)} đặt phòng:")

            checkbox_col_header = "Chọn"
            action_col_header = "Hành động"

            default_data_col_ratios = [1.2, 2.0, 2.0, 1.2, 1.2, 0.8, 1.2, 1.5, 1.5, 1.2]
            action_col_ratio = [1.0]
            checkbox_col_ratio = [0.4]

            current_data_col_ratios_to_use = default_data_col_ratios[:len(display_columns_original_names_mgmt)]
            final_column_ratios = checkbox_col_ratio + current_data_col_ratios_to_use + action_col_ratio

            header_cols_ui = st.columns(final_column_ratios)

            with header_cols_ui[0]:
                st.markdown(f"**{checkbox_col_header}**")

            for i, original_col_name_header in enumerate(display_columns_original_names_mgmt):
                with header_cols_ui[i + 1]:
                    display_name = base_display_columns_map_mgmt.get(original_col_name_header, original_col_name_header)
                    sort_indicator = ""
                    if st.session_state.booking_sort_column == original_col_name_header:
                        sort_indicator = " ▲" if st.session_state.booking_sort_ascending else " ▼"
                    button_label = f"{display_name}{sort_indicator}"
                    if st.button(button_label, key=f"sort_btn_header_{original_col_name_header}", use_container_width=True):
                        if st.session_state.booking_sort_column == original_col_name_header:
                            st.session_state.booking_sort_ascending = not st.session_state.booking_sort_ascending
                        else:
                            st.session_state.booking_sort_column = original_col_name_header
                            st.session_state.booking_sort_ascending = True if original_col_name_header not in ['Booking Date', 'Check-in Date', 'Check-out Date'] else False
                        st.rerun()

            with header_cols_ui[len(display_columns_original_names_mgmt) + 1]:
                 st.markdown(f"**{action_col_header}**")
            st.markdown("<hr style='margin:0; padding:0;'>", unsafe_allow_html=True)

            current_view_checkbox_info = {}

            for original_df_index, original_row_mgmt in df_filtered_for_table.iterrows():
                cols_display_row_mgmt = st.columns(final_column_ratios)
                booking_id_for_key = original_row_mgmt.get('Số đặt phòng', f"index_{original_df_index}")
                checkbox_key = f"select_booking_cb_{booking_id_for_key}_{original_df_index}"

                current_view_checkbox_info[original_df_index] = (checkbox_key, booking_id_for_key, original_df_index)

                with cols_display_row_mgmt[0]:
                    st.checkbox("", key=checkbox_key, value=st.session_state.get(checkbox_key, False))

                col_idx_offset = 1
                for i, original_col_name_mgmt_row in enumerate(display_columns_original_names_mgmt):
                    val_to_write = original_row_mgmt[original_col_name_mgmt_row]
                    if original_col_name_mgmt_row in ['Check-in Date', 'Check-out Date', 'Booking Date']:
                        if pd.notna(val_to_write) and isinstance(val_to_write, (pd.Timestamp, datetime.datetime, datetime.date)): 
                            val_to_write = pd.to_datetime(val_to_write).strftime('%d/%m/%Y') 
                        elif pd.notna(val_to_write): val_to_write = str(val_to_write)
                        else: val_to_write = "N/A"
                    elif original_col_name_mgmt_row == 'Tổng thanh toán' or original_col_name_mgmt_row == 'Giá mỗi đêm':
                        if pd.notna(val_to_write):
                            try: val_to_write = f"{float(val_to_write):,.0f}"
                            except ValueError: val_to_write = "Lỗi định dạng"
                        else: val_to_write = "N/A"
                    elif original_col_name_mgmt_row == 'Stay Duration':
                         if pd.notna(val_to_write):
                            try: val_to_write = str(int(float(val_to_write)))
                            except ValueError: val_to_write = "Lỗi định dạng"
                         else: val_to_write = "N/A"
                    else:
                        if pd.isna(val_to_write): val_to_write = "N/A"
                        else: val_to_write = str(val_to_write)
                    with cols_display_row_mgmt[i + col_idx_offset]: st.write(val_to_write)

                action_col_idx = len(display_columns_original_names_mgmt) + col_idx_offset
                with cols_display_row_mgmt[action_col_idx]:
                    original_booking_id_action = original_row_mgmt.get('Số đặt phòng', f"index_{original_df_index}")
                    action_buttons_cols = st.columns([1,1])
                    with action_buttons_cols[0]:
                        edit_button_key = f"edit_btn_{original_booking_id_action}_{original_df_index}"
                        if st.button("✏️", key=edit_button_key, help=f"Sửa đặt phòng {original_booking_id_action}", use_container_width=True):
                            st.session_state.editing_booking_id_for_dialog = original_booking_id_action
                            st.rerun()

                    with action_buttons_cols[1]:
                        delete_single_button_key = f"delete_single_btn_{original_booking_id_action}_{original_df_index}"
                        if st.button("🗑️", key=delete_single_button_key, help=f"Xóa ĐP {original_booking_id_action}", use_container_width=True):
                            if st.session_state.df is not None and 'Số đặt phòng' in st.session_state.df.columns:
                                df_copy_single_delete = st.session_state.df.copy()
                                if str(original_booking_id_action).startswith("index_"): 
                                    df_copy_single_delete = df_copy_single_delete.drop(index=original_df_index)
                                else: 
                                    df_copy_single_delete = df_copy_single_delete[df_copy_single_delete['Số đặt phòng'] != original_booking_id_action]

                                st.session_state.df = df_copy_single_delete.reset_index(drop=True)
                                if 'Tình trạng' in st.session_state.df.columns:
                                    st.session_state.active_bookings = st.session_state.df[st.session_state.df['Tình trạng'] != 'Đã hủy'].copy()
                                else:
                                     st.session_state.active_bookings = st.session_state.df.copy() 
                                st.session_state.room_types = get_cleaned_room_types(st.session_state.df)
                                st.session_state.last_action_message = f"Đã xóa thành công đặt phòng {original_booking_id_action}."
                                st.session_state.selected_calendar_date = None
                            else:
                                st.session_state.last_action_message = "Lỗi: Không tìm thấy DataFrame hoặc cột 'Số đặt phòng' để xóa."
                            st.rerun()
                st.markdown("<hr style='margin-top: 5px; margin-bottom: 5px;'>", unsafe_allow_html=True)

            st.markdown("---")
            if st.button("🗑️ Xóa các đặt phòng đã chọn", type="primary", key="bulk_delete_bookings_button"):
                ids_to_delete_bulk = []
                indices_to_delete_bulk = []

                for df_idx, (chk_key, booking_id_val, original_df_idx_val) in current_view_checkbox_info.items():
                    if st.session_state.get(chk_key, False):
                        if str(booking_id_val).startswith("index_"):
                            indices_to_delete_bulk.append(original_df_idx_val)
                        else:
                            ids_to_delete_bulk.append(booking_id_val)
                        st.session_state[chk_key] = False 


                indices_to_delete_bulk = sorted(list(set(indices_to_delete_bulk)), reverse=True)
                ids_to_delete_bulk = list(set(ids_to_delete_bulk))

                if ids_to_delete_bulk or indices_to_delete_bulk:
                    df_main_for_bulk_delete = st.session_state.df.copy()
                    initial_count_bulk = len(df_main_for_bulk_delete)

                    if ids_to_delete_bulk:
                        df_main_for_bulk_delete = df_main_for_bulk_delete[~df_main_for_bulk_delete['Số đặt phòng'].isin(ids_to_delete_bulk)]

                    if indices_to_delete_bulk:
                        valid_indices_to_drop_bulk = [idx for idx in indices_to_delete_bulk if idx in df_main_for_bulk_delete.index]
                        if valid_indices_to_drop_bulk:
                             df_main_for_bulk_delete = df_main_for_bulk_delete.drop(index=valid_indices_to_drop_bulk)

                    st.session_state.df = df_main_for_bulk_delete.reset_index(drop=True)
                    if 'Tình trạng' in st.session_state.df.columns:
                        st.session_state.active_bookings = st.session_state.df[st.session_state.df['Tình trạng'] != 'Đã hủy'].copy()
                    else:
                        st.session_state.active_bookings = st.session_state.df.copy()
                    st.session_state.room_types = get_cleaned_room_types(st.session_state.df)

                    num_deleted_bulk = initial_count_bulk - len(st.session_state.df)
                    st.session_state.last_action_message = f"Đã xóa thành công {num_deleted_bulk} đặt phòng đã chọn."
                    st.session_state.selected_calendar_date = None
                    st.rerun()
                else:
                    st.warning("Không có đặt phòng nào được chọn để xóa.")

            if st.session_state.last_action_message:
                if "Lỗi" in st.session_state.last_action_message: st.error(st.session_state.last_action_message)
                else: st.success(st.session_state.last_action_message)
                st.session_state.last_action_message = None
    else:
        st.info("Vui lòng tải file dữ liệu để quản lý đặt phòng.")

    if 'editing_booking_id_for_dialog' in st.session_state and st.session_state.editing_booking_id_for_dialog:
        booking_id_to_edit = st.session_state.editing_booking_id_for_dialog

        current_main_df = st.session_state.get('df', pd.DataFrame())
        if not current_main_df.empty and 'Số đặt phòng' in current_main_df.columns:
            booking_to_edit_series_list = current_main_df[current_main_df['Số đặt phòng'] == booking_id_to_edit]
            if not booking_to_edit_series_list.empty:
                booking_to_edit_series = booking_to_edit_series_list.iloc[0]

                @st.dialog("Chỉnh sửa Ngày Check-in/Check-out")
                def edit_booking_dates_dialog_content(booking_data_series, booking_id):
                    st.write(f"Chỉnh sửa đặt phòng: **{booking_id}**")
                    st.write(f"Khách: {booking_data_series.get('Tên người đặt', 'N/A')}") 
                    st.write(f"Loại phòng: {booking_data_series.get('Tên chỗ nghỉ', 'N/A')}") 
                    st.caption("Lưu ý: Thay đổi ngày check-in có thể tự động điều chỉnh ngày check-out nếu ngày check-out hiện tại không còn hợp lệ. Vui lòng kiểm tra kỹ cả hai ngày trước khi lưu.")

                    current_check_in_dt_obj = pd.to_datetime(booking_data_series['Check-in Date'], errors='coerce').date() if pd.notna(booking_data_series['Check-in Date']) else datetime.date.today()
                    current_check_out_dt_obj = pd.to_datetime(booking_data_series['Check-out Date'], errors='coerce').date() if pd.notna(booking_data_series['Check-out Date']) else datetime.date.today() + timedelta(days=1)

                    dialog_cin_key = f"dialog_cin_{booking_id}"
                    dialog_cout_key = f"dialog_cout_{booking_id}"

                    if dialog_cin_key not in st.session_state:
                        st.session_state[dialog_cin_key] = current_check_in_dt_obj
                    if dialog_cout_key not in st.session_state:
                        st.session_state[dialog_cout_key] = current_check_out_dt_obj

                    new_check_in = st.date_input(
                        "Ngày check-in mới:",
                        value=st.session_state[dialog_cin_key],
                        min_value=datetime.date.today() - timedelta(days=365*2),
                        max_value=datetime.date.today() + timedelta(days=365*2),
                        key=dialog_cin_key 
                    )
                    
                    min_checkout_dialog = st.session_state[dialog_cin_key] + timedelta(days=1)
                    
                    current_dialog_checkout_val = st.session_state[dialog_cout_key]
                    if current_dialog_checkout_val < min_checkout_dialog:
                        st.session_state[dialog_cout_key] = min_checkout_dialog
                        
                    new_check_out = st.date_input(
                        "Ngày check-out mới:",
                        value=st.session_state[dialog_cout_key],
                        min_value=min_checkout_dialog,
                        max_value=st.session_state[dialog_cin_key] + timedelta(days=365*3), 
                        key=dialog_cout_key 
                    )

                    if st.button("Lưu thay đổi", key=f"save_edit_dialog_{booking_id}"):
                        final_new_check_in = st.session_state[dialog_cin_key]
                        final_new_check_out = st.session_state[dialog_cout_key]

                        error_messages_dialog = []
                        if final_new_check_out <= final_new_check_in:
                            error_messages_dialog.append("Ngày check-out mới phải sau ngày check-in mới.")

                        if not error_messages_dialog:
                            active_bks_for_check = st.session_state.get('active_bookings', pd.DataFrame())
                            if active_bks_for_check is not None and not active_bks_for_check.empty:
                                active_bks_for_check['Check-in Date'] = pd.to_datetime(active_bks_for_check['Check-in Date'], errors='coerce')
                                active_bks_for_check['Check-out Date'] = pd.to_datetime(active_bks_for_check['Check-out Date'], errors='coerce')

                            other_active_bookings = active_bks_for_check[active_bks_for_check['Số đặt phòng'] != booking_id].copy() if active_bks_for_check is not None else pd.DataFrame()
                            room_type_of_booking_edit = booking_data_series['Tên chỗ nghỉ']
                            
                            original_check_in_date_from_series = pd.to_datetime(booking_data_series['Check-in Date']).date()
                            original_check_out_date_from_series = pd.to_datetime(booking_data_series['Check-out Date']).date()

                            current_iter_date_dialog = final_new_check_in
                            while current_iter_date_dialog < final_new_check_out:
                                is_original_stay_day = (original_check_in_date_from_series <= current_iter_date_dialog < original_check_out_date_from_series)

                                if not is_original_stay_day and not other_active_bookings.empty: 
                                    availability_specific_dialog = get_room_availability(current_iter_date_dialog, other_active_bookings, [room_type_of_booking_edit], ROOM_UNIT_PER_ROOM_TYPE)
                                    if availability_specific_dialog.get(room_type_of_booking_edit, 0) <= 0:
                                        error_msg = f"Loại phòng '{room_type_of_booking_edit}' đã hết vào ngày {current_iter_date_dialog.strftime('%d/%m/%Y')} (cho phần ngày gia hạn)."
                                        error_messages_dialog.append(error_msg)
                                        break  
                                    
                                    occupied_by_others_on_date_dialog = other_active_bookings[
                                        (other_active_bookings['Check-in Date'].dt.date <= current_iter_date_dialog) &
                                        (other_active_bookings['Check-out Date'].dt.date > current_iter_date_dialog)
                                    ]
                                    if len(occupied_by_others_on_date_dialog) + 1 > TOTAL_HOTEL_CAPACITY:
                                        error_msg = f"Khách sạn hết phòng vào ngày {current_iter_date_dialog.strftime('%d/%m/%Y')} (cho phần ngày gia hạn, tổng công suất: {TOTAL_HOTEL_CAPACITY})."
                                        error_messages_dialog.append(error_msg)
                                        break  
                                current_iter_date_dialog += timedelta(days=1)
                            
                        if not error_messages_dialog: 
                            df_to_update = st.session_state.df.copy() 
                            booking_idx_list = df_to_update[df_to_update['Số đặt phòng'] == booking_id].index
                            if not booking_idx_list.empty:
                                idx_to_update = booking_idx_list[0]
                                df_to_update.loc[idx_to_update, 'Check-in Date'] = pd.Timestamp(final_new_check_in) 
                                df_to_update.loc[idx_to_update, 'Check-out Date'] = pd.Timestamp(final_new_check_out) 
                                df_to_update.loc[idx_to_update, 'Ngày đến'] = f"ngày {final_new_check_in.day} tháng {final_new_check_in.month} năm {final_new_check_in.year}"
                                df_to_update.loc[idx_to_update, 'Ngày đi'] = f"ngày {final_new_check_out.day} tháng {final_new_check_out.month} năm {final_new_check_out.year}"
                                new_stay_duration_dialog = (final_new_check_out - final_new_check_in).days
                                df_to_update.loc[idx_to_update, 'Stay Duration'] = new_stay_duration_dialog
                                total_payment_for_booking_dialog = df_to_update.loc[idx_to_update, 'Tổng thanh toán']
                                df_to_update.loc[idx_to_update, 'Giá mỗi đêm'] = round(total_payment_for_booking_dialog / new_stay_duration_dialog) if new_stay_duration_dialog > 0 and total_payment_for_booking_dialog > 0 else 0.0
                                
                                st.session_state.df = df_to_update
                                if 'Tình trạng' in st.session_state.df.columns:
                                    st.session_state.active_bookings = st.session_state.df[st.session_state.df['Tình trạng'] != 'Đã hủy'].copy()
                                else:
                                    st.session_state.active_bookings = st.session_state.df.copy()

                                st.session_state.last_action_message = f"Đã cập nhật ngày cho đặt phòng {booking_id}."
                                st.session_state.editing_booking_id_for_dialog = None
                                if dialog_cin_key in st.session_state: del st.session_state[dialog_cin_key]
                                if dialog_cout_key in st.session_state: del st.session_state[dialog_cout_key]
                                st.rerun()
                            else: st.error(f"Lỗi: Không tìm thấy đặt phòng {booking_id} để cập nhật.")
                        else:
                            for msg_dialog in error_messages_dialog: st.error(msg_dialog)

                    if st.button("Hủy", key=f"cancel_edit_dialog_{booking_id}"):
                        st.session_state.editing_booking_id_for_dialog = None
                        if dialog_cin_key in st.session_state: del st.session_state[dialog_cin_key]
                        if dialog_cout_key in st.session_state: del st.session_state[dialog_cout_key]
                        st.rerun()

                edit_booking_dates_dialog_content(booking_to_edit_series, booking_id_to_edit)
            else:
                st.warning(f"Không tìm thấy thông tin chi tiết cho đặt phòng {booking_id_to_edit}.")
                st.session_state.editing_booking_id_for_dialog = None
        elif st.session_state.editing_booking_id_for_dialog: 
             st.warning("Không thể tải thông tin đặt phòng để sửa do thiếu dữ liệu.")
             st.session_state.editing_booking_id_for_dialog = None
    else:
        st.info("Vui lòng tải file dữ liệu để quản lý đặt phòng.")


# --- TAB PHÂN TÍCH ---
with tab_analytics:
    st.header("📈 Phân tích & Báo cáo")
    if df is not None and not df.empty and active_bookings is not None and not active_bookings.empty:
        st.sidebar.subheader("Bộ lọc Phân tích")
        min_analytics_filter = min_date_val 
        max_analytics_filter = max_date_val
        if min_analytics_filter > max_analytics_filter: max_analytics_filter = min_analytics_filter + timedelta(days=1) 

        start_date_analytics = st.sidebar.date_input("Ngày bắt đầu (phân tích C/I):", min_analytics_filter, min_value=min_date_val, max_value=max_date_val, key="analytics_start_date_key", help="Lọc theo ngày Check-in.")
        end_date_analytics = st.sidebar.date_input("Ngày kết thúc (phân tích C/I):", max_analytics_filter, min_value=start_date_analytics, max_value=max_date_val, key="analytics_end_date_key", help="Lọc theo ngày Check-in.")
        
        if start_date_analytics > end_date_analytics: st.sidebar.error("Lỗi: Ngày bắt đầu không thể sau ngày kết thúc.") 
        else:
            analytics_df_base = active_bookings.copy()
            analytics_df_base['Check-in Date'] = pd.to_datetime(analytics_df_base['Check-in Date'], errors='coerce')
            
            analytics_df_filtered = analytics_df_base[
                (analytics_df_base['Check-in Date'].dt.date >= start_date_analytics) & 
                (analytics_df_base['Check-in Date'].dt.date <= end_date_analytics)
            ].copy()

            if not analytics_df_filtered.empty:
                st.subheader(f"Số liệu từ {start_date_analytics.strftime('%d/%m/%Y')} đến {end_date_analytics.strftime('%d/%m/%Y')}")
                col_metric_anl1, col_metric_anl2, col_metric_anl3, col_metric_anl4 = st.columns(4)
                with col_metric_anl1: mean_stay = analytics_df_filtered['Stay Duration'].mean() if not analytics_df_filtered['Stay Duration'].empty else 0; st.metric("TB thời gian ở (ngày)", f"{mean_stay:.1f}")
                with col_metric_anl2: total_nights = analytics_df_filtered['Stay Duration'].sum(); st.metric("Tổng số đêm đã đặt", f"{total_nights:,.0f}")
                with col_metric_anl3: mean_payment = analytics_df_filtered['Tổng thanh toán'].mean() if not analytics_df_filtered['Tổng thanh toán'].empty else 0; st.metric("TB Tổng TT/đặt (VND)", f"{mean_payment:,.0f}")
                with col_metric_anl4: st.metric("Tổng lượt khách (OK)", f"{len(analytics_df_filtered):,.0f}")
                st.markdown("---")
                st.subheader("Thống kê theo khách hàng")
                if 'Tên người đặt' in analytics_df_filtered.columns and 'Tổng thanh toán' in analytics_df_filtered.columns:
                    analytics_df_filtered['Booking Date'] = pd.to_datetime(analytics_df_filtered['Booking Date'], errors='coerce')
                    guest_stats_anl = analytics_df_filtered.groupby('Tên người đặt').agg(total_bookings_agg=('Số đặt phòng', 'count'), total_payment_sum_agg=('Tổng thanh toán', 'sum'), avg_stay_duration_agg=('Stay Duration', 'mean'), last_booking_date_agg=('Booking Date', 'max')).reset_index()
                    guest_stats_anl.rename(columns={'Tên người đặt': 'Tên khách', 'total_bookings_agg': 'Tổng đặt phòng', 'total_payment_sum_agg': 'Tổng thanh toán (VND)', 'avg_stay_duration_agg': 'TB số đêm ở', 'last_booking_date_agg': 'Đặt phòng cuối'}, inplace=True)
                    guest_stats_display_anl = guest_stats_anl.copy()
                    if 'Tổng thanh toán (VND)' in guest_stats_display_anl.columns: guest_stats_display_anl['Tổng thanh toán (VND)'] = guest_stats_display_anl['Tổng thanh toán (VND)'].map('{:,.0f}'.format)
                    if 'TB số đêm ở' in guest_stats_display_anl.columns: guest_stats_display_anl['TB số đêm ở'] = guest_stats_display_anl['TB số đêm ở'].map('{:.1f}'.format)
                    if 'Đặt phòng cuối' in guest_stats_display_anl.columns: guest_stats_display_anl['Đặt phòng cuối'] = pd.to_datetime(guest_stats_display_anl['Đặt phòng cuối']).dt.strftime('%d/%m/%Y') 
                    st.dataframe(guest_stats_display_anl.set_index('Tên khách').sort_values(by='Tổng đặt phòng', ascending=False), use_container_width=True)
                    if not guest_stats_anl.empty and 'Tổng thanh toán (VND)' in guest_stats_anl.columns:
                        guest_stats_anl_chart = guest_stats_anl.copy()
                        guest_stats_anl_chart['Tổng thanh toán (VND)'] = pd.to_numeric(guest_stats_anl_chart['Tổng thanh toán (VND)'], errors='coerce').fillna(0)
                        guest_revenue_chart_df_anl = guest_stats_anl_chart.sort_values(by='Tổng thanh toán (VND)', ascending=False).head(15)
                        fig_guest_revenue_anl = px.bar(guest_revenue_chart_df_anl, x='Tên khách', y='Tổng thanh toán (VND)', title='Top 15 khách hàng theo tổng thanh toán', labels={'Tổng thanh toán (VND)': 'Tổng thanh toán (VND)', 'Tên khách': 'Tên khách hàng'}, color='Tổng thanh toán (VND)', color_continuous_scale=px.colors.sequential.Viridis, text_auto='.2s')
                        fig_guest_revenue_anl.update_layout(xaxis_tickangle=-45, height=400); st.plotly_chart(fig_guest_revenue_anl, use_container_width=True)
                else: st.info("Không đủ dữ liệu khách hàng để phân tích.")
                st.markdown("---")
                st.subheader("Phân tích khách hàng theo Genius")
                if 'Thành viên Genius' in analytics_df_filtered.columns:
                    col_genius_anl1, col_genius_anl2 = st.columns(2)
                    with col_genius_anl1:
                        genius_counts_anl = analytics_df_filtered['Thành viên Genius'].value_counts().reset_index(); genius_counts_anl.columns = ['Loại thành viên', 'Số lượng đặt phòng']
                        fig_genius_pie_anl = px.pie(genius_counts_anl, names='Loại thành viên', values='Số lượng đặt phòng', title='Tỷ lệ đặt phòng theo thành viên Genius', hole=0.3)
                        fig_genius_pie_anl.update_traces(textposition='inside', textinfo='percent+label'); st.plotly_chart(fig_genius_pie_anl, use_container_width=True)
                    with col_genius_anl2:
                        revenue_by_genius_anl = analytics_df_filtered.groupby('Thành viên Genius')['Tổng thanh toán'].sum().reset_index()
                        fig_genius_revenue_bar_anl = px.bar(revenue_by_genius_anl, x='Thành viên Genius', y='Tổng thanh toán', title='Tổng thanh toán theo loại thành viên Genius', labels={'Tổng thanh toán': 'Tổng thanh toán (VND)'}, color='Thành viên Genius', text_auto='.2s')
                        st.plotly_chart(fig_genius_revenue_bar_anl, use_container_width=True)
                else: st.info("Thiếu cột 'Thành viên Genius' để phân tích.")
                st.markdown("---")
                col_chart_anl_ts1, col_chart_anl_ts2 = st.columns(2)
                with col_chart_anl_ts1:
                    st.subheader("Xu hướng Tổng thanh toán hàng tháng")
                    df_for_monthly_rev_anl = analytics_df_filtered.copy()
                    df_for_monthly_rev_anl['Năm-Tháng Check-in'] = df_for_monthly_rev_anl['Check-in Date'].dt.to_period('M').astype(str)
                    monthly_revenue_analytics = df_for_monthly_rev_anl.groupby('Năm-Tháng Check-in')['Tổng thanh toán'].sum().reset_index().sort_values('Năm-Tháng Check-in')
                    if not monthly_revenue_analytics.empty:
                        fig_monthly_revenue_anl = px.line(monthly_revenue_analytics, x='Năm-Tháng Check-in', y='Tổng thanh toán', title='Tổng thanh toán hàng tháng (theo ngày Check-in)', markers=True, labels={'Tổng thanh toán': 'Tổng thanh toán (VND)', 'Năm-Tháng Check-in': 'Tháng Check-in'})
                        st.plotly_chart(fig_monthly_revenue_anl, use_container_width=True)
                    else: st.info("Không có dữ liệu tổng thanh toán hàng tháng.")
                with col_chart_anl_ts2:
                    st.subheader("Tỷ lệ lấp đầy hàng tháng (ước tính)")
                    if TOTAL_HOTEL_CAPACITY > 0:
                        df_for_occupancy_anl = analytics_df_filtered.copy()
                        df_for_occupancy_anl['Năm-Tháng Check-in'] = df_for_occupancy_anl['Check-in Date'].dt.to_period('M')
                        actual_nights_per_month_anl = df_for_occupancy_anl.groupby('Năm-Tháng Check-in')['Stay Duration'].sum().reset_index(name='Số đêm đã đặt')
                        if not actual_nights_per_month_anl.empty:
                            def get_max_nights_in_month(period_obj): return TOTAL_HOTEL_CAPACITY * period_obj.days_in_month
                            actual_nights_per_month_anl['Số đêm tối đa'] = actual_nights_per_month_anl['Năm-Tháng Check-in'].apply(get_max_nights_in_month)
                            actual_nights_per_month_anl['Tỷ lệ lấp đầy (%)'] = (actual_nights_per_month_anl['Số đêm đã đặt'] / actual_nights_per_month_anl['Số đêm tối đa']) * 100
                            actual_nights_per_month_anl['Năm-Tháng Check-in'] = actual_nights_per_month_anl['Năm-Tháng Check-in'].astype(str).sort_values()
                            fig_monthly_occupancy_anl = px.bar(actual_nights_per_month_anl, x='Năm-Tháng Check-in', y='Tỷ lệ lấp đầy (%)', title='Tỷ lệ lấp đầy hàng tháng (dựa trên số đêm)', color='Tỷ lệ lấp đầy (%)', color_continuous_scale='RdYlGn', labels={'Năm-Tháng Check-in': 'Tháng Check-in'}, text_auto='.1f')
                            fig_monthly_occupancy_anl.update_yaxes(range=[0, 105]); st.plotly_chart(fig_monthly_occupancy_anl, use_container_width=True)
                        else: st.info("Không có dữ liệu số đêm đã đặt để tính tỷ lệ lấp đầy.")
                    else: st.info("TOTAL_HOTEL_CAPACITY = 0. Không thể tính tỷ lệ lấp đầy.")
            else: st.warning("Không có dữ liệu đặt phòng (trạng thái OK) trong khoảng ngày đã chọn.")
    else: st.info("Vui lòng tải file dữ liệu để xem phân tích.")

# --- TAB THÊM ĐẶT PHÒNG MỚI ---
with tab_add_booking:
    st.header("➕ Thêm đặt phòng mới")

    room_types_options = st.session_state.get('room_types', []) 
    if not room_types_options:
        st.warning("Không có thông tin loại phòng. Vui lòng tải file dữ liệu trước hoặc đảm bảo file có cột 'Tên chỗ nghỉ' hợp lệ.")
        room_types_options = ["Chưa có loại phòng - Vui lòng tải dữ liệu"]


    if 'add_form_check_in_final' not in st.session_state:
        st.session_state.add_form_check_in_final = datetime.date.today()

    _min_checkout_date_calculated_final = st.session_state.add_form_check_in_final + timedelta(days=1)

    if 'add_form_check_out_final' not in st.session_state:
        st.session_state.add_form_check_out_final = _min_checkout_date_calculated_final
    else:
        if st.session_state.add_form_check_out_final < _min_checkout_date_calculated_final:
            st.session_state.add_form_check_out_final = _min_checkout_date_calculated_final

    with st.form(key="add_booking_form_v8_stable_dates"):
        st.subheader("Thông tin đặt phòng")
        col_form_add1, col_form_add2 = st.columns(2)

        with col_form_add1:
            guest_name_form = st.text_input("Tên khách*", placeholder="Nhập tên đầy đủ", key="form_v8_guest_name")
            room_type_form = st.selectbox("Loại phòng*", options=room_types_options, key="form_v8_room_type", index=0 if room_types_options else 0)
            
            genius_df_source_add = st.session_state.get('df')
            genius_options_add_list = []
            if genius_df_source_add is not None and not genius_df_source_add.empty and 'Thành viên Genius' in genius_df_source_add.columns:
                try:
                    genius_options_add_list = sorted(genius_df_source_add['Thành viên Genius'].dropna().astype(str).unique().tolist())
                except Exception:
                    genius_options_add_list = genius_df_source_add['Thành viên Genius'].dropna().astype(str).unique().tolist()
            if not genius_options_add_list: genius_options_add_list = ["Không", "Có"] 
            genius_member_form = st.selectbox("Thành viên Genius", options=genius_options_add_list, index=0, key="form_v8_genius")

        with col_form_add2:
            st.date_input(
                "Ngày check-in*",
                value=st.session_state.add_form_check_in_final, 
                min_value=datetime.date.today() - timedelta(days=365*2),
                max_value=datetime.date.today() + timedelta(days=365*2),
                key="add_form_check_in_final" 
            )
            st.date_input(
                "Ngày check-out*",
                value=st.session_state.add_form_check_out_final, 
                min_value=_min_checkout_date_calculated_final, 
                max_value=st.session_state.add_form_check_in_final + timedelta(days=731),
                key="add_form_check_out_final" 
            )
            status_df_source_add = st.session_state.get('df')
            status_options_add_list = []
            if status_df_source_add is not None and not status_df_source_add.empty and 'Tình trạng' in status_df_source_add.columns:
                try:
                    status_options_add_list = sorted(status_df_source_add['Tình trạng'].dropna().astype(str).unique().tolist())
                except Exception:
                    status_options_add_list = status_df_source_add['Tình trạng'].dropna().astype(str).unique().tolist()
            if not status_options_add_list: status_options_add_list = ["OK", "Đã hủy", "Chờ xử lý"] 
            default_status_idx = status_options_add_list.index("OK") if "OK" in status_options_add_list else 0
            booking_status_form = st.selectbox("Trạng thái đặt phòng", options=status_options_add_list, index=default_status_idx, key="form_v8_status")
        
        st.markdown("---"); st.subheader("Thông tin thanh toán")
        col_form_add3, col_form_add4 = st.columns(2)
        with col_form_add3:
            total_payment_form = st.number_input("Tổng thanh toán (VND)*", min_value=0, value=500000, step=50000, format="%d", key="form_v8_total_payment")
            default_commission = int(total_payment_form * 0.15) if total_payment_form > 0 else 0
            commission_form = st.number_input("Hoa hồng (VND)", min_value=0, value=default_commission, step=10000, format="%d", key="form_v8_commission")
        with col_form_add4:
            currency_df_source_add = st.session_state.get('df')
            currency_options_add_list = []
            if currency_df_source_add is not None and not currency_df_source_add.empty and 'Tiền tệ' in currency_df_source_add.columns:
                try:
                    currency_options_add_list = sorted(currency_df_source_add['Tiền tệ'].dropna().astype(str).unique())
                except Exception:
                     currency_options_add_list = currency_df_source_add['Tiền tệ'].dropna().astype(str).unique().tolist()
            if not currency_options_add_list: currency_options_add_list = ["VND", "USD"] 
            default_currency_idx = currency_options_add_list.index("VND") if "VND" in currency_options_add_list else 0
            currency_form = st.selectbox("Tiền tệ", options=currency_options_add_list, index=default_currency_idx, key="form_v8_currency")
            default_booking_id_add = f"MANUAL{datetime.datetime.now().strftime('%y%m%d%H%M%S%f')[:-3]}" 
            booking_id_form = st.text_input("Mã đặt phòng (tự động nếu trống)", value=default_booking_id_add, key="form_v8_booking_id")
        
        submitted_form_add = st.form_submit_button("💾 Thêm đặt phòng này", type="primary")
        
        if submitted_form_add:
            errors = [] 
            final_check_in_date = st.session_state.add_form_check_in_final
            final_check_out_date = st.session_state.add_form_check_out_final

            if not guest_name_form.strip(): errors.append("Tên khách không được để trống.")
            if final_check_out_date <= final_check_in_date: 
                errors.append(f"Ngày check-out ({final_check_out_date.strftime('%d/%m/%Y')}) phải sau ngày check-in ({final_check_in_date.strftime('%d/%m/%Y')}).")
            if total_payment_form <= 0 and booking_status_form == "OK": errors.append("Tổng thanh toán phải > 0 cho đặt phòng 'OK'.")
            if room_type_form == "Chưa có loại phòng - Vui lòng tải dữ liệu" or not room_type_form :
                errors.append("Loại phòng không hợp lệ. Vui lòng tải dữ liệu có thông tin loại phòng.")

            final_booking_id = booking_id_form.strip() if booking_id_form.strip() else default_booking_id_add
            current_df_for_check = st.session_state.get('df')
            if current_df_for_check is not None and not current_df_for_check.empty and 'Số đặt phòng' in current_df_for_check.columns and final_booking_id in current_df_for_check['Số đặt phòng'].values:
                errors.append(f"Mã đặt phòng '{final_booking_id}' đã tồn tại.")

            active_bookings_for_check = st.session_state.get('active_bookings')
            if active_bookings_for_check is not None and not active_bookings_for_check.empty: 
                active_bookings_for_check['Check-in Date'] = pd.to_datetime(active_bookings_for_check['Check-in Date'], errors='coerce')
                active_bookings_for_check['Check-out Date'] = pd.to_datetime(active_bookings_for_check['Check-out Date'], errors='coerce')


            if not errors and booking_status_form == "OK": 
                if active_bookings_for_check is not None and room_types_options and room_type_form not in ["Chưa có loại phòng - Vui lòng tải dữ liệu", None, ""]: 
                    current_check_date_form_add = final_check_in_date 
                    while current_check_date_form_add < final_check_out_date: 
                        availability_check_specific_add = get_room_availability(current_check_date_form_add, active_bookings_for_check, [room_type_form], ROOM_UNIT_PER_ROOM_TYPE)
                        if availability_check_specific_add.get(room_type_form, 0) <= 0:
                            errors.append(f"Phòng '{room_type_form}' đã hết vào ngày {current_check_date_form_add.strftime('%d/%m/%Y')}.")
                            break 
                        
                        temp_active_bookings_for_add = active_bookings_for_check[
                            (active_bookings_for_check['Check-in Date'].dt.date <= current_check_date_form_add) & 
                            (active_bookings_for_check['Check-out Date'].dt.date > current_check_date_form_add) & 
                            (active_bookings_for_check['Tình trạng'] != 'Đã hủy')
                        ]
                        if len(temp_active_bookings_for_add) + 1 > TOTAL_HOTEL_CAPACITY:
                            errors.append(f"Khách sạn đã đạt tổng công suất ({TOTAL_HOTEL_CAPACITY} phòng) vào ngày {current_check_date_form_add.strftime('%d/%m/%Y')}.")
                            break
                        current_check_date_form_add += timedelta(days=1)
            
            if errors: 
                for error_msg in errors: st.error(error_msg)
            else: 
                default_location = "N/A (Chưa xác định)"
                current_df_for_add = st.session_state.get('df')
                if current_df_for_add is not None and not current_df_for_add.empty and 'Tên chỗ nghỉ' in current_df_for_add.columns and 'Vị trí' in current_df_for_add.columns:
                    room_specific_locations_df = current_df_for_add[current_df_for_add['Tên chỗ nghỉ'] == room_type_form]
                    if not room_specific_locations_df.empty:
                        unique_room_locations = room_specific_locations_df['Vị trí'].dropna().unique()
                        if len(unique_room_locations) > 0 and pd.notna(unique_room_locations[0]):
                            default_location = str(unique_room_locations[0])
                
                stay_duration_val = (final_check_out_date - final_check_in_date).days
                total_payment_val = float(total_payment_form)
                price_per_night_val = round(total_payment_val / stay_duration_val) if stay_duration_val > 0 and total_payment_val > 0 else 0.0

                new_booking_data = {
                    'Tên chỗ nghỉ': room_type_form, 'Vị trí': default_location,
                    'Tên người đặt': guest_name_form.strip(), 'Thành viên Genius': genius_member_form,
                    'Ngày đến': f"ngày {final_check_in_date.day} tháng {final_check_in_date.month} năm {final_check_in_date.year}",
                    'Ngày đi': f"ngày {final_check_out_date.day} tháng {final_check_out_date.month} năm {final_check_out_date.year}",
                    'Được đặt vào': f"ngày {datetime.date.today().day} tháng {datetime.date.today().month} năm {datetime.date.today().year}",
                    'Tình trạng': booking_status_form, 'Tổng thanh toán': total_payment_val,
                    'Hoa hồng': float(commission_form), 'Tiền tệ': currency_form,
                    'Số đặt phòng': final_booking_id,
                    'Check-in Date': pd.Timestamp(final_check_in_date),
                    'Check-out Date': pd.Timestamp(final_check_out_date),
                    'Booking Date': pd.Timestamp(datetime.date.today()),
                    'Stay Duration': stay_duration_val,
                    'Giá mỗi đêm': price_per_night_val
                }
                new_booking_df_row = pd.DataFrame([new_booking_data])
                
                df_to_update = st.session_state.get('df')
                if df_to_update is None or df_to_update.empty:
                    st.session_state.df = new_booking_df_row
                else:
                    st.session_state.df = pd.concat([df_to_update, new_booking_df_row], ignore_index=True)
                
                if 'Tình trạng' in st.session_state.df.columns:
                    st.session_state.active_bookings = st.session_state.df[st.session_state.df['Tình trạng'] != 'Đã hủy'].copy()
                else:
                    st.session_state.active_bookings = st.session_state.df.copy()
                st.session_state.room_types = get_cleaned_room_types(st.session_state.df)

                st.success(f"Đặt phòng '{final_booking_id}' cho khách '{guest_name_form.strip()}' đã được thêm!"); st.balloons()
                st.session_state.last_action_message = f"Đã thêm đặt phòng {final_booking_id}."
                st.session_state.selected_calendar_date = None 
                
                if "add_form_check_in_final" in st.session_state:
                    del st.session_state.add_form_check_in_final
                if "add_form_check_out_final" in st.session_state:
                    del st.session_state.add_form_check_out_final
                
                st.rerun()

# --- TAB MẪU TIN NHẮN ---
with tab_message_templates:
    st.header("💌 Quản lý Mẫu Tin Nhắn")

    st.sidebar.subheader("Tải lên Mẫu Tin Nhắn")
    uploaded_template_file = st.sidebar.file_uploader("Tải lên file .txt chứa mẫu tin nhắn:", type=['txt'], key="template_file_uploader")

    if uploaded_template_file is not None:
        try:
            new_content = uploaded_template_file.read().decode("utf-8")
            parsed_templates = parse_message_templates(new_content)
            if parsed_templates is not None:
                st.session_state.message_templates_dict = parsed_templates
                st.session_state.raw_template_content_for_download = format_templates_to_text(st.session_state.message_templates_dict)
                st.sidebar.success("Đã tải và phân tích thành công file mẫu tin nhắn!")
                st.rerun()
            else:
                st.sidebar.error("Lỗi khi phân tích file mẫu tin nhắn. Nội dung có thể không hợp lệ.")
        except Exception as e:
            st.sidebar.error(f"Lỗi khi xử lý file: {e}")

    st.markdown("---")
    st.subheader("Thêm Mẫu Tin Nhắn Mới")
    with st.form("add_template_form", clear_on_submit=True):
        new_template_category = st.text_input("Chủ đề chính (VD: CHECK OUT, WIFI INFO):").upper().strip()
        new_template_label = st.text_input("Nhãn phụ (VD: Hướng dẫn, Lưu ý 1, 2. - Bỏ trống nếu là tin nhắn chính cho chủ đề):").strip()
        new_template_message = st.text_area("Nội dung tin nhắn:", height=150)
        submit_add_template = st.form_submit_button("➕ Thêm mẫu này")

        if submit_add_template:
            if not new_template_category or not new_template_message:
                st.error("Chủ đề chính và Nội dung tin nhắn không được để trống!")
            else:
                label_to_add = new_template_label if new_template_label else "DEFAULT"
                current_templates = st.session_state.message_templates_dict.copy()
                if new_template_category not in current_templates:
                    current_templates[new_template_category] = []
                label_exists_at_index = -1
                for i, (lbl, _) in enumerate(current_templates[new_template_category]):
                    if lbl == label_to_add:
                        label_exists_at_index = i
                        break
                if label_exists_at_index != -1:
                    current_templates[new_template_category][label_exists_at_index] = (label_to_add, new_template_message)
                    st.success(f"Đã cập nhật mẫu tin nhắn '{label_to_add}' trong chủ đề '{new_template_category}'.")
                else:
                    current_templates[new_template_category].append((label_to_add, new_template_message))
                    st.success(f"Đã thêm mẫu tin nhắn '{label_to_add}' vào chủ đề '{new_template_category}'.")
                st.session_state.message_templates_dict = current_templates
                st.session_state.raw_template_content_for_download = format_templates_to_text(current_templates)
                st.rerun()

    st.markdown("---")
    st.subheader("Danh Sách Mẫu Tin Nhắn Hiện Tại")

    if not st.session_state.get('message_templates_dict'):
        st.info("Chưa có mẫu tin nhắn nào. Hãy thêm mới hoặc tải lên file.")
    else:
        for category, labeled_messages in sorted(st.session_state.message_templates_dict.items()):
            with st.expander(f"Chủ đề: {category}", expanded=False):
                if not labeled_messages:
                    st.caption("Không có tin nhắn nào cho chủ đề này.")
                    continue
                for i, (label, message) in enumerate(labeled_messages):
                    widget_key_prefix = f"tpl_cat_{''.join(filter(str.isalnum, category))}_lbl_{''.join(filter(str.isalnum, label))}_{i}"
                    
                    col1_msg, col2_msg = st.columns([4,1]) 

                    with col1_msg:
                        if label != "DEFAULT":
                            st.markdown(f"**Nhãn: {label}**")
                        else:
                            st.markdown(f"**Nội dung chính:**")
                        st.text_area(
                            label=f"_{label}_in_{category}_content_display_", 
                            value=message,
                            height=max(80, len(message.split('\n')) * 20 + 40),
                            key=f"{widget_key_prefix}_text_area_display", 
                            disabled=True,
                            help="Nội dung tin nhắn. Bạn có thể chọn và sao chép thủ công từ đây."
                        )
                    
                    with col2_msg:
                        st.write("") 
                        st.write("") 
                        if st.button("Sao chép", key=f"{widget_key_prefix}_copy_button", help=f"Nhấn để nhận hướng dẫn sao chép tin nhắn '{label if label != 'DEFAULT' else 'này'}'"):
                            st.toast(f"Hãy chọn nội dung tin nhắn '{label if label != 'DEFAULT' else 'chính'}' từ ô bên trái và nhấn Ctrl+C (hoặc Cmd+C) để sao chép.", icon="📋")

                    if i < len(labeled_messages) - 1:
                        st.markdown("---")
        
        st.markdown("---")
        current_raw_template_content = st.session_state.get('raw_template_content_for_download', "")
        if isinstance(current_raw_template_content, str):
            st.download_button(
                label="📥 Tải về tất cả mẫu tin nhắn (TXT)",
                data=current_raw_template_content.encode("utf-8"),
                file_name="message_templates_download.txt",
                mime="text/plain",
                key="download_message_templates_button_v2" 
            )
        else:
            st.warning("Không thể tạo file tải về do nội dung mẫu tin nhắn không hợp lệ.")


# --- SIDEBAR CUỐI TRANG ---
st.sidebar.markdown("---"); st.sidebar.subheader("Thông tin & Tiện ích")
st.sidebar.info("""🏨 **Hệ thống Quản lý Phòng Khách sạn v3.1.4**\n\n**Tính năng chính:**\n- Theo dõi tình trạng phòng.\n- Lịch trực quan.\n- Quản lý đặt phòng chi tiết.\n- Phân tích doanh thu.\n- Thêm đặt phòng mới.\n- Xuất dữ liệu CSV, HTML & Google Sheets.""") 
if st.sidebar.button("🔄 Làm mới dữ liệu & Tải lại từ đầu", key="refresh_data_button_key_final_v3", help="Xóa toàn bộ dữ liệu và bắt đầu lại."):
    keys_to_clear_sidebar = [
        'df', 'active_bookings', 'room_types', 'data_source', 'uploaded_file_name', 
        'last_action_message', 'current_date_calendar', 'selected_calendar_date', 
        'booking_sort_column', 'booking_sort_ascending', 'editing_booking_id_for_dialog',
        'add_form_check_in_final', 'add_form_check_out_final', 
        'message_templates_dict', 'raw_template_content_for_download',
        'google_service_account_json_content', 'google_sheet_id_input_val', 'google_worksheet_name_input_val'
    ]
    for key in list(st.session_state.keys()): 
        if key.startswith("select_booking_cb_") or \
           key.startswith("dialog_cin_") or key.startswith("dialog_cout_") or \
           key.startswith("tpl_cat_") or key.startswith("day_button_overlay_"):
            del st.session_state[key]
            
    for key_to_del_sidebar in keys_to_clear_sidebar:
        if key_to_del_sidebar in st.session_state: 
            del st.session_state[key_to_del_sidebar]
    st.rerun()

if active_bookings is not None and not active_bookings.empty and room_types:
    st.sidebar.markdown("---"); st.sidebar.subheader("🔔 Thông báo nhanh")
    notifications_list_sidebar = []
    today_sb_notif_date = datetime.date.today()
    tomorrow_sb_notif_date = today_sb_notif_date + timedelta(days=1)
    active_bookings_copy_notif = active_bookings.copy()
    active_bookings_copy_notif['Check-in Date'] = pd.to_datetime(active_bookings_copy_notif['Check-in Date'], errors='coerce')
    active_bookings_copy_notif['Check-out Date'] = pd.to_datetime(active_bookings_copy_notif['Check-out Date'], errors='coerce')

    for room_type_alert_sb_item in room_types: 
        availability_sb_room_tomorrow = get_room_availability(tomorrow_sb_notif_date, active_bookings_copy_notif, [room_type_alert_sb_item], ROOM_UNIT_PER_ROOM_TYPE)
        available_tomorrow_count = availability_sb_room_tomorrow.get(room_type_alert_sb_item, ROOM_UNIT_PER_ROOM_TYPE)
        room_display_name_sb = room_type_alert_sb_item[:20] + "..." if len(room_type_alert_sb_item) > 20 else room_type_alert_sb_item
        if available_tomorrow_count == 0: notifications_list_sidebar.append(f"🔴 **{room_display_name_sb}**: HẾT PHÒNG ngày mai!")
        elif available_tomorrow_count == 1: notifications_list_sidebar.append(f"🟡 **{room_display_name_sb}**: Chỉ còn 1 phòng ({available_tomorrow_count} đơn vị) ngày mai.")
        elif available_tomorrow_count < ROOM_UNIT_PER_ROOM_TYPE : notifications_list_sidebar.append(f"🟠 **{room_display_name_sb}**: Còn {available_tomorrow_count} phòng ngày mai.")

    today_activity_sb_data = get_daily_activity(today_sb_notif_date, active_bookings_copy_notif)
    if today_activity_sb_data['check_in']: notifications_list_sidebar.append(f"🛬 **{len(today_activity_sb_data['check_in'])}** check-in hôm nay.")
    if today_activity_sb_data['check_out']: notifications_list_sidebar.append(f"🛫 **{len(today_activity_sb_data['check_out'])}** check-out hôm nay.")
    
    overall_tomorrow_info = get_overall_calendar_day_info(tomorrow_sb_notif_date, active_bookings_copy_notif, TOTAL_HOTEL_CAPACITY)
    if overall_tomorrow_info['available_units'] == 0:
        notifications_list_sidebar.append(f"🆘 **TOÀN KHÁCH SẠN**: HẾT PHÒNG ngày mai!")
    elif overall_tomorrow_info['available_units'] == 1:
        notifications_list_sidebar.append(f"⚠️ **TOÀN KHÁCH SẠN**: Chỉ còn 1 phòng TRỐNG ngày mai.")

    if notifications_list_sidebar:
        for notif_item_sb in notifications_list_sidebar: st.sidebar.warning(notif_item_sb)
    else: st.sidebar.success("✅ Mọi hoạt động đều ổn định!")

st.sidebar.markdown("---"); st.sidebar.subheader("Xuất dữ liệu")
df_main_export_final = st.session_state.get('df')

if df_main_export_final is not None and not df_main_export_final.empty:
    df_export_final_copy_csv = df_main_export_final.copy()
    date_columns_to_format_export = ['Check-in Date', 'Check-out Date', 'Booking Date']
    for col_date_export_final_item in date_columns_to_format_export:
        if col_date_export_final_item in df_export_final_copy_csv.columns:
            if pd.api.types.is_datetime64_any_dtype(df_export_final_copy_csv[col_date_export_final_item]):
                df_export_final_copy_csv[col_date_export_final_item] = pd.to_datetime(df_export_final_copy_csv[col_date_export_final_item], errors='coerce').dt.strftime('%d/%m/%Y')
            else: 
                df_export_final_copy_csv[col_date_export_final_item] = df_export_final_copy_csv[col_date_export_final_item].astype(str).fillna('')
    try:
        full_csv_data_final_export = df_export_final_copy_csv.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(label="📋 Tải xuống toàn bộ dữ liệu (CSV)", data=full_csv_data_final_export, file_name=f"DanhSachDatPhong_{datetime.date.today().strftime('%Y%m%d')}.csv", mime="text/csv", key="download_full_csv_key_final_v2", help="Tải xuống toàn bộ dữ liệu đặt phòng hiện tại.")
    except Exception as e_export_final: st.sidebar.error(f"Lỗi khi chuẩn bị file CSV: {e_export_final}")

    try:
        df_html_export = df_main_export_final.copy()
        base_display_columns_map_mgmt_for_export = { 
            'Số đặt phòng': 'Mã ĐP', 'Tên người đặt': 'Khách',
            'Tên chỗ nghỉ': 'Loại phòng', 'Check-in Date': 'Check-in',
            'Check-out Date': 'Check-out', 'Stay Duration': 'Số đêm',
            'Tình trạng': 'Trạng thái', 'Tổng thanh toán': 'Tổng tiền (VND)',
            'Giá mỗi đêm': 'Giá/đêm (VND)',
            'Booking Date': 'Ngày đặt'
        }
        display_columns_for_html = [
            'Số đặt phòng', 'Tên người đặt', 'Tên chỗ nghỉ',
            'Check-in Date', 'Check-out Date', 'Stay Duration',
            'Giá mỗi đêm', 'Tổng thanh toán', 'Tình trạng', 'Booking Date'
        ]
        existing_display_columns_html = [col for col in display_columns_for_html if col in df_html_export.columns]

        df_html_export_subset = df_html_export[existing_display_columns_html].copy() if existing_display_columns_html else df_html_export.copy()

        for col_date_html in date_columns_to_format_export:
            if col_date_html in df_html_export_subset.columns:
                if pd.api.types.is_datetime64_any_dtype(df_html_export_subset[col_date_html]):
                    df_html_export_subset.loc[:, col_date_html] = pd.to_datetime(df_html_export_subset[col_date_html], errors='coerce').dt.strftime('%d/%m/%Y')
                else:
                    df_html_export_subset.loc[:, col_date_html] = df_html_export_subset[col_date_html].astype(str).fillna('')

        df_html_export_subset_renamed = df_html_export_subset.rename(columns=base_display_columns_map_mgmt_for_export)
        html_data = df_html_export_subset_renamed.to_html(index=False, border=1, classes="dataframe_html_export table table-striped table-hover", justify="center", escape=False)
        html_string_final = f"""
        <html>
            <head><title>Danh Sách Đặt Phòng</title><meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .dataframe_html_export {{ border-collapse: collapse; width: 90%; margin: 20px auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .dataframe_html_export th, .dataframe_html_export td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                    .dataframe_html_export th {{ background-color: #f2f2f2; font-weight: bold; }}
                    .dataframe_html_export tr:nth-child(even) {{background-color: #f9f9f9;}}
                    .dataframe_html_export tr:hover {{background-color: #f1f1f1;}}
                    h1 {{ text-align: center; color: #333; }}
                </style>
            </head>
            <body><h1>Danh Sách Đặt Phòng - Ngày {datetime.date.today().strftime('%d/%m/%Y')}</h1>{html_data}</body>
        </html>
        """
        st.sidebar.download_button(
            label="🌐 Tải xuống toàn bộ dữ liệu (HTML)",
            data=html_string_final.encode('utf-8'),
            file_name=f"DanhSachDatPhong_{datetime.date.today().strftime('%Y%m%d')}.html",
            mime="text/html", key="download_full_html_key",
            help="Tải xuống toàn bộ dữ liệu đặt phòng hiện tại dưới dạng file HTML."
        )
    except Exception as e_export_html:
        st.sidebar.error(f"Lỗi khi chuẩn bị file HTML để xuất: {e_export_html}")
else:
    st.sidebar.info("Chưa có dữ liệu để xuất CSV/HTML.")


# --- Chức năng tải lên Google Sheets ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Tải lên Google Sheets")

if GSPREAD_AVAILABLE:
    uploaded_sa_key = st.sidebar.file_uploader(
        "Tải lên file JSON Service Account Key của Google",
        type=['json'],
        key="google_sa_key_uploader",
        help="File JSON chứa thông tin xác thực tài khoản dịch vụ Google Cloud."
    )

    if uploaded_sa_key is not None:
        try:
            st.session_state.google_service_account_json_content = json.load(uploaded_sa_key)
            st.sidebar.success(f"Đã tải thành công file key: {uploaded_sa_key.name}")
        except Exception as e:
            st.sidebar.error(f"Lỗi khi đọc file JSON: {e}")
            st.session_state.google_service_account_json_content = None
    
    if st.session_state.get('google_service_account_json_content'):
        st.sidebar.caption("✅ Đã có thông tin Service Account.")
    else:
        st.sidebar.caption("⚠️ Chưa có thông tin Service Account. Vui lòng tải file JSON lên.")

    google_sheet_id_input = st.sidebar.text_input(
        "ID Google Sheet:",  
        value=st.session_state.get("google_sheet_id_input_val", ""), 
        key="google_sheet_id_input_val", 
        help="Nhập ID của Google Sheet (tìm trong URL của Sheet)."
    )
    google_worksheet_name_input = st.sidebar.text_input(
        "Tên Worksheet:",
        value=st.session_state.get("google_worksheet_name_input_val", "Bookings"),
        key="google_worksheet_name_input_val",
        help="Tên của Worksheet trong Google Sheet."
    )

    if st.sidebar.button("📤 Tải lên Google Sheets", key="upload_to_gsheets_button_v3_id"): 
        if df_main_export_final is not None and not df_main_export_final.empty:
            if st.session_state.google_service_account_json_content:
                if google_sheet_id_input and google_worksheet_name_input: 
                    upload_to_google_sheets(
                        df_main_export_final, 
                        st.session_state.google_service_account_json_content,
                        google_sheet_id_input, 
                        google_worksheet_name_input
                    )
                else:
                    st.sidebar.error("Vui lòng nhập ID Google Sheet và tên Worksheet.")
            else:
                st.sidebar.error("Vui lòng tải lên file JSON Service Account Key của Google trước.")
        else:
            st.sidebar.warning("Không có dữ liệu để tải lên. Vui lòng tải file dữ liệu đặt phòng trước.")
elif df_main_export_final is not None: 
     st.sidebar.warning("Thư viện `gspread` hoặc `google-auth` chưa được cài đặt. Không thể tải lên Google Sheets.")


def convert_display_date_to_app_format(display_date_input: Any) -> Optional[str]:
    if pd.isna(display_date_input): return None
    if isinstance(display_date_input, (datetime.datetime, datetime.date, pd.Timestamp)):
        return f"ngày {display_date_input.day} tháng {display_date_input.month} năm {display_date_input.year}"
    cleaned_date_str = str(display_date_input).replace(',', '').strip().lower()
    m = re.search(r"(\d{1,2})\s*tháng\s*(\d{1,2})\s*(\d{4})", cleaned_date_str)
    if m: return f"ngày {m.group(1)} tháng {m.group(2)} năm {m.group(3)}"
    try:
        parsed = pd.to_datetime(cleaned_date_str, errors='coerce', dayfirst=True)
        if pd.notna(parsed): return f"ngày {parsed.day} tháng {parsed.month} năm {parsed.year}"
    except Exception: pass
    return None

def clean_currency_value(value_input: Any) -> float:
    if pd.isna(value_input): return 0.0
    cleaned_str = str(value_input).strip()
    cleaned_str = re.sub(r'(?i)VND\s*', '', cleaned_str)
    cleaned_str = re.sub(r'[^\d,.-]', '', cleaned_str)
    if not cleaned_str: return 0.0
    has_dot, has_comma = '.' in cleaned_str, ',' in cleaned_str
    if has_dot and has_comma:
        last_dot_pos, last_comma_pos = cleaned_str.rfind('.'), cleaned_str.rfind(',')
        if last_comma_pos > last_dot_pos:
            cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
        else:
            cleaned_str = cleaned_str.replace(',', '')
    elif has_comma:
        if cleaned_str.count(',') > 1 or (cleaned_str.count(',') == 1 and len(cleaned_str.split(',')[-1]) == 3 and len(cleaned_str.split(',')[0]) > 0):
            cleaned_str = cleaned_str.replace(',', '')
        else: cleaned_str = cleaned_str.replace(',', '.')
    elif has_dot:
        if cleaned_str.count('.') > 1 or (cleaned_str.count('.') == 1 and len(cleaned_str.split('.')[-1]) == 3 and len(cleaned_str.split('.')[0]) > 0):
            cleaned_str = cleaned_str.replace('.', '')
    numeric_val = pd.to_numeric(cleaned_str, errors='coerce')
    return numeric_val if pd.notna(numeric_val) else 0.0

@st.cache_data
def load_data_from_file(uploaded_file_obj) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Load booking data from an uploaded file (Excel, PDF, HTML) and return a tuple of (full_df, active_bookings_df).
    Handles column mapping, date parsing, and cleaning for each supported file type.
    """
    filename = uploaded_file_obj.name
    df_loaded = pd.DataFrame()
    try:
        if filename.endswith(('.xls', '.xlsx')):
            st.info(f"Đang xử lý file Excel: {filename}...")
            engine = 'xlrd' if filename.endswith('.xls') else 'openpyxl'
            df_loaded = pd.read_excel(uploaded_file_obj, engine=engine)
            excel_to_app_map = {
                'Ngày đến': 'Ngày đến_str_original', 'Ngày đi': 'Ngày đi_str_original',
                'Được đặt vào': 'Được đặt vào_str_original', 'Tên chỗ nghỉ': 'Tên chỗ nghỉ',
                'Vị trí': 'Vị trí', 'Tên người đặt': 'Tên người đặt',
                'Thành viên Genius': 'Thành viên Genius', 'Tình trạng': 'Tình trạng',
                'Tổng thanh toán': 'Tổng thanh toán', 'Hoa hồng': 'Hoa hồng',
                'Tiền tệ': 'Tiền tệ', 'Số đặt phòng': 'Số đặt phòng'
            }
            df_loaded = df_loaded.rename(columns={k: v for k, v in excel_to_app_map.items() if k in df_loaded.columns})
            if 'Ngày đến_str_original' in df_loaded.columns:
                df_loaded['Check-in Date'] = df_loaded['Ngày đến_str_original'].apply(parse_app_standard_date)
            if 'Ngày đi_str_original' in df_loaded.columns:
                df_loaded['Check-out Date'] = df_loaded['Ngày đi_str_original'].apply(parse_app_standard_date)
            if 'Được đặt vào_str_original' in df_loaded.columns:
                df_loaded['Booking Date'] = df_loaded['Được đặt vào_str_original'].apply(parse_app_standard_date)
        elif filename.endswith('.pdf'):
            st.info(f"Đang xử lý file PDF: {filename}...")
            if not PYPDF2_AVAILABLE:
                st.error("Không thể xử lý file PDF do thiếu thư viện PyPDF2. Vui lòng cài đặt: pip install pypdf2")
                return None, None
            st.warning("Chức năng xử lý file PDF đang trong giai đoạn thử nghiệm.")
            reader = PdfReader(uploaded_file_obj)
            text_data = ""
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text: text_data += page_text + "\n"
                else: st.warning(f"Không thể trích xuất văn bản từ trang {page_num + 1} của file PDF.")
            if not text_data.strip():
                st.error("File PDF không chứa văn bản hoặc không thể trích xuất văn bản.")
                return None, None
            lines = text_data.splitlines()
            parsed_rows = []
            pdf_headers_assumed_order = [
                "ID chỗ nghỉ", "Tên chỗ nghỉ", "Tên khách", "Nhận phòng", "Ngày đi",
                "Tình trạng", "Tổng thanh toán", "Hoa hồng", "Số đặt phòng", "Được đặt vào"
            ]
            for line in lines:
                cleaned_line = line.replace('\r', '').strip()
                if cleaned_line.startswith('"') and cleaned_line.count('","') >= (len(pdf_headers_assumed_order) - 5):
                    try:
                        csv_reader_obj = csv.reader(io.StringIO(cleaned_line))
                        fields = next(csv_reader_obj)
                        if len(fields) >= (len(pdf_headers_assumed_order) - 3) and len(fields) <= len(pdf_headers_assumed_order) + 2:
                            processed_fields = [field.replace('\n', ' ').strip() for field in fields]
                            row_dict = {header: (processed_fields[i] if i < len(processed_fields) else None)
                                        for i, header in enumerate(pdf_headers_assumed_order)}
                            parsed_rows.append(row_dict)
                    except csv.Error:
                        st.caption(f"Bỏ qua dòng không hợp lệ trong PDF: {cleaned_line[:50]}...")
                        continue
            if not parsed_rows:
                st.error("Không trích xuất được dữ liệu có cấu trúc từ file PDF.")
                return None, None
            df_loaded = pd.DataFrame(parsed_rows)
            if 'Nhận phòng' in df_loaded.columns: df_loaded['Ngày đến_str_original'] = df_loaded['Nhận phòng'].apply(convert_display_date_to_app_format)
            if 'Ngày đi' in df_loaded.columns: df_loaded['Ngày đi_str_original'] = df_loaded['Ngày đi'].apply(convert_display_date_to_app_format)
            if 'Được đặt vào' in df_loaded.columns: df_loaded['Được đặt vào_str_original'] = df_loaded['Được đặt vào'].apply(convert_display_date_to_app_format)
            if 'Ngày đến_str_original' in df_loaded.columns: df_loaded['Check-in Date'] = df_loaded['Ngày đến_str_original'].apply(parse_app_standard_date)
            if 'Ngày đi_str_original' in df_loaded.columns: df_loaded['Check-out Date'] = df_loaded['Ngày đi_str_original'].apply(parse_app_standard_date)
            if 'Được đặt vào_str_original' in df_loaded.columns: df_loaded['Booking Date'] = df_loaded['Được đặt vào_str_original'].apply(parse_app_standard_date)
            if "Tên khách" in df_loaded.columns:
                df_loaded["Tên người đặt"] = df_loaded["Tên khách"].apply(lambda x: str(x).split("Genius")[0].replace("1 khách", "").replace("2 khách", "").replace("2 người lớn","").strip() if pd.notna(x) else "N/A")
                df_loaded["Thành viên Genius"] = df_loaded["Tên khách"].apply(lambda x: "Có" if pd.notna(x) and "Genius" in str(x) else "Không")
            if "Vị trí" not in df_loaded.columns: df_loaded["Vị trí"] = "N/A (từ PDF)"
            if "Tiền tệ" not in df_loaded.columns: df_loaded["Tiền tệ"] = "VND"
        elif filename.endswith('.html'):
            st.info(f"Đang xử lý file HTML: {filename}...")
            if not BS4_AVAILABLE:
                st.error("Không thể xử lý file HTML do thiếu thư viện BeautifulSoup4.")
                return None, None
            st.info("Đang phân tích cấu trúc bảng trong file HTML...")
            soup = BeautifulSoup(uploaded_file_obj.read(), 'html.parser')
            table = soup.find('table', class_='cdd0659f86')
            if not table:
                st.error("Không tìm thấy bảng dữ liệu phù hợp trong file HTML (class 'cdd0659f86').")
                table = soup.find('table')
                if not table:
                    st.error("Cũng không tìm thấy thẻ <table> nào trong file HTML.")
                    return None, None
                else: st.warning("Đã tìm thấy một thẻ <table> chung, đang thử phân tích.")
            parsed_rows_html = []
            headers_from_html = []
            header_row = table.find('thead')
            if header_row:
                header_row = header_row.find('tr')
                if header_row: headers_from_html = [th.get_text(strip=True) for th in header_row.find_all('th')]
            body = table.find('tbody')
            if not body:
                st.error("Không tìm thấy phần thân (<tbody>) của bảng trong HTML.")
                return None, None
            for row_idx, row in enumerate(body.find_all('tr')):
                cells = row.find_all(['td', 'th'])
                row_data = {}
                for i, cell in enumerate(cells):
                    heading = cell.get('data-heading')
                    if not heading and i < len(headers_from_html): heading = headers_from_html[i]
                    elif not heading: heading = f"Cột {i+1}"
                    if heading:
                        if heading == "Tên khách":
                            guest_name_tag = cell.find('a')
                            guest_name_text = guest_name_tag.get_text(strip=True) if guest_name_tag else cell.get_text(separator=" ", strip=True)
                            row_data["Tên người đặt"] = guest_name_text.split("Genius")[0].replace("1 khách", "").replace("2 khách", "").replace("2 người lớn","").strip()
                            genius_svg = cell.find('svg', alt='Genius')
                            row_data["Thành viên Genius"] = "Có" if genius_svg or "Genius" in guest_name_text else "Không"
                        else: row_data[heading] = cell.get_text(separator=" ", strip=True)
                if row_data: parsed_rows_html.append(row_data)
            if not parsed_rows_html:
                st.error("Không trích xuất được dòng dữ liệu nào từ bảng HTML.")
                return None, None
            df_loaded = pd.DataFrame(parsed_rows_html)
            html_to_app_map = {
                "ID chỗ nghỉ": "ID chỗ nghỉ", "Tên chỗ nghỉ": "Tên chỗ nghỉ", "Vị trí": "Vị trí",
                "Nhận phòng": "Ngày đến_str_original", "Ngày đi": "Ngày đi_str_original",
                "Tình trạng": "Tình trạng", "Tổng thanh toán": "Tổng thanh toán",
                "Hoa hồng": "Hoa hồng", "Số đặt phòng": "Số đặt phòng",
                "Được đặt vào": "Được đặt vào_str_original"
            }
            df_loaded = df_loaded.rename(columns={k: v for k, v in html_to_app_map.items() if k in df_loaded.columns})
            if 'Ngày đến_str_original' in df_loaded.columns: df_loaded['Ngày đến_str'] = df_loaded['Ngày đến_str_original'].apply(convert_display_date_to_app_format)
            if 'Ngày đi_str_original' in df_loaded.columns: df_loaded['Ngày đi_str'] = df_loaded['Ngày đi_str_original'].apply(convert_display_date_to_app_format)
            if 'Được đặt vào_str_original' in df_loaded.columns: df_loaded['Được đặt vào_str'] = df_loaded['Được đặt vào_str_original'].apply(convert_display_date_to_app_format)
            if 'Ngày đến_str' in df_loaded.columns: df_loaded['Check-in Date'] = df_loaded['Ngày đến_str'].apply(parse_app_standard_date)
            if 'Ngày đi_str' in df_loaded.columns: df_loaded['Check-out Date'] = df_loaded['Ngày đi_str'].apply(parse_app_standard_date)
            if 'Được đặt vào_str' in df_loaded.columns: df_loaded['Booking Date'] = df_loaded['Được đặt vào_str'].apply(parse_app_standard_date)
            if "Tiền tệ" not in df_loaded.columns: df_loaded["Tiền tệ"] = "VND"
        else:
            st.error(f"Định dạng file '{filename.split('.')[-1]}' không được hỗ trợ.")
            return None, None

        if df_loaded.empty:
            st.error("Không có dữ liệu nào được tải hoặc tất cả các hàng đều trống.")
            return None, None
        df_loaded = df_loaded.dropna(how='all').reset_index(drop=True)

        for original_date_col_name in ['Ngày đến', 'Ngày đi', 'Được đặt vào']:
            source_col_original = f"{original_date_col_name}_str_original"
            source_col_generic = f"{original_date_col_name}_str"
            if original_date_col_name not in df_loaded.columns: df_loaded[original_date_col_name] = pd.NA
            if source_col_original in df_loaded.columns: df_loaded[original_date_col_name] = df_loaded[original_date_col_name].fillna(df_loaded[source_col_original])
            if source_col_generic in df_loaded.columns: df_loaded[original_date_col_name] = df_loaded[original_date_col_name].fillna(df_loaded[source_col_generic])
            if source_col_original in df_loaded.columns: df_loaded.drop(columns=[source_col_original], inplace=True, errors='ignore')
            if source_col_generic in df_loaded.columns: df_loaded.drop(columns=[source_col_generic], inplace=True, errors='ignore')

        ALL_REQUIRED_COLS = REQUIRED_APP_COLS_BASE + REQUIRED_APP_COLS_DERIVED
        for req_col in ALL_REQUIRED_COLS:
            if req_col not in df_loaded.columns:
                if "Date" in req_col and req_col not in ['Ngày đến', 'Ngày đi', 'Được đặt vào']: df_loaded[req_col] = pd.NaT
                elif "Duration" in req_col: df_loaded[req_col] = 0
                elif req_col in ['Tổng thanh toán', 'Hoa hồng', 'Giá mỗi đêm']: df_loaded[req_col] = 0.0
                else: df_loaded[req_col] = "N/A"

        for col_num_common in ["Tổng thanh toán", "Hoa hồng"]:
            if col_num_common in df_loaded.columns:
                 df_loaded[col_num_common] = df_loaded[col_num_common].apply(clean_currency_value)
            else: df_loaded[col_num_common] = 0.0

        cols_to_datetime = ['Check-in Date', 'Check-out Date', 'Booking Date']
        for col_dt in cols_to_datetime:
            if col_dt in df_loaded.columns:
                df_loaded[col_dt] = pd.to_datetime(df_loaded[col_dt], errors='coerce')
            else: df_loaded[col_dt] = pd.NaT

        if not df_loaded.empty and (df_loaded['Check-in Date'].isnull().any() or df_loaded['Check-out Date'].isnull().any()):
            initial_rows = len(df_loaded)
            df_loaded.dropna(subset=['Check-in Date', 'Check-out Date'], inplace=True)
            dropped_rows_count = initial_rows - len(df_loaded)
            if dropped_rows_count > 0:
                st.warning(f"Đã loại bỏ {dropped_rows_count} đặt phòng do ngày check-in hoặc check-out không hợp lệ.")
        if df_loaded.empty:
            st.error("Không còn dữ liệu hợp lệ sau khi loại bỏ các đặt phòng có ngày không hợp lệ.")
            return None, None

        if 'Check-out Date' in df_loaded.columns and 'Check-in Date' in df_loaded.columns:
            df_loaded['Stay Duration'] = (df_loaded['Check-out Date'] - df_loaded['Check-in Date']).dt.days
            df_loaded['Stay Duration'] = df_loaded['Stay Duration'].apply(lambda x: max(0, x) if pd.notna(x) else 0)
        else: df_loaded['Stay Duration'] = 0

        if 'Tổng thanh toán' in df_loaded.columns and 'Stay Duration' in df_loaded.columns:
            df_loaded['Giá mỗi đêm'] = np.where(
                (df_loaded['Stay Duration'].notna()) & (df_loaded['Stay Duration'] > 0) & (df_loaded['Tổng thanh toán'].notna()),
                df_loaded['Tổng thanh toán'] / df_loaded['Stay Duration'],
                0.0
            ).round(0)
        else:
            df_loaded['Giá mỗi đêm'] = 0.0

        active_bookings_loaded = df_loaded[df_loaded['Tình trạng'] != 'Đã hủy'].copy() if 'Tình trạng' in df_loaded.columns else pd.DataFrame(columns=ALL_REQUIRED_COLS)

        df_final = df_loaded[[col for col in ALL_REQUIRED_COLS if col in df_loaded.columns]].copy()
        if active_bookings_loaded is not None and not active_bookings_loaded.empty:
            active_bookings_final = active_bookings_loaded[[col for col in ALL_REQUIRED_COLS if col in active_bookings_loaded.columns]].copy()
        else: active_bookings_final = pd.DataFrame(columns=ALL_REQUIRED_COLS)

        st.success(f"Đã xử lý thành công file {filename}. Tìm thấy {len(df_final)} đặt phòng, trong đó {len(active_bookings_final)} đang hoạt động.")
        return df_final, active_bookings_final
    except xlrd.XLRDError: st.error(f"Lỗi khi đọc file Excel cũ (.xls): {filename}."); return None, None
    except openpyxl.utils.exceptions.InvalidFileException: st.error(f"Lỗi khi đọc file Excel (.xlsx): {filename}."); return None, None
    except Exception as e: st.error(f"Lỗi nghiêm trọng xảy ra khi xử lý file {filename}: {e}"); import traceback; st.error(f"Chi tiết lỗi: {traceback.format_exc()}"); return None, None
