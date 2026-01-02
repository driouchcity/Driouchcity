import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO

# --- إعدادات ووردبريس ---
WP_URL = "https://driouchcity.com/wp-json/wp/v2"
WP_USER = "ADMIN"

# استدعاء كلمة المرور من Secrets لضمان الأمان
if "WP_PASSWORD" in st.secrets:
    WP_APP_PASSWORD = st.secrets["WP_PASSWORD"]
else:
    st.error("خطأ: لم يتم ضبط WP_PASSWORD في إعدادات Secrets.")
    st.stop()

def upload_to_wordpress(img, title, content):
    buf = BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    headers = {
        "Content-Disposition": "attachment; filename=news_image.png",
        "Content-Type": "image/png"
    }
    
    # 1. رفع الصورة
    media_res = requests.post(
        f"{WP_URL}/media",
        headers=headers,
        auth=(WP_USER, WP_APP_PASSWORD),
        data=img_bytes
    )
    
    if media_res.status_code == 201:
        media_id = media_res.json()['id']
        # 2. إنشاء المقال
        post_data = {
            "title": title,
            "content": content,
            "featured_media": media_id,
            "status": "publish"
        }
        post_res = requests.post(f"{WP_URL}/posts", auth=(WP_USER, WP_APP_PASSWORD), json=post_data)
        return post_res.status_code == 201
    return False

# --- الواجهة الخاصة بالتطبيق ---
st.set_page_config(page_title="محرر الدريوش سيتي", layout="centered")
st.title("🎨 محرر ونشر الصور - DriouchCity")

source = st.radio("اختر مصدر الصورة:", ("رفع من الجهاز", "رابط URL"))
input_image = None

if source == "رفع من الجهاز":
    file = st.file_uploader("اختر صورة...", type=["jpg", "png", "jpeg"])
    if file:
        input_image = Image.open(file)
else:
    url = st.text_input("أدخل رابط الصورة:")
    if url:
        try:
            res = requests.get(url)
            input_image = Image.open(BytesIO(res.content))
        except:
            st.error("فشل في جلب الصورة من الرابط")

if input_image:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        sat = st.slider("إشباع الألوان", 0.0, 2.0, 1.0)
        bright = st.slider("السطوع", 0.0, 2.0, 1.0)
    
    with col2:
        flip = st.checkbox("قلب الصورة ↔️")
        crop = st.checkbox("قص الحواف (10%)")

    # تطبيق التعديلات
    processed_img = ImageEnhance.Color(input_image).enhance(sat)
    processed_img = ImageEnhance.Brightness(processed_img).enhance(bright)
    
    if flip:
        processed_img = ImageOps.mirror(processed_img)
    
    if crop:
        w, h = processed_img.size
        processed_img = processed_img.crop((w*0.1, h*0.1, w*0.9, h*0.9))

    st.image(processed_img, caption="المعاينة قبل النشر", use_container_width=True)

    st.divider()
    post_title = st.text_input("عنوان الخبر")
    post_content = st.text_area("نص الخبر")

    if st.button("🚀 انشر الآن على الموقع"):
        if post_title and post_content:
            with st.spinner("جاري الرفع والنشر..."):
                if upload_to_wordpress(processed_img, post_title, post_content):
                    st.success("🎉 تم النشر بنجاح على DriouchCity.com")
                else:
                    st.error("فشل النشر. تأكد من إعدادات الـ Secrets.")
        else:
            st.warning("يرجى ملء العنوان والنص")
