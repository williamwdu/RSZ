# Slow Zone Check

A one-page site that helps Toronto subway riders set up an Apple Shortcut showing which TTC reduced speed zones are on their commute.

- **The page** (`index.html`) lets people pick their trips (From/To, with automatic Line 1 ↔ Line 2 transfers), copies them, and links to the shortcut.
- **The shortcut** (`TTC Slow Zones.shortcut`) downloads the TTC's [Reduced Speed Zones](https://www.ttc.ca/riding-the-ttc/Updates/Reduced-Speed-Zones) page on the rider's own phone each time it runs, finds the zones on each trip, and shows the result.
- Nothing is hosted or republished here: no TTC data, no server, no tracking. Trips are saved only in the visitor's browser.

## Repo layout

```
index.html                  the site
TTC Slow Zones.shortcut     the shortcut (replace with the SIGNED version before publishing)
tools/make_shortcut.py      regenerates the unsigned shortcut
tools/simulate.py           runs the shortcut's logic against a mock of the TTC page
```

## 1. Sign the shortcut (on your Mac)

iPhones only import shortcuts that Apple has signed. The file in this repo starts **unsigned**.

```sh
cd path/to/this/repo
shortcuts sign --mode anyone --input "TTC Slow Zones.shortcut" --output signed.shortcut
mv signed.shortcut "TTC Slow Zones.shortcut"
```

Then **test it before publishing**: double-click the file, add it, and run it once on your iPhone (tap Allow for ttc.ca). You should see something like:

```
🐢 Work: 2 slow zones
• St Clair West → Dupont, 25 km/h
• Union → King, 20 km/h
```

Keep the file name `TTC Slow Zones.shortcut`. The page links to that name, and the "Check my trips now" button runs the shortcut by that name.

## 2. Publish with GitHub Pages

1. Create a public repo and push these files.
2. Repo **Settings → Pages → Build and deployment → Deploy from a branch**, branch `main`, folder `/ (root)`.
3. Your site will be at `https://<you>.github.io/<repo>/`.

## How trips work

The shortcut gets trips as text, one per line, stations in the order you ride:

```
Work: Cedarvale, St Clair West, Dupont, Spadina, St George, Museum, Queen's Park, St Patrick, Osgoode, St Andrew, Union, King
```

A slow zone counts when its two stations appear next to each other **in the same order** as on the trip, so direction comes for free. Capitals, spaces and punctuation are ignored.

Trips come from either:
- the text pasted at install (the first Text action), used for Siri, automations and the Shortcuts app, or
- the page's **Check my trips now** button, which runs the shortcut with the page's trips through `shortcuts://run-shortcut?...&input=text`.

## Changing the shortcut

Edit `tools/make_shortcut.py`, then:

```sh
python3 tools/make_shortcut.py "TTC Slow Zones.shortcut"
python3 tools/simulate.py "TTC Slow Zones.shortcut"     # check the output looks right
```

…and sign again (step 1). Any change to the file means signing again.

## If it breaks

- **0 zones for every trip, or an error:** the TTC probably changed its page. In Shortcuts, add a Quick Look after the third *Replace Text* action. It should show text like `|Northbound Union to King|168|454|…`. Update the zone pattern (`ZONE_RE` in `tools/make_shortcut.py`) to match. Note: on iPhone, Shortcuts hands the page over as plain text (one table cell per line), not raw HTML. The parser handles both, and `PAGE_MODE=text python3 tools/simulate.py …` tests the plain-text form.
- **Wrong speed shown:** a table column was added or removed. Same fix.
- **A variable shows as missing inside the second loop:** tap it and pick *Repeat Item 2*.

## Notes

- Lines 1 and 2 only. The TTC page currently lists zones on those lines.
- St George → Spadina is the only pair of stations both lines run between in the same order, so a zone there could be counted for the wrong line.
- Not affiliated with or endorsed by the TTC. Don't use TTC logos.
