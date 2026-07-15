from app import __version__

def cap(cid,title,mode,description,risk="low",maturity="beta",confirm=False):
    return {"id":cid,"title":title,"mode":mode,"description":description,"risk":risk,"requires_confirmation":confirm,"supports_attachments":False,"input_schema":{"type":"object","additionalProperties":True},"tags":[f"maturity:{maturity}","city-travel"]}
READ_CAPABILITIES=[
 cap("city.cockpit","City cockpit","read","Places, trips, routes and maturity overview.",maturity="stable"),
 cap("city.place.search","Rank live place candidates","read","Ranks web-researched candidates using situation and personal memory.",maturity="stable"),
 cap("city.place.list","List saved places","read","Lists saved, visited, liked, closed or recheck-needed places.",maturity="stable"),
 cap("city.experience.summary","Place experience ratings","read","Shows solo and couple ratings, return intent and dish impressions.",maturity="stable"),
 cap("city.trip.plan","Validate trip plan","read","Checks a day or multi-day itinerary without saving it.",maturity="stable"),
 cap("city.trip.get","Get saved trip","read","Returns a saved trip, days and itinerary items.",maturity="stable"),
 cap("city.trip.next","What next","read","Selects the next feasible itinerary block and fallback options.",maturity="stable"),
 cap("city.route.walking","Walking route review","read","Evaluates walking route distance, time and constraints.",maturity="beta"),
 cap("city.route.cycling","Cycling route review","read","Evaluates pace, risks, bailout points and novelty.",maturity="beta"),
 cap("city.route.photowalk","Photowalk route review","read","Evaluates light, visual fit and timing.",maturity="beta"),
 cap("city.route.literary","Literary and historical route review","read","Separates facts, book locations and hypotheses.",maturity="beta"),
 cap("city.route.get","Get saved route","read","Returns a route with points and export links.",maturity="stable"),
 cap("city.event.rank","Rank current events","read","Ranks web-researched events by relevance and logistics.",maturity="advisory"),
 cap("city.area.compare","Compare stay areas","read","Scores neighborhoods for transport, food, noise, cost and plan fit.",maturity="beta"),
 cap("city.weather.adapt","Adapt plan to weather","read","Produces rain, heat, wind and fatigue fallbacks from supplied forecast.",maturity="advisory"),
 cap("city.logistics.departure","Departure time calculator","read","Calculates realistic leave time with luggage and buffers.",maturity="beta"),
 cap("city.maturity.status","Capability maturity","read","Returns maturity levels, real tests and promotion recommendations.",maturity="stable"),
]
WRITE_CAPABILITIES=[
 cap("city.place.save","Save or update place","write_preview","Previews saving a place and freshness metadata.","medium","stable",True),
 cap("city.place.status","Update place status","write_preview","Previews VISITED, FAVORITE, CLOSED or RECHECK_NEEDED.","medium","stable",True),
 cap("city.place.preference","Save place signal","write_preview","Previews liked, expensive solo or good after gym signals.","medium","stable",True),
 cap("city.experience.record","Record visit and ratings","write_preview","Previews solo/couple visit, ratings, return intent and dishes.","medium","stable",True),
 cap("city.trip.save","Save trip and itinerary","write_preview","Previews trip, days and itinerary items.","medium","stable",True),
 cap("city.trip.update","Update active trip","write_preview","Previews rescheduling or status changes.","medium","stable",True),
 cap("city.route.save","Save route","write_preview","Previews route and ordered points.","medium","beta",True),
 cap("city.route.export","Export route or guide","write_preview","Previews GPX, KML and PDF export to Google Drive.","medium","beta",True),
 cap("city.event.save","Save event","write_preview","Previews saving an event to shortlist or trip.","medium","advisory",True),
 cap("city.rule.save","Save city rule","write_preview","Previews a personal recommendation rule.","medium","stable",True),
 cap("city.journal.record","Record trip journal","write_preview","Previews post-trip or end-of-day reflection.","medium","beta",True),
 cap("city.maturity.feedback","Record real-world test","write_preview","Previews test result and maturity metrics update.","medium","stable",True),
]
def manifest():
    return {"contract_version":"0.1.0","plugin_id":"city-travel-jarvis","domain":"city","name":"City & Travel Jarvis","version":__version__,"description":"Personal city, travel, route and place-memory plugin with live-source ranking and controlled writes.","capabilities":READ_CAPABILITIES+WRITE_CAPABILITIES,"write_policy":"preview_confirm_commit","autonomous_actions":False,"background_jobs":False,"supports_attachments":False,"attachment_transport":"none","health":{"path":"/health","auth_required":False}}
CAPABILITY_MAP={x["id"]:x for x in READ_CAPABILITIES+WRITE_CAPABILITIES}
