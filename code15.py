import streamlit as st
import requests
import base64
import io
import time
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article
import google.generativeai as genai

# إعداد الصفحة والذاكرة
st.set_page_config(page_title="Editor V20", layout="wide", page_icon="🚀")
if 'res' not in st.session_state: st.session_state.res = {}

# القائمة الجانبية
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
    red_val = st.slider("أحمر", 0.0, 0.3, 0.08)

# الدوال
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
        
        # Resizing 768x432
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
        دورك: رئيس تحرير. المهمة: صياغة وترجمة لـ {lang}.
        القواعد:
        1. فاصل إجباري: ###SPLIT###
        2. قسّم النص لـ 4 فقرات على الأقل.
        3. أسلوب بشري 100%.
        النص: {txt[:15000]}
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

# الواجهة الرئيسية
st.title("💎 محرر الدريوش سيتي (V20)")
t1, t2, t3 = st.tabs(["🔗 رابط", "📝 نص", "🖼️ صورة"])

mode, l_val, f_val, t_val, i_only = None, "", None, "", None

with t1:
    l_val = st.text_input("رابط الخبر")
    if st.button("🚀 تنفيذ الرابط"): mode = "link"
with t2:
    f_val = st.file_uploader("صورة", key="2")
    t_val = st.text_area("نص")
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
                    fi = proc_img(i_only, iu)
                    if fi:
                        st.image(fi, width=400)
                        r = wp_img_only(fi)
                        if r.status_code == 201: st.success(f"تم الرفع: {r.json()['source_url']}")
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
                        fi = proc_img(ti, iu)
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
                        st.success(tit)
                        st.markdown(bod)
                        
                        r = wp_send(fi, tit, bod)
                        if r.status_code == 201: st.success(f"تم النشر! {r.json()['link']}")
                        else: st.error(r.text)
                except Exception as e: st.error(f"خطأ: {e}")
