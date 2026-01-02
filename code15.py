import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO

# إعدادات ووردبريس
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
PASS = st.secrets["WP_PASSWORD"]

def post_to_site(img_obj, t, c):
    buf = BytesIO()
    img_obj.save(buf, format="PNG")
    # رفع الميديا
    r_img = requests.post(f"{URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=x.png","Content-Type":"image/png"},
                         auth=(USER, PASS), data=buf.getvalue())
    if r_img.status_code == 201:
        img_id = r_img.json()['id']
        # رفع المقال
        payload = {"title":t, "content":c, "featured_media":img_id, "status":"publish"}
        r_post = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return r_post.status_code == 201
    return False

# الواجهة
st.title("🗞️ محرر الدريوش سيتي")
src = st.radio("المصدر", ["جهاز", "رابط"])
img_data = None

if src == "جهاز":
    f = st.file_uploader("الصورة", type=["jpg","png","jpeg"])
    if f: img_data = Image.open(f)
else:
    u = st.text_input("الرابط")
    if u:
        try: img_data = Image.open(BytesIO(requests.get(u).content))
        except: st.error("خطأ في الرابط")

if img_data:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        s = st.slider("الألوان", 0.0, 2.0, 1.0)
        b = st.slider("الإضاءة", 0.0, 2.0, 1.0)
    with c2:
        flp = st.checkbox("قلب")
        crp = st.checkbox("قص 10%")
    
    # المعالجة
    res_img = ImageEnhance.Color(img_data).enhance(s)
    res_img = ImageEnhance.Brightness(res_img).enhance(b)
    if flp: res_img = ImageOps.mirror(res_img)
    if crp:
        w, h = res_img.size
        res_img = res_img.crop((w*0.1, h*0.1, w*0.9, h*0.9))
    
    st.image(res_img, use_container_width=True)
    title_in = st.text_input("العنوان")
    text_in = st.text_area("النص")
    
    if st.button("🚀 انشر الآن"):
        if title_in and text_in:
            if post_to_site(res_img, title_in, text_in):
                st.success("تم النشر!")
            else: st.error("خطأ في الاتصال")
