from src.filters import distance_km, distance_to_target, matches_target, normalize

# ISIMA / campus des Cézeaux
ISIMA = (45.7590, 3.1110)


def test_normalize_strips_accents_and_case():
    assert normalize("AUBIÈRE") == "aubiere"
    assert normalize("Clermont-Ferrand") == "clermont-ferrand"


def test_aubiere_matches_in_any_case_and_accents(make_item):
    for city in ("Aubière", "AUBIERE", "aubiere", "AUBIÈRE"):
        item = make_item(address=f"12 avenue de l'Université {city}")
        assert matches_target(item), city


def test_clermont_ferrand_matches(make_item):
    assert matches_target(make_item(address="25 rue Étienne Dolet CLERMONT-FERRAND"))
    assert matches_target(make_item(address="25 rue Étienne Dolet Clermont Ferrand"))


def test_target_zip_matches_even_without_city_name(make_item):
    assert matches_target(make_item(address="10 rue des Liondards 63000"))
    assert matches_target(make_item(address="1 avenue de Lattre 63170"))


def test_clermont_l_herault_does_not_match(make_item):
    item = make_item(address="5 place de la Gare 34800 CLERMONT-L'HERAULT")
    assert not matches_target(item)


def test_bare_clermont_does_not_match(make_item):
    # Clermont (Oise, 60600) is not Clermont-Ferrand.
    assert not matches_target(make_item(address="3 rue de la Croix 60600 CLERMONT"))


def test_rent_in_cents_does_not_trigger_zip(make_item):
    # 363000 cents = 3630 €; must not match zip 63000, and rent fields are
    # never scanned in the first place.
    item = make_item(address="Av. Michel Serres 47000 AGEN", rent_min=363000)
    assert not matches_target(item)


def test_zip_inside_larger_number_in_address_does_not_match(make_item):
    assert not matches_target(make_item(address="BP 363000 AGEN"))


def test_montlucon_fixture_item_does_not_match(sample_items):
    # Real trap from the captured response: residence in Montluçon whose
    # entity is "Clermont Auvergne" and whose description contains a
    # "clermont-aubiere" URL. Only address/label fields may be scanned.
    montlucon = next(i for i in sample_items if i["id"] == 581)
    assert not matches_target(montlucon)


def test_no_fixture_item_matches(sample_items):
    # The captured page contains no Clermont-Ferrand/Aubière accommodation.
    assert [i["id"] for i in sample_items if matches_target(i)] == []


def test_clermont_fd_abbreviation_matches(make_item):
    assert matches_target(make_item(address="25 rue Kessler CLERMONT-FD"))
    assert matches_target(make_item(address="25 rue Kessler Clermont Fd"))


def test_second_clermont_zip_and_aubiere_cedex_match(make_item):
    assert matches_target(make_item(address="130 avenue de Cournon 63100"))
    assert matches_target(make_item(address="BP 86 63178 CEDEX"))


def test_distance_km_isima_to_montlucon():
    # Fixture Montluçon residence is ~75 km from campus.
    d = distance_km(*ISIMA, 46.329, 2.588)
    assert 60 < d < 90


def test_geo_match_catches_unrecognizable_address(make_item):
    # Address gives no usable city/zip, but coordinates are on campus:
    # the radius check must catch it.
    item = make_item(address="1 rue de la Chebarde, Campus des Cezeaux")
    item["residence"]["location"] = {"lat": 45.758, "lon": 3.111}
    assert matches_target(item, radius_km=10)


def test_geo_does_not_match_far_location(make_item, sample_items):
    item = make_item(address="Somewhere in France")
    item["residence"]["location"] = {"lat": 46.329, "lon": 2.588}  # Montluçon
    assert not matches_target(item, radius_km=10)
    # The real Montluçon fixture item has coordinates too and must stay out.
    montlucon = next(i for i in sample_items if i["id"] == 581)
    assert not matches_target(montlucon, radius_km=10)


def test_geo_disabled_with_radius_zero(make_item):
    item = make_item(address="1 rue de la Chebarde")
    item["residence"]["location"] = {"lat": 45.758, "lon": 3.111}
    assert not matches_target(item, radius_km=0)


def test_missing_location_falls_back_to_text_only(make_item):
    item = make_item(address="12 avenue des Landais AUBIERE")
    item["residence"]["location"] = {}
    assert matches_target(item, radius_km=10)
    assert distance_to_target(item) is None
