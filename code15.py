import streamlit as st
import time

# --- فحص المكتبات ---
try:
    from newspaper import Article
    import requests
    import base64
    import google.generativeai as genai
    from PIL import Image, ImageEnhance, ImageOps
    import io
    import re
    import numpy as np
except ImportError as e:
    st.error(f"❌ مكتبة ناقصة: {e}")
    st.stop()

# --- 1. إعدادات الصفحة (تم التعديل هنا) ---
st.set_page_config(page_title="محرر الدريوش سيتي", layout="wide", page_icon="💎")

# --- 2. القائمة الجانبية ---
with st.sidebar:
    st.header("1. البيانات")
    api_key = st.text_input("مفتاح Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة مرور التطبيق", type="password")
    
    st.divider()
    st.header("2. المحتوى")
    langs = ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية", "الهولندية", "الألمانية"]
    target_language = st.selectbox("اللغة:", langs)
    
    st.divider()
    st.header("3. الصورة")
    crop_logo = st.checkbox("قص اللوغو", value=True)
    logo_ratio = st.slider("نسبة القص", 0.0, 0.25, 0.12, step=0.01)
    apply_mirror = st.checkbox("قلب الصورة", value=True)
    red_factor = st.slider("لمسة الأحمر", 0.0, 0.3, 0.08, step=0.01)

# --- 3. الدوال ---

def clean_garbage(text):
    """مصفاة نهائية لحذف أي كود أو رمز"""
    if not text: return ""
    junk = ["###SPLIT###", "###", "##", "**", "*", "العنوان:", "المتن:", "نص المقال:"]
    for j in junk:
        text = text.replace(j, "")
    return text.strip()

def resize_768(img):
    tw, th = 768, 432
    cw, ch = img.size
    tr, cr = tw / th, cw / ch
    if cr > tr:
        nh = th
        nw = int(nh * cr)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw) // 2
        img = img.crop((left, 0, left + tw, th))
    else:
        nw = tw
        nh = int(nw / cr)
        img = img.resize((nw, nh), Image.LANCZOS)
        top = (nh - th) // 2
        img = img.crop((0, top, tw, top + th))
    return img

def process_img(src, is_url, crop, c_amt, mirror, red):
    try:
        if is_url:
            r = requests.get(src, stream=True, timeout=10)
            img = Image.open(r.raw)
        else:
            img = Image.open(src)
        if img.mode != 'RGB': img = img.convert('RGB')
        
        if crop:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - c_amt))))
        if mirror: img = ImageOps.mirror(img)
        
        img = resize_768(img)
        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        
        if red > 0:
            color = (180, 20, 20)
            ov = Image.new('RGB', img.size, color)
            img = Image.blend(img, ov, alpha=red)
            
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        return buf.getvalue()
    except: return None

def ai_rewrite(txt, key, lang):
    try:
        genai.configure(api_key=key)
        mod = genai.GenerativeModel('gemini-2.0-flash')
        
        pmt = f"""
        **الدور:** رئيس تحرير محترف.
        **المهمة:** صياغة وترجمة النص إلى: {lang}.

        **قواعد التعامل مع الحجم:**
        1. **للنص القصير:** قم بتوسعته لمقال كامل (مقدمة، عرض، خاتمة).
        2. **للنص الطويل:** حافظ على نفس الطول والتفاصيل دون اختصار.

        **القواعد الصارمة:**
        1. **الفاصل:** ضع ###SPLIT### بين العنوان والنص.
        2. **الأسلوب:** بشري، صحفي، خالي من الكليشيهات.
        3. **العنوان:** سطر واحد جذاب بدون رموز.

        **النص:** {txt[:15000]}
        """
        return mod.generate_content(pmt).text
    except Exception as e: return f"Error: {e}"

def wp_up_clean(ib, tit, con, url, usr, pwd):
    cred = f"{usr}:{pwd}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    mid = 0
    if ib:
        h2 = head.copy()
        h2.update({'Content-Disposition': 'attachment; filename=news.jpg', 'Content-Type': 'image/jpeg'})
        try:
            r = requests.post(f"{url}/wp-json/wp/v2/media", headers=h2, data=ib)
            if r.status_code == 201: mid = r.json()['id']
        except: pass
    
    h3 = head.copy()
    h3['Content-Type'] = 'application/json'
    d = {'title': tit, 'content': con, 'status': 'draft', 'featured_media': mid}
    return requests.post(f"{url}/wp-json/wp/v2/posts", headers=h3, json=d)

def wp_up_img(ib, url, usr, pwd):
    cred = f"{usr}:{pwd}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    h2 = head.copy()
    fn = f"img-{int(time.time())}.jpg"
    h2.update({'Content-Disposition': f'attachment; filename={fn}', 'Content-Type': 'image/jpeg'})
    return requests.post(f"{url}/wp-json/wp/v2/media", headers=h2, data=ib)

# --- 4. الواجهة ---
st.title("💎 محرر الدريوش سيتي")
t1, t2, t3 = st.tabs(["🔗 رابط", "📝 يدوي", "🖼️ صورة"])
mode, l_val, f_val, t_val, i_only = None, "", None, "", None

with t1:
    l_val = st.text_input("رابط الخبر:")
    if st.button("🚀 تنفيذ (رابط)"): mode = "link"
with t2:
    f_val = st.file_uploader("الصورة", key="mi")
    t_val = st.text_area("أدخل نصاً (ولو قصيراً)", height=150)
    if st.button("🚀 تنفيذ (يدوي)"): mode = "manual"
with t3:
    ic = st.radio("المصدر:", ["ملف", "رابط"], horizontal=True)
    if ic == "ملف": i_only = st.file_uploader("الصورة", key="iof")
    else: i_only = st.text_input("الرابط:", key="iou")
    if st.button("🎨 رفع صورة فقط"): mode = "img_only"

if mode:
    if not api_key or not wp_password:
        st.error("⚠️ أدخل البيانات!")
    else:
        st.
