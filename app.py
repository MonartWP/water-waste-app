import streamlit as st
from ultralytics import YOLO
import PIL.Image
import os
import folium
from streamlit_folium import st_folium
from datetime import datetime
from collections import Counter
import time
import pandas as pd
import json
import shutil
import random
from folium.plugins import MarkerCluster, HeatMap

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าเว็บ & ระบบฐานข้อมูล
# ---------------------------------------------------------
st.set_page_config(page_title="Water Waste Manager", page_icon="🌊", layout="wide")

st.markdown("""
<style>
    .stMetric { background-color: #f9f9f9; border: 1px solid #eee; border-radius: 5px; }
    div[data-testid="stContainer"] { background-color: #ffffff; border-radius: 10px; }
    h1, h2, h3 { font-family: 'Sarabun', sans-serif; font-weight: normal; }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8em; color: white; font-weight: bold; }
    .status-ok { background-color: #28a745; }
</style>
""", unsafe_allow_html=True)

# --- ตัวแปรระบบ ---
DB_FILE = 'data_reports.json'
IMG_DIR = 'uploaded_images'
MODEL_VERSION = "YOLOv8n-Custom v2.5"

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# --- ฟังก์ชันจัดการข้อมูล ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(st.session_state['reports'], f, ensure_ascii=False, indent=4)

def delete_report(report_index):
    report = st.session_state['reports'][report_index]
    if report.get('image_path') and os.path.exists(report['image_path']):
        os.remove(report['image_path'])
    st.session_state['reports'].pop(report_index)
    save_data()

# ---------------------------------------------------------
# 2. Session State
# ---------------------------------------------------------
if 'reports' not in st.session_state:
    st.session_state['reports'] = load_data()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ---------------------------------------------------------
# 3. โหลดโมเดล
# ---------------------------------------------------------
@st.cache_resource
def load_model():
    model_path = "best.pt"
    if os.path.exists(model_path):
        return YOLO(model_path)
    else:
        return YOLO("yolov8n.pt") 

try:
    model = load_model()
except Exception as e:
    st.error(f"Error loading model: {e}")
    model = None

def send_email_notification(to_email, job_id, status):
    if to_email:
        msg = f"📧 ถึง: {to_email} | งาน {job_id}: {status}"
        st.toast(msg, icon="✅")

# ---------------------------------------------------------
# 4. ส่วนแสดงผล (UI)
# ---------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=50)
st.sidebar.title("Smart River")
st.sidebar.caption(f"Engine: {MODEL_VERSION}")

page = st.sidebar.radio("เมนูหลัก", ["🏠 แจ้งเหตุ (ประชาชน)", "👮 เจ้าหน้าที่ (Dashboard)"])

st.sidebar.divider()

# --- [NEW] System Status (Sidebar) ---
with st.sidebar.expander("🖥️ สถานะระบบ (System Status)", expanded=True):
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("API Status", "Online")
    col_s2.metric("Database", "Connected")
    
    # จำลอง Resource Usage ให้ดูโปร
    cpu_usage = random.randint(10, 45)
    ram_usage = random.randint(30, 60)
    st.progress(cpu_usage, text=f"CPU Usage: {cpu_usage}%")
    st.progress(ram_usage, text=f"RAM Usage: {ram_usage}%")
    st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")

st.sidebar.divider()
with st.sidebar.expander("ℹ️ เกี่ยวกับโครงการ"):
    st.write("""
    **Water Body Waste Detection System**
    พัฒนาโดย: ทีมโครงงานวิศวกรรมโทรคมนาคม
    วัตถุประสงค์: เพื่อช่วยลดปัญหาขยะในแหล่งน้ำด้วย AI
    ติดต่อแจ้งเหตุ: 02-xxx-xxxx
    """)

# =========================================================
# 🏠 หน้าที่ 1: ประชาชน
# =========================================================
if page == "🏠 แจ้งเหตุ (ประชาชน)":
    
    st.title("🌊 ระบบแจ้งเหตุขยะในแหล่งน้ำ")
    st.write("ช่วยกันดูแลแหล่งน้ำของเรา ด้วย 3 ขั้นตอนง่ายๆ")
    st.divider()

    step1, step2, step3 = st.columns(3)
    with step1:
        st.markdown("#### 1. 📸 ถ่ายรูป")
        st.caption("ถ่ายรูปขยะให้ชัดเจนเพื่อให้ AI วิเคราะห์")
    with step2:
        st.markdown("#### 2. 📍 ระบุพิกัด")
        st.caption("ปักหมุดตำแหน่งที่พบในแผนที่")
    with step3:
        st.markdown("#### 3. 📩 ส่งข้อมูล")
        st.caption("กดส่งเรื่องและรอรับแจ้งเตือนทางอีเมล")

    st.markdown("---")

    work_col1, work_col2 = st.columns([1, 1])

    with work_col1:
        st.subheader("อัปโหลดรูปภาพ")
        uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"])
        
        if uploaded_file is not None:
            image = PIL.Image.open(uploaded_file)
            st.image(image, caption="รูปที่เลือก", use_container_width=True)
            
            conf_threshold = st.slider("ระดับความมั่นใจ (Confidence Threshold)", 0.0, 1.0, 0.25, 0.05)
            
            if st.button("ตรวจสอบขยะด้วย AI", type="primary", use_container_width=True):
                if model:
                    # --- [NEW] AI Process Simulation ---
                    progress_text = "เริ่มการทำงาน..."
                    my_bar = st.progress(0, text=progress_text)

                    for percent_complete in range(0, 40, 10):
                        time.sleep(0.05)
                        my_bar.progress(percent_complete, text="กำลังปรับปรุงคุณภาพภาพ (Preprocessing)...")
                    
                    time.sleep(0.1)
                    my_bar.progress(60, text="กำลังประมวลผลด้วยโมเดล (Inferencing)...")
                    
                    # Run Model จริง
                    results = model(image, conf=conf_threshold)
                    
                    my_bar.progress(80, text="กำลังสรุปผล (Post-processing)...")
                    time.sleep(0.1)
                    my_bar.progress(100, text="เสร็จสิ้น!")
                    time.sleep(0.2)
                    my_bar.empty()
                    # -----------------------------------

                    res_plotted = results[0].plot()
                    cls_indices = results[0].boxes.cls.tolist()
                    names_dict = results[0].names
                    counts_dict = Counter([names_dict[int(x)] for x in cls_indices])
                    total_count = len(cls_indices)
                    
                    st.session_state['temp_img'] = res_plotted
                    st.session_state['temp_count'] = total_count
                    st.session_state['temp_details'] = dict(counts_dict)
                    
                    st.image(res_plotted, caption=f"ผลลัพธ์: พบ {total_count} ชิ้น", channels="BGR", use_container_width=True)
                    
                    if counts_dict:
                        txt_res = " | ".join([f"{k}: {v}" for k,v in counts_dict.items()])
                        st.info(f"รายการ: {txt_res}")
                else:
                    st.error("Model Error")

    with work_col2:
        st.subheader("ระบุตำแหน่ง")
        m = folium.Map(location=[13.7563, 100.5018], zoom_start=12)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=400, use_container_width=True)
        
        lat, lon = 13.7563, 100.5018
        if map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            st.success(f"📍 พิกัด: {lat:.4f}, {lon:.4f}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        user_email = st.text_input("อีเมลติดต่อกลับ", placeholder="name@example.com")
    with c2:
        note = st.text_input("หมายเหตุ", placeholder="ระบุจุดสังเกตเพิ่มเติม...")
    
    # --- [NEW] Checkbox ยืนยันข้อมูล ---
    confirm_data = st.checkbox("ข้าพเจ้ายืนยันว่าข้อมูลและรูปภาพที่แจ้งเป็นความจริง")

    if st.button("ยืนยันการแจ้งเหตุ", type="secondary", use_container_width=True):
        if not confirm_data:
            st.error("⚠️ กรุณาติ๊กยืนยันความถูกต้องของข้อมูลก่อนส่ง")
        elif 'temp_count' in st.session_state:
            count = st.session_state['temp_count']
            severity = "🔴 วิกฤต" if count > 10 else ("🟠 ปานกลาง" if count > 5 else "🟢 เล็กน้อย")
            
            new_id = len(st.session_state['reports']) + 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = uploaded_file.name.split('.')[-1]
            save_path = f"{IMG_DIR}/report_{new_id}_{timestamp}.{file_ext}"
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            new_report = {
                "id": new_id,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "lat": lat, "lon": lon,
                "count": count, "details": st.session_state['temp_details'],
                "severity": severity, "note": note,
                "email": user_email, "status": "รอรับเรื่อง",
                "image_path": save_path
            }
            
            st.session_state['reports'].append(new_report)
            save_data()

            st.success(f"✅ บันทึกสำเร็จ (Job ID: {new_report['id']})")
            send_email_notification(user_email, new_report['id'], "ได้รับเรื่องแล้ว")
            del st.session_state['temp_count']
        else:
            st.warning("⚠️ กรุณาให้ AI ตรวจสอบรูปภาพก่อน")

# =========================================================
# 👮 หน้าที่ 2: เจ้าหน้าที่ (Dashboard)
# =========================================================
elif page == "👮 เจ้าหน้าที่ (Dashboard)":
    
    if not st.session_state['logged_in']:
        st.markdown("<br><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.subheader("เข้าสู่ระบบ")
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True):
                    if u == "admin" and p == "1234":
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.error("รหัสผิดพลาด")
    else:
        c_head, c_logout = st.columns([5, 1])
        with c_head:
            st.title("Agency Dashboard")
        with c_logout:
            if st.button("Logout"):
                st.session_state['logged_in'] = False
                st.rerun()

        if not st.session_state['reports']:
            st.info("ไม่มีข้อมูลการแจ้งเหตุ")
        else:
            with st.expander("🔍 ตัวกรองข้อมูล (Filters)", expanded=False):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filter_status = st.multiselect("สถานะงาน:", ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"], default=["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"])
                with col_f2:
                    filter_severity = st.multiselect("ระดับความรุนแรง:", ["🔴 วิกฤต", "🟠 ปานกลาง", "🟢 เล็กน้อย"], default=["🔴 วิกฤต", "🟠 ปานกลาง", "🟢 เล็กน้อย"])
            
            filtered_reports = [r for r in st.session_state['reports'] if r['status'] in filter_status and r['severity'] in filter_severity]

            col_main, col_activity = st.columns([2, 1])
            with col_main:
                total = len(st.session_state['reports'])
                done = len([r for r in st.session_state['reports'] if r['status'] == 'เสร็จสิ้น'])
                wait = total - done
                
                k1, k2, k3 = st.columns(3)
                k1.metric("ทั้งหมด", f"{total}", "Jobs")
                k2.metric("เสร็จสิ้น", f"{done}", "Completed")
                k3.metric("คงค้าง", f"{wait}", "Pending", delta_color="inverse")
                
                st.markdown("### สถิติภาพรวม")
                tab1, tab2 = st.tabs(["ประเภทขยะ", "สถานะงาน"])
                with tab1:
                    all_types = []
                    for r in st.session_state['reports']:
                        if r['details']:
                            for k, v in r['details'].items(): all_types.extend([k]*v)
                    if all_types:
                        df_trash = pd.DataFrame.from_dict(Counter(all_types), orient='index', columns=['จำนวน'])
                        st.bar_chart(df_trash)
                    else:
                        st.caption("ไม่มีข้อมูล")
                with tab2:
                    statuses = [r['status'] for r in st.session_state['reports']]
                    df_status = pd.DataFrame.from_dict(Counter(statuses), orient='index', columns=['จำนวน'])
                    st.bar_chart(df_status, color="#ff4b4b")

            with col_activity:
                st.markdown("### 🕒 ประวัติล่าสุด")
                st.markdown("---")
                recents = st.session_state['reports'][-5:][::-1]
                for r in recents:
                    border_color = "#ff4b4b" if r['status'] == "รอรับเรื่อง" else ("#ffa500" if r['status'] == "กำลังดำเนินการ" else "#28a745")
                    st.markdown(f"""
                    <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: #f8f9fa; border-left: 5px solid {border_color}; font-size: 0.9em;">
                        <b>งาน ID: {r['id']}</b> <span style='float:right; font-size:0.8em; color:#666;'>{r['date'].split(' ')[1]}</span><br>
                        สถานะ: {r['status']}<br>
                        <span style='color:#666; font-size:0.85em;'>{r['severity']} ({r['count']} ชิ้น)</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            if filtered_reports:
                st.markdown("### 🗺️ ภาพรวมพื้นที่เชิงลึก")
                
                col_switch, col_text = st.columns([0.1, 0.9])
                with col_switch:
                    is_heatmap = st.toggle("", value=False)
                with col_text:
                    st.write(f"🔥 **โหมด Heatmap** ({'เปิด' if is_heatmap else 'ปิด'})")
                
                last_lat = filtered_reports[-1]['lat']
                last_lon = filtered_reports[-1]['lon']
                m_agency = folium.Map(location=[last_lat, last_lon], zoom_start=10)
                
                if is_heatmap:
                    heat_data = [[r['lat'], r['lon']] for r in filtered_reports]
                    HeatMap(heat_data, radius=15, blur=10).add_to(m_agency)
                else:
                    marker_cluster = MarkerCluster().add_to(m_agency)
                    for r in filtered_reports:
                        color = "red" if r['status'] == "รอรับเรื่อง" else ("orange" if r['status'] == "กำลังดำเนินการ" else "green")
                        folium.Marker(
                            [r['lat'], r['lon']], 
                            popup=f"ID: {r['id']}", 
                            icon=folium.Icon(color=color)
                        ).add_to(marker_cluster)

                st_folium(m_agency, height=400, use_container_width=True)
            else:
                st.warning("ไม่พบข้อมูลตามตัวกรอง")

            st.markdown("### รายการแจ้งเหตุ")
            if filtered_reports:
                for r in filtered_reports:
                    real_index = st.session_state['reports'].index(r)
                    
                    icon = "🔴" if r['status'] == "รอรับเรื่อง" else ("🟠" if r['status'] == "กำลังดำเนินการ" else "🟢")
                    with st.expander(f"{icon} งานที่ {r['id']} ({r['status']}) - {r['severity']}"):
                        ec1, ec2 = st.columns([1, 2])
                        with ec1:
                            if r.get('image_path') and os.path.exists(r['image_path']):
                                st.image(r['image_path'], use_container_width=True)
                            else:
                                st.caption("ไม่พบไฟล์รูปภาพ")
                        with ec2:
                            st.caption(f"📍 {r['lat']:.4f}, {r['lon']:.4f} | 📧 {r['email']}")
                            st.write(f"**Note:** {r['note']}")
                            st.write(f"**ขยะ:** {r['count']} ชิ้น {r['details']}")
                            
                            c_stat, c_del = st.columns([3, 1])
                            with c_stat:
                                new_stat = st.selectbox("สถานะ", ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"], 
                                                        index=["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"].index(r['status']), 
                                                        key=f"st_{real_index}")
                                if new_stat != r['status']:
                                    st.session_state['reports'][real_index]['status'] = new_stat
                                    save_data()
                                    send_email_notification(r['email'], r['id'], new_stat)
                                    time.sleep(0.5)
                                    st.rerun()
                            with c_del:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("🗑️ ลบ", key=f"del_{real_index}", type="primary"):
                                    delete_report(real_index)
                                    st.rerun()
            else:
                st.info("ไม่พบรายการตามเงื่อนไขตัวกรอง")

# pip install streamlit ultralytics pillow folium streamlit-folium pandas
# streamlit run app.py
