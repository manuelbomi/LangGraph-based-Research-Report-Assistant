"""Seed corpus for the demo knowledge base: history & fundamentals of
renewable energy.

This is a small, fixed, hand-written reference corpus (not scraped) so the
demo is self-contained, reproducible, and free of licensing concerns. It
exists purely to give the `knowledge_base` tool something real to retrieve
from the KB tool selection logic in `app/graph/nodes.py`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KBDocument:
    doc_id: str
    title: str
    text: str


KB_DOCUMENTS: list[KBDocument] = [
    KBDocument(
        doc_id="re-001",
        title="Defining Renewable Energy",
        text=(
            "Renewable energy comes from naturally replenishing sources -- sunlight, "
            "wind, moving water, geothermal heat, and biomass -- that are not "
            "depleted on human timescales, unlike finite fossil fuels (coal, oil, "
            "natural gas). Because these sources are continuously replenished, "
            "renewable energy systems generally produce far lower lifecycle "
            "greenhouse gas emissions than fossil generation, though manufacturing "
            "and land-use impacts still matter and vary by technology."
        ),
    ),
    KBDocument(
        doc_id="re-002",
        title="Early History: Wind and Water Power",
        text=(
            "Humans harnessed renewable energy long before electricity existed. "
            "Windmills were used in Persia as early as the 9th century for grinding "
            "grain and pumping water, and spread to Europe by the 12th century. "
            "Waterwheels date back over two thousand years and powered mills across "
            "the ancient and medieval world. The first electricity-generating wind "
            "turbine was built by Scottish engineer James Blyth in 1887; hydroelectric "
            "power followed shortly after, with the first hydroelectric plant opening "
            "at Niagara Falls in 1879 for arc lighting."
        ),
    ),
    KBDocument(
        doc_id="re-003",
        title="Solar Photovoltaics: From Lab to Grid Scale",
        text=(
            "The photovoltaic effect was first observed by Edmond Becquerel in 1839, "
            "but practical silicon solar cells were not developed until Bell Labs "
            "demonstrated a 6%-efficient cell in 1954. Early use was largely limited "
            "to spacecraft due to high cost. Decades of manufacturing scale-up and "
            "research drove costs down roughly 90% between 2010 and 2020, making "
            "utility-scale solar one of the cheapest sources of new electricity "
            "generation in much of the world by the early 2020s. Modern commercial "
            "panels typically convert 18-22% of incident sunlight to electricity."
        ),
    ),
    KBDocument(
        doc_id="re-004",
        title="Modern Wind Power",
        text=(
            "Modern utility-scale wind turbines convert kinetic energy in moving air "
            "into electricity via rotor blades connected to a generator. Turbine "
            "capacity has grown enormously: early 1980s turbines produced tens of "
            "kilowatts, while modern offshore turbines exceed 12-15 megawatts per "
            "unit. Offshore wind benefits from stronger, steadier winds than onshore "
            "sites but costs more to install and maintain due to marine foundations "
            "and subsea cabling. Wind is now one of the fastest-growing electricity "
            "sources globally, alongside solar."
        ),
    ),
    KBDocument(
        doc_id="re-005",
        title="Hydropower and Pumped Storage",
        text=(
            "Hydropower generates electricity by passing water through turbines, "
            "typically from a dam-created reservoir or a run-of-river installation. "
            "It is the largest source of renewable electricity globally by installed "
            "capacity and can respond quickly to demand changes, making it valuable "
            "for grid stability. Pumped-storage hydropower acts as a large-scale "
            "battery: excess electricity pumps water uphill to a reservoir, which is "
            "later released downhill through turbines to generate power on demand, "
            "making it the dominant form of grid-scale energy storage in use today."
        ),
    ),
    KBDocument(
        doc_id="re-006",
        title="Geothermal Energy",
        text=(
            "Geothermal energy taps heat stored beneath the Earth's surface, most "
            "commonly at tectonically active sites where hot water or steam "
            "reservoirs are close enough to the surface to be economically drilled. "
            "The world's first geothermal power plant began operating at "
            "Larderello, Italy, in 1904. Geothermal provides steady, always-available "
            "('baseload') power unlike variable solar and wind, but is geographically "
            "limited to regions with suitable underground heat and permeability, "
            "such as Iceland, parts of the western United States, and Indonesia."
        ),
    ),
    KBDocument(
        doc_id="re-007",
        title="Biomass and Bioenergy",
        text=(
            "Biomass energy comes from burning or converting organic material -- wood, "
            "agricultural residue, dedicated energy crops, or organic waste -- into "
            "heat, electricity, or liquid biofuels such as ethanol and biodiesel. "
            "Biomass is considered renewable because the carbon released was recently "
            "absorbed from the atmosphere by the growing plant, though the net "
            "climate benefit depends heavily on how the biomass is sourced, whether "
            "land-use change is involved, and combustion efficiency."
        ),
    ),
    KBDocument(
        doc_id="re-008",
        title="Tidal and Wave Energy",
        text=(
            "Tidal energy captures the predictable rise and fall of ocean tides, "
            "typically using underwater turbines (tidal stream) or barrages across "
            "estuaries. Wave energy converters instead capture the up-and-down or "
            "back-and-forth motion of surface waves. Both remain far less mature and "
            "more expensive than wind or solar, with only a handful of commercial-"
            "scale installations worldwide, such as the Sihwa Lake tidal station in "
            "South Korea and the MeyGen tidal stream array in Scotland. Their key "
            "advantage is predictability: unlike wind and solar, tidal timing can be "
            "forecast years in advance from astronomical cycles."
        ),
    ),
    KBDocument(
        doc_id="re-009",
        title="Energy Storage and Grid Integration",
        text=(
            "Because solar and wind output varies with weather and time of day, "
            "integrating large shares of them onto the electricity grid requires "
            "either flexible backup generation, transmission to move power between "
            "regions, demand-side flexibility, or energy storage. Lithium-ion battery "
            "storage costs fell roughly 80% between 2013 and 2023, making short-"
            "duration (2-4 hour) battery storage increasingly common alongside solar "
            "farms. Longer-duration storage needs -- covering multi-day lulls -- remain "
            "an active area of technology development, including flow batteries, "
            "compressed air, and green hydrogen."
        ),
    ),
    KBDocument(
        doc_id="re-010",
        title="Policy Drivers: Feed-in Tariffs and Tax Credits",
        text=(
            "Government policy has strongly shaped renewable energy adoption. "
            "Feed-in tariffs, pioneered in Germany's 2000 Renewable Energy Sources "
            "Act, guarantee producers a fixed above-market price for renewable "
            "electricity, providing investment certainty that drove early solar and "
            "wind deployment in Europe. In the United States, the Investment Tax "
            "Credit (ITC) and Production Tax Credit (PTC) have similarly offset "
            "capital costs since the 1990s and 2000s respectively. Carbon pricing "
            "and renewable portfolio standards (minimum renewable-share mandates for "
            "utilities) are two other common policy levers used worldwide."
        ),
    ),
    KBDocument(
        doc_id="re-011",
        title="Global Growth Trends",
        text=(
            "Renewable electricity generation has grown from a small fraction of the "
            "global mix in the 1990s to roughly 30% of global electricity generation "
            "by the early 2020s, driven mainly by solar and wind. The International "
            "Energy Agency has repeatedly revised its renewable growth forecasts "
            "upward as deployment consistently outpaced earlier projections, a pattern "
            "attributed to continued cost declines and supportive policy. China, the "
            "United States, and the European Union have been the largest markets for "
            "new renewable capacity additions in recent years."
        ),
    ),
    KBDocument(
        doc_id="re-012",
        title="Common Criticisms and Limitations",
        text=(
            "Renewable energy is not without trade-offs. Solar and wind are "
            "intermittent and weather-dependent, requiring grid flexibility or "
            "storage to maintain reliability at high penetration. Manufacturing "
            "panels, turbines, and batteries requires mined materials (silicon, "
            "rare earth elements, lithium, cobalt) with their own environmental and "
            "labor concerns. Large hydropower and some wind or solar farms can "
            "disrupt local ecosystems and communities. These limitations are widely "
            "studied and are a normal part of energy-system planning rather than "
            "arguments against renewables outright; they inform decisions about "
            "energy mix, siting, and storage investment."
        ),
    ),
]
