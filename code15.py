import streamlit as st
import time

# --- 1. فحص المكتبات ---
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

# --- 2. إعدادات الصفحة ---
st.set_page_config(page_title="محرر الدريوش سيتي", layout="wide", page_icon="💎")

# --- 3. القائمة الجانبية ---
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

# --- 4. الدوال ---

def clean_garbage(text):
    if not text: return ""
    # قائمة التنظيف
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
            
        if img.mode != 'RGB': 
            img = img.convert('RGB')
        
        if crop:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - c_amt))))
            
        if mirror: 
            img = ImageOps.mirror(img)
        
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
    except: 
        return None

def ai_rewrite(txt, key, lang):
    try:
        genai.configure(api_key=key)
        mod = genai.GenerativeModel('gemini-2.0-flash')
        
        pmt = f"""
        **الدور:** رئيس تحرير محترف.
        **المهمة:** صياغة وترجمة النص إلى: {lang}.

        **القواعد:**
        1. **الفاصل:** ضع ###SPLIT### بين العنوان والنص.
        2. **الطول:** لا تختصر النصوص الطويلة، ووسع النصوص القصيرة.
        3. **الأسلوب:** صحفي بشري 100%.

        **النص:** {txt[:15000]}
        """
        return mod.generate_content(pmt).text
    except Exception as e: 
        return f"Error: {e}"

def wp_up_clean(ib, tit, con, url, usr, pwd):
    cred = f"{usr}:{pwd}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    mid = 0
    if ib:
        h2 = head.copy()
        h2.update({
            'Content-Disposition': 'attachment; filename=news.jpg', 
            'Content-Type': 'image/jpeg'
        })
        try:
            r = requests.post(f"{url}/wp
