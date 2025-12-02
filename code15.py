import streamlit as st
import requests
import base64
import io
import time
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article
import google.generativeai as genai

st.set_page_config(page_title="Editor V23", layout="wide", page_icon="📰")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة المرور", type="password")
    st.divider()
    lang = st.selectbox("اللغة", ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية", "الهولندية", "الألمانية"])
    crop_logo = st.checkbox("قص اللوغو", True)
    logo_r = st.slider("نسبة القص", 0.0, 0.25, 0.12)
    mirror = st.checkbox("قلب الصورة", True)
    red_val = st.slider("لمسة حمراء", 0.0, 0.3, 0.08)

def clean_txt(text):
    if not text: return ""
    for x in ["###SPLIT###", "###", "**", "العنوان:", "المتن:", "نص المقال:"]:
        text = text.replace(x, "")
    return text.strip()

def proc_img(src, is_url):
    try:
        if is_url:
            img = Image.open(requests.get(src, stream=True).raw)
        else:
            img = Image.open(src)
        if img.mode != 'RGB': img = img.convert('RGB')
        if crop_logo:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - logo_r))))
        if mirror: img = ImageOps.mirror(img)
        
        tw, th = 768, 432
        cw, ch = img.size
        tr, cr = tw/th, cw/ch
        if cr > tr:
            nh, nw = th, int(th * cr)
            img = img.resize((nw, nh), Image.LANCZOS)
            img = img.crop(((nw-tw)//2, 0, (nw-tw)//2 + tw, th))
        else:
            nw, nh = tw, int(tw / cr)
            img = img.resize((nw, nh), Image.LANCZOS)
            img = img.crop((0, (nh-th)//2, tw, (nh-th)//2 + th))

        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        if red_val > 0:
            ov = Image.new('RGB', img.size, (180, 20, 20))
            img = Image.blend(img, ov, alpha=red_val)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        return buf.getvalue()
    except: return None

def ai_gen(txt):
    try:
        genai.configure(api_key=api_key)
        mod = genai.GenerativeModel('gemini-2.0-flash')
        p = f"""
        الدور: صحفي محترف. المهمة: إعادة صياغة شاملة (Reportage) للنص أدناه إلى اللغة {lang}.
        القواعد الصارمة:
        1. الهيكل: عنوان جذاب، يليه الرمز ###SPLIT###، يليه جسم المقال.
        2. الأسلوب: تقرير صحفي متكامل (مقدمة، عرض، خاتمة).
        3. الفقرات: قسم النص إلى 4 فقرات على الأقل. لا تكتب كتلة واحدة.
        4. الحجم: حافظ على نفس كمية المعلومات والتفاصيل (لا تلخص).
        5. تجنب الترجمة الحرفية، أعد بناء الجمل بأسلوب صحفي.
        النص الأصلي:
        {txt[:20000]}
        """
        return mod.generate_content(p).text
    except Exception as e: return f"Error: {e}"

def wp_send(ib, tit, con):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    mid = 0
    if ib:
        h2 = head.copy
