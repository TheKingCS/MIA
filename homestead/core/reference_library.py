"""
MIA Homestead — Aquaponics & Greenhouse Reference Library
v0.1

Real gap: this system is grounded entirely in live operational data —
correctly so for "what's happening in my greenhouse right now," but it
left a whole category of legitimate questions with nowhere real to go:
general aquaponics/greenhouse science ("why does pH matter here?",
"what's a reasonable stocking density?", "what causes algae blooms?").
Without a real source for these, a local model asked one of them would
either wrongly say "no data" (this was never a live-data question) or,
worse, freelance an answer from its own uncontrolled pretraining —
exactly the fabrication failure mode this project's whole tool-
grounding discipline (_annotate_if_empty, the system prompt's anti-
fabrication rule) exists to prevent, just via a path that discipline
didn't cover yet.

Same two-part shape as core/pest_disease.py and core/species_registry.py
(a real, seeded knowledge base), but broader in scope — general
technique and science, not symptom diagnosis, which pest_disease.py
already owns. Content below is written fresh, in my own words, from
well-established, widely-taught aquaponics/greenhouse science —
general guidelines and consensus ranges, not attributed to or copied
from any specific textbook, and hedged as "typical"/"a common
guideline" rather than false precision where the real literature
itself reports a range, not one exact number.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.reference_library")

BASELINE_TOPICS = [
    # ---------- Nitrogen cycle ----------
    {
        "category": "nitrogen_cycle", "title": "The Nitrogen Cycle in Aquaponics",
        "summary": "Fish waste (ammonia) is converted by two groups of bacteria — first to nitrite, "
                    "then to nitrate — which plants can actually use as fertilizer.",
        "detail": "Fish excrete ammonia (NH3/NH4+) directly into the water. Nitrosomonas bacteria "
                   "oxidize ammonia into nitrite (NO2-), which is toxic to fish at much lower "
                   "concentrations than ammonia. Nitrobacter and Nitrospira bacteria then oxidize "
                   "nitrite into nitrate (NO3-), which is far less toxic and is the form of "
                   "nitrogen plants actually absorb through their roots. This two-step conversion "
                   "is why a new system needs time to 'cycle' before it can safely support fish at "
                   "normal stocking density — the bacteria colonies take weeks to establish.",
        "keywords": "nitrogen cycle,ammonia,nitrite,nitrate,nitrosomonas,nitrobacter,nitrospira,biofilter,bacteria",
    },
    {
        "category": "nitrogen_cycle", "title": "Cycling a New System (Fishless Cycling)",
        "summary": "Before adding fish, most guides recommend dosing pure ammonia into the system "
                    "and tracking ammonia/nitrite/nitrate until nitrite and ammonia both read zero "
                    "and nitrate is present — typically 4-6 weeks.",
        "detail": "Fishless cycling avoids stressing or risking real fish during the weeks it takes "
                   "the nitrifying bacteria colonies to establish. The general pattern: ammonia "
                   "rises first (since nothing is consuming it yet), then nitrite rises as "
                   "Nitrosomonas bacteria establish and start converting ammonia, then nitrite "
                   "falls and nitrate rises as Nitrobacter/Nitrospira establish. A system is "
                   "usually considered cycled once it can process a real ammonia dose down to "
                   "near-zero ammonia AND near-zero nitrite within 24 hours, consistently across "
                   "more than one test — a single clean reading isn't enough to be confident the "
                   "colony is actually established, not just a fluke reading.",
        "keywords": "cycling,fishless cycling,new system,startup,establish biofilter",
    },
    # ---------- Water chemistry ----------
    {
        "category": "water_chemistry", "title": "Why pH Matters in Aquaponics",
        "summary": "Fish, plants, and nitrifying bacteria each prefer a different pH range, so "
                    "aquaponics runs a compromise — commonly 6.8-7.2 — rather than any one "
                    "organism's ideal.",
        "detail": "Most fish tolerate pH roughly 6.5-8.0. Most plants prefer slightly acidic water, "
                   "roughly 5.5-6.5, for best nutrient uptake. Nitrifying bacteria work best in a "
                   "more alkaline range, roughly 7.0-9.0, and nitrification itself slows "
                   "significantly below pH 6.0. Because all three share the same water in "
                   "aquaponics (unlike separate hydroponics and aquaculture systems), most "
                   "aquaponics guidance settles on a compromise range around 6.8-7.2 — not "
                   "perfectly ideal for any one organism, but workable for all three. pH also "
                   "directly affects how toxic ammonia is: un-ionized ammonia (the toxic form) "
                   "becomes more dominant at higher pH and higher temperature, so a high-pH, "
                   "warm system is more dangerous at a given total ammonia reading than a cooler, "
                   "lower-pH one.",
        "keywords": "pH,acidity,alkalinity,compromise range,ideal pH",
    },
    {
        "category": "water_chemistry", "title": "Understanding EC (Electrical Conductivity)",
        "summary": "EC measures the concentration of dissolved nutrient ions in the water — "
                    "roughly, 'how much fertilizer is actually in solution' — not any single "
                    "nutrient specifically.",
        "detail": "EC (electrical conductivity, often in uS/cm or mS/cm) rises as more dissolved "
                   "salts/nutrients are in the water and falls as plants consume them or as water "
                   "is diluted. It's a useful proxy for overall nutrient concentration but doesn't "
                   "tell you WHICH nutrient is high or low — two systems can have identical EC "
                   "with very different actual nutrient balances. Leafy greens generally tolerate "
                   "a wide EC range; fruiting crops (tomatoes, peppers) typically want higher EC "
                   "than leafy greens can tolerate, which is part of why fruiting crops are harder "
                   "to grow well in a fish-limited aquaponics system — fish waste alone often "
                   "can't push EC as high as those crops want without overstocking the fish.",
        "keywords": "EC,electrical conductivity,nutrients,fertilizer concentration,TDS",
    },
    {
        "category": "water_chemistry", "title": "Dissolved Oxygen Basics",
        "summary": "Dissolved oxygen (DO) is critical for fish, for root health, and for the "
                    "nitrifying bacteria themselves — a DO crash can harm all three at once.",
        "detail": "Fish breathe dissolved oxygen through their gills; most warm-water aquaponics "
                   "fish (tilapia, catfish) do reasonably well above roughly 5 mg/L, with real "
                   "stress and risk of suffocation as DO drops toward 2-3 mg/L or below. Plant "
                   "roots also need oxygen — waterlogged, low-DO root zones are a common real cause "
                   "of root rot, not just overwatering. The nitrifying bacteria that run the "
                   "nitrogen cycle are aerobic too, so a sustained DO crash can knock back the "
                   "biofilter's capacity right when ammonia is already a risk. Aeration (air stones, "
                   "venturi injectors, waterfalls/splash return) and adequate circulation are the "
                   "usual ways DO is maintained; warmer water holds less dissolved oxygen than "
                   "cooler water at the same aeration rate, which is part of why warm systems are "
                   "more DO-sensitive.",
        "keywords": "dissolved oxygen,DO,aeration,oxygen,suffocation,root rot,hypoxia",
    },
    {
        "category": "water_chemistry", "title": "Ammonia and Nitrite Toxicity",
        "summary": "Both are dangerous to fish well below levels that are visibly obvious — ammonia "
                    "toxicity gets worse at higher pH and temperature; nitrite interferes with a "
                    "fish's ability to carry oxygen in its blood.",
        "detail": "Total ammonia readings include both the toxic un-ionized form (NH3) and the far "
                   "less toxic ionized form (NH4+) — the ratio between them shifts with pH and "
                   "temperature, so the SAME total-ammonia number is more dangerous in warmer, "
                   "higher-pH water. Most guidance treats any sustained detectable ammonia in a "
                   "stocked system as a real problem worth investigating, not just a number to "
                   "watch. Nitrite is dangerous through a different mechanism — it interferes with "
                   "hemoglobin's ability to carry oxygen (sometimes called 'brown blood disease'), "
                   "so nitrite-stressed fish can show oxygen-starvation symptoms even with normal "
                   "dissolved oxygen in the water. Both are the two things a fishless cycle (see "
                   "that entry) is specifically working to establish real bacterial capacity "
                   "against before fish are added.",
        "keywords": "ammonia toxicity,nitrite toxicity,brown blood disease,un-ionized ammonia,fish poisoning",
    },
    {
        "category": "water_chemistry", "title": "Water Hardness, Alkalinity, and pH Drift",
        "summary": "Nitrification consumes alkalinity, which is why aquaponics systems tend to "
                    "drift toward lower pH over time even without anyone adding anything acidic.",
        "detail": "Alkalinity (often measured as KH, carbonate hardness) is the water's buffering "
                   "capacity — its ability to resist pH swings. The nitrification process itself "
                   "consumes alkalinity as a byproduct of converting ammonia to nitrate, which is "
                   "the real, well-documented reason a healthy, actively-cycling aquaponics system "
                   "tends to drift toward more acidic pH over time on its own, not because of "
                   "anything going wrong. This is part of why pH-up dosing is a normal, expected, "
                   "ongoing part of running a mature aquaponics system rather than a one-time "
                   "correction — and why a system that suddenly stops needing pH-up at all is "
                   "itself worth investigating (it could mean nitrification has slowed or stalled).",
        "keywords": "alkalinity,KH,water hardness,buffering,pH drift,pH down over time",
    },
    # ---------- Stocking ----------
    {
        "category": "stocking", "title": "Fish Stocking Density Guidelines",
        "summary": "A common beginner guideline is roughly 0.5-1 lb of fish per 5-10 gallons of "
                    "water — overstocking, not understocking, is the most common beginner mistake.",
        "detail": "Real safe stocking density depends heavily on filtration capacity, aeration, "
                   "species, and system maturity, so any single number is a starting guideline, not "
                   "a hard rule — commonly cited beginner ranges run from roughly 0.5 lb of fish "
                   "per 5-10 gallons of system water, well below the higher densities experienced, "
                   "well-instrumented commercial operations can sometimes sustain with heavier "
                   "aeration and filtration. Overstocking is the single most common beginner "
                   "mistake in aquaponics — it doesn't just stress the fish, it overwhelms the "
                   "biofilter's real capacity to process the resulting ammonia load, which is what "
                   "actually causes most beginner ammonia/nitrite crises, not any one bad water "
                   "change or feeding.",
        "keywords": "stocking density,how many fish,overstocking,fish per gallon",
    },
    {
        "category": "stocking", "title": "Choosing Fish Species for Aquaponics",
        "summary": "Tilapia is the most common beginner choice (hardy, fast-growing, tolerant of "
                    "variable water quality); catfish and koi/goldfish are common alternatives with "
                    "different tradeoffs.",
        "detail": "Tilapia is widely chosen for beginner and commercial aquaponics because it's "
                   "unusually tolerant of imperfect water quality and a wide pH/temperature range "
                   "compared to many food fish, grows quickly, and is a real food fish (not purely "
                   "ornamental) — but it's a warm-water species (generally wants water above "
                   "roughly 60F, ideally warmer) and is illegal to keep in some jurisdictions as an "
                   "invasive-species precaution, worth checking locally before choosing it. Catfish "
                   "are another hardy, tolerant warm-water food-fish option. Koi and goldfish are "
                   "popular where the goal is ornamental rather than food (or a beginner learning "
                   "system before committing to a food fish) — more cold-tolerant, but not "
                   "typically eaten. Trout are a real cold-water option but are generally more "
                   "demanding of consistently high dissolved oxygen and cooler, stable water "
                   "temperatures than the warm-water species above.",
        "keywords": "fish species,tilapia,catfish,koi,goldfish,trout,which fish",
    },
    {
        "category": "stocking", "title": "Fish-to-Plant Ratio (Grow Bed Sizing)",
        "summary": "A common starting guideline is roughly 1:1 to 1:2 fish-tank-gallons to grow-bed "
                    "square feet, though the right ratio depends on stocking density and crop choice.",
        "detail": "The grow bed (or equivalent hydroponic component) needs to be sized to both "
                   "process the nutrient load the fish produce AND give the biofilter (whether a "
                   "dedicated component or the media bed itself) enough surface area to support "
                   "nitrification. A commonly cited beginner starting ratio is roughly 1:1 to 1:2 "
                   "— tank gallons to grow bed square feet — as a starting point to size around, "
                   "adjusted from there based on real observed plant growth and water quality once "
                   "the system is actually running, not treated as a fixed final answer.",
        "keywords": "fish to plant ratio,grow bed sizing,tank to bed ratio,system sizing",
    },
    # ---------- Plant care ----------
    {
        "category": "plant_care", "title": "Best Plants for Aquaponics",
        "summary": "Leafy greens and herbs are the easiest, lowest-nutrient-demand crops for "
                    "aquaponics; fruiting crops like tomatoes need more nutrients than fish waste "
                    "alone often provides; root crops generally don't do well in media-free setups.",
        "detail": "Lettuce, basil, kale, and similar leafy greens/herbs are the most commonly "
                   "recommended beginner crops — they have relatively low nutrient demand, grow "
                   "quickly, and tolerate the EC range fish waste alone typically produces. "
                   "Fruiting crops (tomatoes, peppers, cucumbers) generally want higher nutrient "
                   "concentrations, particularly potassium and calcium, than a fish-waste-only "
                   "system easily supplies without overstocking fish — commercial and advanced "
                   "aquaponics setups growing these crops often supplement with additional mineral "
                   "nutrients rather than relying on fish waste alone. Root vegetables (carrots, "
                   "potatoes) are generally not well-suited to media-free techniques (DWC, NFT) "
                   "since they need something to actually form a root bulb/tuber in — a deep media "
                   "bed is the more workable aquaponics technique for them, still less common than "
                   "leafy greens.",
        "keywords": "what to grow,best plants,leafy greens,fruiting crops,tomatoes,root vegetables",
    },
    {
        "category": "plant_care", "title": "Nutrient Deficiencies in Aquaponics",
        "summary": "Yellowing older leaves often signals nitrogen deficiency; yellowing between "
                    "leaf veins with veins staying green often signals iron deficiency, which is "
                    "commonly a pH-lockout problem rather than an actual absence of iron.",
        "detail": "General (not aquaponics-specific) plant deficiency patterns: nitrogen deficiency "
                   "typically shows as overall yellowing starting with older/lower leaves first "
                   "(nitrogen is mobile within the plant, so it's pulled from older growth to "
                   "support new growth). Iron deficiency typically shows as interveinal chlorosis — "
                   "yellowing BETWEEN leaf veins while the veins themselves stay green — usually on "
                   "newer growth first (iron is not very mobile within the plant). In aquaponics "
                   "specifically, iron 'deficiency' is very often actually iron LOCKOUT — iron is "
                   "present in the water but becomes chemically unavailable to plant roots at "
                   "higher pH, which is part of why chronically running pH noticeably above the "
                   "typical aquaponics range can produce iron-deficiency symptoms even with "
                   "adequate iron in solution. Purple/reddish leaf discoloration is a commonly "
                   "cited phosphorus-deficiency sign in general horticulture.",
        "keywords": "nutrient deficiency,yellowing leaves,iron chlorosis,iron lockout,nitrogen deficiency,phosphorus",
    },
    {
        "category": "plant_care", "title": "Media Bed vs. DWC vs. NFT",
        "summary": "The three common aquaponics growing techniques trade off differently on cost, "
                    "root support, and which crops they suit.",
        "detail": "Media bed (grow bed filled with an inert media like expanded clay) doubles as "
                   "mechanical/biological filtration and can support a wider range of crops "
                   "including some root vegetables, but is heavier and can be harder to fully clean "
                   "out between crops. DWC (deep water culture / raft) floats plants in net pots on "
                   "a foam raft over an aerated tank of nutrient-rich water — good for leafy greens "
                   "at scale, needs its own dedicated aeration and generally needs a separate "
                   "biofilter/mechanical filtration stage since the raft tank itself isn't doing "
                   "that job. NFT (nutrient film technique) runs a thin film of water through "
                   "sloped channels past bare roots — efficient use of water and space, but roots "
                   "are more exposed if flow stops even briefly (a pump failure is more urgent in "
                   "NFT than in a media bed, which retains more moisture on its own).",
        "keywords": "media bed,DWC,deep water culture,raft,NFT,nutrient film technique,growing technique",
    },
    # ---------- Climate (greenhouse) ----------
    {
        "category": "climate", "title": "Greenhouse Ventilation Basics",
        "summary": "Air exchange manages temperature, humidity, and CO2 all at once — poor "
                    "ventilation is a common root cause behind fungal disease, heat stress, and "
                    "stunted growth that each look like separate problems.",
        "detail": "Ventilation (passive — roof/side vents relying on convection, or active — "
                   "exhaust fans) does several jobs simultaneously: it vents excess heat on sunny "
                   "days, it removes excess humidity that would otherwise linger on leaf surfaces "
                   "and encourage fungal disease (like powdery mildew), and it exchanges CO2-"
                   "depleted air near the plant canopy (photosynthesis draws down CO2 faster than "
                   "still air replaces it) for fresher air. Because it affects all three at once, "
                   "chronically poor ventilation can produce symptoms that look unrelated — some "
                   "plants heat-stressed, others showing fungal spotting, growth generally slower "
                   "than expected — when the actual root cause is airflow, not three separate "
                   "problems.",
        "keywords": "ventilation,airflow,greenhouse humidity,heat venting,exhaust fan",
    },
    {
        "category": "climate", "title": "Supplemental CO2 for Plant Growth",
        "summary": "Ambient CO2 (roughly 400-420 ppm outdoor air) is often the limiting factor for "
                    "plant growth in a sealed, sunny greenhouse — but CO2 enrichment has a real, "
                    "hard human-safety ceiling, not just a plant-benefit curve.",
        "detail": "In a well-lit, well-fertilized, temperature-controlled greenhouse, ambient CO2 "
                   "can become the actual bottleneck on photosynthesis rate, which is why "
                   "commercial greenhouses sometimes enrich CO2 to roughly 800-1200 ppm to push "
                   "growth further. This is real horticultural practice, but it has a hard ceiling "
                   "that has nothing to do with plants: OSHA's 8-hour permissible exposure limit "
                   "for human CO2 exposure is 5000 ppm — well above what plants need, but a real, "
                   "binding human-safety limit that any CO2 enrichment system needs to respect, "
                   "not just a suggested target to optimize toward.",
        "keywords": "CO2,carbon dioxide,CO2 enrichment,supplemental CO2,OSHA CO2 limit",
    },
    {
        "category": "climate", "title": "Managing Greenhouse Humidity",
        "summary": "Plants transpire moisture into the air constantly, so a sealed greenhouse "
                    "tends toward high humidity on its own — too high raises fungal disease risk, "
                    "too low stresses plants through excess water loss.",
        "detail": "Relative humidity in the roughly 50-70% range is a commonly cited comfortable "
                   "middle ground for many greenhouse crops, though the right target varies by "
                   "species and growth stage. Sustained high humidity (especially combined with "
                   "still air — see ventilation) is a common real driver of fungal disease like "
                   "powdery mildew and botrytis, since standing moisture on leaf surfaces is what "
                   "many fungal pathogens actually need to establish. Sustained low humidity "
                   "increases how fast plants lose water through transpiration, which can stress "
                   "plants even when the root zone itself has adequate water, since the roots "
                   "can't always keep up with a very high transpiration demand.",
        "keywords": "humidity,relative humidity,fungal disease,transpiration,condensation",
    },
    {
        "category": "climate", "title": "Frost Protection Basics",
        "summary": "Thermal mass (large volumes of water are a classic passive option), row "
                    "covers, and active heating are the three common layers of frost protection, "
                    "often combined rather than relying on just one.",
        "detail": "Water has a high thermal mass — it absorbs heat during the day and releases it "
                   "slowly overnight, which is a big part of why aquaponics/greenhouse systems with "
                   "large tanks of water have some natural frost buffering that a purely dry "
                   "greenhouse doesn't. Row covers or thermal curtains add a passive insulating "
                   "air layer over more frost-sensitive plants specifically. Active heating (the "
                   "real fallback when passive measures aren't enough for a genuinely hard freeze) "
                   "is the most reliable option but the most costly to run continuously. Most real "
                   "frost-protection plans layer more than one of these rather than relying on a "
                   "single method, since each has a different failure mode.",
        "keywords": "frost protection,freeze,cold snap,thermal mass,row cover,winter greenhouse",
    },
    # ---------- Troubleshooting ----------
    {
        "category": "troubleshooting", "title": "Common Causes of Algae Blooms",
        "summary": "Algae needs light and nutrients to grow, same as any plant — a bloom almost "
                    "always means both are available somewhere they shouldn't be, most often "
                    "sunlit water with dissolved nutrients in it.",
        "detail": "The most common real cause is light reaching nutrient-rich water directly — an "
                   "uncovered fish tank or sump in a sunny spot, or a grow bed with too much light "
                   "reaching the water surface rather than being absorbed by plant canopy first. "
                   "The fix that actually addresses the cause is blocking light from reaching open "
                   "water (opaque tank covers, siting away from direct sun, denser plant canopy "
                   "shading the water below it) rather than only treating the symptom once a bloom "
                   "is already established. Algae in the fish tank specifically can also complicate "
                   "water chemistry readings (some algae photosynthesis/respiration cycles can "
                   "shift dissolved oxygen and pH over a day/night cycle), which is worth knowing "
                   "before assuming a fluctuating reading is a sensor or dosing problem.",
        "keywords": "algae,algae bloom,green water,too much light",
    },
    {
        "category": "troubleshooting", "title": "Why Fish Might Stop Eating",
        "summary": "Poor water quality is the most common real cause, but water temperature "
                    "swings, stress, and early disease are also common — reduced appetite is often "
                    "the earliest visible sign something's wrong, before other symptoms appear.",
        "detail": "Fish reducing or stopping feeding is frequently one of the EARLIEST visible "
                   "signs of a real problem — by the time more obvious symptoms (visible spots, "
                   "lethargy, gasping at the surface) appear, whatever caused the appetite change "
                   "has often been building for a while. Real common causes, roughly in likelihood "
                   "order for an established system: a water quality problem (ammonia, nitrite, pH "
                   "swing, dissolved oxygen), a temperature swing (fish generally reduce feeding "
                   "as water temperature drops outside their comfortable range, more so than most "
                   "people expect), stress (a new tank-mate, a loud disturbance, recent handling), "
                   "or the early stage of a disease that hasn't shown other visible symptoms yet. "
                   "Checking water chemistry first, before assuming illness, is the generally "
                   "recommended first troubleshooting step since it's the most common cause and the "
                   "easiest to rule in or out quickly.",
        "keywords": "fish not eating,loss of appetite,fish stopped eating,feeding problem",
    },
    {
        "category": "troubleshooting", "title": "Diagnosing a Sudden Fish Die-Off",
        "summary": "An ammonia/nitrite spike or a dissolved-oxygen crash are the two most common "
                    "real causes of a sudden, multi-fish die-off — checking both immediately is the "
                    "generally recommended first step, before assuming disease.",
        "detail": "A die-off affecting many fish suddenly, rather than one fish over time, points "
                   "toward a shared water-quality event rather than an individual illness — "
                   "individual disease processes usually don't kill an entire stock simultaneously "
                   "the way a water chemistry crash can. The two most common real causes: an "
                   "ammonia or nitrite spike (from overfeeding, overstocking beyond biofilter "
                   "capacity, a biofilter that was recently disrupted, or dead organic matter "
                   "decaying unnoticed), or a dissolved oxygen crash (aeration equipment failure, "
                   "a power outage, or a sudden temperature spike reducing how much oxygen the "
                   "water can hold). Testing ammonia, nitrite, and dissolved oxygen immediately — "
                   "not after the fact — is the generally recommended first step, since a delayed "
                   "test can miss the actual spike if the underlying cause has already partly "
                   "resolved (e.g. aeration restored, or ammonia already partly reprocessed) by the "
                   "time testing happens.",
        "keywords": "fish die off,fish dying,mass mortality,fish kill,sudden death",
    },
]


class ReferenceLibrary(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn
        self._seed_if_empty()

    def _seed_if_empty(self):
        count = self.db.execute("SELECT COUNT(*) FROM reference_topics").fetchone()[0]
        if count > 0:
            return
        for t in BASELINE_TOPICS:
            self.db.execute(
                "INSERT INTO reference_topics (category, title, summary, detail, keywords, source) "
                "VALUES (?, ?, ?, ?, ?, 'baseline')",
                (t["category"], t["title"], t["summary"], t["detail"], t["keywords"]),
            )
        self.db.commit()
        logger.info("Seeded %d baseline reference topics", len(BASELINE_TOPICS))

    def search(self, query: str, limit: int = 3) -> list[dict]:
        """Real keyword search over title/summary/keywords — no
        semantic/vector search, this is a small curated table where a
        straightforward LIKE match is honest about what it's actually
        doing, not dressed up as smarter than it is. Scores by how many
        of the query's real words hit, so a multi-word query finds the
        most relevant topic(s) first, not just the first LIKE match."""
        self.db.row_factory = sqlite3.Row
        words = [w.strip().lower() for w in query.replace("?", " ").split() if len(w.strip()) > 2]
        if not words:
            return []
        rows = self.db.execute("SELECT * FROM reference_topics").fetchall()
        scored = []
        for row in rows:
            r = dict(row)
            haystack = f"{r['title']} {r['summary']} {r['keywords'] or ''}".lower()
            score = sum(1 for w in words if w in haystack)
            if score > 0:
                scored.append((score, r))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [r for _, r in scored[:limit]]

    def get_topic(self, topic_id: int) -> dict | None:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM reference_topics WHERE id = ?", (topic_id,)).fetchone()
        return dict(row) if row else None

    def add_topic(self, category: str, title: str, summary: str, detail: str = None,
                  keywords: str = None) -> int:
        cur = self.db.execute(
            "INSERT INTO reference_topics (category, title, summary, detail, keywords, source) "
            "VALUES (?, ?, ?, ?, ?, 'human_added')",
            (category, title, summary, detail, keywords),
        )
        self.db.commit()
        return cur.lastrowid

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="reference_library",
            display_name="Aquaponics & Greenhouse Reference Library",
            purpose=(
                "A real, curated knowledge base of general aquaponics/greenhouse science and "
                "technique — nitrogen cycle, water chemistry, stocking, plant care, climate, "
                "troubleshooting — for questions that aren't about live system state but still "
                "deserve a real, grounded answer instead of the model fabricating one or wrongly "
                "saying 'no data' to a question that was never about live data in the first place."
            ),
            data_produced=[f"{len(BASELINE_TOPICS)} curated reference topics across 7 categories"],
            actions_possible=[
                "search the reference library by keyword",
                "look up a specific topic",
                "add a new reference topic",
            ],
            limits_and_safety=(
                "Read/search only — never touches dosing, control, or any live-system decision. "
                "General guidance and typical/commonly-cited ranges, not tuned to this specific "
                "system's real sensors or species — get_current_status and species tools remain "
                "the source of truth for this system's actual live numbers; this library answers "
                "'why'/'what's typical' questions, not 'what is it right now' ones. Keyword search "
                "only, no semantic matching — described honestly as what it is, not oversold."
            ),
            example_questions=[
                "Why does pH matter in aquaponics?",
                "What's a reasonable fish stocking density?",
                "What causes algae blooms?",
            ],
            verification_evidence=["scenarios.py::scenario_reference_library_search"],
        )

    def describe_hardware_requirements(self) -> list:
        return []
