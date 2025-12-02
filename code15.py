import streamlit as st
import requests
import base64
import io
import time
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article
import google.generativeai as genai

# --- إعداد الصفحة ---
st.set_page_config(page_title="Editor V22 (Final)", layout="wide", page_icon="📰")

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة المرور", type="password")
    st.divider()
    lang = st.selectbox("اللغة", ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية", "الهولندية", "الألمانية"])
    
    st.divider()
    st.caption("أدوات الصورة")
    crop_logo = st.checkbox("قص اللوغو", True)
    logo_r = st.slider("نسبة القص", 0.0, 0.25, 0.12)
    mirror = st.checkbox("قلب الصورة", True)
    red_val = st.slider("لمسة حمراء", 0.0, 0.3, 0.08)

# --- دوال المعالجة ---

def clean_txt(text):
    if not text: return ""
    # تنظيف العبارات الزائدة
    for x in ["###SPLIT###", "###", "**", "العنوان:", "المتن:", "نص المقال:"]:
        text = text.replace(x, "")
    return text.strip()

def proc_img(src, is_url):
    try:
        if is_url:
            r = requests.get(src, stream=True, timeout=10)
            img = Image.open(r.raw)
        else:
            img = Image.open(src)
            
        if img.mode != 'RGB': img = img.convert('RGB')
        
        # 1. قص اللوغو
        if crop_logo:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - logo_r))))
            
        # 2. القلب
        if mirror: img = ImageOps.mirror(img)
        
        # 3. الأبعاد 768x432 (Fit & Crop)
        target_w, target_h = 768, 432
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

        # 4. التأثيرات
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
        
        # --- البرومبت "الصحفي الباني" (Journalistic Builder) ---
        p = f"""
        الدور: صحفي محترف في جريدة دولية.
        المهمة: كتابة "تقرير صحفي شامل" (Comprehensive Report) باللغة {lang} استناداً إلى المعلومات الواردة أدناه.

        التعليمات الصارمة جداً:
        1. **لا تترجم سطراً بسطر:** اقرأ النص بالكامل، افهمه، ثم أعد صياغته بأسلوبك الصحفي الخاص (Narrative Flow).
        2. **الهيكلة (بناء المقال):**
           - **العنوان:** جذاب وشامل (بدون أي مقدمات).
           - **الفاصل:** ضع ###SPLIT###
           - **المقدمة (Lead):** فقرة قوية تجيب عن (من، ماذا، أين، متى).
           - **جسم التقرير:** تفاصيل الحدث موزعة على **4 إلى 6 فقرات متماسكة**. استخدم أدوات الربط (وفي هذا السياق، ومن جانب آخر، كما أضاف...).
           - **الخاتمة:** خلاصة أو سياق عام.
        3. **الحجم:** يجب أن يكون المقال طويلاً ومفصلاً (لا تختصر المعلومات).
        4. **الأسلوب:** لغة صحفية رصينة، خالية من التكرار وركاكة الترجمة الآلية.

        النص المصدري:
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
        h2 = head.copy()
        h2.update({'Content-Disposition': 'attachment; filename=news.jpg', 'Content-Type': 'image/jpeg'})
        try:
            r = requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)
            if r.status_code == 201: mid = r.json()['id']
        except: pass
        
    h3 = head.copy()
    h3['Content-Type'] = 'application/json'
    d = {'title': tit, 'content': con, 'status': 'draft', 'featured_media': mid}
    return requests.post(f"{wp_url}/wp-json/wp/v2/posts", headers=h3, json=d)

def wp_img_only(ib):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    h2 = head.copy()
    h2.update({'Content-Disposition': f'attachment; filename=img-{int(time.time())}.jpg', 'Content-Type': 'image/jpeg'})
    return requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)

# --- الواجهة ---
st.title("💎 محرر الدريوش سيتي (V22)")
t1, t2, t3 = st.tabs(["🔗 رابط", "📝 نص", "🖼️ صورة"])

mode, l_val, f_val, t_val, i_only = None, "", None, "", None

with t1:
    l_val = st.text_input("رابط الخبر")
    if st.button("🚀 تنفيذ الرابط"): mode = "link"
with t2:
    f_val = st.file_uploader("صورة", key="2")
    t_val = st.text_area("النص", height=200)
    if st.button("🚀 تنفيذ النص"): mode = "manual"
with t3:
    ic = st.radio("المصدر", ["ملف", "رابط"])
    if ic == "ملف": i_only = st.file_uploader("صورة", key="3")
    else: i_only = st.text_input("
