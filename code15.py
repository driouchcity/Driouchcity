import streamlit as st
import time
import requests
import base64
import io
import re
import numpy as np
from newspaper import Article
import google.generativeai as genai
from PIL import Image, ImageEnhance, ImageOps

# --- 1. إعدادات الصفحة (أول سطر إجباري) ---
st.set_page_config(page_title="محرر الدريوش 18", layout="wide", page_icon="🔥")

# --- 2. تهيئة الذاكرة (لحل مشكلة الشاشة البيضاء) ---
if 'result_title' not in st.session_state:
    st.session_state.result_title = ""
if 'result_body' not in st.session_state:
    st.session_state.result_body = ""
if 'result_image' not in st.session_state:
    st.session_state.result_image = None
if 'upload_status' not in st.session_state:
    st.session_state.upload_status = ""

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة مرور التطبيق", type="password")
    
    st.divider()
    langs = ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية", "الهولندية", "الألمانية"]
    target_lang = st.selectbox("اللغة:", langs)
    
    st.divider()
    crop_logo = st.checkbox("قص اللوغو", value=True)
    logo_ratio = st.slider("نسبة القص", 0.0, 0.25, 0.12)
    apply_mirror = st.checkbox("قلب الصورة", value=True)
    red_factor = st.slider("لمسة الأحمر", 0.0, 0.3, 0.08)

# --- 4. المحرك (الدوال) ---

def clean_text(text):
    if not text: return ""
    junk = ["###SPLIT###", "###", "##", "**", "*", "العنوان:", "المتن:"]
    for j in junk:
        text = text.replace(j, "")
    return text.strip()

def process_img(src, is_url):
    try:
        if is_url:
            r = requests.get(src, stream=True, timeout=10)
            img = Image.open(r.raw)
        else:
            img = Image.open(src)
            
        if img.mode != 'RGB': 
            img = img.convert('RGB')
        
        # 1. قص اللوغو
        if crop_logo:
            w, h = img.size
            cut = int(h * (1 - logo_ratio))
            img = img.crop((0, 0, w, cut))
            
        # 2. قلب الصورة
        if apply_mirror: 
            img = ImageOps.mirror(img)
        
        # 3. الأبعاد 768x432
        target_w, target_h = 768, 432
        # تغيير الحجم مع الحفاظ على النسبة (Cover)
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h
        
        if img_ratio > target_ratio:
            new_h = target_h
            new_w = int(new_h * img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - target_w) // 2
            img = img.crop((left, 0, left + target_w, target_h))
        else:
            new_w = target_w
            new_h = int(new_w / img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            top = (new_h - target_h) // 2
            img = img.crop((0, top, target_w, top + target_h))

        # 4. الألوان
        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        
        # 5. الأحمر
        if red_factor > 0:
            ov = Image.new('RGB', img.size, (180, 20, 20))
            img = Image.blend(img, ov, alpha=red_factor)
            
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        return buf.getvalue()
    except Exception as e:
        st.error(f"خطأ الصورة: {e}")
        return None

def ai_work(txt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        **الدور:** رئيس تحرير.
        **المهمة:** صياغة وترجمة إلى {target_lang}.
        **القواعد:**
        1. افصل بين العنوان والمقال بـ ###SPLIT###
        2. اكتب 4 فقرات على الأقل.
        3. أسلوب بشري 100%.
        
        **النص:** {txt[:15000]}
        """
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

def upload_wp(img_bytes, tit, con):
    try:
        cred = f"{wp_user}:{wp_password}"
        token = base64.b64encode(cred.encode()).decode('utf-8')
        head = {'Authorization': f'Basic {token}'}
        
        # رفع الصورة
        mid = 0
        if img_bytes:
            h2 = head.copy()
            h2['Content-Disposition'] = 'attachment; filename=news.jpg'
            h2['Content-Type'] = 'image/jpeg'
            api_m = f"{wp_url}/wp-json/wp/v2/media"
            r = requests.post(api_m, headers=h2, data=img_bytes)
            if r.status_code == 201: mid = r.json()['id']
            
        # رفع المقال
        h3 = head.copy()
        h3['Content-Type'] = 'application/json'
        d = {'title': tit, 'content': con, 'status': 'draft', 'featured_media': mid}
        api_p = f"{wp_url}/wp-json/wp/v2/posts"
        
        r2 = requests.post(api_p, headers=h3, json=d)
        if r2.status_code == 201:
            link = r2.json()['link']
            return f"✅ تم النشر! [رابط المعاينة]({link})"
        else:
            return f"❌ خطأ النشر: {r2.text}"
    except Exception as e:
        return f"خطأ اتصال: {e}"

# --- 5. الواجهة الرئيسية ---
st.title("📰 محرر الدريوش سيتي (النسخة الثابتة)")

tab1, tab2 = st.tabs(["🔗 رابط خبر", "📝 رفع يدوي"])

# متغيرات التشغيل
start_run = False
input_text = ""
input_img = None
is_url_mode = False

with tab1:
    url_val = st.text_input("رابط الخبر:")
    if st.button("🚀 معالجة الرابط"):
        start_run = True
        is_url_mode = True

with tab2:
    f_val = st.file_uploader("الصورة")
    t_val = st.text_area("النص")
    if st.button("🚀 معالجة اليدوي"):
        start_run = True
        is_url_mode = False
        input_text = t_val
        input_img = f_val

# --- 6. منطق التشغيل (State Machine) ---
if start_run:
    if not api_key or not wp_password:
        st.error("⚠️ أدخل البيانات في القائمة الجانبية!")
    else:
        status = st.status("جاري العمل... ⏳", expanded=True)
        try:
            # 1. الجلب
            status.write("📥 جلب البيانات...")
            if is_url_mode:
                art = Article(url_val)
                art.download()
                art.parse()
                input_text = art.text
                input_img = art.top_image # رابط
            
            # 2. الصورة
            status.write("🎨 معالجة الصورة...")
            final_img = process_img(input_img, is_url_mode)
            st.session_state.result_image = final_img
            
            # 3. النص
            status.write("✍️ الذكاء الاصطناعي...")
            raw_ai = ai_work(input_text)
            
            if "Error" in raw_ai:
                st.error(raw_ai)
            else:
                if "###SPLIT###" in raw_ai:
                    parts = raw_ai.split("###SPLIT###")
                    t, b = parts[0], parts[1]
                else:
                    lines = raw_ai.split('\n')
                    t = lines[0]
                    b = "\n".join(lines[1:])
                
                st.session_state.result_title = clean_text(t)
                st.session_state.result_body = clean_text(b)
                
                # 4. النشر
                status.write("🚀 الرفع...")
                res_msg = upload_wp(final_img, st.session_state.result_title, st.session_state.result_body)
                st.session_state.upload_status = res_msg
                
                status.update(label="تمت العملية!", state="complete", expanded=False)

        except Exception as e:
            st.error(f"
