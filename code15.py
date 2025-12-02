import streamlit as st

# 1. إعداد الصفحة فوراً لتجنب الشاشة البيضاء
st.set_page_config(page_title="Editor Diagnostic", layout="wide")
st.title("🛠️ وضع التشخيص والإصلاح")

# 2. فحص المكتبات واحدة تلو الأخرى
missing_libs = []

try:
    import requests
    st.success("✅ مكتبة Requests: موجودة")
except ImportError:
    missing_libs.append("requests")

try:
    from PIL import Image
    st.success("✅ مكتبة Pillow (الصور): موجودة")
except ImportError:
    missing_libs.append("Pillow")

try:
    import google.generativeai as genai
    st.success("✅ مكتبة Google AI: موجودة")
except ImportError:
    missing_libs.append("google-generativeai")

try:
    from newspaper import Article
    st.success("✅ مكتبة Newspaper3k (الأخبار): موجودة")
except ImportError:
    # غالباً المشكلة هنا بسبب lxml
    missing_libs.append("newspaper3k lxml_html_clean")

# 3. عرض النتيجة
if missing_libs:
    st.error("❌ توقف التطبيق! المكتبات التالية مفقودة:")
    st.code(f"pip install {' '.join(missing_libs)}")
    st.warning("المرجو فتح الشاشة السوداء (CMD) وكتابة الأمر أعلاه لتثبيت النواقص.")
    st.stop() # إيقاف التنفيذ هنا

# ---------------------------------------------------------
# إذا وصلت لهذا السطر، فالمكتبات سليمة وسيعمل التطبيق
# ---------------------------------------------------------

import base64
import io
import time
from PIL import ImageEnhance, ImageOps

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("Gemini API", type="password")
    wp_url = st.text_input("رابط الموقع", "https://driouchcity.com")
    wp_user = st.text_input("اسم المستخدم")
    wp_password = st.text_input("كلمة المرور", type="password")
    st.divider()
    lang = st.selectbox("اللغة", ["العربية", "الإسبانية", "الفرنسية", "الإنجليزية"])
    crop_logo = st.checkbox("قص اللوغو", True)
    logo_r = st.slider("نسبة القص", 0.0, 0.25, 0.12)
    mirror = st.checkbox("قلب الصورة", True)
    red_val = st.slider("لمسة حمراء", 0.0, 0.3, 0.08)

# --- الدوال ---
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
        img_ratio = img.width / img.height
        target_ratio = tw / th
        
        if img_ratio > target_ratio:
            new_h = th
            new_w = int(new_h * img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            img = img.crop(((new_w-tw)//2, 0, (new_w-tw)//2 + tw, th))
        else:
            new_w = tw
            new_h = int(new_w / img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            img = img.crop((0, (new_h-th)//2, tw, (new_h-th)//2 + th))

        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        if red_val > 0:
            ov = Image.new('RGB', img.size, (180, 20, 20))
            img = Image.blend(img, ov, alpha=red_val)
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        return buf.getvalue()
    except Exception as e:
        return None

def ai_gen(txt):
    try:
        genai.configure(api_key=api_key)
        mod = genai.GenerativeModel('gemini-2.0-flash')
        p = f"""
        الدور: صحفي محترف. المهمة: إعادة صياغة (Paraphrasing) للنص أدناه للغة {lang}.
        القواعد:
        1. العنوان في السطر الأول.
        2. الفاصل ###SPLIT###
        3. المتن: مقال كامل التفاصيل، نفس حجم النص الأصلي، مقسم لفقرات.
        4. لا تحذف المعلومات.
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
        h2 = head.copy()
        h2.update({'Content-Disposition': 'filename=news.jpg', 'Content-Type': 'image/jpeg'})
        try:
            r = requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib)
            if r.status_code == 201: mid = r.json()['id']
        except: pass
    
    h3 = head.copy()
    h3['Content-Type'] = 'application/json'
    d = {'title': tit, 'content': con, 'status': 'draft', 'featured_media': mid}
    return requests.post(f"{wp_url}/wp-json/wp/v2/posts", headers=h3, json=d)

# --- الواجهة ---
st.info("النظام يعمل بنجاح. اختر العملية:")
t1, t2 = st.tabs(["🔗 رابط", "📝 يدوي"])

mode, l_val, f_val, t_val = None, "", None, ""

with t1:
    l_val = st.text_input("الرابط")
    if st.button("🚀 تنفيذ الرابط"): mode = "link"
with t2:
    f_val = st.file_uploader("صورة")
    t_val = st.text_area("نص")
    if st.button("🚀 تنفيذ اليدوي"): mode = "manual"

if mode:
    if not api_key: st.error("أدخل المفتاح!")
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
                    fi = proc_img(ti, iu)
                    if fi: st.image(fi, width=400)
                
                rai = ai_gen(tt)
                if "Error" in rai: st.error(rai)
                else:
                    parts = rai.split("###SPLIT###") if "###SPLIT###" in rai else [rai[:50], rai]
                    tit = parts[0].replace("العنوان:", "").strip()
                    bod = parts[1].replace("المتن:", "").strip()
                    
                    st.success(tit)
                    st.markdown(bod)
                    
                    r = wp_send(fi, tit, bod)
                    if r.status_code == 201: st.success("تم النشر!")
                    else: st.error(r.text)
            except Exception as e: st.error(f"Error: {e}")
