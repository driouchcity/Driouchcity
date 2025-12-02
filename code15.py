import streamlit as st
import requests
import base64
import io
import time
import datetime # جديد
import random # جديد
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article
import google.generativeai as genai

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="محرر الدريوش سيتي", layout="wide", page_icon="💎")

# --- 2. تهيئة الذاكرة (لتجنب الشاشة البيضاء) ---
if 'res_tit' not in st.session_state: st.session_state.res_tit = ""
if 'res_bod' not in st.session_state: st.session_state.res_bod = ""
if 'res_img' not in st.session_state: st.session_state.res_img = None
if 'res_msg' not in st.session_state: st.session_state.res_msg = ""

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة المرور", type="password")
    
    st.divider()
    st.header("🌍 اللغة")
    langs = ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية", "الهولندية", "الألمانية", "الإيطالية"]
    target_lang = st.selectbox("اختر لغة المقال:", langs)
    
    st.divider()
    st.header("🎨 الصورة")
    crop_logo = st.checkbox("قص اللوغو", value=True)
    logo_ratio = st.slider("نسبة القص", 0.0, 0.25, 0.12)
    apply_mirror = st.checkbox("قلب الصورة", value=True)
    red_factor = st.slider("لمسة الأحمر", 0.0, 0.3, 0.08)

# --- 4. الدوال (المحرك) ---

def generate_filename():
    """توليد اسم الملف بالصيغة المطلوبة: driouchcity-YYYYMMDD-XXXX.jpg"""
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"driouchcity-{today_str}-{random_num}.jpg"

def clean_txt(text):
    if not text: return ""
    for x in ["###SPLIT###", "###", "**", "العنوان:", "المتن:", "نص المقال:"]:
        text = text.replace(x, "")
    return text.strip()

def resize_768(img):
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
    return img

def process_img(src, is_url):
    try:
        if is_url:
            img = Image.open(requests.get(src, stream=True).raw)
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
    except: return None

def ai_writer(txt):
    try:
        genai.configure(api_key=api_key)
        mod = genai.GenerativeModel('gemini-2.0-flash')
        
        p = f"""
        الدور: محرر صحفي محترف. المهمة: إعادة صياغة شاملة للنص أدناه للغة {target_lang}.
        القواعد:
        1. الفاصل: ###SPLIT###
        2. الطول: لا تلخص. حافظ على نفس كمية المعلومات.
        3. الهيكل: عنوان، مقدمة، جسم (4 فقرات على الأقل).
        4. الأسلوب: بشري، خالي من الكليشيهات.
        النص: {txt[:20000]}
        """
        return mod.generate_content(p).text
    except Exception as e: return f"Error: {e}"

def wp_send(ib, tit, con):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    
    mid = 0
    if ib:
        filename = generate_filename() # توليد الاسم الجديد
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

def wp_img_only(ib):
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    
    filename = generate_filename() # توليد الاسم الجديد
    h2 = head.copy()
    h2.update({'Content-Disposition': f'attachment; filename={filename}', 'Content-Type': 'image/jpeg'})
    
    return requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)

# --- 5. الواجهة ---
st.title("💎 محرر الدريوش سيتي (V26)")
t1, t2, t3 = st.tabs(["🔗 رابط", "📝 نص", "🖼️ صورة"])

# ... (الواجهة والمحتوى هنا يبقى كما هو) ...

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

if mode:
    if not api_key or not wp_password:
        st.error("⚠️ أدخل البيانات!")
    else:
        st.divider()
        
        if mode == "img":
            if not i_only: st.error("لا توجد صورة")
            else:
                with st.spinner("جاري المعالجة..."):
                    iu = isinstance(i_only, str)
                    fi = process_img(i_only, iu)
                    if fi:
                        st.image(fi, width=400)
                        r = wp_img_only(fi)
                        if r.status_code == 201: st.success(f"تم الرفع! {r.json()['source_url']}")
                        else: st.error(r.text)
        
        else:
            with st.spinner("جاري العمل..."):
                tt, ti, iu = "", None, False
                try:
                    if mode == "link":
                        a = Article(l_val)
                        a.download(); a.parse()
                        tt, ti, iu = a.text, a.top_image, True
                    else:
                        tt, ti = t_val, f_val
                    
                    fi = None
                    if ti:
                        fi = process_img(ti, iu)
                        if fi: st.image(fi, width=400, caption="الصورة")
                    
                    rai = ai_gen(tt)
                    if "Error" in rai: st.error(rai)
                    else:
                        tit, bod = "", ""
                        if "###SPLIT###" in rai:
                            p = rai.split("###SPLIT###")
                            tit, bod = p[0], p[1]
                        else:
                            l = rai.split('\n')
                            tit, bod = l[0], "\n".join(l[1:])
                        
                        tit = clean_txt(tit)
                        bod = clean_txt(bod)
                        
                        st.success(f"📌 {tit}")
                        st.markdown(bod)
                        
                        r = wp_send(fi, tit, bod)
                        if r.status_code == 201: 
                            st.balloons()
                            st.success(f"تم النشر! [رابط المعاينة]({r.json()['link']})")
                        else: st.error(r.text)
                except Exception as e: st.error(f"Error: {e}")
