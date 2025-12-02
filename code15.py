# --- الواجهة ---
st.title("💎 محرر الدريوش سيتي (V28)")
t1, t2, t3 = st.tabs(["🔗 رابط", "📝 نص", "🖼️ صورة"])

mode, l_val, f_val, t_val, i_only = None, "", None, "", None

with t1:
    l_val = st.text_input("رابط الخبر:")
    if st.button("🚀 تنفيذ (رابط)"): mode = "link"
with t2:
    f_val = st.file_uploader("صورة", key="2")
    t_val = st.text_area("نص", height=200)
    if st.button("🚀 تنفيذ النص"): mode = "manual"
with t3:
    ic = st.radio("المصدر:", ["ملف", "رابط"])
    if ic == "ملف": i_only = st.file_uploader("صورة", key="3")
    else: i_only = st.text_input("رابط")
    if st.button("🎨 رفع صورة فقط"): mode = "img"

# --- 5. التنفيذ (تأكد أن هذا الجزء غير مدفوع لليمين) ---
if mode:
    if not api_key or not wp_password:
        st.error("⚠️ أدخل البيانات!")
    else:
        st.divider()
        # ... (بقية الكود) ...
        # (بدء التنفيذ الفعلي هنا)
        with st.spinner("جاري العمل..."):
            tt, ti, iu = "", None, False
            try:
                if mode == "link":
                    a = Article(l_val)
                    a.download(); a.parse()
                    tt, ti, iu = a.text, a.top_image, True
                elif mode == "manual":
                    tt, ti = t_val, f_val
                
                # مسار الصورة فقط
                if mode == "img":
                    if not i_only: st.error("لا توجد صورة")
                    else:
                        iu = isinstance(i_only, str)
                        fi = process_img(i_only, iu)
                        if fi:
                            st.image(fi, width=400)
                            r = wp_up_img(fi)
                            if r.status_code == 201: st.success(f"تم الرفع! {r.json()['source_url']}")
                            else: st.error(r.text)
                    st.stop() 

                # مسار المقال الكامل
                fi = None
                if ti:
                    fi = process_img(ti, iu)
                    if fi: st.image(fi, width=400)
                
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
            except Exception as e:
                st.error(f"Error: {e}")
