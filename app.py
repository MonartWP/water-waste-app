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
</style>
""", unsafe_allow_html=True)

# --- ตัวแปรระบบ ---
DB_FILE = 'data_reports.json'
IMG_DIR = 'uploaded_images'
MODEL_VERSION = "YOLOv8n-Custom v3.0 (Pro)"

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
# 4. ส่วนแสดงผล (Sidebar & Login Logic)
# ---------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=50)
st.sidebar.title("Smart River")
st.sidebar.caption(f"Engine: {MODEL_VERSION}")

st.sidebar.divider()
with st.sidebar.expander("ℹ️ เกี่ยวกับโครงการ"):
    st.write("""
    **Water Body Waste Detection System**
    พัฒนาโดย: ทีมโครงงานวิศวกรรมโทรคมนาคม
    แจ้งเหตุพบขยะในแหล่งน้ำเพื่อการจัดการที่รวดเร็ว
    """)

st.sidebar.markdown("---")

# --- [NEW] ส่วนจัดการ Admin แบบซ่อน (Hidden Login) ---
# ไม่ใช้ Radio Button แล้ว แต่ใช้ Expander ซ่อนไว้ด้านล่าง
if not st.session_state['logged_in']:
    with st.sidebar.expander("🔐 สำหรับเจ้าหน้าที่ (Admin Access)"):
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ")
            
            if submitted:
                # ตรวจสอบรหัสผ่าน (รองรับทั้ง st.secrets และ hardcode เผื่อเทส)
                # วิธีใช้ Secrets: ตั้งค่าใน Streamlit Cloud Setting
                admin_user = st.secrets.get("admin_user", "admin") 
                admin_pass = st.secrets.get("admin_password", "1234")
                
                if user_input == admin_user and pass_input == admin_pass:
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
else:
    # ถ้าล็อกอินแล้ว แสดงปุ่มออกจากระบบแทน
    st.sidebar.success("สถานะ: เจ้าหน้าที่ (Admin)")
    if st.sidebar.button("ออกจากระบบ (Logout)"):
        st.session_state['logged_in'] = False
        st.rerun()

# ---------------------------------------------------------
# 5. Main Content Switching
# ---------------------------------------------------------

# ถ้าล็อกอิน -> ไปหน้า Dashboard
# ถ้ายังไม่ล็อกอิน -> ไปหน้า แจ้งเหตุ (หน้า default)
if st.session_state['logged_in']:
    page = "Dashboard"
else:
    page = "Citizen"

# =========================================================
# 🏠 ส่วนที่ 1: หน้าแจ้งเหตุ (Citizen View)
# =========================================================
if page == "Citizen":
    
    st.title("🌊 ระบบแจ้งเหตุขยะในแหล่งน้ำ")
    st.write("ช่วยกันดูแลแหล่งน้ำของเรา ด้วย 3 ขั้นตอนง่ายๆ")
    st.divider()

    step1, step2, step3 = st.columns(3)
    with step1:
        st.markdown("#### 1. 📸 ถ่ายรูป")
        st.caption("ถ่ายรูปขยะหรืออัปโหลดรูปภาพ")
    with step2:
        st.markdown("#### 2. 📍 ระบุพิกัด")
        st.caption("ปักหมุดตำแหน่งที่พบในแผนที่")
    with step3:
        st.markdown("#### 3. 📩 ส่งข้อมูล")
        st.caption("กดส่งเรื่องเพื่อให้เจ้าหน้าที่ตรวจสอบ")

    st.markdown("---")

    work_col1, work_col2 = st.columns([1, 1])

    with work_col1:
        st.subheader("หลักฐานรูปภาพ")
        
        # --- [NEW] เลือกวิธีนำเข้าภาพ (Camera vs Upload) ---
        input_method = st.radio("เลือกวิธีนำเข้าภาพ:", ["📸 ถ่ายภาพ", "📂 อัปโหลดไฟล์"], horizontal=True)
        
        uploaded_file = None
        if input_method == "📸 ถ่ายภาพ":
            camera_file = st.camera_input("กดเพื่อถ่ายภาพ")
            if camera_file:
                uploaded_file = camera_file
        else:
            uploaded_file = st.file_uploader("เลือกรูปภาพ", type=["jpg", "png", "jpeg"])
        
        if uploaded_file is not None:
            image = PIL.Image.open(uploaded_file)
            st.image(image, caption="ตัวอย่างภาพ", use_container_width=True)
            
            # Slider ปรับความมั่นใจ
            conf_threshold = st.slider("ความละเอียดการตรวจจับ (AI Confidence)", 0.0, 1.0, 0.25, 0.05)
            
            if st.button("ตรวจสอบขยะด้วย AI", type="primary", use_container_width=True):
                if model:
                    # Simulation Progress Bar
                    progress_text = "AI กำลังวิเคราะห์..."
                    my_bar = st.progress(0, text=progress_text)
                    for percent in range(0, 101, 10):
                        time.sleep(0.02)
                        my_bar.progress(percent, text=progress_text)
                    my_bar.empty()

                    # AI Prediction
                    results = model(image, conf=conf_threshold)
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
                        st.success(f"รายการที่พบ: {txt_res}")
                    else:
                        st.warning("ไม่พบวัตถุต้องสงสัย")
                else:
                    st.error("Model Error: ไม่พบไฟล์โมเดล")

    with work_col2:
        st.subheader("ระบุตำแหน่ง")
        m = folium.Map(location=[13.7563, 100.5018], zoom_start=12)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=400, use_container_width=True)
        
        lat, lon = 13.7563, 100.5018
        if map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            st.success(f"📍 พิกัดที่เลือก: {lat:.4f}, {lon:.4f}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        user_email = st.text_input("อีเมลติดต่อกลับ (Optional)", placeholder="name@example.com")
    with c2:
        note = st.text_input("รายละเอียดเพิ่มเติม", placeholder="เช่น ขยะส่งกลิ่นเหม็น, กีดขวางทางน้ำ")
    
    confirm_data = st.checkbox("ข้าพเจ้ายืนยันว่าข้อมูลและรูปภาพที่แจ้งเป็นความจริง")

    if st.button("ยืนยันการแจ้งเหตุ", type="secondary", use_container_width=True):
        if not confirm_data:
            st.error("⚠️ กรุณาติ๊กยืนยันความถูกต้องของข้อมูลก่อนส่ง")
        elif 'temp_count' in st.session_state:
            count = st.session_state['temp_count']
            severity = "🔴 วิกฤต" if count > 10 else ("🟠 ปานกลาง" if count > 5 else "🟢 เล็กน้อย")
            
            # Save Image
            new_id = len(st.session_state['reports']) + 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = uploaded_file.name.split('.')[-1] if uploaded_file.name != "camera_input" else "jpg"
            save_path = f"{IMG_DIR}/report_{new_id}_{timestamp}.{file_ext}"
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Create Record
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

            st.balloons()
            st.success(f"✅ บันทึกสำเร็จ! รหัสงาน: #{new_report['id']}")
            send_email_notification(user_email, new_report['id'], "ได้รับเรื่องแล้ว")
            
            # Clear Temp
            if 'temp_count' in st.session_state: del st.session_state['temp_count']
        else:
            st.warning("⚠️ กรุณาให้ AI ตรวจสอบรูปภาพก่อนกดส่ง")

# =========================================================
# 👮 ส่วนที่ 2: หน้าเจ้าหน้าที่ (Dashboard View)
# =========================================================
elif page == "Dashboard":
    
    c_head, c_space = st.columns([5, 1])
    with c_head:
        st.title("🔐 Agency Dashboard")
    
    if not st.session_state['reports']:
        st.info("ยังไม่มีข้อมูลการแจ้งเหตุในระบบ")
    else:
        # --- Filters ---
        with st.expander("🔍 ตัวกรองข้อมูล (Filters)", expanded=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_status = st.multiselect("สถานะงาน:", ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"], default=["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"])
            with col_f2:
                filter_severity = st.multiselect("ระดับความรุนแรง:", ["🔴 วิกฤต", "🟠 ปานกลาง", "🟢 เล็กน้อย"], default=["🔴 วิกฤต", "🟠 ปานกลาง", "🟢 เล็กน้อย"])
        
        filtered_reports = [r for r in st.session_state['reports'] if r['status'] in filter_status and r['severity'] in filter_severity]

        # --- Stats & Charts ---
        col_main, col_activity = st.columns([2, 1])
        with col_main:
            total = len(st.session_state['reports'])
            done = len([r for r in st.session_state['reports'] if r['status'] == 'เสร็จสิ้น'])
            wait = total - done
            
            k1, k2, k3 = st.columns(3)
            k1.metric("งานทั้งหมด", f"{total}", "Reports")
            k2.metric("ดำเนินการแล้ว", f"{done}", "Done")
            k3.metric("คงค้าง", f"{wait}", "Pending", delta_color="inverse")
            
            st.markdown("### สถิติเชิงลึก")
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
            st.markdown("### 📥 ส่งออกข้อมูล")
            # --- [NEW] Export CSV Button ---
            if st.session_state['reports']:
                df_export = pd.DataFrame(st.session_state['reports'])
                df_export['details'] = df_export['details'].apply(lambda x: str(x)) # แปลง dict เป็น str เพื่อให้ save ได้
                csv = df_export.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📄 Download CSV",
                    data=csv,
                    file_name=f"waste_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.markdown("### 🕒 แจ้งเตือนล่าสุด")
            recents = st.session_state['reports'][-5:][::-1]
            for r in recents:
                border_color = "#ff4b4b" if r['status'] == "รอรับเรื่อง" else ("#ffa500" if r['status'] == "กำลังดำเนินการ" else "#28a745")
                st.markdown(f"""
                <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: #f8f9fa; border-left: 5px solid {border_color}; font-size: 0.85em;">
                    <b>#{r['id']}</b> {r['date'].split(' ')[1]} | {r['status']}<br>
                    <span style='color:#666;'>{r['severity']} ({r['count']} ชิ้น)</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # --- Advanced Map ---
        if filtered_reports:
            st.markdown("### 🗺️ แผนที่ปฏิบัติการ (Operation Map)")
            
            col_switch, col_text = st.columns([0.1, 0.9])
            with col_switch:
                is_heatmap = st.toggle("", value=False)
            with col_text:
                st.write(f"🔥 **Heatmap Mode** ({'ON' if is_heatmap else 'OFF'})")
            
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

            st_folium(m_agency, height=450, use_container_width=True)
        else:
            st.warning("ไม่พบข้อมูลตามตัวกรอง")

        # --- Task Management ---
        st.markdown("### 📝 รายการแจ้งเหตุ (Task List)")
        if filtered_reports:
            for r in filtered_reports:
                real_index = st.session_state['reports'].index(r)
                
                icon = "🔴" if r['status'] == "รอรับเรื่อง" else ("🟠" if r['status'] == "กำลังดำเนินการ" else "🟢")
                with st.expander(f"{icon} Ticket #{r['id']} : {r['date']} - {r['severity']}"):
                    ec1, ec2 = st.columns([1, 2])
                    with ec1:
                        if r.get('image_path') and os.path.exists(r['image_path']):
                            st.image(r['image_path'], use_container_width=True)
                        else:
                            st.caption("ไม่พบไฟล์รูปภาพ")
                    with ec2:
                        st.caption(f"📍 {r['lat']:.4f}, {r['lon']:.4f} | 📧 {r['email']}")
                        st.write(f"**Note:** {r['note']}")
                        st.info(f"**AI Detected:** {r['count']} ea. | {r['details']}")
                        
                        c_stat, c_del = st.columns([3, 1])
                        with c_stat:
                            new_stat = st.selectbox("Update Status", ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"], 
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