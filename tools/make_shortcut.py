import plistlib, uuid, json, sys

PAGE_URL = "https://www.ttc.ca/riding-the-ttc/Updates/Reduced-Speed-Zones"
ZONE_RE = r"(North|South|East|West)bound[\s|]*([^|]+?) to ([^|]+?)\|([\d,.]+)[^|]*\|[^|]*\|[^|]*\|([\d.]+)[^|]*\|([\d.]+)[^|]*\|[^|]*\|([^|]*)"
DEFAULT_TRIPS = ("Work: Cedarvale, St Clair West, Dupont, Spadina, St George, Museum, Queen's Park, St Patrick, Osgoode, St Andrew, Union, King\n"
                 "Home: King, Union, St Andrew, Osgoode, St Patrick, Queen's Park, Museum, St George, Spadina, Dupont, St Clair West, Cedarvale")

actions = []
def U(): return str(uuid.uuid4()).upper()

def var(name):  return {"Type": "Variable", "VariableName": name}
def out(uid, name): return {"Type": "ActionOutput", "OutputUUID": uid, "OutputName": name}
def att(v): return {"Value": v, "WFSerializationType": "WFTextTokenAttachment"}
def tok(*parts):
    """parts: str or variable dict -> WFTextTokenString"""
    s, rng = "", {}
    for p in parts:
        if isinstance(p, str): s += p
        else:
            pos = len(s.encode("utf-16-le")) // 2
            rng["{%d, 1}" % pos] = p
            s += "￼"
    return {"Value": {"string": s, "attachmentsByRange": rng}, "WFSerializationType": "WFTextTokenString"}

def add(ident, **params):
    actions.append({"WFWorkflowActionIdentifier": "is.workflow.actions." + ident, "WFWorkflowActionParameters": params})
    return params

def text(*parts):
    uid = U(); add("gettext", UUID=uid, WFTextActionText=tok(*parts) if any(not isinstance(p, str) for p in parts) else "".join(parts)); return out(uid, "Text")
def setv(name, src): add("setvariable", WFVariableName=name, WFInput=att(src))
def replace(src, find, rep, regex=True):
    uid = U(); add("text.replace", UUID=uid, WFInput=tok(src), WFReplaceTextFind=find, WFReplaceTextReplace=rep,
                   WFReplaceTextRegularExpression=regex, WFReplaceTextCaseSensitive=True); return out(uid, "Updated Text")
def match(src, pattern):
    uid = U(); add("text.match", UUID=uid, text=tok(src), WFMatchTextPattern=pattern, WFMatchTextCaseSensitive=True); return out(uid, "Matches")
def lower(src):
    uid = U(); add("text.changecase", UUID=uid, text=tok(src), WFCaseType="lowercase"); return out(uid, "Updated Text")
def calc(*parts):
    uid = U(); add("calculateexpression", UUID=uid, Input=tok(*parts)); return out(uid, "Calculation Result")
def rnd(src, to=None):
    uid = U(); p = add("round", UUID=uid, WFInput=att(src), WFRoundMode="Normal")
    if to: p["WFRoundTo"] = to
    return out(uid, "Rounded Number")
def number(n):
    uid = U(); add("number", UUID=uid, WFNumberActionNumber=n); return out(uid, "Number")
def comment(t): add("comment", WFCommentActionText=t)
def normalize(src):
    a = replace(src, r"&#?\w+;", "")
    b = lower(a)
    return replace(b, r"[^a-z0-9,]", "")

# ---------- build ----------
comment("TTC Slow Zones\nTrips: one per line, 'Name: station, station, …' in the order you ride. "
        "Direction comes from the order. For transfers just keep listing stations. "
        "Use the TTC's names (e.g. TMU, Cedarvale). Punctuation and capitals don't matter.")
trips_text = text(DEFAULT_TRIPS)                      # action index 1 -> import question
setv("SavedTrips", trips_text)
# Trips passed in from the web page's Run link win over the saved ones.
setv("Input", text({"Type": "ExtensionInput"}))
gi = U(); add("conditional", GroupingIdentifier=gi, WFControlFlowMode=0, WFCondition=99,
              WFInput={"Type": "Variable", "Variable": att(var("Input"))}, WFConditionalActionString=":")
setv("Trips", var("Input"))
add("conditional", GroupingIdentifier=gi, WFControlFlowMode=1)
setv("Trips", var("SavedTrips"))
add("conditional", GroupingIdentifier=gi, WFControlFlowMode=2, UUID=U())

uid = U(); add("downloadurl", UUID=uid, WFURL=PAGE_URL, WFHTTPMethod="GET")
page = replace(out(uid, "Contents of URL"), r"<[^>]+>", "|")
page = replace(page, r"&nbsp;|&#160;", " ")
page = replace(page, r"[ \t]*[\r\n\u2028\u2029|][\s|\u2028\u2029]*", "|")
setv("Page", page)
setv("Updated", match(var("Page"), r"Last Updated:\s*[^|]+"))
setv("Zones", match(var("Page"), ZONE_RE))
setv("Report", text(""))

trip_lines = match(var("Trips"), r"(?m)^[^:\n]+:.+$")
g1 = U(); add("repeat.each", GroupingIdentifier=g1, WFControlFlowMode=0, WFInput=att(trip_lines))
setv("TripName", replace(var("Repeat Item"), r"^\s*([^:]*?)\s*:.*$", "$1"))
stations = replace(var("Repeat Item"), r"^[^:]*:", "")
setv("Route", normalize(text(",", stations, ",")))
zero = number(0)
setv("N", zero)
setv("Lines", text(""))

g2 = U(); add("repeat.each", GroupingIdentifier=g2, WFControlFlowMode=0, WFInput=att(var("Zones")))
setv("Key", normalize(replace(var("Repeat Item 2"), ZONE_RE, ",$2,$3,")))
g3 = U(); add("conditional", GroupingIdentifier=g3, WFControlFlowMode=0, WFCondition=99,
              WFInput={"Type": "Variable", "Variable": att(var("Route"))},
              WFConditionalActionString=tok(var("Key")))
setv("N", calc(var("N"), "+1"))
desc = replace(var("Repeat Item 2"), ZONE_RE, "$2 → $3, $5 km/h")
setv("Lines", text(var("Lines"), "\n• ", desc))
add("conditional", GroupingIdentifier=g3, WFControlFlowMode=2, UUID=U())
add("repeat.each", GroupingIdentifier=g2, WFControlFlowMode=2, UUID=U())

# "1 slow zone" / "3 slow zones"
plural = replace(replace(var("N"), r"^1$", ""), r"^[\d.]+$", "s")
g4 = U(); add("conditional", GroupingIdentifier=g4, WFControlFlowMode=0, WFCondition=99,
              WFInput={"Type": "Variable", "Variable": att(var("Lines"))}, WFConditionalActionString="•")
setv("Block", text("🐢 ", var("TripName"), ": ", var("N"), " slow zone", plural, var("Lines")))
add("conditional", GroupingIdentifier=g4, WFControlFlowMode=1)
setv("Block", text("✅ ", var("TripName"), ": no slow zones"))
add("conditional", GroupingIdentifier=g4, WFControlFlowMode=2, UUID=U())
setv("Report", text(var("Report"), var("Block"), "\n\n"))
add("repeat.each", GroupingIdentifier=g1, WFControlFlowMode=2, UUID=U())

add("showresult", Text=tok(var("Report"), var("Updated")))

wf = {
    "WFWorkflowClientVersion": "2607.0.3",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983, "WFWorkflowIconGlyphNumber": 59511},
    "WFWorkflowImportQuestions": [{
        "ActionIndex": 1, "Category": "Parameter", "ParameterKey": "WFTextActionText",
        "DefaultValue": DEFAULT_TRIPS,
        "Text": "Your trips, one per line: 'Name: station, station, …' in the order you ride (e.g. 'Work: Union, King, Queen'). Use TTC station names like TMU and Cedarvale."}],
    "WFWorkflowInputContentItemClasses": ["WFStringContentItem"],
    "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowTypes": [],
    "WFQuickActionSurfaces": [],
    "WFWorkflowHasShortcutInputVariables": True,
    "WFWorkflowActions": actions,
}
with open(sys.argv[1], "wb") as f:
    plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
print(len(actions), "actions")
