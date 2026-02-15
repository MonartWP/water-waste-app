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
# 1. ตั้งค่าหน้าเว็บ & CSS (Theme: Clean & Professional)
# ---------------------------------------------------------
st.set_page_config(page_title="Water Waste Manager", page_icon="🌊", layout="wide")

st.markdown("""
<style>
    .stMetric { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 8px; padding: 10px; }
    div[data-testid="stContainer"] { background-color: #ffffff; border-radius: 10px; }
    h1, h2, h3 { font-family: 'Sarabun', sans-serif; font-weight: 600; color: #2c3e50; }
    .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 0.8em; color: white; font-weight: bold; }
    .report-card { background-color: #f1f8ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #007bff; }
</style>
""", unsafe_allow_html=True)

# --- ตัวแปรระบบ ---
DB_FILE = 'data_reports.json'
IMG_DIR = 'uploaded_images'
MODEL_VERSION = "YOLOv8n-Custom v8.0 (Ultimate)"

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# ---------------------------------------------------------
# 2. ฟังก์ชันจัดการข้อมูล (Data Management)
# ---------------------------------------------------------
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
# 3. Session State & Model Init
# ---------------------------------------------------------
if 'reports' not in st.session_state:
    st.session_state['reports'] = load_data()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
        msg = f"📧 ถึง: {to_email} | งาน #{job_id}: {status}"
        st.toast(msg, icon="✅")

# ---------------------------------------------------------
# 4. Sidebar & Hidden Admin Login
# ---------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=60)
st.sidebar.title("Smart River")
st.sidebar.caption(f"System: {MODEL_VERSION}")

st.sidebar.markdown("---")

# --- System Status (Fake but Cool) ---
with st.sidebar.expander("🖥️ สถานะเซิร์ฟเวอร์ (Server Status)", expanded=False):
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("API", "🟢 Online")
    col_s2.metric("DB", "🟢 Connected")
    st.progress(random.randint(20, 40), text="CPU Load")
    st.caption(f"Last heartbeat: {datetime.now().strftime('%H:%M:%S')}")

# --- Hidden Admin Login ---
if not st.session_state['logged_in']:
    st.sidebar.markdown("---")
    with st.sidebar.expander("🔐 สำหรับเจ้าหน้าที่ (Admin Only)"):
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ")
            
            if submitted:
                # ใช้ st.secrets เพื่อความปลอดภัย (Fallback เป็น admin/1234)
                admin_user = st.secrets.get("admin_user", "admin") 
                admin_pass = st.secrets.get("admin_password", "1234")
                
                if user_input == admin_user and pass_input == admin_pass:
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
else:
    st.sidebar.success("👤 สวัสดี, เจ้าหน้าที่")
    if st.sidebar.button("ออกจากระบบ (Logout)"):
        st.session_state['logged_in'] = False
        st.rerun()

# ---------------------------------------------------------
# 5. Main Page Router
# ---------------------------------------------------------
if st.session_state['logged_in']:
    page = "Dashboard"
else:
    page = "Citizen"

# =========================================================
# 🏠 ส่วนที่ 1: หน้าประชาชน (Citizen View)
# =========================================================
if page == "Citizen":
    
    st.title("🌊 แจ้งเหตุขยะในแหล่งน้ำ")
    st.markdown("**ร่วมเป็นส่วนหนึ่งในการดูแลแม่น้ำของเรา ง่ายๆ เพียง 3 ขั้นตอน**")
    
    # --- [NEW] Recent Feed (Social Proof) ---
    if st.session_state['reports']:
        st.markdown("---")
        with st.container():
            col_feed, col_txt = st.columns([0.1, 0.9])
            with col_feed:
                st.markdown("📢")
            with col_txt:
                last_report = st.session_state['reports'][-1]
                st.caption(f"**ล่าสุดเมื่อกี้:** มีเพื่อนพลเมืองแจ้งเหตุเข้ามาที่เขต {last_report.get('lat', 0):.2f}, {last_report.get('lon', 0):.2f} (งาน #{last_report['id']})")

    st.divider()

    # --- Step 1-3 Workflow ---
    step1, step2, step3 = st.columns(3)
    with step1:
        st.info("1. 📸 ถ่ายรูป")
    with step2:
        st.info("2. 📍 ระบุพิกัด")
    with step3:
        st.info("3. 📝 ส่งข้อมูล")

    col_left, col_right = st.columns([1, 1])

    # --- Left Column: Camera & AI ---
    with col_left:
        st.subheader("1. หลักฐานรูปภาพ")
        
        # เลือกแหล่งภาพ
        input_type = st.radio("เลือกวิธี:", ["📸 ถ่ายภาพ", "📂 อัปโหลด"], horizontal=True, label_visibility="collapsed")
        
        uploaded_file = None
        if input_type == "📸 ถ่ายภาพ":
            uploaded_file = st.camera_input("กดปุ่มเพื่อถ่ายภาพ")
        else:
            uploaded_file = st.file_uploader("เลือกไฟล์รูปภาพ", type=["jpg", "png", "jpeg"])
        
        if uploaded_file:
            image = PIL.Image.open(uploaded_file)
            st.image(image, caption="ภาพตัวอย่าง", use_container_width=True)
            
            # AI Options
            with st.expander("⚙️ ตั้งค่า AI (ขั้นสูง)"):
                conf_threshold = st.slider("ความละเอียด (Confidence)", 0.0, 1.0, 0.25, 0.05)

            if st.button("🔍 วิเคราะห์ด้วย AI", type="primary", use_container_width=True):
                if model:
                    # Progress Bar Simulation
                    progress_text = "AI กำลังทำงาน..."
                    my_bar = st.progress(0, text=progress_text)
                    for percent in range(0, 101, 20):
                        time.sleep(0.05)
                        my_bar.progress(percent, text=progress_text)
                    my_bar.empty()

                    # Prediction
                    results = model(image, conf=conf_threshold)
                    res_plotted = results[0].plot()
                    
                    # Count Logic
                    cls_indices = results[0].boxes.cls.tolist()
                    names_dict = results[0].names
                    counts_dict = Counter([names_dict[int(x)] for x in cls_indices])
                    total_count = len(cls_indices)
                    
                    # Store in Session
                    st.session_state['temp_img'] = res_plotted
                    st.session_state['temp_count'] = total_count
                    st.session_state['temp_details'] = dict(counts_dict)
                    
                    st.image(res_plotted, caption=f"ผลลัพธ์: พบ {total_count} ชิ้น", channels="BGR", use_container_width=True)
                    
                    if counts_dict:
                        items_str = ", ".join([f"{k} ({v})" for k,v in counts_dict.items()])
                        st.success(f"✅ พบ: {items_str}")
                    else:
                        st.warning("⚠️ ไม่พบวัตถุต้องสงสัย")
                else:
                    st.error("ไม่พบโมเดล AI")

    # --- Right Column: Map & Details ---
    with col_right:
        st.subheader("2. จุดเกิดเหตุ")
        
        m = folium.Map(location=[13.7563, 100.5018], zoom_start=12)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=300, use_container_width=True)
        
        lat, lon = 13.7563, 100.5018
        if map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            st.success(f"📍 พิกัด: {lat:.4f}, {lon:.4f}")
        else:
            st.info("👆 จิ้มบนแผนที่เพื่อระบุตำแหน่ง")

        st.markdown("---")
        st.subheader("3. รายละเอียด")
        
        # --- [NEW] Smart Tags (ลดการพิมพ์) ---
        st.write("ประเภทปัญหา (เลือกได้หลายข้อ)")
        tags = st.multiselect(
            "Tags",
            ["ถุงพลาสติก/ขวดน้ำ", "ผักตบชวา/วัชพืช", "ขยะชิ้นใหญ่", "สัตว์ตาย/กลิ่นเหม็น", "คราบน้ำมัน", "กีดขวางทางระบายน้ำ"],
            label_visibility="collapsed"
        )
        
        other_note = st.text_input("เพิ่มเติม (ถ้ามี)", placeholder="เช่น อยู่ใต้สะพาน...")
        contact_email = st.text_input("อีเมลติดต่อกลับ (ไม่บังคับ)")
        
        # Combine notes
        final_note = ", ".join(tags)
        if other_note:
            final_note += f" | {other_note}"

    # --- Submit Section ---
    st.markdown("---")
    col_check, col_btn = st.columns([2, 1])
    with col_check:
        confirm = st.checkbox("ยืนยันว่าข้อมูลเป็นความจริง")
    with col_btn:
        btn_submit = st.button("🚀 ส่งเรื่องแจ้งเหตุ", type="primary", use_container_width=True)

    if btn_submit:
        if not confirm:
            st.toast("⚠️ กรุณายืนยันข้อมูลก่อนส่ง", icon="⚠️")
        elif 'temp_count' not in st.session_state:
            st.toast("⚠️ กรุณาให้ AI ตรวจสอบรูปก่อน", icon="🤖")
        else:
            # Process Saving
            new_id = len(st.session_state['reports']) + 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # File Handling
            ext = "jpg"
            if hasattr(uploaded_file, 'name') and uploaded_file.name != "camera_input":
                ext = uploaded_file.name.split('.')[-1]
            
            save_path = f"{IMG_DIR}/report_{new_id}_{timestamp}.{ext}"
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            severity = "🔴 วิกฤต" if st.session_state['temp_count'] > 10 else ("🟠 ปานกลาง" if st.session_state['temp_count'] > 5 else "🟢 เล็กน้อย")

            new_report = {
                "id": new_id,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "lat": lat, "lon": lon,
                "count": st.session_state['temp_count'],
                "details": st.session_state['temp_details'],
                "severity": severity,
                "note": final_note, # Smart Tag Data
                "email": contact_email,
                "status": "รอรับเรื่อง",
                "image_path": save_path
            }

            st.session_state['reports'].append(new_report)
            save_data()

            st.balloons()
            st.success(f"✅ บันทึกสำเร็จ! รหัสงานของคุณคือ: #{new_id}")
            send_email_notification(contact_email, new_id, "ได้รับเรื่องแล้ว")
            
            # Reset
            if 'temp_count' in st.session_state: del st.session_state['temp_count']

    # --- [NEW] Tracking System (ลดความระแวง) ---
    st.markdown("---")
    with st.expander("🔍 ติดตามสถานะงาน (Tracking)"):
        c_track1, c_track2 = st.columns([3, 1])
        with c_track1:
            track_id = st.text_input("กรอกรหัสงาน (Job ID)", placeholder="เช่น 1")
        with c_track2:
            st.write("") # Spacer
            st.write("") 
            btn_track = st.button("ตรวจสอบ")
        
        if btn_track and track_id:
            found = False
            for r in st.session_state['reports']:
                if str(r['id']) == track_id:
                    st.info(f"🆔 งานหมายเลข: {r['id']}")
                    st.write(f"📅 วันที่: {r['date']}")
                    st.markdown(f"🚦 สถานะปัจจุบัน: **{r['status']}**")
                    if r['status'] == "เสร็จสิ้น":
                        st.success("🎉 ดำเนินการเรียบร้อยแล้ว!")
                    found = True
                    break
            if not found:
                st.error("❌ ไม่พบข้อมูล")

# =========================================================
# 👮 ส่วนที่ 2: หน้าเจ้าหน้าที่ (Dashboard View)
# =========================================================
elif page == "Dashboard":
    
    st.title("🔐 Agency Dashboard")
    st.caption("ระบบบริหารจัดการงานแจ้งเหตุ (Admin Only)")
    
    if not st.session_state['reports']:
        st.warning("ยังไม่มีข้อมูลในระบบ")
    else:
        # --- Filters ---
        with st.expander("🛠️ ตัวกรอง (Filters)", expanded=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                status_filter = st.multiselect("สถานะ", ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"], default=["รอรับเรื่อง", "กำลังดำเนินการ"])
            with f_col2:
                severity_filter = st.multiselect("ระดับความรุนแรง", ["🔴 วิกฤต", "🟠 ปานกลาง", "🟢 เล็กน้อย"], default=["🔴 วิกฤต", "🟠 ปานกลาง", "🟢 เล็กน้อย"])
        
        # Apply Filter
        filtered_list = [r for r in st.session_state['reports'] if r['status'] in status_filter and r['severity'] in severity_filter]

        # --- KPI Cards ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("ทั้งหมด", len(st.session_state['reports']))
        k2.metric("รอรับเรื่อง", len([r for r in st.session_state['reports'] if r['status'] == 'รอรับเรื่อง']), delta_color="inverse")
        k3.metric("ดำเนินการ", len([r for r in st.session_state['reports'] if r['status'] == 'กำลังดำเนินการ']))
        k4.metric("เสร็จสิ้น", len([r for r in st.session_state['reports'] if r['status'] == 'เสร็จสิ้น']))

        st.divider()

        # --- Advanced Map & Export ---
        c_map, c_act = st.columns([2, 1])
        
        with c_map:
            st.subheader("🗺️ แผนที่ปฏิบัติการ")
            # Toggle Map Type
            is_heatmap = st.toggle("แสดงแบบ Heatmap (ความหนาแน่น)", value=False)
            
            if filtered_list:
                center_lat = filtered_list[-1]['lat']
                center_lon = filtered_list[-1]['lon']
                m_admin = folium.Map(location=[center_lat, center_lon], zoom_start=11)
                
                if is_heatmap:
                    heat_data = [[r['lat'], r['lon']] for r in filtered_list]
                    HeatMap(heat_data, radius=15).add_to(m_admin)
                else:
                    cluster = MarkerCluster().add_to(m_admin)
                    for r in filtered_list:
                        color = "red" if r['status'] == "รอรับเรื่อง" else ("orange" if r['status'] == "กำลังดำเนินการ" else "green")
                        folium.Marker(
                            [r['lat'], r['lon']],
                            popup=f"#{r['id']} ({r['severity']})",
                            icon=folium.Icon(color=color)
                        ).add_to(cluster)
                
                st_folium(m_admin, height=400, use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลตามตัวกรอง")

        with c_act:
            st.subheader("📥 จัดการข้อมูล")
            # [NEW] CSV Export
            df = pd.DataFrame(st.session_state['reports'])
            if not df.empty:
                # Cleanup for CSV
                df['details'] = df['details'].astype(str) 
                csv = df.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📄 ดาวน์โหลดรายงาน (Excel/CSV)",
                    data=csv,
                    file_name="waste_report.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            
            st.markdown("### 📊 กราฟสรุป")
            if not df.empty:
                st.caption("จำแนกตามความรุนแรง")
                st.bar_chart(df['severity'].value_counts(), color="#ffaa00")

        # --- Task Management List ---
        st.divider()
        st.subheader("📝 รายการงาน (Task List)")
        
        if filtered_list:
            for r in filtered_list:
                idx = st.session_state['reports'].index(r)
                
                # Card Styling
                with st.expander(f"📌 งาน #{r['id']} | {r['status']} | {r['note'][:30]}..."):
                    c_img, c_info = st.columns([1, 2])
                    
                    with c_img:
                        if os.path.exists(r['image_path']):
                            st.image(r['image_path'], use_container_width=True)
                        else:
                            st.error("ไม่พบไฟล์ภาพ")
                    
                    with c_info:
                        st.write(f"**วันที่:** {r['date']}")
                        st.write(f"**พิกัด:** {r['lat']}, {r['lon']}")
                        st.write(f"**รายละเอียด:** {r['note']}")
                        st.info(f"🤖 AI พบ: {r['count']} ชิ้น {r['details']}")
                        
                        # Admin Actions
                        c_act1, c_act2 = st.columns(2)
                        with c_act1:
                            new_status = st.selectbox("อัปเดตสถานะ", ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"], index=["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"].index(r['status']), key=f"s_{idx}")
                            if new_status != r['status']:
                                st.session_state['reports'][idx]['status'] = new_status
                                save_data()
                                st.rerun()
                        
                        with c_act2:
                            st.write("")
                            st.write("")
                            if st.button("🗑️ ลบงานนี้", key=f"d_{idx}", type="primary"):
                                delete_report(idx)
                                st.rerun()
        else:
            st.info("ไม่พบรายการ")