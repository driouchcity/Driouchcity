import streamlit as st
import requests
import base64
import io
import time
import random
import datetime
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article
from openai import OpenAI  # تم التغيير هنا
import numpy as np

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Editor V37.0 - OpenAI", layout="wide", page_icon="✅")

# --- 2. القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    # تغيير المسمى ليصبح OpenAI API Key
    api_key = st.text_input("مفتاح OpenAI API", type="password") 
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

# [دوال clean_txt و resize_768 و process_img و generate_filename تبقى كما هي بدون تغيير]
def clean_txt(text):
    if not text: return ""
    junk = ["###SPLIT###", "###", "##", "**", "*", "العنوان:", "المتن:", "نص المقال:", "عنوان رئيسي", "المقدمة", "جسم المقال", "الخاتمة", "الفقرة"]
    for x in junk:
        text = text.replace(x, "")
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

# --- الدالة المحدثة لـ OpenAI ---
def ai_gen(txt):
    try:
        # إعداد عميل OpenAI
        client = OpenAI(api_key=api_key)
        
        pmt = (
            f"**ROLE:** Senior Journalist. **TASK:** Rewrite and translate the text below into {target_lang}. "
            "**RULES:** Produce a complete, neutral, objective news report. "
            "1. **STRUCTURE:** The article MUST be composed of exactly 5 distinct paragraphs (Intro, 3 Body, Conclusion). "
            "2. **OUTPUT FORMAT:** Strictly use the following labels for separation:\nTITLE_START\n[Your title here]\nBODY_START\n[Your 5 paragraphs here]\n"
            "3. **STYLE:** Highly objective. Avoid exaggeration, emotion, or advice. Focus only on facts. "
            f"TEXT: {txt[:20000]}"
        )

        # استدعاء نموذج GPT-4o (يمكنك تغييره لـ gpt-3.5-turbo)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional news editor."},
                {"role": "user", "content": pmt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e: 
        return f"Error: {e}"

# [بقية الدوال wp_send و wp_img_only والواجهة تبقى كما هي]
def generate_filename():
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"driouchcity-{today_str}-{random_num}.jpg"

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
            api_media = f"{wp_url}/wp-json/wp/v2/media"
            r = requests.post(api_media, headers=h2, data=ib)
            if r.status_code == 201: mid = r.json()['id']
        except: pass
    h3 = head.copy()
    h3['Content-Type'] = 'application/json'
    api_posts = f"{wp_url}/wp-json/wp/v2/posts"
    d = {'title': tit, 'content': con, 'status': 'draft', 'featured_media': mid}
    return requests.post(api_posts, headers=h3, json=d)

def wp_img_only(ib):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    fn = generate_filename()
    h2 = head.copy()
    h2.update({'Content-Disposition': f'attachment; filename={fn}', 'Content-Type': 'image/jpeg'})
    return requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)

# --- 4. الواجهة ---
st.title("💎 محرر الدريوش سيتي (V37 - OpenAI)")
t1, t2, t3 = st.tabs(["🔗 رابط", "📝 نص", "🖼️ صورة"])

mode, l_val, f_val, t_val, i_only = None, "", None, "", None

with t1:
    l_val = st.text_input("رابط الخبر")
    if st.button("🚀 تنفيذ الرابط"): mode = "link"
with t2:
    f_val = st.file_uploader("صورة", key="2")
    t_val = st.text_area("نص", height=200)
    if st.button("🚀 تنفيذ النص"): mode = "manual"
with t3:
    ic = st.radio("المصدر", ["ملف", "رابط"])
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
                
                if mode == "img":
                    if not i_only: st.error("لا توجد صورة")
                    else:
                        iu = isinstance(i_only, str)
                        fi = process_img(i_only, iu)
                        if fi:
                            st.image(fi, width=400)
                            r = wp_img_only(fi)
                            if r.status_code == 201: st.success(f"تم الرفع! {r.json()['source_url']}")
                            else: st.error(r.text)
                    st.stop() 

                fi = None
                if ti:
                    fi = process_img(ti, iu)
                    if fi: st.image(fi, width=400)
                
                rai = ai_gen(tt)
                if "Error" in rai: st.error(rai)
                else:
                    raw_output = rai
                    if "TITLE_START" in raw_output and "BODY_START" in raw_output:
                        title_part = raw_output.split("TITLE_START")[1].split("BODY_START")[0].strip()
                        body_part = raw_output.split("BODY_START")[1].strip()
                        tit = clean_txt(title_part)
                        bod = clean_txt(body_part)
                        bod = bod.replace('\n', '\n\n')
                    else:
                        tit = clean_txt(raw_output.split('\n')[0])
                        bod = clean_txt("\n".join(raw_output.split('\n')[1:]))

                    st.success(f"📌 {tit}")
                    st.markdown(bod)
                    
                    r = wp_send(fi, tit, bod)
                    if r.status_code == 201: 
                        st.balloons()
                        st.success(f"تم النشر! [رابط المعاينة]({r.json()['link']})")
                    else: st.error(r.text)
            except Exception as e:
                st.error(f"Error: {e}")
