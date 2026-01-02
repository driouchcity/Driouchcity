import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO

# --- إعدادات ووردبريس ---
WP_URL = "https://driouchcity.com/wp-json/wp/v2"
WP_USER = "ADMIN"
WP_APP_PASSWORD = st.secrets["WP_PASSWORD"]

def publish_to_wp(img, title, content):
    # تحويل الصورة لبيانات رقمية
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    # 1. رفع الصورة
    media_res = requests.post(
        f"{WP_URL}/media",
        headers={"Content-Disposition": "attachment; filename=img.png", "Content-Type": "image/png"},
        auth=(WP_USER, WP_APP_PASSWORD),
        data=buf.getvalue()
    )
    
    if media_res.status_code == 201:
        media_id = media_res.json()['id']
        # 2. إنشاء المقال
        data = {"title": title, "content": content, "featured_media": media_id, "status": "publish"}
        post_res = requests.post(f"{WP_URL}/posts", auth=(WP_USER, WP_APP_PASSWORD), json=data)
        return post_res.status_code == 201
    return False

# --- الواجهة ---
st.title("🗞️ ناشر الدريوش سيتي")

source = st.radio("مصدر الصورة:", ["جهازي", "رابط"])
raw_img = None

if source == "جهازي":
    file = st.file_uploader("اختر صورة", type=["jpg", "jpeg", "png"])
    if file: raw_img = Image.open(file)
else:
    url = st.text_input("ضع الرابط")
    if url:
        try:
            res = requests.get(url)
            raw_img = Image.open(BytesIO(res.content))
        except: st.error("رابط غير صحيح")

if raw_img:
    st.subheader("🛠️ التعديلات")
    col1, col2 = st.columns(2)
    with col1:
        sat = st.slider("الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
    with col2:
        flip = st.checkbox("قلب الصورة")
        crop = st.checkbox("قص الحواف")

    # تطبيق التعديلات
    proc_img = ImageEnhance.Color(raw_img).enhance(sat)
    proc_img = ImageEnhance.Brightness(proc_img).enhance(bri)
    if flip: proc_img = ImageOps.mirror(proc_img)
    if crop:
        w, h = proc_img.size
        proc_img = proc_img.crop((w*0.1, h*0.1, w*0.9, h*0.9))

    st.image(proc_img, use_container_width=True)

    title = st.text_input("العنوان")
    text = st.text_area("النص")

    if st.button("🚀 انشر الآن"):
        if title and text:
            if publish_to_wp(proc_img, title, text):
                st.success("تم النشر بنجاح!")
            else: st.error("خطأ في النشر")
        else: st.warning("اكتب العنوان والنص أولاً")
