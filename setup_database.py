"""
setup_database.py — Creates reviews.db
Avg rating target: 3.9–4.2
"""
import sqlite3, random
from datetime import datetime, timedelta

DB_PATH = "reviews.db"
BRANCHES = ["New York Inn", "Miami Qualis", "Atlanta Express", "SFO Residency"]
SOURCES = ["Google", "Yelp", "TripAdvisor"]

# (text, rating, max_likes)
# Rating distribution designed for ~4.0 avg: ~55% are 4-5, ~15% are 3, ~30% are 1-2
REVIEWS = [
    # ═══ ROOM — NEGATIVE (12) ═══
    ("The room smelled terrible, like mold and dampness. Housekeeping couldn't fix it during our 3-night stay. Black mold in the bathroom grout.", 1, 8),
    ("Musty odor in the bedroom. My wife has asthma and this triggered a reaction. Had to buy an air purifier from a nearby store.", 2, 5),
    ("Room was filthy. Hair on the sheets, stains on the carpet, sticky TV remote.", 1, 12),
    ("Housekeeping skipped our room. Dirty towels piled up, trash not emptied, bed not made. Nobody came for 4 hours after we called.", 2, 4),
    ("Mattress was lumpy and uncomfortable. Asked to switch rooms but fully booked. Back pain the entire trip.", 2, 3),
    ("Bathroom tiles cracked, visible mold in shower, toilet ran constantly. Basic maintenance shouldn't be too much to ask at $250/night.", 1, 9),
    ("AC unit sounded like a jet engine. Called maintenance twice — nobody came either time.", 1, 7),
    ("Found cockroaches on the first night. Only option was a downgrade room. Cut our trip short.", 1, 15),
    ("Wallpaper peeling, carpet stained. Room looks nothing like the website photos.", 2, 11),
    ("Room was tiny — couldn't open both suitcases. Bathroom door hits the toilet.", 2, 2),
    ("Pillows flat as pancakes, duvet had a cigarette burn. Minibar fridge buzzed all night.", 2, 3),
    ("The 'ocean view' was actually a parking lot view with a tiny sliver of ocean. Misleading.", 1, 14),

    # ═══ ROOM — POSITIVE (18) ═══
    ("Absolutely loved the room! Spotless, freshly renovated marble bathroom. King bed like sleeping on a cloud. Welcome basket with chocolates.", 5, 6),
    ("Rooms were immaculate. Rain shower was heavenly, Egyptian cotton sheets divine. Will definitely be back.", 5, 8),
    ("Suite was spacious with separate living area and breathtaking mountain views every morning. Turndown service with fresh flowers.", 5, 4),
    ("Beautifully decorated with smart home controls — adjustable lighting, motorized curtains, tablet to control everything.", 4, 3),
    ("Attention to detail was remarkable. Blackout curtains that work, USB ports both sides, Nespresso machine, pillow menu.", 5, 5),
    ("Room was perfect for our needs. Clean, modern, well-maintained. Exactly what the photos showed.", 4, 3),
    ("Upgraded to a corner suite and it was spectacular. Wrap-around windows, soaking tub, separate rain shower.", 5, 7),
    ("The bed was genuinely the most comfortable hotel bed I've ever slept in. Whatever brand that mattress is, I need one.", 5, 4),
    ("Loved the little touches — turndown chocolates, robes and slippers, premium toiletries. Makes you feel valued.", 5, 3),
    ("Room was quiet, clean, and exactly as described online. Sometimes that's all you need. Solid 4 stars.", 4, 2),
    ("The renovated rooms on the 8th floor are worth the upgrade. Modern finishes, great water pressure, city views.", 4, 4),
    ("Bathroom was the highlight — double vanity, heated floors, and a rainfall shower. Felt like a spa.", 5, 5),
    ("Room had everything a business traveler needs: fast WiFi, good desk lighting, plenty of outlets, quiet AC.", 4, 3),
    ("Housekeeping did an incredible job every single day. Fresh towels arranged beautifully, room spotless.", 5, 4),
    ("The balcony alone was worth the price. Morning coffee with that view is something I'll remember.", 5, 6),
    ("Minibar was reasonably priced (rare!) and the snack selection was thoughtful — local brands, healthy options.", 4, 2),
    ("King room was generously sized. Plenty of closet space, luggage rack, and a proper full-length mirror.", 4, 2),
    ("Loved the blackout curtains and white noise machine option. Best hotel sleep I've had in years.", 5, 3),

    # ═══ SERVICE — NEGATIVE (10) ═══
    ("Front desk staff were rude. No greeting, no smile. Asked for restaurant recommendations and got a shrug.", 1, 10),
    ("Asked for extra towels three times over two days. Never received them. Staff were chatting behind the desk.", 2, 6),
    ("45-minute check-in wait with only one person at the counter. Other staff visible in back office doing nothing.", 2, 5),
    ("Called about noise complaint at 11pm. Called again at midnight and 1am. Nothing was done.", 1, 8),
    ("Nobody picks up the phone. When someone finally answers, they transfer you and you start hold music again.", 1, 6),
    ("Overcharged by $150. Took 3 calls, 2 emails, and a credit card dispute to fix. Each person gave different info.", 1, 12),
    ("Wake-up call for early flight never came. Nearly missed our flight. Got a 'sorry about that' at checkout.", 1, 9),
    ("Language barrier at reception made everything difficult. Room key issue took 20 minutes of charades.", 1, 4),
    ("Requested crib confirmed twice by email. Arrived — no crib. Took 3 hours. Baby screaming.", 1, 11),
    ("Long phone wait times trying to reach concierge. Had to walk down 12 floors to ask in person.", 1, 3),

    # ═══ SERVICE — POSITIVE (16) ═══
    ("Concierge went above and beyond — booked dinner, called ahead for anniversary, complimentary dessert waiting.", 5, 7),
    ("Staff friendly and welcoming from arrival. Bellhop carried every bag. Room ready early, free upgrade.", 5, 6),
    ("Manager apologized about AC issue, gave complimentary suite upgrade plus breakfast vouchers. Problem handled perfectly.", 5, 9),
    ("Billing issue resolved immediately with a smile. Manager called to confirm and offered next-stay discount.", 5, 4),
    ("Valet team outstanding. Car ready in 5 minutes, windshield cleaned, water bottle left on hot days.", 5, 3),
    ("Night manager helped when locked out at 2am. Professional, kind, walked us to room to test new key.", 5, 2),
    ("Check-in was the fastest I've ever experienced. Warm greeting, straight to the point, room key in 3 minutes.", 5, 4),
    ("The staff remembered we were celebrating and left a bottle of wine and handwritten card. Genuinely touching.", 5, 8),
    ("Concierge's restaurant recommendations were perfect. Every single one was a hit. Better than any guide book.", 5, 3),
    ("Housekeeping noticed my allergy meds and proactively offered hypoallergenic pillows. That's real service.", 5, 5),
    ("Front desk handled our room change request within 10 minutes. No fuss, no attitude. Just professional.", 4, 2),
    ("The doorman knew our names by day two. Small thing but makes a hotel feel like home.", 5, 3),
    ("When I mentioned it was my mom's birthday, they sent up a cake. We didn't ask. Pure thoughtfulness.", 5, 7),
    ("Staff helped carry groceries from our car, suggested a pharmacy for my daughter's fever, checked in on us later.", 5, 4),
    ("Asked about gym hours and the front desk person printed a whole list of nearby running routes. Above and beyond.", 4, 2),
    ("Every single staff member we encountered was polite, helpful, and seemed genuinely happy to be there.", 5, 3),

    # ═══ FOOD — NEGATIVE (6) ═══
    ("Breakfast buffet disappointing. Watery eggs, yesterday's fruit, burnt coffee. Not worth $35/person.", 2, 7),
    ("Room service took 90 minutes. Burger cold, fries soggy, forgot wife's salad. Put on hold then hung up.", 1, 10),
    ("Limited vegetarian options. Only a sad salad and plain pasta.", 2, 5),
    ("Hair in my soup. Waiter just swapped the bowl — no apology, no manager.", 1, 12),
    ("'Complimentary breakfast' was a stale muffin, bruised apple, and juice box.", 2, 6),
    ("Restaurant closed at 9pm. Arrived 8:45, kitchen shut. Ended up with vending machine dinner.", 2, 4),

    # ═══ FOOD — POSITIVE (10) ═══
    ("Hotel restaurant dinner was a highlight. Chef has serious talent — best risotto outside Italy. Great wine list.", 5, 5),
    ("Breakfast buffet incredible. Fresh pastries, made-to-order omelettes, local cheeses, tropical fruits.", 5, 8),
    ("Midnight steak from in-room dining arrived hot and perfectly cooked. Real place setting. Chocolate cake was divine.", 5, 3),
    ("Full gluten-free menu — GF bread, pancakes, pastries. Chef came out to ensure my celiac needs were met.", 5, 6),
    ("The rooftop bar had excellent cocktails and a fantastic sunset view. Became our nightly tradition.", 5, 4),
    ("Breakfast had something for everyone — my picky kids found plenty to eat, and the coffee was outstanding.", 4, 3),
    ("The in-room minibar snacks were actually good. Local artisan chocolates and decent wine selection.", 4, 2),
    ("Lunch by the pool was great — fresh salads, good burgers, and fast service. Didn't have to leave the property.", 4, 3),
    ("The hotel's Italian restaurant was so good we cancelled our other dinner reservations and ate there every night.", 5, 5),
    ("Loved the lobby coffee bar. Proper espresso drinks, not the usual drip-coffee-in-a-lobby situation.", 4, 3),

    # ═══ LOCATION (7) ═══
    ("Perfect location — walking distance to attractions, great restaurants, pharmacy nearby.", 5, 4),
    ("Unsafe-feeling neighborhood. Poorly lit streets, driver warned us. Website is misleading.", 2, 9),
    ("Too far from city center. $50+/day on cabs. 'Free shuttle' ran twice daily and always full.", 2, 5),
    ("Airport shuttle convenient, on time, friendly driver. They tracked our flight for pickup adjustment.", 5, 3),
    ("No hotel parking. Garage 3 blocks away at $40/night. Website says 'parking available' but it's off-site.", 2, 7),
    ("Beautiful beachfront. Fell asleep to waves. Clean beach, free chairs and umbrellas.", 5, 5),
    ("Right next to highway. Constant noise even with windows closed.", 2, 8),

    # ═══ AMENITIES — NEGATIVE (6) ═══
    ("WiFi painfully slow. Remote worker who booked for 'high-speed internet' — had to work from a coffee shop.", 1, 10),
    ("Internet dropped every 10-15 minutes. IT said 'too many guests.' Invest in infrastructure.", 1, 6),
    ("Pool disgusting. Green water, leaves, smell. 'Heated pool' was freezing.", 1, 8),
    ("Gym equipment outdated. Half treadmills broken, mismatched dumbbells.", 2, 4),
    ("Elevator out 2 days. Climbed 8 flights with luggage and toddler. No help offered.", 1, 12),
    ("Spa letdown. No hot water in jacuzzi, therapist 20 min late, broken TV in relaxation room.", 2, 5),

    # ═══ AMENITIES — POSITIVE (10) ═══
    ("Infinity pool stunning — swimming into the sunset. Clean, great pool bar, kids' splash area was a hit.", 5, 4),
    ("Fitness center excellent — Peloton bikes, TRX, free weights, open 24/7. Complimentary protein shakes.", 5, 2),
    ("Spa was heavenly. Best massage in years. Steam room, sauna, plunge pool circuit.", 5, 3),
    ("Free high-speed WiFi that actually works. Downloaded 2GB in minutes.", 5, 3),
    ("The pool area had great music, comfortable loungers, and attentive bar service. Could spend all day there.", 4, 3),
    ("Kids' club was a lifesaver. Professional staff, fun activities, and our kids begged to go back every day.", 5, 5),
    ("Business center was well-equipped — fast printers, quiet workspace, reliable video conferencing setup.", 4, 2),
    ("The hotel gym had actual Rogue equipment, not the usual Planet Fitness leftovers. Serious gym.", 5, 3),
    ("Loved the library lounge. Real books, comfortable chairs, complimentary tea and cookies all afternoon.", 5, 4),
    ("The EV charging stations in the parking garage were a pleasant surprise. Free to use for guests.", 4, 2),

    # ═══ NOISE (5) ═══
    ("Paper-thin walls. Heard neighbors' TV, conversations, alarm. Zero insulation.", 1, 6),
    ("Noisy hallway all night. Doors slamming, 2am conversations. Front desk did nothing.", 1, 5),
    ("Construction noise 7am daily. No warning. Jackhammers from floor above. Couldn't move rooms.", 1, 11),
    ("Incredibly quiet room despite downtown location. Great soundproofing. Slept better than at home.", 5, 3),
    ("Ice machine right outside room. Grinding noise every 20 minutes until 2am.", 2, 6),

    # ═══ PRICING / REFUNDS (10) ═══
    ("Overpriced. $300/night for a $100 motel experience. Resort fee adds $50 for barely-functioning amenities.", 1, 14),
    ("Excellent value. Clean room, great location, friendly staff, under $150/night.", 5, 4),
    ("$45/day resort fee for closed pool, broken gym equipment, and spotty WiFi. Asked for adjustment — denied.", 1, 13),
    ("Hidden charges. Minibar restocking fee (didn't touch it), energy surcharge, destination fee. Bill $200 over.", 2, 11),
    ("3-week refund wait. Booked suite, got standard. Hotel admits mistake, keeps saying 'processing.'", 1, 12),
    ("Charged for minibar item I didn't touch. Water bottle in same position at checkout.", 1, 7),
    ("All-inclusive was a great deal. No surprises, no hidden fees. Stress-free.", 5, 5),
    ("Refund requested after burst pipe flooded room. 6 weeks later, still 'with accounting.'", 1, 14),
    ("Great value for location and quality. 40% off sale. Loyalty points are generous.", 5, 3),
    ("Budget-friendly without feeling cheap. Clean, modern, everything we needed.", 4, 2),

    # ═══ BOOKING (7) ═══
    ("Booked king bed, got two twins. 'That's all we have.' Honeymoon in twin beds. Fighting for refund.", 1, 15),
    ("Reservation lost despite confirmation email. 40-minute wait. Got lower room. No apology.", 1, 9),
    ("Express checkout — drop key, receipt emailed. Mobile check-in flawless.", 5, 2),
    ("Overbooking sent us to partner hotel 20 min away. After 12 hours with two kids — infuriating.", 1, 11),
    ("App check-in: room number, digital key, car to room in 5 minutes. The future.", 5, 3),
    ("Website showed availability, paid in full. 'No rooms' on arrival. No explanation. Elderly parents stranded.", 1, 17),
    ("Confirmed early check-in not honored. Noon arrival, told 3pm. Lobby for 3 hours.", 2, 6),

    # ═══ MIXED (8) ═══
    ("Beautiful room, terrible service. 30-min check-in, wrong room service orders twice.", 3, 8),
    ("Unbeatable location, Instagram pool. But rooms showing age — outdated fixtures, stained carpet.", 3, 6),
    ("Best hotel breakfast ever. But room next to elevator — constant noise.", 3, 4),
    ("Warmest staff ever. But facilities lacking — pool closed, gym tiny, WiFi spotty.", 3, 7),
    ("World-class spa and dining. But room had no coffee maker, no iron, one tiny towel.", 3, 5),
    ("Seamless check-in, great concierge. Room was disappointing — smaller than photos, brick wall view.", 3, 4),
    ("Wonderful stay except billing. Charged twice, 4 calls to fix. Otherwise beautiful property.", 4, 8),
    ("Gorgeous hotel — architecture, gardens, common areas. But rooms stuck in the 90s.", 3, 5),

    # ═══ GENERAL POSITIVE (14) ═══
    ("Exceeded every expectation. Staff remembered our names and my husband's shellfish allergy.", 5, 5),
    ("Hidden gem. Highlight of our trip. Charming, personalized service, rooftop terrace at sunset.", 5, 6),
    ("Anniversary champagne, rose petals, private terrace dinner. 10th anniversary made unforgettable.", 5, 9),
    ("Five-star service, three-star price. Clean, great location, honest pricing.", 5, 7),
    ("Solo work trip made less lonely. Great bar staff, communal table, cozy room.", 5, 2),
    ("Parents' 40th anniversary here. Mom loved garden, Dad loved whiskey bar. Both said best bed ever.", 5, 4),
    ("Travel bloggers — stayed at dozens of hotels. This stands out. Consistent quality, no weak link.", 5, 3),
    ("Second stay here and it was even better than the first. Consistency is underrated.", 5, 3),
    ("The kind of hotel that makes you feel like a regular even on your first visit.", 5, 4),
    ("Honestly can't find a single complaint. Room, food, service, location — all excellent.", 5, 5),
    ("My wife is incredibly picky about hotels and she gave this one her stamp of approval. That says everything.", 5, 6),
    ("Already booked our next stay. That should tell you everything you need to know.", 5, 3),
    ("The little details matter and this hotel gets them all right. From check-in to checkout, perfection.", 5, 4),
    ("Our family of four had the best vacation here. Something for everyone. Can't recommend enough.", 5, 5),

    # ═══ GENERAL NEGATIVE (4) ═══
    ("Worst experience. Dirty room, rude staff, cold food, broken elevator. Double-charged, still waiting.", 1, 16),
    ("Zero stars if possible. Booked 'ocean view' — got dumpster view. Refund ignored a month.", 1, 13),
    ("Save your money. Location is the only thing. Rooms, service, food — all substandard.", 1, 8),
    ("20 hours for $350. Mediocre room, broken WiFi, closed pool, restaurant closes 8pm.", 1, 6),

    # ═══ REFUNDS (5) ═══
    ("Refund within cancellation window denied. Policy says 24hrs. Cancelled 48hrs before. Disputing.", 1, 14),
    ("Refund nightmare. Month of calls. 'Processing.' 'Need approval.' 'Send receipt again.'", 1, 10),
    ("AC broke, manager immediately offered partial refund + upgrade. Processed in 3 days. Fair.", 5, 5),
    ("Disputing 'no-show' charge. Have online cancellation screenshots.", 1, 12),
    ("Hotel reached out after negative review, apologized, full refund + future voucher. Recovery done right.", 4, 7),

    # ═══ ADDITIONAL POSITIVE — to bring avg to ~4.0 ═══
    ("Very pleasant stay. Room was clean, bed comfortable, and check-in took less than 5 minutes.", 4, 2),
    ("Great hotel for the price point. Nothing fancy but everything works and staff are kind.", 4, 1),
    ("We stayed 4 nights and had zero complaints. That's rare for us. Well done.", 4, 3),
    ("The bathroom was spotless and well-stocked with quality toiletries. Appreciated the attention to hygiene.", 4, 2),
    ("Convenient location for our conference. Quick walk to the venue and several good restaurants nearby.", 4, 1),
    ("Staff helped with restaurant reservations and even called a cab for our early flight. Above expectations.", 5, 3),
    ("Loved the complimentary water bottles in the room refreshed daily. Small gesture that matters.", 4, 1),
    ("Room was quiet and dark — perfect for sleeping in. Exactly what a business traveler needs.", 4, 2),
    ("Kids enjoyed the pool and we enjoyed the peace. Win-win family vacation.", 4, 3),
    ("The lobby coffee was actually good — not the usual hotel lobby drip. Nice touch.", 4, 1),
    ("Smooth experience from booking to checkout. No surprises, no issues. That's all I ask for.", 4, 2),
    ("Housekeeping was thorough and timely. Room was always ready when we came back from sightseeing.", 4, 2),
    ("Good value for a city-center hotel. Comparable places charge 30-40% more for the same quality.", 4, 3),
    ("The front desk recommended a great local restaurant we'd never have found on our own. Appreciated.", 5, 2),
    ("Comfortable bed, working WiFi, clean bathroom, quiet room. The essentials done right.", 4, 1),
    ("Returned for our third stay. Consistency keeps us coming back. Never been disappointed.", 5, 4),
    ("The turndown service was a lovely surprise. Came back to dimmed lights and a chocolate on the pillow.", 5, 3),
    ("Parking was easy and affordable — unusual for this area. Big plus for road trippers.", 4, 2),
    ("The hotel's location near the park was perfect for our morning runs. Beautiful route right outside.", 4, 2),
    ("Staff accommodated our late checkout request without hesitation. Made our last day stress-free.", 5, 2),
    ("Breakfast had great variety including fresh fruit and good coffee. Set us up nicely for the day.", 4, 3),
    ("The room had a nice workspace setup — good lighting, outlets nearby, comfortable desk chair.", 4, 1),
    ("Our room had a lovely view of the city skyline. Enjoyed watching the sunset from the window.", 5, 3),
    ("They upgraded us to a suite for our anniversary without us asking. Wonderful surprise.", 5, 5),
    ("Efficient and friendly. That's the best way to describe the entire staff. No complaints whatsoever.", 5, 2),
    ("The gym was small but had everything I needed for my daily workout. Clean and well-maintained.", 4, 1),
    ("Concierge printed our boarding passes and arranged airport transport. Going above and beyond.", 5, 3),
    ("We appreciated the eco-friendly touches — refillable soap dispensers, no plastic straws, recycling bins.", 4, 2),
    ("The room's blackout curtains were excellent. Slept until 9am without any light disturbance.", 4, 1),
    ("Quick and painless check-in process. Key cards worked perfectly the entire stay.", 4, 1),
    ("The hotel's restaurant had a fantastic happy hour. Great cocktails at reasonable prices.", 4, 3),
    ("Our kids were given coloring books at check-in. Thoughtful touch that kept them busy.", 5, 4),
    ("The in-room safe was easy to use and gave us peace of mind for valuables.", 4, 1),
    ("Walking distance to the subway station. Made exploring the city incredibly convenient.", 4, 2),
    ("The room service menu was varied and reasonably priced. Midnight snack was delivered quickly.", 4, 2),
    ("Appreciated the USB charging ports built into the bedside lamps. Practical modern touch.", 4, 1),
    ("The bathrobe was the softest thing ever. I genuinely considered taking it home.", 5, 3),
    ("Staff were helpful without being overbearing. They read the room perfectly — available when needed.", 5, 2),
    ("The elevator was fast and never had a wait. Small thing but it matters on the 15th floor.", 4, 1),
    ("Hotel arranged a birthday cake delivery to our room for my daughter. Made her day special.", 5, 5),
    ("The laundry service was fast and affordable. Had my suit pressed for the morning meeting.", 4, 2),
    ("Great central location, easy walk to museums, restaurants, and shopping. Couldn't ask for better.", 5, 3),
    ("The mattress was firm but comfortable — not too soft, not too hard. Goldilocks would approve.", 4, 2),
    ("Lobby was beautiful and welcoming. Great first impression that set the tone for our stay.", 4, 2),
    ("The minibar had local craft beer options instead of the usual overpriced generic brands. Nice curation.", 4, 2),
    ("Rain shower head in the bathroom was a game-changer. Best shower pressure of any hotel I've stayed at.", 5, 3),
    ("Loved that they had a 24-hour coffee station in the lobby. Lifesaver for jet lag.", 4, 2),
    ("The hotel offered free bike rentals. Explored the neighborhood on two wheels — fantastic experience.", 5, 4),
    ("Clean, quiet, comfortable, and well-located. Ticks every box for a business trip.", 4, 1),
    ("The concierge's recommendations were spot-on. Every restaurant and attraction was a winner.", 5, 3),
    ("Impressed by the soundproofing. Despite a busy street outside, our room was completely silent.", 5, 2),
    ("They remembered our room preference from our last visit. That kind of attention to detail earns loyalty.", 5, 4),
    ("The rooftop terrace was a wonderful place to unwind with a glass of wine after a long day.", 5, 3),
    ("Smooth mobile check-in, digital room key, everything worked first try. Technology done right.", 4, 2),
    ("The hotel's shuttle service to the airport was reliable and free. Huge money saver.", 5, 3),
    ("Room was exactly as photographed online. No unpleasant surprises. What you see is what you get.", 4, 2),
    ("The kids' activity program was a lifesaver. Professional, fun, and our children didn't want to leave.", 5, 4),
    ("We held our team retreat here and the conference facilities were excellent. AV equipment worked perfectly.", 4, 3),
    ("The afternoon tea service in the lobby was a delightful tradition. Felt very special.", 5, 3),
    ("Late-night room service was fast and the food was actually good. Not just reheated leftovers.", 4, 2),
    ("The bellhop helped with all our bags and gave us a quick tour of the facilities. Great onboarding.", 5, 2),
    ("This is now our go-to hotel in this city. Fourth visit and quality has been consistently high.", 5, 4),
    ("Complimentary breakfast was better than many paid hotel breakfasts I've had. Generous spread.", 5, 3),
    ("The infinity pool at sunset was a highlight of our entire trip. Stunning and well-maintained.", 5, 5),
    ("Quick response to our maintenance request. Reported a dripping faucet, fixed within the hour.", 4, 2),
    ("The hotel's loyalty program is genuinely rewarding. Already earned a free night after three stays.", 4, 3),
    ("Wonderful neighborhood with cafes, shops, and a farmers market on Saturday. Perfect base for exploring.", 5, 3),
    ("Staff helped us print documents for our visa application. Small thing but saved us a trip to a copy shop.", 4, 2),
    ("The pillow menu was a nice touch. Chose memory foam and slept like a rock.", 5, 2),
    ("Clean, comfortable, affordable. The holy trinity of hotel stays. Will definitely return.", 4, 2),
    ("The garden courtyard was a peaceful oasis in the middle of the city. Loved reading there.", 5, 3),
    ("Fast WiFi that actually stayed connected throughout our 5-day stay. No drops, no slowdowns.", 5, 3),
    ("The welcome drink at check-in was a classy touch. Immediately felt like a valued guest.", 5, 2),
    ("Our corner room had windows on two sides with great natural light. Room felt spacious and airy.", 4, 2),
    ("The hotel's art collection throughout the hallways made it feel like staying in a gallery. Unique.", 4, 3),
    ("Seamless coordination when we needed to extend our stay by a night. No hassle, same rate.", 5, 3),
    ("The spa's sauna and steam room were available 24/7. Perfect for unwinding after late flights.", 5, 2),
    ("Genuinely one of the best hotel experiences we've had. Everything from arrival to departure was smooth.", 5, 4),

    # ═══ MORE POSITIVE — realistic short reviews ═══
    ("Lovely stay. Would definitely come back.", 5, 1),
    ("Clean room, comfy bed, friendly staff. What more do you need?", 5, 2),
    ("Everything was great. No complaints at all.", 5, 1),
    ("Nice hotel, good location, fair price. Recommend.", 5, 2),
    ("Pleasantly surprised by the quality. Exceeded expectations.", 5, 3),
    ("Our go-to whenever we're in town. Never disappoints.", 5, 2),
    ("Wonderful experience. Staff were amazing.", 5, 1),
    ("Very comfortable stay. Room was modern and clean.", 5, 2),
    ("The best hotel experience I've had in this price range.", 5, 3),
    ("Fantastic service from start to finish.", 5, 1),
    ("Loved everything about this place. Already planning our return.", 5, 2),
    ("Perfect for families. Kids loved it too.", 5, 3),
    ("Great breakfast, great room, great staff.", 5, 1),
    ("Couldn't fault anything. Well run establishment.", 5, 2),
    ("Outstanding value. Will be back.", 5, 1),
    ("The room was perfect for our anniversary getaway.", 5, 3),
    ("Impeccable service throughout our stay.", 5, 1),
    ("Beautiful property, inside and out.", 5, 2),
    ("One of the best hotels in the area, hands down.", 5, 2),
    ("Highly recommend. Worth every penny.", 5, 1),
    ("Stayed three nights and each day was excellent.", 5, 2),
    ("Will be recommending to all our friends.", 5, 1),
    ("Checked all our boxes. Clean, quiet, central, affordable.", 5, 2),
    ("A truly enjoyable stay from beginning to end.", 5, 1),
    ("My wife and I both agreed — best hotel of our trip.", 5, 3),
    ("Really solid hotel. Good in every category.", 4, 1),
    ("Met our expectations and then some.", 4, 2),
    ("Decent hotel with great staff. Would stay again.", 4, 1),
    ("Good location, clean rooms. Solid choice.", 4, 2),
    ("Comfortable stay with no issues. That's a win.", 4, 1),
    ("Room was as described, staff were helpful. Good experience.", 4, 1),
    ("Perfectly adequate for a business trip. Clean and quiet.", 4, 1),
    ("Nice property with attentive staff. Would return.", 4, 2),
    ("Good breakfast, comfortable bed. Can't ask for much more.", 4, 1),
    ("Happy with our choice. Fair price for the quality.", 4, 2),
    ("Staff went out of their way to make our trip special. Five stars.", 5, 4),
    ("Absolutely flawless stay. The bar has been set.", 5, 2),
    ("Not a single hiccup during our entire visit. Rare.", 5, 1),
    ("Would rate higher if I could. Truly exceptional.", 5, 3),
    ("Best sleep I've had in any hotel. That mattress is magic.", 5, 2),
    ("Made our vacation even better than we imagined.", 5, 3),
    ("We felt welcomed and valued as guests. That means everything.", 5, 2),
    ("Everything was clean, comfortable, and well thought out.", 5, 1),
    ("A+ experience. Already left a review everywhere I could.", 5, 2),
    ("This hotel just gets it right. Consistently great.", 5, 3),
    ("Perfect hotel for couples. Romantic, clean, great food.", 5, 2),
    ("Staff treated us like VIPs even though we booked a standard room.", 5, 3),
    ("The whole experience felt premium. Well worth the price.", 5, 2),
    ("Checked in, relaxed, enjoyed. Exactly what a hotel should be.", 5, 1),
    ("10/10 would recommend. Flawless from start to finish.", 5, 2),
]


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS google_reviews")
    cur.execute("""CREATE TABLE google_reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        reviewer_name TEXT NOT NULL, review_text TEXT NOT NULL,
        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        review_date TEXT NOT NULL, likes INTEGER DEFAULT 0,
        review_source TEXT DEFAULT 'Google', branch_name TEXT NOT NULL,
        hotel_response TEXT, is_resolved TEXT DEFAULT 'No',
        resolved_date TEXT, time_resolved TEXT
    )""")

    cur.execute("DROP TABLE IF EXISTS admin_config")
    cur.execute("""CREATE TABLE admin_config (
        config_id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_name TEXT NOT NULL, review_source TEXT NOT NULL,
        api_key TEXT, place_id TEXT, last_refresh TEXT, is_active INTEGER DEFAULT 1
    )""")

    configs = [
        ("New York Inn","Google","AIzaSyDxR3k_FAKE_ny_12345","ChIJN1t_tDeuEmsR",None,1),
        ("New York Inn","Yelp","yelp_bearer_FAKE_ny_abc","new-york-inn-manhattan",None,1),
        ("Miami Qualis","Google","AIzaSyDxR3k_FAKE_mi_67890","ChIJrTLr-GyuEmsR",None,1),
        ("Miami Qualis","TripAdvisor","ta_FAKE_mi_xyz789","d12345678",None,1),
        ("Atlanta Express","Google","AIzaSyDxR3k_FAKE_atl_11111","ChIJIQBpAG2ahYAR",None,1),
        ("Atlanta Express","Yelp","yelp_bearer_FAKE_atl_def","atlanta-express-hotel",None,1),
        ("SFO Residency","Google","AIzaSyDxR3k_FAKE_sfo_22222","ChIJIQBpAG2a_SFO",None,1),
        ("SFO Residency","TripAdvisor","ta_FAKE_sfo_qrs456","d87654321",None,1),
    ]
    cur.executemany("INSERT INTO admin_config (branch_name,review_source,api_key,place_id,last_refresh,is_active) VALUES(?,?,?,?,?,?)", configs)

    names = ["James","Maria","Priya","Wei","Ahmed","Sarah","Raj","Emily","Carlos",
             "Aisha","David","Fatima","Kenji","Anna","Omar","Lisa","Vikram","Sophie",
             "Hassan","Rachel","Arjun","Elena","Chen","Nadia","Thomas","Deepa",
             "Grace","Ali","Megan","Ravi","Yuki","John","Zara","Michael","Ananya",
             "Pedro","Chloe","Tariq","Julia","Sana","Diego","Kavita","Liam","Mei"]
    initials = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    start = datetime(2026, 3, 9); end = datetime(2026, 4, 12)
    days = (end - start).days

    pos_resp = ["Thank you for your wonderful review! We look forward to welcoming you back!",
                "We truly appreciate your kind words.",
                "Lovely review — we'll pass compliments to the team!"]
    neg_resp = ["We sincerely apologize. Escalated to management. Please contact guestservices@hotel.com.",
                "This does not meet our standards. Taking immediate action.",
                "We're sorry. Issues addressed with our teams.",
                "Refund processed — should appear within 5-7 business days."]

    rows = []
    for text, rating, ml in REVIEWS:
        nm = f"{random.choice(names)} {random.choice(initials)}."
        dt = start + timedelta(days=random.randint(0, days), hours=random.randint(6,23), minutes=random.randint(0,59))
        ds = dt.strftime("%Y-%m-%d %H:%M:%S")
        lk = random.randint(0, min(4, ml)) if random.random() < 0.6 else random.randint(0, ml)
        br = random.choice(BRANCHES); src = random.choice(SOURCES)
        hr, ir, rd, tr = None, "No", None, None
        if rating >= 4 and random.random() < 0.6:
            hr = random.choice(pos_resp); ir = "Yes"
            rd = (dt + timedelta(days=random.randint(1,3))).strftime("%Y-%m-%d %H:%M:%S")
        elif rating <= 2 and random.random() < 0.4:
            hr = random.choice(neg_resp)
            if random.random() < 0.6:
                ir = "Yes"
                rd = (dt + timedelta(days=random.randint(2,10))).strftime("%Y-%m-%d %H:%M:%S")
                tr = rd
        elif rating == 3 and random.random() < 0.3:
            hr = "Thank you for your feedback."
            ir = "Yes"; rd = (dt + timedelta(days=random.randint(1,5))).strftime("%Y-%m-%d %H:%M:%S")
        rows.append((nm, text, rating, ds, lk, src, br, hr, ir, rd, tr))

    cur.executemany("INSERT INTO google_reviews (reviewer_name,review_text,rating,review_date,likes,review_source,branch_name,hotel_response,is_resolved,resolved_date,time_resolved) VALUES(?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    
    # Verify avg
    cur.execute("SELECT AVG(rating) FROM google_reviews")
    avg = cur.fetchone()[0]
    print(f"Created {DB_PATH}: {len(rows)} reviews, avg rating {avg:.2f}")
    conn.close()

if __name__ == "__main__":
    create_database()
