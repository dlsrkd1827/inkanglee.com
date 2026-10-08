import urllib.request, re, json, os, sys, html as H
OUT=sys.argv[1]
PAGES=[("index",""),("lightgrass-01","%EB%B3%B5%EC%A0%9C-motorized-wheelchair-sensory-rel-1"),("susu-sangseung","%EB%B3%B5%EC%A0%9C-motorized-wheelchair-sensory-rel"),("sensory-relay-01","sensoryrelay01"),("drawing-suit-01-02","drawingsuit01-02"),("performing-suit-02","performing-suit-02-2023"),("performing-suit-01","%ED%8D%BC%ED%8F%AC%EB%B0%8D-%EC%88%98%ED%8A%B8-01-2022-12"),("drawing-suit-02","%EB%93%9C%EB%A1%9C%EC%9E%89-%EC%88%98%ED%8A%B8-02-2022"),("drawing-suit-01","drawing-suit-01"),("memory","memory"),("undead-weight","undead-weight"),("tinker-ball","tinker-ball"),("perfect-posture","perfectposture"),("hack-the-boxing-2","hack-the-boxing-2"),("hack-the-boxing","hack-the-box"),("1997-11-22-1","1997-11-22-1"),("windows-diary","untitled1"),("wood-diary","wood-diary"),("reddish-brothers","reddish-brothers"),("jangsaengpo-people","untitled2"),("eyes-2017","eyes-2017"),("1997-11-22","1997-11-22"),("the-boxer","the-boxer"),("light-of-memory","light-of-memory"),("coated-memory","coated-memory"),("coated-memory-2","coated-memory-2"),("the-flying-arrow","the-flying-arrow-is-therefore-motio"),("hello-nice-to-meet-you","hello-nice-to-meet-you"),("prepper","prepper"),("eyes-2013","eyes-2013"),("reviews","critic"),("cv","cv"),("contact","contact")]
def get(u):
    r=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
    return urllib.request.urlopen(r,timeout=60).read().decode("utf8")
for name,slug in PAGES:
    d=os.path.join(OUT,name); os.makedirs(d,exist_ok=True)
    html=get("https://www.inkanglee.com/"+slug)
    open(os.path.join(d,"ssr.html"),"w",encoding="utf8").write(html)
    urls=sorted(set(u.replace("\u0026","&").replace("&amp;","&") for u in re.findall(r'https://siteassets\.parastorage\.com/pages/pages/thunderbolt\?[^"]*module=thunderbolt-features[^"]*',html)))
    merged={"types":{},"props":{},"seo":None}
    for u in urls:
        j=json.loads(get(u))
        for k,v in j.get("structure",{}).get("components",{}).items(): merged["types"][k]=v.get("componentType")
        merged["props"].update(j.get("props",{}).get("render",{}).get("compProps",{}))
        if j.get("props",{}).get("seo"): merged["seo"]=merged["seo"] or j["props"]["seo"]
    json.dump(merged,open(os.path.join(d,"data.json"),"w",encoding="utf8"),ensure_ascii=False)
    print(name,len(urls),len(merged["props"]),flush=True)
