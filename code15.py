import streamlit as st
import requests
import base64
import io
import time
import random
import datetime
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article
import google.generativeai as genai
import numpy as np

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Editor V28.0 - Final Structure", layout="wide", page_icon="✅")

# --- 2. القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة المرور", type="password")
    
    st.divider()
    langs = ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية", "الهولندية", "الألمانية", "الإيطالية"]
    target_lang = st.selectbox("اللغة:", langs)
    
    st.divider()
    crop_logo = st.checkbox("قص اللوغو", value=True)
    logo_ratio = st.slider("نسبة القص", 0.0, 0.25, 0.12)
    apply_mirror = st.checkbox("قلب الصورة", value=True)
    red_factor = st.slider("لمسة الأحمر", 0.0, 0.3, 0.08)

# --- 3. الدوال ---

def clean_txt(text):
    # التنظيف من الرموز والكلمات الداخلية
    if not text: return ""
    junk = ["###SPLIT###", "###", "##", "**", "*", "العنوان:", "المتن:", "نص المقال:"]
    for x in junk:
        text = text.replace(x, "")
    # حذف الترقيم الآلي الزائد الذي سيضعه النموذج
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
    return text.strip()

def resize_768(img):
    tw, th = 768, 432
    cw, ch = img.size
    tr, cr = tw / th, cw / ch
    if cr > tr:
        nh, nw = th, int(th * cr)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw) // 2
        img = img.crop((left, 0, left + tw, th))
    else:
        nw, nh = tw, int(nw / cr)
        img = img.resize((nw, nh), Image.LANCZOS)
        top = (nh - th) // 2
        img = img.crop((0, top, tw, top + th))
    return img

def process_img(src, is_url):
    try:
        if is_url:
            r = requests.get(src, stream=True, timeout=10)
            img = Image.open(r.raw)
        else:
            img = Image.open(src)
            
        if img.mode != 'RGB': img = img.convert('RGB')
        
        if crop_logo:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - logo_ratio))))
            
        if apply_mirror: img = ImageOps.mirror(img)
        
        img = resize_768(img)
        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        
        if red_factor > 0:
            ov = Image.new('RGB', img.size, (180, 20, 20))
            img = Image.blend(img, ov, alpha=red_factor)
            
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        return buf.getvalue()
        
    except Exception as e:
        return None

def ai_gen(txt):
    try:
        genai.configure(api_key=api_key)
        mod = genai.GenerativeModel('gemini-2.0-flash')
        
        # --- التعليمات النهائية: إجبار الترقيم والفصل ---
        pmt = f"""
        **الدور:** صحفي محترف ونزيه. أسلوب بشري وطبيعي.
        المهمة: كتابة تقرير صحفي شامل باللغة {target_lang} بناءً على النص أدناه.

        **القواعد الصارمة:**
        1. **الهيكل:** يجب أن يتكون المقال من 5 فقرات محددة.
        2. **الترقيم (مهم جداً):** قم بترقيم الفقرات من 1 إلى 5.
        3. **الفاصل:** ضع ###SPLIT### بين العنوان وبداية الفقرة الأولى.
        4. **الطول:** فقرات متوسطة الحجم (3-4 أسطر). لا حشو أو مبالغة.

        **النص:** {txt[:20000]}
        """
        raw_output = mod.generate_content(pmt).text
        
        # معالجة الناتج: حذف الترقيم والفاصل
        if "###SPLIT###" in raw_output:
            title_part, body_part = raw_output.split("###SPLIT###", 1)
        else:
            title_part, body_part = raw_output.split('\n', 1)
        
        # تنظيف الفقرات من الأرقام وإضافة فاصل بصري
        body_cleaned = re.sub(r'^\s*\d+\.\s*', '', body_part, flags=re.MULTILINE)
        
        # إعادة تقسيم النص بفاصل سطرين لضمان ظهور الفقرات
        body_paragraphs = body_cleaned.split('\n')
        
        # تصفية الفراغات والسطور القصيرة جداً
        final_body = "\n\n".join([p.strip() for p in body_paragraphs if len(p.strip()) > 10])
        
        # إرجاع النتيجة النهائية
        return f"{title_part}\n###SPLIT###\n{final_body}"
        
    except Exception as e: return f"Error: {e}"

def wp_send(ib, tit, con):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    
    mid = 0
    if ib:
        filename = generate_filename()
        h2 = head.copy()
        h2.update({'Content-Disposition': f'attachment; filename={filename}', 'Content-Type': 'image/jpeg'})
        try:
            r = requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)
            if r.status_code == 201: mid = r.json()['id']
        except: pass
    
    h3 = head.copy()
    h3['Content-Type'] = 'application/json'
    d = {'title': tit, 'content': con, 'status': 'draft', 'featured_media': mid}
    return requests.post(f"{wp_url}/wp-json/wp/v2/posts", headers=h3, json=d)

def generate_filename():
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"driouchcity-{today_str}-{random_num}.jpg"

# دالة رفع الصورة فقط (للتذييل)
def wp_img_only(ib):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    fn = generate_filename()
    h2 = head.copy()
    h2.update({'Content-Disposition': f'attachment; filename={fn}', 'Content-Type': 'image/jpeg'})
    return requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)

# --- 4. الواجهة ---
st.title("💎 محرر الدريوش سيتي (V28)")
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
    ic = st.radio("المصدر", ["ملف", "رابط"], horizontal=True)
    if ic == "ملف": i_only = st.file_uploader("صورة", key="3")
    else: i_only = st.text_input("رابط")
    if st.button("🎨 رفع صورة فقط"): mode = "img"

# --- 5. التنفيذ ---
if mode:
    if not api_key or not wp_password:
        st.error("⚠️ أدخل البيانات!")
    else:
        st.divider()
        with st.spinner("جاري العمل..."):
            tt, ti, iu = "", None, False
            try:
                if mode == "link":
                    a = Article(l_val)
                    a.download(); a.parse()
                    tt, ti, iu = a.text, a.top_image, True
                elif mode == "manual":
                    tt, ti = t_val, f_val
                
                # مسار الصورة فقط (تم حذفه من التتبع لأنه مسار فرعي لا يتأثر بالخطأ)
                if mode == "img":
                    if not i_only: st.error("لا توجد صورة")
                    else:
                        iu = isinstance(i_only, str)
                        fi = process_img(i_only, iu)
                        if fi:
