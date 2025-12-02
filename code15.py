import streamlit as st
import base64
import io
import time
import requests
from PIL import Image, ImageEnhance, ImageOps
from newspaper import Article # تأكد من تثبيت هذه المكتبة: pip install newspaper3k
import google.generativeai as genai

# 1. إعداد الصفحة فوراً لتجنب الشاشة البيضاء
st.set_page_config(page_title="Editor Diagnostic and Article Refiner", layout="wide")
st.title("🛠️ وضع التشخيص والإصلاح والتحسين الصحفي")

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
    """
    معالجة وتحسين الصورة لتناسب مقاسات النشر الرقمي.
    تتضمن: القص، القلب، تغيير الحجم، وتحسين الألوان والتباين.
    """
    try:
        if is_url:
            # يجب تعيين timeout لتجنب التعليق عند الروابط غير الصالحة
            img = Image.open(requests.get(src, stream=True, timeout=10).raw)
        else:
            img = Image.open(src)
            
        if img.mode != 'RGB': img = img.convert('RGB')
        
        # قص اللوغو من الأعلى
        if crop_logo:
            w, h = img.size
            img = img.crop((0, 0, w, int(h * (1 - logo_r))))
            
        # قلب الصورة (Mirror)
        if mirror: img = ImageOps.mirror(img)
        
        # تغيير الحجم والقص إلى نسبة 16:9 (768x432)
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

        # تحسينات اللون والتباين
        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        
        # إضافة لمسة حمراء خفيفة
        if red_val > 0:
            ov = Image.new('RGB', img.size, (180, 20, 20))
            img = Image.blend(img, ov, alpha=red_val)
            
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        return buf.getvalue()
    except Exception as e:
        st.error(f"خطأ في معالجة الصورة: {e}")
        return None

def ai_gen(txt):
    """
    استخدام نموذج Gemini لتوليد المقال بالبرومبت الصحفي الجديد والمعدل.
    """
    try:
        genai.configure(api_key=api_key)
        
        # ----------------------------------------------------------------------
        # تم تحديث البرومبت لإزالة العناوين الفرعية ومنع الحشو
        # ----------------------------------------------------------------------
        p = f"""
        التعليمات: أنت صحفي استقصائي محترف وخبير في تحسين محركات البحث (SEO). مهمتك هي إعادة صياغة النص الأصلي المقدم بأسلوب صحفي حيوي ومقنع ومُحسّن للقراءة الرقمية.

        1. العنوان (H1): يجب أن يكون العنوان في السطر الأول. قم بإنشاء عنوان رئيسي (H1) جديد وجذاب للغاية ومُحفّز للنقر (Clickbait-style) ويوافق معايير الـ SEO. يجب أن يتضمن العنوان كلمات مفتاحية ذات صلة بالموضوع الأصلي.
        2. الفاصل: يجب أن يكون السطر الثاني هو ###SPLIT###.
        3. المتن: يجب أن لا يقل المقال عن 500 كلمة، وأن يكون بأسلوب كتابة صحفي احترافي، بشري، وغير آلي المظهر. يجب هيكلة المقال لتحسين محركات البحث (SEO):
           - استخدم فقرات متوسطة يسهل قراءتها.
           - يجب أن يتراوح عدد الفقرات ما بين 5 إلى 15 فقرة كحد أقصى.
           - **يجب الالتزام الصارم بالمعلومات الأساسية الواردة في النص الأصلي فقط، وتجنب الإضافة أو الحشو غير المبرر.**
           - دمج الكلمات المفتاحية ذات الصلة بشكل طبيعي في كامل النص.
           - **لا تستخدم أي عناوين فرعية (H2, H3) أو وسوم HTML داخل المتن.**
        4. اللغة المطلوبة: {lang}.
        5. لا تحذف المعلومات الأساسية من النص الأصلي.

        النص الأصلي للتحليل وإعادة الصياغة:
        {txt[:20000]}
        """
        # استخدام الطراز الموصى به حالياً
        mod = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        
        response = mod.generate_content(p)
        return response.text
        
    except Exception as e: 
        return f"Error: {e}"

def wp_send(ib, tit, con):
    """
    إرسال الصورة والمقال إلى ووردبريس عبر REST API.
    تم تعديل رأس (Header) رفع الصورة لمعالجة خطأ 400.
    """
    st.info("جاري إرسال المقال إلى ووردبريس...")
    cred = f"{wp_user}:{wp_password}"
    tok = base64.b64encode(cred.encode()).decode('utf-8')
    head = {'Authorization': f'Basic {tok}'}
    mid = 0 # Media ID for featured image
    
    # 1. رفع الصورة المميزة (Featured Image) - تم إصلاح مشكلة Content-Disposition هنا
    if ib:
        h2 = head.copy()
        # استخدام X-WP-Attachment-Filename وهو الأكثر موثوقية لتحديد اسم الملف في ووردبريس
        h2.update({
            'Content-Type': 'image/jpeg',
            'X-WP-Attachment-Filename': 'news_processed.jpg'
        })
        try:
            # يجب تحديد الرابط الصحيح لنقطة نهاية الـ Media
            r = requests.post(f"{wp_url}/wp-json/wp/v2/media", headers=h2, data=ib, timeout=30)
            if r.status_code == 201: 
                mid = r.json()['id']
                st.success(f"✅ تم رفع الصورة بنجاح. Media ID: {mid}")
            else: 
                # عرض جزء من الرسالة لتسهيل التشخيص إذا استمر الخطأ
                st.error(f"❌ فشل رفع الصورة: {r.status_code} - {r.text[:200]}")
        except requests.exceptions.Timeout:
            st.error("❌ فشل رفع الصورة: انتهت مهلة الاتصال بالخادم.")
        except Exception as e: 
            st.error(f"❌ خطأ غير متوقع أثناء رفع الصورة: {e}")
            
    # 2. إنشاء المقال (Post)
    h3 = head.copy()
    h3['Content-Type'] = 'application/json'
    d = {
        'title': tit, 
        'content': con, 
        'status': 'draft', # النشر كمسودة (Draft)
        'featured_media': mid # ربط الصورة
    }
    
    try:
        r = requests.post(f"{wp_url}/wp-json/wp/v2/posts", headers=h3, json=d, timeout=30)
        if r.status_code == 201: 
            st.success(f"✅ تم النشر بنجاح! رابط المسودة: {r.json().get('link', 'لا يوجد رابط متاح')}")
        else: 
            st.error(f"❌ فشل نشر المقال: {r.status_code} - {r.text[:300]}")
            st.code(d) # عرض البيانات المرسلة للمساعدة في التشخيص
    except requests.exceptions.Timeout:
        st.error("❌ فشل نشر المقال: انتهت مهلة الاتصال بالخادم.")
    except Exception as e:
        st.error(f"❌ خطأ غير متوقع أثناء نشر المقال: {e}")


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
                    if not l_val: raise ValueError("الرجاء إدخال رابط صالح.")
                    a = Article(l_val)
                    a.download(); a.parse()
                    tt, ti, iu = a.text, a.top_image, True
                    st.info("✅ تم تحليل الرابط بنجاح.")
                else:
                    if not t_val: raise ValueError("الرجاء إدخال نص المقال.")
                    tt, ti = t_val, f_val
                    st.info("✅ تم استلام النص والصورة يدوياً.")
                    
                # 1. معالجة الصورة
                fi = None
                if ti:
                    st.info("جاري معالجة الصورة...")
                    fi = proc_img(ti, iu)
                    if fi: 
                        st.image(fi, caption="الصورة المميزة بعد المعالجة", width=400)
                        st.success("✅ تم معالجة الصورة بنجاح.")
                    else:
                        st.warning("⚠️ لم يتم العثور على صورة أو فشلت المعالجة.")

                # 2. توليد المقال بواسطة الذكاء الاصطناعي
                st.info("جاري توليد وإعادة صياغة المقال بأسلوب صحفي...")
                rai = ai_gen(tt)
                
                if "Error" in rai: 
                    st.error(rai)
                else:
                    # تقسيم العنوان عن المتن باستخدام الفاصل الجديد
                    parts = rai.split("###SPLIT###", 1) 
                    tit = parts[0].strip()
                    bod = parts[1].strip() if len(parts) > 1 else ""
                    
                    st.subheader("🎉 المقال جاهز للنشر")
                    st.success(f"العنوان (H1): {tit}")
                    st.markdown("---")
                    st.markdown("المتن:")
                    # تم إزالة unsafe_allow_html=True
                    st.markdown(bod) 
                    st.markdown("---")
                    
                    # 3. إرسال إلى ووردبريس
                    if wp_url and wp_user and wp_password:
                        wp_send(fi, tit, bod)
                    else:
                        st.warning("⚠️ لم يتم إدخال بيانات ووردبريس (الرابط، المستخدم، كلمة المرور). لن يتم النشر تلقائياً.")

            except Exception as e: 
                st.error(f"❌ حدث خطأ عام أثناء التنفيذ: {e}")
