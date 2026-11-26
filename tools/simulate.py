import plistlib, re, sys
wf = plistlib.load(open(sys.argv[1], "rb"))
acts = wf["WFWorkflowActions"]
rows = [("Line 1 to VMC", [("Northbound St Clair West to Cedarvale",221,"2,617",8,25,53,"TBD"),("Northbound Wilson to Sheppard West",410,"2,032",20,35,71,"TBD")]),
        ("Line 1 to Finch", [("Southbound Sheppard West to Wilson",213,"2,047",10,20,63,"TBD"),("Southbound St Clair West to Dupont",279,"1,441",19,25,65,"Mid-December"),
          ("Northbound Union to King",168,454,37,20,36,"TBD"),("Northbound Queen to TMU",152,437,35,15,44,"Early January"),
          ("Northbound TMU to College",251,501,50,15,49,"Early December"),("Northbound Davisville to Eglinton",174,895,19,40,48,"TBD")]),
        ("Line 2 to Kipling", [("Westbound Warden to Victoria Park",153,"2,159",7,40,64,"TBD"),("Westbound Greenwood to Donlands",302,738,41,25,62,"TBD")])]
html = "<html><body><p class='upd'>Last Updated: Nov 25, 9:55 AM</p>"
for h, rs in rows:
    html += f"<h3>{h}</h3>\n<table><tr><th>Location</th><th>Length of defect (metres)</th><th>Distance</th><th>%</th><th>Reduced speed (km/h)</th><th>Normal</th><th>Reason</th><th>Target removal</th></tr>\n"
    for r in rs: html += "<tr>" + "".join(f"\n  <td>{c}</td>" for c in (*r[:6], "Track issue", r[6])) + "\n</tr>"
    html += "</table>"
html += "<p>Queen&#39;s Park FAQ</p></body></html>"

V, O = {}, {}
import os
INPUT=os.environ.get("SC_INPUT","")
TRIPS="Weekend:  broadview , castle frank,Sherbourne, Bloor-Yonge, Bay, st. george, Museum\n\nEast: Warden, Victoria Park, Main Street\nWest: Main Street, Victoria Park, Warden\nDowntown: queen, tmu, college"
def resolve(a):
    t = a["Type"]
    if t == "Variable": return V[a["VariableName"]]
    if t == "ActionOutput": return O[a["OutputUUID"]]
    if t == "ExtensionInput": return INPUT
    raise Exception(t)
def val(p):
    if isinstance(p, (str, int, float)): return p
    if p["WFSerializationType"] == "WFTextTokenAttachment": return resolve(p["Value"])
    s, rng = p["Value"]["string"], p["Value"]["attachmentsByRange"]
    u = s.encode("utf-16-le"); res=""; pos=0
    subs = sorted((int(k.strip("{}").split(",")[0]), v) for k, v in rng.items())
    i = 0; out=""
    units = [u[j:j+2] for j in range(0, len(u), 2)]
    for idx, unit in enumerate(units):
        d = dict(subs)
        if idx in d:
            x = resolve(d[idx]); out += "\n".join(map(fmt, x)) if isinstance(x, list) else fmt(x)
        else: out += unit.decode("utf-16-le", "surrogatepass")
    return out.encode("utf-16","surrogatepass").decode("utf-16")
def fmt(x):
    if isinstance(x, float) and x.is_integer(): return str(int(x))
    return str(x)
def icu_rep(r): return re.sub(r"\$(\d)", r"\\g<\1>", r)

def run(lo, hi):
    i = lo
    while i < hi:
        a = acts[i]; ident = a["WFWorkflowActionIdentifier"].split("actions.")[1]; p = a["WFWorkflowActionParameters"]; r = None
        if ident == "repeat.each" and p["WFControlFlowMode"] == 0:
            g = p["GroupingIdentifier"]; end = next(j for j in range(i+1, hi) if acts[j]["WFWorkflowActionParameters"].get("GroupingIdentifier")==g)
            items = val(p["WFInput"]); depth = sum(1 for k in V if k.startswith("__d"))+1
            name = "Repeat Item" if depth == 1 else f"Repeat Item {depth}"
            V[f"__d{depth}"]=1
            for it in items: V[name] = it; run(i+1, end)
            del V[f"__d{depth}"]; i = end+1; continue
        if ident == "conditional" and p["WFControlFlowMode"] == 0:
            g = p["GroupingIdentifier"]; end = next(j for j in range(i+1, hi) if acts[j]["WFWorkflowActionParameters"].get("GroupingIdentifier")==g and acts[j]["WFWorkflowActionParameters"]["WFControlFlowMode"]==2)
            assert p["WFCondition"] == 99
            els = next((j for j in range(i+1, end) if acts[j]["WFWorkflowActionParameters"].get("GroupingIdentifier")==g and acts[j]["WFWorkflowActionParameters"]["WFControlFlowMode"]==1), end)
            if val(p["WFConditionalActionString"]) in val(p["WFInput"]["Variable"]): run(i+1, els)
            else: run(els+1, end)
            i = end+1; continue
        if ident == "comment": pass
        elif ident == "gettext":
            r = val(p["WFTextActionText"]); r = (TRIPS if os.environ.get("SC_ALT") else r) if r.startswith("Work:") else r
        elif ident == "setvariable": V[p["WFVariableName"]] = val(p["WFInput"])
        elif ident == "downloadurl": r = html
        elif ident == "text.replace":
            s = val(p["WFInput"])
            r = re.sub(p["WFReplaceTextFind"], icu_rep(p["WFReplaceTextReplace"]), s) if p["WFReplaceTextRegularExpression"] else s.replace(p["WFReplaceTextFind"], p["WFReplaceTextReplace"])
        elif ident == "text.match": r = [m.group(0) for m in re.finditer(p["WFMatchTextPattern"], val(p["text"]))]
        elif ident == "text.changecase": r = val(p["text"]).lower()
        elif ident == "calculateexpression": r = float(eval(val(p["Input"])))
        elif ident == "round":
            x = float(val(p["WFInput"])); r = round(x, 1) if p.get("WFRoundTo") == "Tenths" else float(round(x))
        elif ident == "number": r = p["WFNumberActionNumber"]
        elif ident == "showresult": print(val(p["Text"]))
        else: raise Exception(ident)
        if "UUID" in p and r is not None: O[p["UUID"]] = r
        i += 1
run(0, len(acts))
