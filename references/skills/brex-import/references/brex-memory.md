# brex-memory.md — Merchant → Payee Override + Sub Category mappings

Confirmed merchant-to-vendor mappings for the **brex-import** skill's monthly imports. Append-only; entries should only be removed if Zayn explicitly says so.

**Schema (Hard-confirmed table):** Description contains | Payee Override | Sub Category Override | Confirmed | Reason
- Sub Category Override may be blank — when blank, the resolver's default applies (Travel Vendor → Other Travel Expenses, Office Vendor → Dues & Subscriptions, etc.). Fill it in only when the right answer differs from the default.

Last updated: 2026-07-20 (07-20 corrections added)

---

## How to use

For each qualifying row (column E blank AND column S = 0):

1. Pull merchant from column C (everything before "MASTERCARD").
2. Search this file in order: **Hard-confirmed mappings → This month's confirmed → Historical specific mappings → Historical fallback patterns**. Case-insensitive substring; longest matching pattern wins.
3. If a match is found, write the listed Payee Override into column J. **A hit here beats CLAUDE.md hard rules** — that's the whole point of this file (e.g., `Canyon Ranch Cafe` → The Venetian overrides the literal-match rule).
4. If no match here, fall through to `CLAUDE.md` workflow rules, then the description-based fallback at the bottom of this file, then best-guess (flag as low confidence).

---

## Hard-confirmed mappings

These are direct overrides confirmed by Zayn. Higher priority than anything else in this file.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `wlv mobile app ecomm` | Travel Vendor |  | 2026-05-20 | NOT "Mobil" gas station — the substring match was wrong. Treat as travel-related. |
| `Canyon Ranch Cafe` | The Venetian |  | 2026-05-21 | Specific-merchant override beats CLAUDE.md Rule 1's literal-match. Canyon Ranch Cafe is at The Venetian; book to the property even when "Venetian" isn't in the description string. |
| `Bouchon Bakery` | The Venetian |  | 2026-05-21 | Same as Canyon Ranch — specific-merchant override. `Bouchon At The Venetian` (literal match) and `Bouchon Bakery` (no literal match) both → The Venetian. |
| `Girls Who Code` | Girls Who Code |  | 2026-05-21 | Use recipient name, NOT "Charitable Contribution" (revised — see CLAUDE.md Rule 3). Treat charitable donations as ordinary merchants. |
| `Custom Ink` | Custom Ink |  | 2026-05-21 | T-shirt/swag printer. In vendor list or QBO will create on import. |
| `Certn` | Office Vendor |  | 2026-05-21 | Background-check service for hiring. Also matches `Certn (Formerly Credence) Background Screening`. This OVERRIDES the older "Credence → Food Vendor" historical entry below — that was a stale misclassification. |
| `Robertsons Pharmacy` | Travel Vendor |  | 2026-05-21 | Airport/travel-context pharmacy — treat as Travel Vendor, not Office Vendor. |
| `Poma Palazzo` | Food Vendor |  | 2026-05-21 | Restaurant whose name contains "Palazzo" but is NOT a charge at the Palazzo casino. Don't substring-match property names from merchant strings (see CLAUDE.md Rule 1, false-positive guard). |
| `Lake Effect` | Food Vendor |  | 2026-05-21 | Confirmed during April test run. |
| `MERPAGO*AXIRI` | Food Vendor |  | 2026-05-21 | MercadoPago payment processor; underlying merchant Axiri is a restaurant (user looked up). Reminder: for `MERPAGO*`, `PAY*`, `SQ*` and similar processor prefixes, look up the underlying merchant rather than guessing from the prefix. |
| `Counterpart` | Office Vendor |  | 2026-05-21 | Insurance SaaS (per user). NOT a restaurant despite the generic name. |
| `Pure` | Food Vendor |  | 2026-05-21 | Default to Food Vendor for small amounts. If amount is large (>$200), reconsider — could also be Travel Vendor. Flag in notes when seen. |
| `UKVI` | Office Vendor |  | 2026-05-21 | UK Visas & Immigration. Per CLAUDE.md Rule 7: gov/immigration fees → Office Vendor. |
| `Ministry of Home Affairs` | Office Vendor |  | 2026-05-21 | Per CLAUDE.md Rule 7: gov/immigration fees → Office Vendor. |
| `KERIAH GRI` | Food Vendor |  | 2026-05-21 | Truncated descriptor seen as `KERIAH GRI* (2 OF 2 PA…` — was a restaurant on a 2-installment payment (April 2026 data). NOT a payment-processor / office expense as I'd initially guessed. |
| `Philip Morris USA` | Travel Vendor |  | 2026-05-21 | Per Zayn's April 2026 call. Tiny amounts (e.g., $0.57) — likely a foreign-transaction or incidental fee from a travel-related purchase, not a real tobacco purchase. |
| `Lothian Buses` | Taxi Vendor |  | 2026-05-20 | Buses → Taxi Vendor (see CLAUDE.md rule 2). |
| `PayPal` | PayPal |  | 2026-05-20 | Clean spelling. Requires QBO rename of `Paypal_` → `PayPal` before import. |
| `Palace Station Race & Sports Book` | Travel Vendor | Meals & Entertainment | 2026-05-22 | Sportsbook entertainment expense — always Travel Vendor + M&E (confirmed Zayn 2026-05-22). |
| `Holafly` | Travel Vendor | Other Travel Expenses | 2026-05-22 | eSIM travel data service (international roaming). Not food despite the resolver's default. |
| `GoMoWorld` | Travel Vendor | Other Travel Expenses | 2026-05-22 | eSIM travel data service (international roaming). |
| `Sundries` | Travel Vendor | Other Travel Expenses | 2026-05-22 | Hotel-incidental "sundries" line items. Always travel context per Zayn's data. |
| `Cvent` | Office Vendor | Software Licenses | 2026-05-22 | Annual licensed event-management SaaS — Software Licenses, not Dues & Subscriptions. |
| `Weissgerber` | Food Vendor |  | 2026-05-26 | Weissgerber's Golden Mast — German restaurant in Okauchee Lake, WI. Brex truncates merchant string to `WEISSGERBER S GOLDEN M`. Confirmed Zayn 2026-05-26. |
| `QANTAS` | Qantas | Airfare | 2026-06-16 | Australian airline — map to the airline name (was Travel Vendor). Brex string `QANTASXXXXXXXX41055`. |
| `PUROWARSZA` | Hotel Vendor | Lodging | 2026-05-28 | Puro Hotel Warsaw (Poland), booked via Guestrs reservation platform — Brex string is `GUESTRS*PUROWARSZA`. Confirmed Zayn 2026-05-28. |
| `SOUTHWES` | Southwest Air | Airfare | 2026-06-16 | Airline raw descriptor (Zayn PDF). Brex truncates "Southwest". |
| `AMERICAN` | American Airlines | Airfare | 2026-06-16 | Airline raw descriptor. The airline, NOT American Express — if Amex fees ever appear, add a longer `American Express` entry (longest-match wins). Overrides the older inconsistent `American`→Travel Vendor. |
| `DELTA` | Delta | Airfare | 2026-06-16 | Airline raw descriptor; also covers `DELTA AIRLINES ONBOARD`. |
| `UNITED` | United Airlines | Airfare | 2026-06-16 | Airline raw descriptor (incl. `UA INFLT`). |
| `VIR` | Virgin Atlantic | Airfare | 2026-06-16 | Airline raw descriptor (Virgin Atlantic). Short pattern — longest-match guards collisions. |
| `KLM` | KLM | Airfare | 2026-06-16 | Airline raw descriptor. |
| `JETBLUE` | JetBlue | Airfare | 2026-06-16 | Airline raw descriptor. |
| `LUFTHAN` | Lufthansa | Airfare | 2026-06-16 | Airline raw descriptor (Lufthansa). |
| `BRITISH A` | British Airways | Airfare | 2026-06-16 | Airline raw descriptor. |
| `RYANAIR` | Ryanair | Airfare | 2026-06-16 | Airline raw descriptor. |
| `AIR CAN` | Air Canada | Airfare | 2026-06-16 | Airline raw descriptor. |
| `ALASKA A` | Alaska Air | Airfare | 2026-06-16 | Airline raw descriptor. |
| `AIR FRAN` | Air France | Airfare | 2026-06-16 | Airline raw descriptor. |
| `VUELING AHKA` | Vueling | Airfare | 2026-06-16 | Airline raw descriptor. |
| `ALLEGNT` | Allegiant | Airfare | 2026-06-16 | Airline raw descriptor (Allegiant). |
| `AERLING` | Aer Lingus | Airfare | 2026-06-16 | Airline raw descriptor. |
| `FRONTIER` | Frontier Air | Airfare | 2026-06-16 | Airline raw descriptor. |
| `AEROMEXICO` | AeroMexico | Airfare | 2026-06-16 | Airline raw descriptor. |
| `Shell` | Shell | Ground Transportation | 2026-07-01 | Gas/fuel station. Keep the exact vendor name (Rule 5 — Shell is in the vendor list) but always write Sub Category Override = Ground Transportation, consistent with the Gulf Oil / Chevron fuel treatment. Confirmed Zayn 2026-07-01. |

---

## This month's confirmed (May 2026)

User-confirmed mappings from the 15-row May file:

| Description contains | Payee Override | Notes |
|---|---|---|
| `Versa` | Food Vendor | Restaurant, NOT a software/rental company. |
| `Matteos Ristorante Italiano` | Food Vendor | Italian restaurant. |
| `Pro Shop at Wynn Golf Club` | Wynn Las Vegas | Property match. |
| `Gift Card Granny` | Office Vendor | Gift card marketplace (Wolfe, LLC). |
| `Equinox Hotel` | Hotel Vendor | Not in vendor list. |
| `Juliet Cocktail Room` | Food Vendor | Cocktail bar. |
| `Milo's Bocce Garden` | Food Vendor | Restaurant/bar. |
| `Bouchon At The Venetian` | The Venetian | Description literally contains "The Venetian" → match the property (CLAUDE.md rule 1). Bare `Bouchon` (without property name in the string) would be Food Vendor. |
| `Toast Transaction` | Food Vendor | Toast is the POS; underlying merchant is always a restaurant. |
| `Venetian / Palazzo Las Vegas` | The Venetian | Standalone hotel charge — keep as property match. |
| `The Capital Grille` | Food Vendor | Boston steakhouse; recurring big-ticket. Promoted from Brex (38) May 2026 run. |
| `Stephanies On Newbury` | Food Vendor | Boston Newbury St restaurant. Promoted from Brex (38) May 2026 run. |
| `Cousins BBQ` | Food Vendor | BBQ restaurant. Promoted from Brex (38) May 2026 run. |

---

## This month's confirmed (June 2026)

User-confirmed mappings from the 2026-06-02 feed-mode run (100 expenses, last 14 days). The bottom 4 entries reclassify Ayla Hourani purchases that the QBO "Aylab DE" rule (text=`Ayla`) blanket-matches into Marketing — user wants them as Food Vendor / M&E by default, pharmacy as Office Vendor. Note: until pipeline precedence is changed OR the QBO Aylab rule is tightened, these memory entries are reference-only — the cardholder rule still wins in feed mode.

| Description contains | Payee Override | Sub Category Override | Notes |
|---|---|---|---|
| `BIL*Cathleen Stone Isl` | Office Vendor | Office Supplies | Cathleen Stone Island consultant — Brex coded CONSULTANT_AND_CONTRACTOR (MCC 8931). $2,574 recurring. |
| `TOUR* CHICAGO RIVER` | Travel Vendor | Other Travel Expenses | Chicago river boat tour. Two $1,590 charges in this run. |
| `NAMI.ORG` | NAMI | Charitable Contribution | National Alliance on Mental Illness — charity per Rule 3 (recipient name as Payee). $1,046. |
| `IN *GREENLINE DEVICE` | Office Vendor | Office Supplies | Electronics vendor — Brex MCC 7399. |
| `BESTBUYCOM` | Office Vendor | Office Supplies | Best Buy online. |
| `ROBERTSON'S DRUG STORE` | Office Vendor | Office Supplies | Pharmacy/drug store — Office Vendor per user 2026-06-02. Distinct from the `Robertsons Pharmacy` Hard-confirmed entry (airport-context → Travel Vendor) — these are separate patterns. Currently overridden by the QBO Aylab DE cardholder rule. |
| `FOODHUB ST GEORGE ECOM` | Food Vendor | Meals & Entertainment | Bermuda food delivery service. Currently overridden by the QBO Aylab DE cardholder rule. |
| `SOMER'S SUPERMART` | Food Vendor | Meals & Entertainment | Supermarket. Currently overridden by the QBO Aylab DE cardholder rule. |
| `CUSTOMINK` | Custom Ink | Office Supplies | Confirmed Zayn 2026-06-02. Branded apparel/swag. Brex descriptor `CUSTOMINK LLC` (no space) failed to match the existing `Custom Ink` Hard-confirmed entry → defaulted Food Vendor. Keep exact vendor name (Rule 5) + Office Supplies sub-cat. |
| `Audible` | Office Vendor | Dues & Subscriptions | Confirmed Zayn 2026-06-02. Audiobook subscription — recurring SaaS, not a meal. Was guessed Food Vendor. |
| `Dependable Cleaners` | Office Vendor | Office Supplies | Confirmed Zayn 2026-06-02. Dry cleaning / laundry service, not food. Was guessed Food Vendor. |
| `BCY* BLACKWOLFRUN` | Food Vendor |  | web: Blackwolf Run golf resort restaurant, Kohler WI (Kohler Co. property) — food/beverage charges at resort. |
| `BLACKWOLFRUN` | Food Vendor |  | web: Blackwolf Run golf resort restaurant, Kohler WI — catches bare descriptor variant. |
| `BUREAU OF WORKERS COMP` | Office Vendor | Dues & Subscriptions | web: State Workers' Compensation Bureau — insurance/regulatory payment, NOT food. |
| `DIG` | Food Vendor |  | Confirmed Zayn 2026-06-23. DIG restaurant chain — matched by MCC 5814. |

---

## Historical specific mappings (≥2 occurrences across 5 months, ≥80% consistent)

Promoted from 1,072 historical resolved transactions across the April 2026 weekly files + this month.

| Description contains | Payee Override | Seen |
|---|---|---|
| `Uber HQ` | Uber | 148 |
| `Claude` | Claude.AI | 91 |
| `Amazon Marketplace US` | Amazon | 27 |
| `Uber Cash` | Uber | 25 |
| `Starbucks` | Starbucks | 21 |
| `Uber Eats` | Uber Eats | 18 |
| `Southwest Airlines` | Southwest Air | 16 |
| `Tatte Bakery and Cafe` | Tatte | 13 |
| `Sweetgreen` | Sweetgreen | 12 |
| `McDonald's` | McDonald's | 11 |
| `Amazon` | Amazon | 10 |
| `Chick - fil - A` | Chick-Fil-A | 10 |
| `Chipotle Mexican Grill` | Chipotle | 10 |
| `Life Alive Organic Cafe` | Life Alive | 10 |
| `JW Marriott Atlanta Buckhead` | Marriott | 9 |
| `Wynn Las Vegas` | Wynn Las Vegas | 9 |
| `Boston Common Garage` | Boston Common Garage | 8 |
| `DoorDash` | Door Dash | 8 |
| `Thinking Cup Coffee Shop` | Thinking Cup | 7 |
| `Amtrak` | Amtrak | 6 |
| `Delta Airlines` | Delta | 6 |
| `Lyft` | Lyft | 6 |
| `Uber` | Uber | 6 |
| `Back Bay Garage` | Back Bay Garage | 5 |
| `Goa Marriott Resort & Spa` | Marriott | 5 |
| `CAVA` | Cava | 4 |
| `National Car Rental` | National Car | 4 |
| `PKL Boston` | PKL Boston | 4 |
| `Radisson Blu Mumbai International Airport` | Radisson | 4 |
| `United Airlines` | United Airlines | 4 |
| `United InFlight Purchase` | United Airlines | 4 |
| `Apple` | Apple | 3 |
| `Bamboo HR` | Bamboo HR | 3 |
| `Cvs` | CVS | 3 |
| `Delta Air Lines` | Delta | 3 |
| `Expedia` | Expedia.com | 3 |
| `Inkd Stores` | Ink'd Stores | 3 |
| `Marriott Santa Clara` | Marriott | 3 |
| `Sheraton Grand Seattle` | Sheraton Hotel | 3 |
| `Webflow` | webflow.com | 3 |
| `7 - eleven` | 7-Eleven | 2 |
| `Adobe` | Adobe | 2 |
| `Amazon Marketplace` | Amazon | 2 |
| `Asana` | Asana | 2 |
| `Best Buy` | Best Buy | 2 |
| `Hertz Car Rental` | Hertz | 2 |
| `Hilton Santa Clara` | Hilton | 2 |
| `Hyatt House Denver Downtown` | Hyatt | 2 |
| `JW Marriott Houston Downtown` | Marriott | 2 |
| `Maverik` | Maverik | 2 |
| `Mcca - bcg - online Payment` | Boston Common Garage | 2 |
| `Microsoft` | Microsoft | 2 |
| `Miro` | Miro.com | 2 |
| `P.F. Changs` | P.F. Chang's | 2 |
| `Paddle.net Transaction  -  Now2` | Paddle.net | 2 |
| `Renaissance Amsterdam Schiphol Airport Hotel` | Renaissance Hotel | 2 |
| `Shell` | Shell | 2 |
| `South Western Railway` | Southwest Air | 2 |
| `TD Garden` | TD Garden | 2 |
| `The Newbury Boston  -  Food & Beverage` | The Newbury Boston | 2 |
| `The Westin Galleria Dallas` | Westin Hotels & Resorts | 2 |
| `Trader Joe's` | Trader Joe's | 2 |
| `Whole Foods` | Whole Foods | 2 |

---

## Historical fallback patterns (≥2 occurrences, consistent)

Merchants NOT in the QBO vendor list — fallback treatment confirmed by history.

| Description contains | Fallback | Seen |
|---|---|---|
| `El Globo tavern` | Food Vendor | 5 |
| `tfl travel charge` | Travel Vendor | 5 |
| `Bilbotxo Ostalaritza S` | Food Vendor | 4 |
| `Taxi` | Taxi Vendor | 4 |
| `500 Boylston` | Travel Vendor | 3 |
| `Flour Bakery + Cafe` | Food Vendor | 3 |
| `Hotel Ercilla de Bilbao, Autograph Collection` | Hotel Vendor | 3 |
| `JustPark` | Travel Vendor | 3 |
| `SumUp  *Ottos Coffee` | Food Vendor | 3 |
| `TaskRabbit` | Office Vendor | 3 |
| `Twyford` | Food Vendor | 3 |
| `Virgin At92293AE111E54` | Travel Vendor | 3 |
| `99 Restaurants` | Food Vendor | 2 |
| `Asher Adams, Autograph Collection` | Hotel Vendor | 2 |
| `BAUHAUS Berlin - Kurfürstendamm` | Food Vendor | 2 |
| `Bca Ltd* Belfast City` | Travel Vendor | 2 |
| `Black & White Coffee, at Videri Chocolate Factory` | Food Vendor | 2 |
| `CPI Security Systems` | Office Vendor | 2 |
| `Caffè Nero` | Food Vendor | 2 |
| `Café Urbano` | Food Vendor | 2 |
| `Credence` | Office Vendor (was Food Vendor — corrected 2026-05-21) | 2 |
| `DFW Airport Parking` | Travel Vendor | 2 |
| `EZ Cater` | Food Vendor | 2 |
| `El Agave Restaurant` | Food Vendor | 2 |
| `Electric Lemon` | Food Vendor | 2 |
| `Element Reno Experience District` | Hotel Vendor | 2 |
| `Farmer J Fenchurch Street` | Food Vendor | 2 |
| `Garage At Post Office Square` | Travel Vendor | 2 |
| `Guinness Open Gate Brewery – West Loop` | Food Vendor | 2 |
| `Hingham Launch` | Travel Vendor | 2 |
| `Holiday Extras` | Travel Vendor | 2 |
| `Hub Arpto Bilbao` | Travel Vendor | 2 |
| `Juliet Cocktail Room` | Food Vendor | 2 |
| `Legal Sea Foods  -  Copley Place` | Food Vendor | 2 |
| `Limantour Polanco` | Food Vendor | 2 |
| `Ls 563 Boylston Inc` | Food Vendor | 2 |
| `MSN Airport Parking` | Travel Vendor | 2 |
| `Maman` | Food Vendor | 2 |
| `Marcolinos Italia` | Food Vendor | 2 |
| `Megazoo Hamburg - Osdorf` | Food Vendor | 2 |
| `Northlink M1 Limited` | Travel Vendor | 2 |
| `Our Green House` | Office Vendor | 2 |
| `Potbelly Sandwich Shop` | Food Vendor | 2 |
| `Puesto Santa Clara` | Food Vendor | 2 |
| `Ringo` | Food Vendor | 2 |
| `SPiN Seattle` | Travel Vendor | 2 |
| `Southside News St2385` | Travel Vendor | 2 |
| `The Flower Pot Cafe and Bakery` | Food Vendor | 2 |
| `Urban Market` | Food Vendor | 2 |
| `Virgin At651148EF73384` | Travel Vendor | 2 |
| `Wh Smith Edinbu` | Food Vendor | 2 |
| `Wi - fi Onboard Amx` | Travel Vendor | 2 |
| `iStore` | Office Vendor | 2 |
| `msn trip advisor shop` | Travel Vendor | 2 |

---

## Description-based fallback (when no pattern matches above)

Apply in this priority order, using ONLY the merchant string (column C before "MASTERCARD"):

1. Has taxi/rideshare/cab/bus/transit keyword → **Taxi Vendor**
2. Has hotel/inn/resort/motel/suites + a major hotel brand → **Hotel Vendor**
3. Has airline/airfare/airways/flight/Amtrak/rental car keyword → **Travel Vendor**
4. Has restaurant/café/bar/grill/kitchen/lounge/cocktail/bakery/pizza keyword → **Food Vendor**
5. Has software/license/subscription/SaaS/supply keyword → **Office Vendor**
6. Pure junk (only card numbers, no merchant name) → **Travel Vendor**
7. None of the above → **best guess** (lean Food Vendor in Las Vegas data; Office Vendor elsewhere). Flag as low-confidence.

---

## Inconsistent merchants — DECISIONS STILL NEEDED

These have split history. Zayn has not yet picked canonical treatment. Use majority for now; flag in notes.

| Merchant | Total seen | Historical split | Current default |
|---|---|---|---|
| `Hudson News` | 15 | Food Vendor: 11, Hudson News: 4 | Food Vendor |
| `American` | 11 | Travel Vendor: 7, American Airlines: 4 | Travel Vendor |
| `NAYA` | 7 | Food Vendor: 4, Naya: 3 | Food Vendor |
| `Marissa L Promotions` | 4 | Creative Solutions: 3, Office Vendor: 1 | Creative Solutions |
| `9levy@oriolespark` | 4 | Food Vendor: 3, Travel Vendor: 1 | Food Vendor |
| `Intelsat` | 4 | Office Vendor: 3, Travel Vendor: 1 | Office Vendor |
| `RainFocus` | 4 | Rain Focus: 3, Office Vendor: 1 | Rain Focus |
| `AllAntico Vinaio` | 3 | Food Vendor: 2, All'Antico Vinaio: 1 | Food Vendor |
| `Courtyard Boston Downtown` | 3 | Courtyard: 2, Hotel Vendor: 1 | Courtyard |
| `Pret a Manger` | 3 | Food Vendor: 2, Pret a Manger: 1 | Food Vendor |
| `Taj Bangalore` | 3 | Food Vendor: 2, Hotel Vendor: 1 | Food Vendor |
| `AeroMexico` | 2 | resolved 2026-05-21 | **AeroMexico** (exists in vendor list — use the exact name) |
| `Air Canada` | 2 | split 1/1 | flag for user |
| `Newslink` | 2 | split 1/1 | flag for user |
| `Venetian / Palazzo Las Vegas` | 2 | split 1/1 | The Venetian (per Zayn 5/20) |

---

## Org changes log

Reference log of changes to the Department Listing tab in the Brex Transaction Import template. The template file itself is the source of truth; this log exists for context (when an employee shows up on a Brex CSV with a different QBO Department than expected, check here first).

### 2026-05-28

- **QBO Department reassignments** — three employees moved into `400- Synechron:410- Triumph G&A`:
  - #1 Tameem Hourani (was `100- Operations:110- G&A`)
  - #7 Erik Williams (was `200- Datadog:210- Delivery`)
  - #69 Alta Abel (was `100- Operations:110- G&A`)
- **New hire**: #259 Brendan Nolan — Division: ServiceNow, Department: Engineering, hire date 2026-03-03.
- **Name correction**: #156 Dwight Henderson — "Henderson Jr" → "Henderson".
- None of the three reassigned employees appear in May 2026 Brex CSV cardholders, so the 2026-05-28-Brex-Filled.xlsx output was NOT rebuilt. Future imports will pick up the new template automatically.
- Previous template archived as `tools/Brex Transaction Import File.2026-05-28-prev.xlsx`.

### 2026-07-01

- **Name corrections** (Zayn 2026-07-01) — these are the nickname/preferred forms; `finalize` never overwrites matched employees' name columns (B/C) from BambooHR, so once fixed here they stick across future runs:
  - #2 Jonathan Giara → **Jon Giara**
  - #184 Zaynaldine Moselhy → **Zayn Moselhy**

### 2026-06-29

- **QBO Department rename** — the `410` sub-department was renamed `410- Triumph G&A` -> `410- Digital platforms G&A`. The curated QBO Department (col L) on the Department Listing tab now reads `400- Synechron:410- Digital platforms G&A` for the three 410 employees (#1 Tameem Hourani, #7 Erik Williams, #69 Alta Abel). Fixed in the template (`references/BREXTR~3.xlsx`). Confirmed Zayn 2026-06-29.

---

## How to evolve this file

After each monthly run, diff Zayn's edits against your fills. For each correction:
1. If the same merchant has been corrected before → upgrade priority in this file.
2. If it's a new merchant → add to "Hard-confirmed mappings" or appropriate section.
3. If the correction reveals a workflow rule (not a one-off) → also update `CLAUDE.md` in this folder.
4. Never silently overwrite an existing mapping. If a new correction conflicts with an old one, surface the conflict to Zayn before resolving.

---

## This month's confirmed (June 2026, 06/11 addendum)

Confirmed by Zayn 2026-06-11 during the feed-mode run. Schema same as Hard-confirmed.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `THE WHARF LTD` | Food Vendor |  | 2026-06-11 | Pub/restaurant. Was caught by the broken `Aylab DE` cardholder rule (text "Ayla" blanket-matches Ayla Hourani's budget → Marketing). Route by merchant instead. |
| `LINDO'S FAMILY FOOD` | Food Vendor |  | 2026-06-11 | Grocery/food shop. Same Aylab DE cardholder-rule misfire — route by merchant. |
| `Congstar` | Office Vendor |  | 2026-06-11 | German mobile carrier (Brex string `ACS*05356516 Congstar`). Telecom subscription → Office Vendor. Same Aylab DE misfire. |
| `PAY*SPIN` | Taxi Vendor | Ground Transportation | 2026-06-11 | SPIN e-scooter micromobility → ground transportation, not food. `PAY*` is a processor prefix; underlying merchant is Spin. |
| `SPTHOTEL` | Hotel Vendor | Lodging | 2026-06-11 | Hotel charge (Brex string `SPTHOTEL*<ref>`). Lodging, not food. |
| `ENTERPRISE RENT-A-CAR` | Travel Vendor | Ground Transportation | 2026-06-11 | Car rental → ground transportation. |
| `GULF OIL` | Travel Vendor | Ground Transportation | 2026-06-11 | Fuel → ground transportation, not food. |
| `CHEVRON` | Travel Vendor | Ground Transportation | 2026-06-11 | Fuel → ground transportation, not food. |
| `USCUSTOMS ESTA` | Office Vendor |  | 2026-06-11 | US ESTA travel-authorization gov fee. Per CLAUDE.md Rule 7 (gov/immigration fees → Office Vendor); same treatment as UKVI / Ministry of Home Affairs. |
| `OXYLABS` | Office Vendor | Software Licenses | 2026-06-11 | Proxy / web-data SaaS → Software Licenses, not food. |
| `AGA SERVICE COMPANY` | Travel Vendor | Other Travel Expenses | 2026-06-11 | Allianz Global Assistance travel insurance. |
| `AGASERVICECO` | Travel Vendor | Other Travel Expenses | 2026-06-11 | Allianz Global Assistance travel insurance (no-space Brex variant `AGASERVICECO MAR`). |
| `SUNDANCE TRAVEL ESSENT` | Travel Vendor | Other Travel Expenses | 2026-06-11 | Travel-essentials retailer (airport). |
| `LIBERTY BAGELS` | Food Vendor |  | 2026-06-11 | Bagel shop — genuinely food; confirming to clear the low-confidence flag. |

> **Known broken QBO rule — `Aylab DE` (condition text = "Ayla"):** this cardholder rule blanket-matches every charge in **Ayla Hourani's** budget to payee `Aylab DE` / Marketing Expenses, regardless of merchant (THE WHARF, LINDO'S, SALTWATER JEWELLERY, Congstar, EAST END DRIVING SCHL all misfired on the 06/01–06/11 run). The rule text is too short / is a person's first name. **Fix at the source in QBO** (tighten or delete the rule). Until then, route real business charges by merchant (above). `SALTWATER JEWELLERY DE` and `EAST END DRIVING SCHL` look personal — left flagged for human review, not force-categorized.

---

## This month's confirmed (June 2026, 06-17 feed test)

Confirmed during the 2026-06-17 feed-mode test run (Brex posted-date window 06-16..06-17). Web-searched the merchants that matched no QB rule / memory / vendor entry, mapped each to one of Food/Office/Travel/Taxi/Hotel, and recorded them here so the next run resolves them instantly. Schema same as Hard-confirmed.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `500Boylston` | Travel Vendor | Ground Transportation | 2026-06-17 | **SUPERSEDED 2026-07-01** — see QBO bank rule `500 Boylston - Naya` (Naya / Meals & Entertainment), added 2026-06-30, refreshed into `qbo-bank-rules.xlsx` 2026-07-01. The merchant-rule step runs before this memory lookup, so the QBO rule wins automatically going forward; entry kept per the append-only policy (not deleted). Original 2026-06-17 reasoning: web-confirmed as 500 Boylston St (Back Bay office tower) underground parking garage — turned out to be a misidentification; the actual merchant is Naya (confirmed Zayn 2026-07-01). |
| `UNUSUAL TIMES` | Food Vendor | Meals & Entertainment | 2026-06-17 | The Unusual Times — bar/restaurant + grab-n-go, Newark Liberty (EWR) Terminal B. (web-confirmed) |
| `YVONNE` | Food Vendor | Meals & Entertainment | 2026-06-17 | Yvonne's — New American restaurant & supper club, Downtown Crossing Boston. Large charges are private-event buyouts (verify big tickets). (web-confirmed) |
| `BackBayGarage` | Back Bay Garage | Ground Transportation | 2026-06-17 | VPNE-managed Back Bay parking garage, Boston (Brex `VPNE BackBayGarage`). Exact vendor name per Rule 5. |
| `SWHotels The Westi` | Westin Hotels & Resorts | Lodging | 2026-06-17 | Westin hotel charge via RTI booking platform (`RTI*SWHotels The Westi`). |
| `SWRAILWAY` | Taxi Vendor | Ground Transportation | 2026-06-17 | South Western Railway (UK commuter rail) ticket office — ground transit per Rule 2. Supersedes the stale `South Western Railway -> Southwest Air` historical entry. |
| `HORSE & PLOW` | Food Vendor |  | 2026-06-17 | Restaurant at The American Club, Kohler WI. (web-confirmed) |
| `TONY'S ITALIAN BEE` | Food Vendor |  | 2026-06-17 | Tony's Italian Beef (Chicago) via Square. |
| `THE CHICKEN & RICE` | Food Vendor |  | 2026-06-17 | Restaurant via Square. |
| `FARMER J` | Food Vendor |  | 2026-06-17 | Farmer J — London healthy-food chain (Farringdon). |

---

## This month's confirmed (June 2026, 06-29 feed run)

Confirmed by Zayn 2026-06-29 during the feed-mode run (Brex posted-date window 06-23..06-29). Schema same as Hard-confirmed.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `MPY*BOOKINGCARS` | Travel Vendor | Other Travel Expenses | 2026-06-29 | Car booking service (Brex string `MPY*BOOKINGCARS ENTER`). Ayla Hourani cardholder-rule misfire; route by merchant. |
| `MEGAIMAGE` | Food Vendor | Meals & Entertainment | 2026-06-29 | Mega Image — Romanian grocery/supermarket chain (Brex string `MEGAIMAGE 0891 Vasile`). Ayla Hourani cardholder-rule misfire; route by merchant. |
| `AIRBNB` | Hotel Vendor | Lodging | 2026-06-29 | Airbnb lodging. Ayla Hourani cardholder-rule misfire; route by merchant. |
| `Laduree` | Food Vendor | Meals & Entertainment | 2026-06-29 | Ladurée — luxury café/patisserie at Heathrow T3. Ayla Hourani cardholder-rule misfire; route by merchant. |
| `DUTY FREE SHOPS BDA` | Travel Vendor | Other Travel Expenses | 2026-06-29 | Airport duty-free (Bermuda BDA). Ayla Hourani cardholder-rule misfire; route by merchant. |
| `DION'S` | Food Vendor | Meals & Entertainment | 2026-06-29 | Dion's — New Mexico pizza/restaurant chain. |
| `DIONS SPIRITS` | Food Vendor | Meals & Entertainment | 2026-06-29 | Dion's Spirits Waltham — liquor store / meals. |
| `DAKOTA PETALS` | Food Vendor | Meals & Entertainment | 2026-06-29 | Dakota Petals — flagged for human review (possible flowers); categorized Food Vendor pending confirmation. |
| `COPPER CELLAR` | Food Vendor | Meals & Entertainment | 2026-06-29 | Copper Cellar #102 — restaurant (Knoxville TN). |
| `PHILADELPHIA PARKING A` | Travel Vendor | Other Travel Expenses | 2026-06-29 | Philadelphia Parking Authority — parking. |
| `DFW THE FLYING SAUCER` | Food Vendor | Meals & Entertainment | 2026-06-29 | The Flying Saucer — bar/restaurant at DFW airport. |
| `QUIZNOS TYS` | Food Vendor | Meals & Entertainment | 2026-06-29 | Quiznos at TYS (Knoxville airport). |
| `SONNY BRYANS E13 DFW` | Food Vendor | Meals & Entertainment | 2026-06-29 | Sonny Bryan's BBQ at DFW airport. |
| `SQ *BON ME` | Food Vendor | Meals & Entertainment | 2026-06-29 | Bon Me — Boston Asian-fusion restaurant (Square POS). |
| `Contactless.travel` | Travel Vendor | Other Travel Expenses | 2026-06-29 | Contactless.travel — UK transit/Oyster card top-up service. |
| `MS* COVEMOORGATE` | Hotel Vendor | Lodging | 2026-06-29 | Cove Moorgate — serviced apartments/hotel in Moorgate, London (Microsoft booking prefix `MS*`). |

## This month's confirmed (July 2026, 07-02 feed run)

Confirmed by Zayn 2026-07-02 during the feed-mode run (Brex posted-date window 07-01..07-02). Schema same as Hard-confirmed. Previously MCC-hint fallbacks (5812/5813/5814); promoted to memory so future runs hit High confidence.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `DD *BLUEBOTTLECOFFEE` | Food Vendor | Meals & Entertainment | 2026-07-02 | Blue Bottle Coffee (DoorDash-routed charge string). |
| `The Anthologist` | Food Vendor | Meals & Entertainment | 2026-07-02 | The Anthologist — restaurant/bar. |
| `BURRITO BEACH` | Food Vendor | Meals & Entertainment | 2026-07-02 | Burrito Beach — fast-casual restaurant. |
| `UNION TACO II` | Food Vendor | Meals & Entertainment | 2026-07-02 | Union Taco II — restaurant. |
| `POMPEI` | Food Vendor | Meals & Entertainment | 2026-07-02 | Pompei — restaurant. |
| `CIRA CABRA LAZY BIRD` | Food Vendor | Meals & Entertainment | 2026-07-02 | Cira Cabra Lazy Bird — restaurant. |
| `GREAT AM BAG 3 KSK ORD` | Food Vendor | Meals & Entertainment | 2026-07-02 | Great American Bagel #3, O'Hare (ORD) — airport food. |
| `PAR*MOKA - MINERAL POI` | Food Vendor | Meals & Entertainment | 2026-07-02 | Moka — coffee/café (Par payment processor prefix). |

## This month's confirmed (July 2026, 07-10 feed run)

Confirmed by Zayn 2026-07-10 during the feed-mode run (Brex posted-date window **07-01..07-10** — corrected mid-run; QBO's `date_max` discovery had initially resolved to 07-07, giving a too-narrow 07-07..07-10 pull, but Zayn confirmed the correct window starts 07-01). Schema same as Hard-confirmed. Previously MCC-hint fallbacks; promoted to memory so future runs hit High confidence.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `CTLP*PHOTO-MATICA` | Travel Vendor | Meals & Entertainment | 2026-07-10 | **Corrected by Zayn** — MCC 5814 hint said food, but this is a travel-context charge, not a food/beverage vendor. Kept the M&E sub-category; supersedes the earlier same-day Food Vendor guess. |
| `LUELLA` | Food Vendor |  | 2026-07-10 | Luella — restaurant (MCC 5812). |
| `ONE FLEW SOUTH` | Food Vendor |  | 2026-07-10 | One Flew South — airport restaurant (MCC 5812). |
| `Vivat Bacchus` | Food Vendor |  | 2026-07-10 | Vivat Bacchus — restaurant/wine bar (MCC 5812). |
| `ACCOR* NOVOTEL BAROSSA` | Hotel Vendor |  | 2026-07-10 | Novotel Barossa Valley Resort (Accor booking prefix, MCC 7011). |
| `Farnsworth Garage` | Travel Vendor |  | 2026-07-10 | Parking garage (MCC 7523). |
| `SQ *THOMAS J OKOUA` | Taxi Vendor |  | 2026-07-10 | Rideshare/ground-transport charge via Square (MCC 4121). |
| `TFL TRAVEL CH` | Taxi Vendor |  | 2026-07-10 | Transport for London (MCC 4111) — ground transit. |
| `SAINSBURYS LONDON` | Food Vendor |  | 2026-07-10 | Sainsbury's — UK supermarket (MCC 5411). |
| `TESCO STORES` | Food Vendor |  | 2026-07-10 | Tesco — UK supermarket (MCC 5411). |
| `THE IVY ASIA ST PAULS` | Food Vendor |  | 2026-07-10 | The Ivy Asia St Paul's — restaurant (MCC 5812). |
| `501 BOYLSTON STREET` | Travel Vendor |  | 2026-07-10 | Parking (MCC 7523) — distinct property from the `500 Boylston` / Naya bank-rule entry. |
| `GLOBE   003700` | Food Vendor |  | 2026-07-10 | Restaurant (MCC 5812). |
| `TRAINLINE` | Taxi Vendor |  | 2026-07-10 | Trainline — UK rail ticketing (MCC 4112), ground transport. |
| `VALUE CABS LIMITED` | Taxi Vendor |  | 2026-07-10 | Taxi company (MCC 4121). |
| `PARK CHICAGO MOBILE` | Travel Vendor |  | 2026-07-10 | Chicago parking-meter app (MCC 7523). |
| `THE HOXTON CHICAGO` | Hotel Vendor |  | 2026-07-10 | The Hoxton Chicago — hotel (MCC 7011). |
| `THE EMILY CHICAGO` | Hotel Vendor |  | 2026-07-10 | The Emily Hotel Chicago — hotel (MCC 7011). |

**Left unresolved (Aylab DE misfire, Zayn 2026-07-10):** `TICKETNET RO SRL` ($1.30) and `Kaufland 6570 Andronac` ($270.26) both landed on the broken `Aylab DE` cardholder rule (see the known-issue note above). Zayn opted to leave these as Aylab DE for this run rather than override — not yet added as merchant overrides here.

### Corrections from Zayn's reviewed 07-10 output (diffed against the delivered xlsx)

These 8 rows were corrected by Zayn in the returned file — the resolver's original guess is noted for context. Promoted here so the next run resolves them the same way without another round-trip.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `PAY*SPIN SAN FRANCISCO` | Travel Vendor | Meals & Entertainment | 2026-07-10 | **Corrected by Zayn** from Taxi Vendor / Ground Transportation. More specific than the generic `PAY*SPIN` Hard-confirmed entry (SPIN e-scooter → Taxi Vendor) — this exact descriptor overrides it by longest-match. |
| `SQ *VALET` | Travel Vendor | Ground Transportation | 2026-07-10 | **Corrected by Zayn** from Office Vendor / Office Supplies. Valet parking, not an office expense. |
| `BLOOD CANCER UNITED` | Office Vendor | Charitable Contribution | 2026-07-10 | **Corrected by Zayn** from United Airlines / Airfare — a false-positive hit on the generic `UNITED` Hard-confirmed airline pattern (this is a charity, not the airline). This entry is longer than `UNITED` so it wins by longest-match and fixes the collision going forward. **Known risk:** the bare `UNITED` pattern below can still false-positive on any other merchant string containing the word "united" that hasn't been seen yet — check the descriptor makes sense as an airline charge before trusting it. |
| `500Boylston` | Naya | Meals & Entertainment | 2026-07-10 | **Corrected by Zayn** from Travel Vendor / Ground Transportation. Replaces the 2026-06-17 entry for this exact no-space descriptor variant — the QBO `500 Boylston - Naya` bank rule (added 2026-06-30) does not match this no-space Brex string, so memory carries it directly instead of relying on the rule. |
| `TST* NAYA` | Naya | Meals & Entertainment | 2026-07-10 | **Corrected by Zayn** from Food Vendor (descriptor seen as `TST* NAYA - 500 BOYLST`). Same underlying merchant as `500Boylston` above — Naya restaurant at 500 Boylston St. |
| `ECOVADIS` | Office Vendor | Dues & Subscriptions | 2026-07-10 | **Corrected by Zayn** — Sub Category only, from Other Business Expenses. EcoVadis is a recurring sustainability-rating subscription. |
| `JUICEBOX` | Juicebox | Dues & Subscriptions | 2026-07-10 | **Corrected by Zayn** — Sub Category only, from Recruiting Expenses (descriptor `JUICEBOX (PEOPLEGPT)`). |
| `GOOGLE*CLOUD` | Google | Dues & Subscriptions | 2026-07-10 | **Corrected by Zayn** — Sub Category was blank (defaulted), now Dues & Subscriptions. Covers both the `Q2X3T5` and `VXRQFH` descriptor variants seen this run. |

### Corrections from Zayn's reviewed 07-16 output (diffed against the delivered xlsx)

These 5 rows were corrected by Zayn in the returned file — the resolver's original guess is noted for context. Promoted here so the next run resolves them the same way without another round-trip.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `Hotel at Booking.com` | Booking.com | Lodging | 2026-07-16 | **Corrected by Zayn** — Sub Category only, from Other Travel Expenses. A hotel booking, not generic travel. |
| `WENDY'S` | Wendy's | Meals & Entertainment | 2026-07-16 | **Corrected by Zayn** — Sub Category was blank (defaulted), now Meals & Entertainment. |
| `HARGROVE LLC` | Office Vendor | Other Marketing Expenses | 2026-07-16 | **Corrected by Zayn** from Travel Vendor / Meals & Entertainment. Hargrove is an event-production/marketing vendor, not travel. |
| `INTUIT *QBooks Online` | Intuit | Software Licenses | 2026-07-16 | **Corrected by Zayn** — Sub Category was blank (defaulted), now Software Licenses. |
| `RACETRAC` | RaceTrac | Meals & Entertainment | 2026-07-16 | **Corrected by Zayn** — Sub Category was blank (defaulted), now Meals & Entertainment. Gas-station/convenience descriptor, coded as M&E not fuel. |

### Corrections from Zayn's reviewed 07-20 output (diffed against the delivered xlsx)

These 5 rows were corrected by Zayn in the returned file — the resolver's original guess is noted for context. Promoted here so the next run resolves them the same way without another round-trip.

| Description contains | Payee Override | Sub Category Override | Confirmed | Reason |
|---|---|---|---|---|
| `HEADLINES THE SALON` | Office Vendor | Office Supplies | 2026-07-20 | **Corrected by Zayn** — Sub Category only, from Other Business Expenses. |
| `COVERMORE TRAVEL INS` | Office Vendor | Dues & Subscriptions | 2026-07-20 | **Corrected by Zayn** — Sub Category only, from Insurance. Travel-insurance subscription/policy line item. |
| `GLF*VINEYARD` | Travel Vendor | Meals & Entertainment | 2026-07-20 | **Corrected by Zayn** from Office Vendor / Other Business Expenses. Covers both descriptor variants seen this run. |
| `CROWN AWARDS INC` | Crown Awards | Office Supplies | 2026-07-20 | **Corrected by Zayn** — Sub Category was blank (defaulted), now Office Supplies. |
| `APH` | Travel Vendor | Ground Transportation | 2026-08-02 | UK Airport Parking & Hotels — airport parking, not food. Confirmed by Zayn on the 20260802 run. |
| `Tonbridge` | Travel Vendor | Ground Transportation | 2026-08-02 | UK rail station fare. Confirmed by Zayn on the 20260802 run. |
| `APCOA PARKING` | Travel Vendor | Ground Transportation | 2026-08-02 | UK car-park operator. Confirmed by Zayn on the 20260802 run. |
| `Big Green Egg` | Office Vendor | Office Supplies | 2026-08-02 | Matches the category already on the Brex CSV. Confirmed by Zayn on the 20260802 run. |
| `PrintWithMe` | Office Vendor | Office Supplies | 2026-08-02 | Print kiosk — office supplies, not the coffeehouse it sits inside. Confirmed by Zayn on the 20260802 run. |
| `Sainsbury` | Food Vendor | Meals & Entertainment | 2026-08-02 | UK grocery — Food Vendor is correct; confirming to clear the low-confidence flag. |
| `Google Workspace` | Office Vendor | Software Licenses | 2026-08-02 | **Corrected by Zayn** — was resolving to Food Vendor with no rule, and the `Google Workspace_amana` variant was blanket-matched by the cardholder rule `Aylab DE` (matched Ayla Hourani's budget, not the merchant) and booked to Other Marketing Expenses. A merchant entry here beats the cardholder rule. |
| `FIVE IRON GOLF` | Food Vendor | Meals & Entertainment | 2026-08-02 | Client/team entertainment venue that serves food. Confirmed by Zayn on the 20260802 run. |
| `AMC 2657` | Food Vendor | Meals & Entertainment | 2026-08-02 | Cinema — team entertainment. Confirmed by Zayn on the 20260802 run. |
