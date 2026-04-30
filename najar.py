import streamlit as st
import sqlite3
from fpdf import FPDF
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- إعدادات الصفحة ---
st.set_page_config(page_title="مساعد النجار المحترف", layout="wide")

# --- 1. إعداد قاعدة البيانات ---
conn = sqlite3.connect('carpentry_data.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS projects 
             (id INTEGER PRIMARY KEY, client_name TEXT, category TEXT, cut_list TEXT)''')
conn.commit()

# --- 2. وظائف مساعدة ---
def generate_pdf(client_name, cut_list_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', size=16)
    pdf.cell(200, 10, txt=f"Client: {client_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for item in cut_list_data:
        # تحويل بسيط للإنجليزية لضمان ظهور النص في PDF الأساسي
        eng_text = item.replace("درج", "Drawer").replace("قطعة", "pcs").replace("جنب", "Side")
        pdf.cell(200, 10, txt=eng_text, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. القائمة الجانبية ---
st.sidebar.title("🛠️ لوحة التحكم")
category = st.sidebar.selectbox("اختر القسم:", ["الرئيسية", "المطابخ 🍳", "الأدراج 🗄️", "الدواليب 👕"])
client_name = st.sidebar.text_input("اسم العميل:", value="عميل جديد")
thickness = st.sidebar.number_input("تخانة الخشب (مم):", value=18.0) / 10
color_choice = st.sidebar.color_picker("اختر لون الخشب للكروكي:", "#DEB887")

# --- 4. الأقسام ---

# --- قسم الرئيسية ---
if category == "الرئيسية":
    st.title("مرحباً بك في تطبيق النجارة الذكي")
    st.write("هذا التطبيق يساعدك في حساب مقاسات التقطيع وتصميم الوحدات وحفظها.")
    if st.checkbox("عرض السجلات المحفوظة"):
        df = pd.read_sql_query("SELECT * FROM projects", conn)
        st.dataframe(df, use_container_width=True)

# --- قسم المطابخ ---
elif category == "المطابخ 🍳":
    st.title("تصميم وحدات المطبخ")
    c1, c2, c3 = st.columns(3)
    w = c1.number_input("العرض (سم)", value=60.0)
    h = c2.number_input("الارتفاع (سم)", value=72.0)
    d = c3.number_input("العمق (سم)", value=55.0)
    
    inner_w = w - (2 * thickness)
    st.subheader("📋 قائمة تقطيع الوحدة:")
    results = [
        f"الجوانب (2 قطعة): {h}x{d}",
        f"القاعدة والسقف (2 قطعة): {inner_w:.1f}x{d}",
        f"الظهر (1 قطعة): {h}x{inner_w:.1f}"
    ]
    for res in results: st.write(f"- {res}")
    
    if st.button("حفظ المطبخ"):
        c.execute("INSERT INTO projects (client_name, category, cut_list) VALUES (?,?,?)",
                  (client_name, "Kitchen", " | ".join(results)))
        conn.commit()
        st.success("تم الحفظ!")

# --- قسم الأدراج ---
elif category == "الأدراج 🗄️":
    st.title("توزيع وحسابات الأدراج")
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        total_w = st.number_input("عرض الفتحة (سم)", value=60.0)
        total_h = st.number_input("ارتفاع الفتحة (سم)", value=80.0)
        num_d = st.number_input("عدد الأدراج", min_value=1, value=3)
        slide_gap = st.number_input("خصم المجرى كلي (سم)", value=2.6)
        edge_gap = 0.3 # فاصل 3 مم
        
        # الحسابات
        f_h = (total_h - (edge_gap * (num_d + 1))) / num_d
        f_w = total_w - (edge_gap * 2)
        
        st.info(f"مقاس الوجه: {f_h:.1f}x{f_w:.1f} سم")
        
    with col_b:
        # الرسم الكروكي
        fig, ax = plt.subplots()
        ax.add_patch(patches.Rectangle((0,0), total_w, total_h, fill=False, lw=2))
        curr_y = edge_gap
        for i in range(int(num_d)):
            ax.add_patch(patches.Rectangle((edge_gap, curr_y), f_w, f_h, facecolor=color_choice, edgecolor='black'))
            ax.text(total_w/2, curr_y + f_h/2, f"Drawer {i+1}", ha='center')
            curr_y += f_h + edge_gap
        plt.axis('off')
        st.pyplot(fig)

    # توليد التقطيع
    box_list = [f"وجه خارجي (عدد {int(num_d)}): {f_h:.1f}x{f_w:.1f}"]
    inner_box_w = (total_w - slide_gap) - (2 * thickness)
    box_list.append(f"ظهر ووجه داخلي للصناديق: {inner_box_w:.1f}x{f_h-4:.1f}")
    
    if st.button("تحميل PDF"):
        pdf_bytes = generate_pdf(client_name, box_list)
        st.download_button("Download PDF", pdf_bytes, f"{client_name}.pdf")

# --- قسم الدواليب ---
elif category == "الدواليب 👕":
    st.title("تصميم الدولاب")
    dw = st.number_input("عرض الدولاب", value=120.0)
    dh = st.number_input("ارتفاع الدولاب", value=200.0)
    sh_count = st.slider("عدد الأرفف", 0, 10, 4)
    
    st.subheader("📋 تقطيع الدولاب:")
    wardrobe_list = [
        f"جوانب طويلة (2 قطعة): {dh}x60",
        f"أرفف (عدد {sh_count}): {dw-(2*thickness):.1f}x58"
    ]
    for item in wardrobe_list: st.write(f"- {item}")
    
    # رسم مبسط
    fig2, ax2 = plt.subplots()
    ax2.add_patch(patches.Rectangle((0,0), dw, dh, fill=False, lw=3))
    for i in range(1, sh_count + 1):
        y = (dh/(sh_count+1)) * i
        ax2.plot([0, dw], [y, y], color='brown')
    st.pyplot(fig2)

