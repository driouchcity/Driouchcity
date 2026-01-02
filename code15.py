import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO

# --- إعدادات ووردبريس ---
WP_URL = "https://driouchcity.com/wp-json/wp/v2"
WP_USER = "ADMIN"

# استدعاء كلمة المرور من Secrets لضمان الأمان
try:
    WP_APP_PASSWORD = st.secrets["WP_PASSWORD"]
except KeyError:
    st.error("خطأ: لم يتم ضبط كلمة المرور في إعدادات Secrets.")
    st.stop()

def upload_to_wordpress(img, title, content):
    buf = BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    headers = {
        "Content-Disposition": "attachment; filename=image.png",
        "Content-Type": "image/png"
    }
    
    # رفع الصورة
    media_res = requests.post(
        f"{WP_URL}/media",
        headers=headers,
        auth=(WP_USER, WP_APP_PASSWORD),
        data=img_bytes
    )
    
    if media_res.status_code == 201:
        media_id = media_res.json()['id']
        # إنشاء المقال
        post_data = {
            "title": title,
            "content": content,
            "featured_media": media_id,
            "status": "publish"
        }
        post_res = requests.post(f"{WP_URL}/posts", auth=(WP_USER, WP_APP_PASSWORD), json=post_data)
        return post_res.status_code == 201
    return False

# --- الواجهة ---
st.set_page_config(page_title="محرر الدريوش سيتي", layout="centered")
st.title("🗞️ محرر ونشر الأخبار - DriouchCity")

source = st.radio("مصدر الصورة:", ("رفع من الجهاز", "رابط URL"))
image = None

if source == "رفع من الجهاز":
    file = st.file_uploader("اختر صورة", type=["jpg", "png", "jpeg"])
    if file: image = Image.open(file)
else:
    url = st.text_input("ضع الرابط:")
    if url:
        try:
            res = requests.get(url)
            image = Image.open(BytesIO(res.content))
        except: st.error("فشل جلب الصورة")

if image:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        sat = st.slider("الإشباع", 0.0, 2.0, 1.0)
        bright = st.slider("الإضاءة", 0.0, 2.0, 1.0)
    with col2:
        if st.button("قلب الصورة ↔️"): image = ImageOps.mirror(image)
        crop = st.checkbox("قص تلقائي")

    image = ImageEnhance.Color(image).enhance(sat)
    image = ImageEnhance.Brightness(image).enhance(bright)
    if crop:
        w, h = image.size
        image = image.crop((w*0.1, h*0.1, w*0.9, h*0.9))
    
    # السطر الذي تسبب في الخطأ تم تصحيحه هنا
    st.image(image, caption="المعاينة النهائية", use_container_width=True)

    title = st.text_input("عنوان الخبر")
    content = st.text_area("نص الخبر")

    if st.button("🚀 انشر الآن"):
        if title and content:
            with st.spinner("جاري النشر..."):
                if upload_to_wordpress(image, title, content):
                    st.success("تم النشر بنجاح!")
                else: st.error("فشل النشر")
