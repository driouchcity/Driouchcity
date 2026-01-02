import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO

# --- البيانات الأساسية ---
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
PASS = st.secrets["WP_PASSWORD"]

def post_to_wp(img, t, c):
    buf = BytesIO()
    img.save(buf, format="PNG")
    # رفع الصورة
    res_m = requests.post(f"{URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=x.png","Content-Type":"image/png"},
                         auth=(USER, PASS), data=buf.getvalue())
    if res_m.status_code == 201:
        mid = res_m.json()['id']
        # نشر المقال
        payload = {"title":t, "content":c, "featured_media":mid, "status":"publish"}
        res_p = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return res_p.status_code == 201
    return False

# --- الواجهة ---
st.title("🗞️ ناشر الدريوش سيتي")
src = st.radio("المصدر", ["جهاز", "رابط"])
raw = None

if src == "جهاز":
    f = st.file_uploader("الصورة", type=["jpg","png","jpeg"])
    if f: raw = Image.open(f)
else:
    u = st.text_input("الرابط")
    if u:
        try: raw = Image.open(BytesIO(requests.get(u).content))
        except: st.error("خطأ في الرابط")

if raw:
    st.divider()
    s = st.slider("الألوان", 0.0, 2.0, 1.0)
    b = st.slider("الإضاءة", 0.0, 2.0, 1.0)
    if st.button("قلب الصورة ↔️"): raw = ImageOps.mirror(raw)
    
    # المعالجة
    img = ImageEnhance.Color(raw).enhance(s)
    img = ImageEnhance.Brightness(img).enhance(b)
    
    st.image(img, use_container_width=True)
    t_in = st.text_input("العنوان")
    c_in = st.text_area("النص")
    
    if st.button("🚀 انشر الآن"):
        if t_in and c_in:
            if post_to_wp(img, t_in, c_in):
                st.success("✅ تم النشر بنجاح!")
            else: st.error("❌ فشل النشر - تحقق من كلمة المرور")
