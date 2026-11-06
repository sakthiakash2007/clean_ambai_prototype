
import streamlit as st
import sqlite3, uuid, json
from pathlib import Path
from datetime import datetime
import pandas as pd

try:
    import folium
    from streamlit_folium import st_folium
    MAP_OK = True
except Exception:
    MAP_OK = False

ROOT = Path(__file__).parent
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
DB = ROOT / "clean_ambai.db"

st.set_page_config(page_title="Clean Ambai AI", page_icon="🌿", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:linear-gradient(180deg,#eff8f4,#fbfdfc 60%,#fff)}
.block-container{max-width:1400px;padding-top:1.2rem}
.hero{border-radius:24px;padding:34px;color:white;min-height:230px;background:linear-gradient(100deg,rgba(4,39,49,.94),rgba(6,92,81,.72)),url('https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=1800&q=85') center/cover;box-shadow:0 14px 40px #164d4420}
.hero h1{font-family:Manrope,sans-serif;font-size:clamp(2rem,4vw,3.3rem);margin:.4rem 0;color:#fff}
.hero p{color:#e2f7ed;font-size:1.05rem}
.eyebrow{font-size:.72rem;letter-spacing:.15em;font-weight:800;color:#a8e8d1}
.metric{background:#fff;border:1px solid #deeee7;border-radius:16px;padding:17px;min-height:105px}
.metric small{color:#69857e;font-weight:600}.metric h2{font-family:Manrope,sans-serif;color:#15463e;margin:.2rem 0}.muted{color:#6e8983;font-size:.86rem}
div[data-testid="stSidebar"]{background:#f1f8f4;border-right:1px solid #dcebe4}
</style>
""", unsafe_allow_html=True)

def db():
    c=sqlite3.connect(DB,check_same_thread=False)
    c.row_factory=sqlite3.Row
    return c

def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS reports(
        id TEXT PRIMARY KEY, created TEXT, reporter TEXT, description TEXT, landmark TEXT, location TEXT,
        lat REAL, lon REAL, photo TEXT, categories TEXT, severity TEXT, status TEXT, assigned TEXT,
        sent INTEGER DEFAULT 0, submission_note TEXT, after_photo TEXT, verified INTEGER DEFAULT 0)""")
        c.commit()

def all_reports():
    with db() as c: return [dict(x) for x in c.execute("SELECT * FROM reports ORDER BY created DESC").fetchall()]

def one(rid):
    with db() as c:
        x=c.execute("SELECT * FROM reports WHERE id=?",(rid,)).fetchone()
        return dict(x) if x else None

def update(rid, **kw):
    if not kw:return
    with db() as c:
        c.execute("UPDATE reports SET "+",".join(f"{k}=?" for k in kw)+" WHERE id=?",list(kw.values())+[rid])
        c.commit()

def save_photo(upload, prefix):
    if not upload:return ""
    ext=Path(upload.name).suffix.lower() or ".jpg"
    path=UPLOADS/f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    path.write_bytes(upload.getbuffer())
    return str(path)

def log_metric(label,val,note):
    st.markdown(f'<div class="metric"><small>{label}</small><h2>{val}</h2><span class="muted">{note}</span></div>',unsafe_allow_html=True)

def hero():
    st.markdown('<div class="hero"><div class="eyebrow">AMBI • COMMUNITY • CLEAN RIVER</div><h1>Clean Ambai AI</h1><p>Report waste. Track cleanups. Protect our Thamirabarani.</p><b>🌿 Smart community reporting for a cleaner riverbank</b></div>',unsafe_allow_html=True)

def repeat_for(r, reports, days=30, radius=.0012):
    if r["lat"] is None or r["lon"] is None:return None
    try: dt=datetime.fromisoformat(r["created"])
    except: return None
    for old in reports:
        if old["id"]==r["id"] or old["lat"] is None or old["lon"] is None: continue
        try: odt=datetime.fromisoformat(old["created"])
        except: continue
        if abs((dt-odt).days)<=days:
            d=((r["lat"]-old["lat"])**2+(r["lon"]-old["lon"])**2)**.5
            if d<=radius:return old["id"]
    return None

init()
if not all_reports():
    demo=[
      ("CA-DEMO1","Food stalls near river steps","Riverbank food-stall stretch",8.7014,77.4528,"Plastic; Food packaging","High","Assigned","Cleaning Team A"),
      ("CA-DEMO2","Path beside river","River walkway",8.7020,77.4540,"Plastic","Low","Completed","Cleaning Team A"),
      ("CA-DEMO3","Near riverside entry","Riverbank food-stall stretch",8.7015,77.4529,"Plastic; Paper; Food packaging","High","Submitted","")
    ]
    with db() as c:
        for i,(land,loc,loc2,lat,lon,cats,sev,status,assignee) in enumerate(demo):
            c.execute("INSERT INTO reports(id,created,reporter,description,landmark,location,lat,lon,photo,categories,severity,status,assigned) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"CA-100{i+1}","2026-10-2"+str(i+2)+"T10:00:00","Demo citizen","Demo record; no real photo",land,loc2,lat,lon,"",cats,sev,status,assignee))
        c.commit()

with st.sidebar:
    st.markdown("## 🌿 Clean Ambai AI")
    page=st.radio("Navigation",["Overview","Report Waste","Hotspot Map","Cleaning Team","Repeat-Waste Alerts","Cleanup Verification","Impact Dashboard","About & Export"])
    st.divider()
    st.caption("Editable Streamlit prototype")
    st.caption("Demo AI • Local SQLite • No cameras required")

reports=all_reports()
hero()
st.write("")

if page=="Overview":
    st.subheader("Riverbank at a glance")
    reports=all_reports()
    cols=st.columns(4)
    with cols[0]:log_metric("Total reports",len(reports),"Saved reports")
    with cols[1]:log_metric("Open tasks",sum(r["status"] not in ["Completed","Verified"] for r in reports),"Need action or review")
    with cols[2]:log_metric("Completed",sum(r["status"] in ["Completed","Verified"] for r in reports),"Completed / verified")
    with cols[3]:log_metric("Locations",len(set(r["location"] for r in reports)),"Unique location labels")
    left,right=st.columns([1.2,1])
    with left:
        st.markdown("### Recent reports")
        st.dataframe(pd.DataFrame([{"ID":r["id"],"Landmark":r["landmark"],"Severity":r["severity"],"Status":r["status"],"Created":r["created"][:16].replace("T"," ")} for r in reports]),use_container_width=True,hide_index=True)
    with right:
        st.markdown("### Waste categories")
        counts={}
        for r in reports:
            for cat in (r["categories"] or "").split(";"):
                cat=cat.strip(); counts[cat]=counts.get(cat,0)+1
        st.bar_chart(pd.Series(counts,name="Reports"))
    st.info("Demo records are included. The AI model and municipality delivery are not connected in this starter version.")

elif page=="Report Waste":
    st.subheader("Submit a waste report")
    st.caption("Photo + landmark + location details help the cleaning team find the spot.")
    with st.form("report",clear_on_submit=True):
        a,b=st.columns(2)
        with a:
            photo=st.file_uploader("Waste photo",type=["jpg","jpeg","png","webp"])
            reporter=st.text_input("Your name (optional)")
            landmark=st.text_input("Nearby landmark *",placeholder="Food stalls near river steps")
            location=st.text_input("Location description *",placeholder="Thamirabarani riverbank, Ambasamudram")
            desc=st.text_area("What did you notice?")
        with b:
            st.markdown("**Coordinates (optional)**")
            st.caption("This starter version uses manually entered coordinates.")
            lat=st.number_input("Latitude",value=8.7014,format="%.6f")
            lon=st.number_input("Longitude",value=77.4528,format="%.6f")
            cats=st.multiselect("Visible waste types",["Plastic","Paper","Food packaging","Food waste","Glass/metal","Mixed waste","Other"])
            severity=st.select_slider("Visible litter level",["Low","Medium","High"],value="Medium")
            st.warning("AI demo mode: no real image model is connected. Please review categories and severity manually.")
        ok=st.checkbox("I confirm this report describes visible waste in a public/community area.")
        submit=st.form_submit_button("Submit report",type="primary",use_container_width=True)
    if submit:
        if not landmark.strip() or not location.strip():st.error("Enter both landmark and location.")
        elif not ok:st.error("Please confirm the report.")
        else:
            rid="CA-"+uuid.uuid4().hex[:6].upper()
            path=save_photo(photo,rid)
            with db() as c:
                c.execute("INSERT INTO reports(id,created,reporter,description,landmark,location,lat,lon,photo,categories,severity,status,assigned,sent,submission_note,after_photo,verified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid,datetime.now().isoformat(timespec="seconds"),reporter,desc,landmark,location,lat,lon,path,"; ".join(cats or ["Needs review"]),severity,"Submitted","",0,"","",0))
                c.commit()
            st.success(f"Report saved. Your report ID is {rid}.")
            st.info("This saves locally only; it has not been sent to the municipality.")
            st.rerun()

elif page=="Hotspot Map":
    st.subheader("Reported waste hotspots")
    st.caption("Map shows reports, not continuous live monitoring or proof that waste remains.")
    reports=all_reports(); geo=[r for r in reports if r["lat"] is not None and r["lon"] is not None]
    if MAP_OK and geo:
        m=folium.Map(location=[sum(r["lat"] for r in geo)/len(geo),sum(r["lon"] for r in geo)/len(geo)],zoom_start=15)
        for r in geo:
            color={"Low":"green","Medium":"orange","High":"red"}.get(r["severity"],"blue")
            folium.Marker([r["lat"],r["lon"]],tooltip=f'{r["id"]} • {r["severity"]}',popup=f'{r["landmark"]}<br>{r["status"]}',icon=folium.Icon(color=color)).add_to(m)
        st_folium(m,use_container_width=True,height=430)
    else:st.info("Install map dependencies or use the report list below.")
    st.dataframe(pd.DataFrame([{"ID":r["id"],"Location":r["location"],"Landmark":r["landmark"],"Severity":r["severity"],"Status":r["status"],"Lat":r["lat"],"Lon":r["lon"]} for r in reports]),use_container_width=True,hide_index=True)

elif page=="Cleaning Team":
    st.subheader("Cleaning-team task board")
    reports=all_reports()
    if reports:
        label=st.selectbox("Select report",[f'{r["id"]} — {r["landmark"]}' for r in reports])
        rid=label.split(" — ")[0]; r=one(rid)
        a,b=st.columns(2)
        with a:
            st.markdown(f"### {r['id']} · {r['severity']} priority")
            st.write("**Landmark:**",r["landmark"]); st.write("**Location:**",r["location"])
            st.write("**Waste:**",r["categories"]); st.write("**Description:**",r["description"] or "—")
            if r["photo"] and Path(r["photo"]).exists():st.image(r["photo"],caption="Reported photo",use_container_width=True)
        with b:
            with st.form("task"):
                status=st.selectbox("Status",["Submitted","Reviewed","Assigned","Cleaning in Progress","Completed","Verified","Needs Review"],index=["Submitted","Reviewed","Assigned","Cleaning in Progress","Completed","Verified","Needs Review"].index(r["status"]) if r["status"] in ["Submitted","Reviewed","Assigned","Cleaning in Progress","Completed","Verified","Needs Review"] else 0)
                assigned=st.text_input("Assigned team/member",r["assigned"] or "")
                sent=st.checkbox("Mark submitted to municipality (only if actually sent)",value=bool(r["sent"]))
                note=st.text_input("Submission reference/channel",r["submission_note"] or "")
                save=st.form_submit_button("Save task",type="primary")
            if save:
                update(rid,status=status,assigned=assigned,sent=int(sent),submission_note=note)
                st.success("Task updated."); st.rerun()
            payload={k:r.get(k) for k in ["id","created","description","landmark","location","lat","lon","photo","categories","severity","status"]}
            st.download_button("Export report JSON",json.dumps(payload,indent=2),f"{rid}.json","application/json")
            st.caption("Exporting does not send the report to the municipality.")
    else:st.info("No reports yet.")

elif page=="Repeat-Waste Alerts":
    st.subheader("Repeat-waste alerts")
    reports=all_reports(); rows=[]
    for r in reports:
        old=repeat_for(r,reports)
        if old:rows.append({"New report":r["id"],"Nearby earlier report":old,"Landmark":r["landmark"],"Severity":r["severity"],"Status":r["status"]})
    if rows:
        st.warning(f"{len(rows)} possible repeat reports need review.")
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    else:st.success("No repeat reports found using the current sample thresholds.")
    st.caption("A repeat report is a signal for review, not proof that a location is still dirty.")

elif page=="Cleanup Verification":
    st.subheader("Before-and-after cleanup verification")
    reports=all_reports()
    if reports:
        label=st.selectbox("Choose report",[f'{r["id"]} — {r["landmark"]}' for r in reports])
        rid=label.split(" — ")[0]; r=one(rid)
        a,b=st.columns(2)
        with a:
            st.markdown("**Before**")
            if r["photo"] and Path(r["photo"]).exists():st.image(r["photo"],use_container_width=True)
            else:st.info("No before-photo.")
        with b:
            st.markdown("**After**")
            if r["after_photo"] and Path(r["after_photo"]).exists():st.image(r["after_photo"],use_container_width=True)
            else:st.info("No after-photo uploaded.")
        after=st.file_uploader("Upload after-cleaning photo",type=["jpg","jpeg","png","webp"])
        note=st.text_input("Verification note")
        if st.button("Save photo and mark verified",type="primary"):
            if after:
                path=save_photo(after,rid+"_after")
                update(rid,after_photo=path,verified=1,status="Verified")
                st.success("After-photo saved; marked verified.")
                st.rerun()
            else:st.error("Upload an after-photo first.")
    else:st.info("No reports yet.")

elif page=="Impact Dashboard":
    st.subheader("Impact dashboard")
    reports=all_reports()
    cols=st.columns(4)
    with cols[0]:log_metric("Reports",len(reports),"Saved reports")
    with cols[1]:log_metric("Completed",sum(r["status"] in ["Completed","Verified"] for r in reports),"Marked complete")
    with cols[2]:log_metric("Verified",sum(bool(r["verified"]) for r in reports),"After-photo saved")
    with cols[3]:log_metric("Possible repeats",sum(bool(repeat_for(r,reports)) for r in reports),"Needs review")
    if reports:
        d=pd.DataFrame([{"Date":r["created"][:10],"Status":r["status"],"Severity":r["severity"],"ID":r["id"]} for r in reports])
        st.markdown("### Reports by date"); st.bar_chart(d.groupby("Date").size())
        st.markdown("### Task status"); st.bar_chart(d.groupby("Status").size())
        st.dataframe(d,use_container_width=True,hide_index=True)
    st.info("Workflow metrics are not proof of reduced river pollution. Measure comparable litter counts before and after real interventions.")

elif page=="About & Export":
    st.subheader("About this prototype")
    st.write("A community reporting and cleaning coordination prototype for waste around the Thamirabarani riverbank.")
    st.markdown("""
    **Current limitations**
    - No real computer-vision model is connected. The reporter manually selects waste types and severity.
    - Municipality delivery is not configured. Reports can be exported, but an authorized channel is needed.
    - Repeat alerts are location/time heuristics and require human review.
    - Coordinates are entered manually; browser GPS can be added later.
    - SQLite is local storage, not a secure multi-user production database.
    - The river hero image loads from Unsplash and needs internet access.
    """)
    reports=all_reports()
    if reports:
        st.download_button("Download all reports CSV",pd.DataFrame(reports).to_csv(index=False).encode(), "clean_ambai_reports.csv","text/csv")
        st.download_button("Download all reports JSON",json.dumps(reports,indent=2),"clean_ambai_reports.json","application/json")
    st.markdown("### Future upgrades")
    st.write("1. Browser GPS capture  2. Real litter-detection model  3. Authentication and roles  4. Verified municipality integration  5. Hosted database and secure image storage.")

st.markdown("<hr><p class='muted'>Clean Ambai AI • Editable Streamlit prototype • Not an official municipal service.</p>",unsafe_allow_html=True)
