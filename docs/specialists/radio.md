# Radio and communications

*One of MIA's specialists (DEC-0109). Written by `core/specialists.py` from its workbook (`work/specialists/radio.json`); don't edit by hand.*

Radio and how things talk: amateur (ham) radio and its licences, GMRS and FRS, Meshtastic and LoRa mesh, antennas and propagation, SDR, and keeping in touch without the internet or cell service.

**Limits:** Transmitting follows the licence and the band plan where it happens, and the note says which licence a thing needs; listening and receiving are described, never jamming or interference. Every note says where it comes from; a claim without a source isn't written. When the right answer depends on where someone lives (a code, a law, a licence), the note says so and names who to check with. Nothing about a real person's private life.

**Develops:** skills: Technology; loops: phone.link.

## Notes, not confirmed yet

### Which US two-way radios need a licence

In the US the FCC sets the rules, and each kind of radio is different.

- FRS (Family Radio Service, the blister-pack walkie-talkies): no licence. Power is capped at 2 W on most channels and 0.5 W on 8 to 14. The antenna can't be removed. (47 CFR Part 95, Subpart B)
- GMRS (General Mobile Radio Service): needs an FCC licence, but there's no exam. You apply through the FCC's ULS system. The fee is about $35 and the licence lasts 10 years. It also covers your immediate family. It allows repeaters, detachable antennas and up to 50 W. (Part 95, Subpart E)
- CB (Citizens Band, 27 MHz): no licence. Power limit is 4 W AM and 12 W PEP SSB. (Part 95, Subpart D)
- MURS (5 VHF channels near 151 to 154 MHz): no licence, 2 W. (Part 95, Subpart J)
- Amateur (ham) radio: needs a licence and an exam. There are three classes: Technician, General and Amateur Extra. Each one opens more bands. Exams are given by Volunteer Examiners, and the FCC charges $35 per application. Ham radio can't be used for business, and messages can't be coded to hide their meaning. (Part 97)
- Marine VHF: a recreational boat in US waters doesn't need a station licence. A boat going to foreign ports does. (Part 80)
- Meshtastic/LoRa on 902 to 928 MHz: no licence under Part 15 if you stick to the device limits.

Fees and details change, so check the FCC's own pages before applying. Outside the US the rules are completely different. Check with your national regulator: ISED in Canada, Ofcom in the UK, ACMA in Australia.

Sources: Code of Federal Regulations, Title 47, Part 95 (Personal Radio Services) and Part 97 (Amateur Radio Service); FCC, 'General Mobile Radio Service (GMRS)' and 'Family Radio Service (FRS)' pages, fcc.gov; FCC, 'Ship Radio Stations' page, fcc.gov (47 CFR Part 80); ARRL, 'Getting Licensed', arrl.org

### Meshtastic range and how to extend it

Meshtastic sends LoRa radio packets, on 902 to 928 MHz in the US and 868 MHz in Europe. How far one gets depends mostly on whether the two nodes have a clear line of sight. Power matters much less.

Typical ranges:
- Handheld node in a town, near the ground: often 1 to 3 km. Buildings and trees block it.
- Open ground or across water: several km.
- High point to high point (hills, towers): tens of km. Record links of hundreds of km have been made between mountaintops or with balloons.

What helps, in order:
1. Height. Get the node up high and outdoors: a roof, a mast or a window facing the other node. This beats every other fix.
2. A better antenna. Stock antennas are often poor. Use a tuned antenna for your band (915 MHz in the US), mounted vertically to match the other nodes.
3. A clear path. Keep the space around the line between the antennas (the Fresnel zone) free of obstacles, not just the line itself.
4. The mesh. Each node rebroadcasts messages. The default hop limit is 3 and can be raised to 7. One node on a hilltop set to a router role can link a whole area.
5. Modem preset. Slower presets (Long Slow) reach further but send less data. Every node in a channel must use the same preset.

Rules: the unlicensed limits come from the region you pick in the app (FCC Part 15 in the US). Licensed hams can use Meshtastic's licensed mode, which turns off encryption to follow Part 97. Always set the region to where you actually are. Elsewhere, check your national regulator.

Sources: Meshtastic documentation, meshtastic.org/docs (Overview, Radio Settings / LoRa Config, Device Roles); Semtech, 'LoRa and LoRaWAN: A Technical Overview', semtech.com; Code of Federal Regulations, Title 47, Part 15.247

### A simple half-wave dipole for 2 metres

A dipole is two equal wires or rods in a line, fed in the middle with coax.

Length: the usual formula for a half-wave dipole is length in feet = 468 / frequency in MHz. For 146 MHz, the middle of the US 2 m band (144 to 148 MHz), that comes to about 3.2 ft (97 cm) end to end. So each leg is about 19 inches (48 to 49 cm). Cut each leg a little long, about 2 cm extra, and trim it later.

Build:
1. Use two pieces of stiff wire, rod or brass tube. Mount them on a non-conductive centre block, such as plastic or a PVC tee, with a small gap between them.
2. Use 50-ohm coax. Solder the centre conductor to one leg and the braid (shield) to the other. Seal the joint against water.
3. Add a choke right at the feed point: about 5 to 8 turns of the coax coiled tightly. This keeps current off the outside of the coax. Without it, the pattern and the SWR readings both get worse.
4. Mount it vertically for FM and repeaters, which use vertical polarisation. Mount it horizontally for SSB weak-signal work. Keep it clear of metal.

Tune: measure the SWR across the band with an SWR meter or an antenna analyser such as a NanoVNA. If the dip in SWR is below where you want it, the legs are too long. Trim both legs equally, a few mm at a time. An SWR under about 1.5:1 is good. A dipole's feed impedance is around 70 ohms, so it matches 50-ohm coax well enough.

Licence: you can build one and listen with no licence. To transmit on 2 m in the US you need a Technician licence or higher (47 CFR Part 97). Band edges differ by country: Region 1 (Europe and Africa) has only 144 to 146 MHz. Check your national band plan.

Sources: ARRL Antenna Book, ARRL (American Radio Relay League), chapter on dipoles; The ARRL Handbook for Radio Communications, ARRL; Code of Federal Regulations, Title 47, Part 97.301 (amateur frequency allocations); IARU Region 1 VHF Band Plan, iaru-r1.org

## Open questions

- How do you prepare for and pass the US Technician exam, and where are exams held?
- How do repeaters work (offsets, CTCSS tones), and how do you find local ones?
- What can a beginner receive with an RTL-SDR dongle, such as weather satellites, aircraft ADS-B and NOAA weather radio?
