"""Venue-specific checks against the saved fixtures (recorded 2026-11-23)."""
from datetime import date, datetime

from conftest import FIXTURE_DATE, FIXTURES, load_fixture
from scrapers import melkweg, paradiso, zwijger
from scrapers.base import TZ


def by_title(events, needle):
    hits = [e for e in events if needle.lower() in e.title.lower()]
    assert hits, f"no event matching {needle!r}"
    return hits[0]


def test_paradiso():
    events = paradiso.parse(load_fixture("paradiso"), FIXTURE_DATE)
    venues = {e.venue for e in events}
    assert {"Paradiso", "Tolhuistuin", "Bitterzoet"} <= venues  # one scraper covers all three
    e = by_title(events, "Mighty Oaks")
    assert e.venue == "Tolhuistuin"
    assert e.title == "Mighty Oaks + June Carousel"
    assert e.start == datetime(2026, 11, 23, 19, 30, tzinfo=TZ)
    assert e.url.startswith("https://www.paradiso.nl/programma/")
    assert any(x.status == "sold_out" for x in events)


def test_melkweg():
    events = melkweg.parse(load_fixture("melkweg"), FIXTURE_DATE)
    e = by_title(events, "Techno Tuesday")
    assert e.category == "club"
    assert e.start == datetime(2026, 11, 24, 23, 30, tzinfo=TZ)  # 22:30 UTC
    assert e.url == "https://www.melkweg.nl/nl/agenda/techno-tuesday-24-11-2026"
    statuses = {x.status for x in events}
    assert {"sold_out", "cancelled"} <= statuses
    expo = by_title(events, "No Need To Pretend")
    assert expo.kind == "series" and expo.end.date() == date(2026, 12, 30)


def test_zwijger_dates():
    today = FIXTURE_DATE
    assert zwijger.parse_when("Vandaag, 20.00", today) == datetime(2026, 11, 23, 20, 0, tzinfo=TZ)
    assert zwijger.parse_when("Morgen, 19.00", today) == datetime(2026, 11, 24, 19, 0, tzinfo=TZ)
    assert zwijger.parse_when("do 26 nov, 19.30", today) == datetime(2026, 11, 26, 19, 30, tzinfo=TZ)
    # yearless date in January rolls over to next year
    assert zwijger.parse_when("di 12 jan, 20.00", today).year == 2027


def test_zwijger():
    events = zwijger.parse(load_fixture("zwijger"), FIXTURE_DATE)
    assert len(events) >= 20
    e = by_title(events, "Terug naar de toekomst")
    assert e.title.startswith("AAN TAFEL! presenteert")
    assert e.start == datetime(2026, 11, 24, 20, 0, tzinfo=TZ)
    assert e.category == "talk"
    q = by_title(events, "Queer Poetry Night")
    assert q.title.count("Queer Poetry Night") == 1


def test_occii():
    from scrapers import occii
    events = occii.parse(load_fixture("occii"), FIXTURE_DATE)
    codeine = by_title(events, "CODEINE")
    assert codeine.title.startswith("CODEINE") and codeine.status == "sold_out"
    assert by_title(events, "JAWBREAKER").category == "film"
    assert by_title(events, "DRAW NAKED PEOPLE").category == "other"
    assert by_title(events, "DIS FIG").category == "music"
    assert by_title(events, "DIS FIG").start == datetime(2026, 12, 3, 20, 0, tzinfo=TZ)


def test_koepel_cinemas_only_specials():
    from scrapers import filmhallen, themovies
    fh = filmhallen.parse(load_fixture("filmhallen"), FIXTURE_DATE)
    nineties = by_title(fh, "Nineties")
    assert nineties.kind == "series" and nineties.end > nineties.start and "39 films" in nineties.subtitle
    assert not any("Première" in e.title or "+Extra" in e.title for e in fh), "regular releases must be skipped"
    nut = by_title(fh, "De Notenkraker (LIVE)")
    assert nut.category == "theatre" and nut.start == datetime(2026, 12, 1, 20, 0, tzinfo=TZ)
    tm = themovies.parse(load_fixture("themovies"), FIXTURE_DATE)
    assert {e.title for e in tm if e.kind == "event"} >= {"Fjord (Preview)", "Dune: Part Three (Preview)"}
    assert all(len(e.subtitle.split(",")) >= 2 for e in tm if e.kind == "series")


def test_debalie():
    from scrapers import debalie
    events = debalie.parse(load_fixture("debalie"), FIXTURE_DATE)
    e = by_title(events, "Na het einde van de geschiedenis")
    assert e.start == datetime(2026, 11, 23, 20, 0, tzinfo=TZ)  # raw says +00:00 but means local time
    assert e.category == "talk" and not e.all_day
    assert by_title(events, "Nationaal Gesprek over Vrijheid").all_day
    assert by_title(events, "CinéConcert: Zare").category == "film"
    assert not any(e.title == "Naza" for e in events), "regular cinema screenings must be skipped"
    assert any(e.status == "sold_out" for e in events)


def test_felixmeritis():
    from scrapers import felixmeritis
    assert felixmeritis.parse_time("8PM").hour == 20 and felixmeritis.parse_time("19.30").minute == 30
    events = felixmeritis.parse(load_fixture("felixmeritis"), FIXTURE_DATE)
    m = by_title(events, "Morpheus")
    assert m.start == datetime(2026, 11, 27, 20, 0, tzinfo=TZ)
    assert by_title(events, "Never Just Hair").category == "talk"  # 'book club' is not a club night


def test_ot301():
    from scrapers import ot301
    events = ot301.parse(load_fixture("ot301"), FIXTURE_DATE)
    assert not any(e.title == "Lunch at Café Gilde" and e.kind == "event" for e in events), "lunch → one weekly item"
    assert {"film", "club"} <= {e.category for e in events}
    assert all(e.url.startswith("https://www.ot301.nl/agenda/") for e in events)


def test_rodehoed():
    from scrapers import rodehoed
    events = rodehoed.parse(load_fixture("rodehoed"), FIXTURE_DATE)
    e = by_title(events, "verborgen verleden van Oekra")
    assert e.start == datetime(2026, 11, 27, 20, 0, tzinfo=TZ)
    assert e.status == "sold_out" and e.price == "€ 15"
    assert by_title(events, "Jingle Bells").category == "music"


def test_nieuweanita():
    from scrapers import nieuweanita
    # weekday + yearless date pins the year
    assert nieuweanita.resolve_date("Sunday", "January 24", FIXTURE_DATE) == date(2027, 1, 24)
    assert nieuweanita.resolve_date("Saturday", "September 19", FIXTURE_DATE) == date(2026, 9, 19)
    events = nieuweanita.parse(load_fixture("nieuweanita"), FIXTURE_DATE)
    t = by_title(events, "Turkish movie night")
    assert t.start == datetime(2027, 1, 24, 19, 30, tzinfo=TZ) and t.category == "film"
    assert by_title(events, "Vinylbingo").category == "other"
    assert by_title(events, "Silent But Violent").category == "club"
    assert not any(e.title == "Timm Knipt!" for e in events)
    assert by_title(events, "Backroom Blues").category == "music"


def test_lab111_post_page():
    """LAB111 is disabled (bot check) but its parser is tested on a post page saved during recon."""
    from scrapers import lab111
    rows, _ = lab111._rows((FIXTURES / "lab111_post.html").read_text(encoding="utf-8"))
    raw = [{"id": 1, "link": "https://www.lab111.nl/dune-part-one-two-double-bill-incl-lunch/",
            "title": "Dune: Part One &#038; Two (Double Bill incl. lunch)", "categories": [79], "image": None,
            "rows": rows}]
    (e,) = lab111.parse(raw, FIXTURE_DATE)
    assert e.title == "Dune: Part One & Two (Double Bill incl. lunch)"
    assert e.start == datetime(2026, 12, 13, 12, 0, tzinfo=TZ)
    assert e.status == "sold_out" and e.subtitle == "LAB 2"


def test_jazzin():
    from scrapers import jazzin
    events = jazzin.parse(load_fixture("jazzin"), FIXTURE_DATE)
    e = by_title(events, "Chris Potter Trio")
    assert e.venue == "Bimhuis" and e.price == "€20" and e.category == "jazz"
    assert e.start == datetime(2026, 11, 23, 20, 30, tzinfo=TZ)
    venues = {x.venue for x in events}
    assert "Melkweg" not in venues and "OCCII" not in venues  # covered by own scrapers
    assert "theater De Richel" not in venues and "Theater De Richel" in venues


def test_cavia():
    from scrapers import cavia
    events = cavia.parse(load_fixture("cavia"), FIXTURE_DATE)
    e = by_title(events, "Six short movies")
    assert e.title.startswith("Palestine Cinema Days")
    assert e.start == datetime(2026, 11, 2, 18, 30, tzinfo=TZ) and e.subtitle == "Special"
    assert e.url.endswith("/programma/palestine-cinema-days-around-world")
    c = by_title(events, "Caligari")
    assert c.start == datetime(2026, 12, 12, 20, 0, tzinfo=TZ) and c.category == "film"
    assert cavia.month_urls(date(2026, 12, 5))[1] == ("https://www.filmhuiscavia.nl/programma/januari-2027", 2027)


def test_rialto():
    from scrapers import rialto
    events = rialto.parse(load_fixture("rialto"), FIXTURE_DATE)
    shaw = by_title(events, "Rumble in Hong Kong with the Shaw Brothers")
    assert shaw.kind == "series" and shaw.end > shaw.start
    assert not any(e.title == "Klassiek" for e in events), "standing line, not a series"
    vp = [e for e in events if "Voorpremière" in e.title]
    assert vp and all(e.status == "sold_out" for e in vp)
    assert not any(e.start.hour == 0 and e.kind == "event" for e in events), "no 'verwacht' placeholders"


def test_peppered_theatres():
    from scrapers import bellevue, frascati, kleinekomedie
    kk = kleinekomedie.parse(load_fixture("kleinekomedie"), FIXTURE_DATE)
    bros = by_title(kk, "BRO'S")
    assert bros.start == datetime(2026, 11, 24, 20, 15, tzinfo=TZ)  # from data-event-start
    assert bros.price == "€ 10,75–€ 25,00" and bros.category == "theatre"
    assert by_title(kk, "Micha Wertheim").kind == "series"
    kiem = [e for e in kk if e.title == "KIEM"]
    assert kiem and all(e.kind == "event" for e in kiem), "monthly recurring show is not a run"
    bv = bellevue.parse(load_fixture("bellevue"), FIXTURE_DATE)
    assert by_title(bv, "Houden het luchtig").status == "cancelled"
    assert by_title(bv, "Harlekino").kind == "series"
    fr = frascati.parse(load_fixture("frascati"), FIXTURE_DATE)
    assert by_title(fr, "All before death is life").start == datetime(2026, 11, 24, 19, 30, tzinfo=TZ)


def test_ita():
    from scrapers import ita
    events = ita.parse(load_fixture("ita"), FIXTURE_DATE)
    incident = [e for e in events if e.title == "Het incident"]
    assert len(incident) > 3 and all(e.kind == "event" for e in incident)  # every performance listed
    m = [e for e in events if e.title == "Mefisto"]
    assert m and m[0].start == datetime(2026, 12, 3, 19, 30, tzinfo=TZ)
    assert by_title(events, "Dirk De Wachter").status == "sold_out" and by_title(events, "Dirk De Wachter").category == "talk"


def test_kriterion_and_eye():
    from scrapers import eye, kriterion
    k = kriterion.parse(load_fixture("kriterion"), FIXTURE_DATE)
    assert {e.title for e in k} == {"Sneak Preview", "Pandemonium (late night)"}  # specials only
    ey = eye.parse(load_fixture("eye"), FIXTURE_DATE)
    assert all(e.kind == "series" for e in ey) and not any(e.title == "Eye Classics" for e in ey)
    seidl = by_title(ey, "Ulrich Seidl")
    assert seidl.start.date() == date(2026, 9, 19) and seidl.end.date() == date(2027, 1, 31)


def test_peppered_skips_performances_elsewhere():
    from scrapers import bellevue, kleinekomedie
    bv = bellevue.parse(load_fixture("bellevue"), FIXTURE_DATE)
    kk = kleinekomedie.parse(load_fixture("kleinekomedie"), FIXTURE_DATE)
    assert not any(e.title == "KIEM" for e in bv), "KIEM plays at sister venue Kleine Komedie"
    assert any(e.title == "KIEM" for e in kk)
    (teckel,) = [e for e in bv if e.title == "Teckel"]
    # tour dates elsewhere (De Schuur, Haarlem; Podium Mozaiek, Amsterdam) are skipped, and the
    # September festival reprise doesn't stretch the run
    assert teckel.start.date() == date(2027, 3, 11) and teckel.end.date() == date(2027, 4, 5)


def test_weticket_venues():
    from scrapers import garagenoord, skatecafe
    sk = skatecafe.parse(load_fixture("skatecafe"), FIXTURE_DATE)
    d = by_title(sk, "DRUKWERK")
    assert d.title.startswith("DRUKWERK") and d.status == "sold_out"
    assert d.start == datetime(2026, 11, 26, 18, 0, tzinfo=TZ)  # feed is UTC
    assert by_title(sk, "SKATELES VOOR KIDS").category == "other"
    gn = garagenoord.parse(load_fixture("garagenoord"), FIXTURE_DATE)
    assert sum(e.category == "club" for e in gn) >= len(gn) - 2  # (daytime sound system = music)
    assert by_title(gn, "Kynant").start == datetime(2026, 11, 28, 23, 30, tzinfo=TZ)


def test_fchyena_specials_only():
    from scrapers import fchyena
    assert fchyena.nth_weekday(2026, 12, 1, 3) == date(2026, 12, 15)  # third Tuesday
    events = fchyena.parse(load_fixture("fchyena"), FIXTURE_DATE)
    scream = by_title(events, "Hyena Scream")
    assert scream.start == datetime(2026, 11, 30, 11, 0, tzinfo=TZ) and "Paper Tiger" in scream.title
    sneaks = [e for e in events if "sneak" in e.title.lower()]
    assert [e.start.date() for e in sneaks] == [date(2026, 12, 15), date(2027, 1, 19)] and sneaks[0].all_day


def test_ingang():
    from scrapers import ingang
    events = ingang.parse(load_fixture("ingang"), FIXTURE_DATE)
    e = by_title(events, "Second Night")
    assert e.venue == "Ingang" and e.start.date() == date(2026, 11, 28)


def test_nachbar_and_voorwaarts():
    from scrapers import cafevoorwaarts, nachbar
    n = nachbar.parse(load_fixture("nachbar"), FIXTURE_DATE)
    e = by_title(n, "Sweetlips")
    assert e.start == datetime(2026, 12, 3, 23, 59, tzinfo=TZ) and e.category == "club" and e.price == "€ 8,75"
    v = cafevoorwaarts.parse(load_fixture("cafevoorwaarts"), FIXTURE_DATE)
    expo = by_title(v, "Arjen van Opstal")
    assert expo.all_day and expo.kind == "series" and expo.end.date() == date(2026, 11, 28)  # exclusive DTEND


def test_food_weekly_and_aa_network():
    from scrapers import amsterdamalternative as aa, ot301, recurring
    o = ot301.parse(load_fixture("ot301"), FIXTURE_DATE)
    lunch = [e for e in o if e.title == "Lunch at Café Gilde"]
    assert len(lunch) == 1 and lunch[0].kind == "weekly" and lunch[0].category == "food"
    assert lunch[0].subtitle.startswith("Elke wo, do, vr, za 12:00")
    net = aa.parse(load_fixture("amsterdamalternative"), FIXTURE_DATE)
    venues = {e.venue for e in net}
    assert {"Cinetol", "Plein Theater", "Teatro Munganga"} <= venues
    assert not venues & {"OT301", "OCCII", "Filmhuis Cavia", "De Nieuwe Anita"}, "own scrapers win"
    assert not any("Zaandam" in v for v in venues)
    assert by_title(net, "Eetcafé ADM Noord").kind == "weekly"
    sering = by_title(recurring.parse(load_fixture("recurring"), FIXTURE_DATE), "Community Kitchen")
    assert sering.venue == "De Sering" and sering.kind == "weekly" and sering.category == "food"


def test_weekly_items_not_in_ics():
    from ics import to_ics
    from scrapers import recurring
    text = to_ics(recurring.parse(load_fixture("recurring"), FIXTURE_DATE), datetime(2026, 11, 23, tzinfo=TZ))
    assert "BEGIN:VEVENT" not in text


def test_carre():
    from scrapers import carre
    events = carre.parse(load_fixture("carre"), FIXTURE_DATE)
    jj = [e for e in events if e.title == "Joe Jackson 2026"]
    assert jj and jj[0].start == datetime(2026, 12, 1, 20, 0, tzinfo=TZ) and jj[0].category == "music"
    assert jj[0].status == "sold_out"
    circus = by_title(events, "Wereldkerstcircus")
    assert circus.kind == "series" and circus.end.date() == date(2027, 1, 3)


def test_tolhuistuin_own_programme():
    from scrapers import tolhuistuin
    events = tolhuistuin.parse(load_fixture("tolhuistuin"), FIXTURE_DATE)
    assert not any(e.title in ("Dave Lofts", "Mighty Oaks") for e in events), "Paradiso concerts come via paradiso"
    fair = by_title(events, "Colourful Noord Winter Fair")
    assert fair.start == datetime(2026, 12, 20, 12, 0, tzinfo=TZ) and fair.price == "gratis"
    assert by_title(events, "Toegankelijk uitgaansfeest").category == "club"


def test_radar_venues():
    from scrapers import joesgarage, vrankrijk
    vk = vrankrijk.parse(load_fixture("vrankrijk"), FIXTURE_DATE)
    pirate = [e for e in vk if e.title == "Friday Pirate Kitchen and Punk Night"]
    assert len(pirate) == 1 and pirate[0].kind == "weekly" and pirate[0].category == "food"
    assert pirate[0].subtitle == "Elke vr 19:00"
    jg = joesgarage.parse(load_fixture("joesgarage"), FIXTURE_DATE)
    voku = by_title(jg, "Benefit voku")
    assert voku.category == "food" and voku.start == datetime(2026, 11, 23, 19, 0, tzinfo=TZ)
    assert not any("Kraakspreekuur" in e.title for e in jg), "office hours are skipped"
    assert all(e.venue in ("Vrankrijk", "Joe's Garage") for e in vk + jg)


def test_new_clubs_and_venues():
    from scrapers import brakkegrond, jazzin, lofi, mezrab, radion, sexyland, thuishaven
    from scrapers.base import guess_category
    assert guess_category("Club Amsterdam Klezmer Band") != "club"  # 'club' alone is not a club night
    klez = by_title(mezrab.parse(load_fixture("mezrab"), FIXTURE_DATE), "Klezmer")
    assert klez.category == "music"
    th = thuishaven.parse(load_fixture("thuishaven"), FIXTURE_DATE)
    jm = by_title(th, "Jeff Mills")
    assert jm.start == datetime(2026, 11, 28, 13, 0, tzinfo=TZ) and jm.price == "€34,50" and jm.subtitle == "Techno"
    assert by_title(th, "Jamback").status == "sold_out"
    ra = radion.parse(load_fixture("radion"), FIXTURE_DATE)
    assert by_title(ra, "Labyrinth").start == datetime(2026, 11, 27, 23, 0, tzinfo=TZ)
    lo = lofi.parse(load_fixture("lofi"), FIXTURE_DATE)
    assert by_title(lo, "Dax J").all_day and all(e.category == "club" for e in lo)
    bg = brakkegrond.parse(load_fixture("brakkegrond"), FIXTURE_DATE)
    assert not any("Residentie" in (e.subtitle or "") for e in bg)
    assert by_title(bg, "BauGrond").start == datetime(2026, 11, 27, 19, 30, tzinfo=TZ)  # time from ticket API
    (sx,) = sexyland.parse(load_fixture("sexyland"), FIXTURE_DATE)
    assert sx.start == datetime(2026, 12, 16, 19, 0, tzinfo=TZ) and "Café de Krom" in sx.subtitle
    yayang = by_title(jazzin.parse(load_fixture("jazzin"), FIXTURE_DATE), "Restaurant: Yayang")
    assert yayang.category == "food" and yayang.venue == "Zaal 100"


def test_radar_food_venues():
    from scrapers import mkz, mollichaoot
    m = mkz.parse(load_fixture("mkz"), FIXTURE_DATE)
    eet = [e for e in m if e.title == "MKZ Eetcafé"]
    assert len(eet) == 1 and eet[0].kind == "weekly" and eet[0].category == "food" and eet[0].price == "€5"
    voku = by_title(mollichaoot.parse(load_fixture("mollichaoot"), FIXTURE_DATE), "Vegan Voku")
    assert voku.kind == "weekly" and voku.category == "food" and voku.subtitle == "Elke di 18:00"
